"""Fact harvest: one structured call per source, producing dense facts.

The semantic extraction stage produces key points, which are abstractions.
Measured on the films corpus (2026-08-16): 10,465 source words carrying 85
numbers were compressed into 1,165 brief words carrying 1 number. The document
was starved of the concrete material a researcher actually needs.

A harvest pass over the same sources produced 258 dense facts for $0.24, and
brief density went from 1.8 to 7.2 numbers per thousand words. This stage makes
that pass part of the pipeline, and its output is the inventory the Briefing's
coverage gate checks against: anything harvested that the Briefing never says
is a loss the gate reports mechanically, never a model's judgment call.

Source isolation holds (Architecture Rule 1): a source is never mixed with
another, and a source longer than one call's budget is chunked rather than
truncated (D-032). The truncating version silently dropped 34.8% of the Hawara
fixture's longest source, which the I.25 recall audit caught as a 0.0
back-of-source recall — text that was never sent to a model at all.
"""

import re
from typing import Any, Optional

from loguru import logger

from backend.config import get_settings
from backend.pipeline.context import PipelineContext
from backend.pipeline.injection_guard import delimit
from backend.pipeline.text_similarity import group_matching
from backend.state import update_job

HARVEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"facts": {"type": "array", "items": {"type": "string"}}},
    "required": ["facts"],
}

# The measured prompt (08-16), with the constitution's guardrail components
# added: identity lock, confidence ceiling, and empty-output permission.
HARVEST_SYSTEM = """You extract the concrete content of a text as dense, self-contained fact statements.

Each fact is ONE sentence that survives being read alone. Preserve every
specific: numbers with what they measure, names of people, places, works and
companies and what they did, dates, events in order, causal claims as the text
makes them.

NEVER write meta-statements ("the article argues", "a perceived decline is
characterized by"). Write the content itself: "Jurassic Park contains about 50
fully digital dinosaur shots" not "the article discusses the film's limited
CGI use". If the text argues something, state the argument's content: "Deep
focus matches human vision because both eyes keep the whole scene sharp."

{quota}
Opinions and arguments in the text ARE content: state them as what they claim.
Skip filler, greetings, sponsor reads.

EMPTY OUTPUT PERMISSION
Return an empty list if the text carries no facts. Never invent content to
fill it. Sparse and accurate beats dense and fabricated.

SOURCE ISOLATION
This text is the only thing you know about. Do not add anything you know from
elsewhere, and do not refer to other sources."""


def _identity_block(source_id: str, title: str, mode: str, ceiling: str) -> str:
    """Build the source identity lock the constitution requires on every prompt.

    Args:
        source_id: The source's stable ID.
        title: Source title.
        mode: Analysis mode value.
        ceiling: Confidence ceiling for this source's mode.

    Returns:
        The identity and ceiling block for the prompt.
    """
    return (
        "SOURCE IDENTITY LOCK - DO NOT MODIFY OR INFER\n"
        f"  source_id: {source_id}\n"
        f"  title: {title}\n"
        f"  analysis_mode: {mode}\n"
        f"  confidence_ceiling: {ceiling}\n\n"
        f"CONFIDENCE CEILING: {ceiling}\n"
        "Facts may only be as certain as this source allows. State what the "
        "text states; do not upgrade a hedge into a certainty.\n"
    )


def harvest_quota(rate: Optional[str] = None) -> str:
    """The length-scaled extraction instruction.

    "Extract 10 to 40 facts" is a FIXED range, and a model handed a fixed range
    returns a roughly fixed number whatever the input length — measured on the
    Hawara harvest, short sources yielded 40 facts per 1,000 words and long
    ones 12, a 3.3x decline that is entirely an artefact of the instruction.
    D-030 fixed the same defect in extraction by scaling the ask to the input,
    which took that pass from 39 quotes to 182 over the same six sources.

    Args:
        rate: Facts per 1,000 words as "low-high"; defaults to the configured
            value.

    Returns:
        The quota block for the system prompt.
    """
    band = rate or get_settings().harvest_facts_per_1000
    return (
        f"Extract {band} facts for every 1,000 words of the text you are given. "
        "Count the words and meet the rate — a long text carries proportionally "
        "more facts, and returning the same number for 10,000 words as for 1,000 "
        "means you summarized it instead of harvesting it.\n\n"
        "This is a floor on EFFORT, not on output. If the text genuinely does not "
        "carry that many facts, return fewer. Never repeat, pad, split one fact "
        "into two, or invent content to reach the rate."
    )


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split a source into overlapping chunks, never losing the tail.

    The overlap exists because a fact can straddle a boundary — a sentence
    that names a figure in one chunk and what it measures in the next would be
    harvested wrong from both halves. Each chunk repeats the previous chunk's
    last `overlap` characters so both readings see the whole statement.

    Args:
        text: The source's raw text.
        max_chars: Characters per chunk.
        overlap: Characters each chunk repeats from the one before it.

    Returns:
        Chunks in document order; a single chunk when the text already fits.
    """
    if len(text) <= max_chars:
        return [text] if text else []

    # An overlap at or above the chunk size would never advance.
    overlap = max(0, min(overlap, max_chars // 2))
    step = max_chars - overlap

    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + max_chars])
        start += step
    return chunks


def merge_facts(chunk_facts: list[list[str]]) -> list[str]:
    """Merge per-chunk facts, dropping the duplicates the overlap creates.

    Dedup uses the conservative `says_the_same_thing` matcher on purpose: this
    is the one place where a false match DELETES a fact, so the cost of being
    too eager is a real loss rather than a duplicate line.

    Args:
        chunk_facts: One list of facts per chunk, in document order.

    Returns:
        Facts in document order, one per distinct statement.
    """
    flat = [fact for facts in chunk_facts for fact in facts]
    if len(flat) < 2:
        return flat

    groups = group_matching([(str(i), fact) for i, fact in enumerate(flat)])
    kept: list[str] = []
    seen_groups: set[str] = set()
    for index, fact in enumerate(flat):
        group = groups.get(str(index), str(index))
        if group not in seen_groups:
            seen_groups.add(group)
            kept.append(fact)
    return kept


def harvest_source(
    client: Any,
    source_id: str,
    title: str,
    text: str,
    mode: str = "article_fetched",
    ceiling: str = "MEDIUM",
    max_chars: Optional[int] = None,
    overlap: Optional[int] = None,
) -> tuple[list[str], float]:
    """Harvest one source's facts, chunking it when it exceeds one call.

    The confidence ceiling and the identity lock are rebuilt for every chunk,
    so a chunked source carries exactly the same provenance guarantees as a
    single-call one.

    Args:
        client: A client exposing `generate_structured(prompt, schema, system,
            max_tokens)`.
        source_id: The source's stable ID.
        title: Source title, for the identity lock.
        text: The source's raw text.
        mode: Analysis mode value, for the identity lock.
        ceiling: Confidence ceiling for the source's mode.
        max_chars: Characters per call; defaults to the configured value.
        overlap: Characters of chunk overlap; defaults to the configured value.

    Returns:
        Tuple of (facts, cost in dollars).
    """
    settings = get_settings()
    limit = max_chars or settings.harvest_max_chars
    lap = settings.harvest_chunk_overlap if overlap is None else overlap

    chunks = chunk_text(text or "", limit, lap)
    if not chunks:
        return [], 0.0

    identity = _identity_block(source_id, title, mode, ceiling)
    system = HARVEST_SYSTEM.replace("{quota}", harvest_quota())
    per_chunk: list[list[str]] = []
    total_cost = 0.0

    for index, chunk in enumerate(chunks):
        part = (
            f"\n(Part {index + 1} of {len(chunks)} of this source.)"
            if len(chunks) > 1
            else ""
        )
        prompt = (
            identity
            + f"\nTEXT FROM: {title}{part}\n\n"
            + delimit(chunk, source_id)
        )
        data, usage = client.generate_structured(
            prompt=prompt,
            schema=HARVEST_SCHEMA,
            system=system,
            max_tokens=8_000,
        )
        per_chunk.append(
            [fact.strip() for fact in data.get("facts", []) if fact and fact.strip()]
        )
        total_cost += float(usage.get("cost", 0.0) or 0.0)

    merged = merge_facts(per_chunk)
    if len(chunks) > 1:
        raw = sum(len(f) for f in per_chunk)
        logger.info(
            f"{source_id}: {len(chunks)} chunks, {raw} facts -> {len(merged)} after "
            f"overlap dedup"
        )
    return merged, total_cost


def fact_id(source_id: str, index: int) -> str:
    """Build a globally unique ID for a harvested fact.

    Args:
        source_id: Owning source.
        index: 0-based position in that source's harvest.

    Returns:
        An ID of the form `SRC_3:F_1`.
    """
    return f"{source_id}:F_{index + 1}"


def build_inventory(harvest: dict[str, list[str]]) -> list[dict]:
    """Turn per-source facts into the flat inventory the gates read.

    Args:
        harvest: Map of source_id to that source's facts.

    Returns:
        List of dicts with `fact_id`, `source_id`, `text`, and `has_number`.
    """
    return [
        {
            "fact_id": fact_id(source_id, index),
            "source_id": source_id,
            "text": text,
            "has_number": bool(re.search(r"\d", text)),
        }
        for source_id, facts in harvest.items()
        for index, text in enumerate(facts)
    ]


def stage_harvest(ctx: PipelineContext) -> None:
    """Pipeline stage: harvest dense facts from every source.

    Stores `harvest` (source_id to facts) and `harvest_inventory` (flat, with
    IDs) on the context. A source that fails to harvest is a warning, not a
    failed job: the coverage gate then reports what it could not check.

    Args:
        ctx: Pipeline context carrying `source_identity_packages`.
    """
    settings = get_settings()
    if not settings.harvest_enabled:
        logger.info(f"[{ctx.job_id}] Fact harvest disabled by config")
        return

    packages = [
        pkg for pkg in getattr(ctx, "source_identity_packages", [])
        if (pkg.content or "").strip()
    ]
    if not packages:
        logger.info(f"[{ctx.job_id}] Fact harvest: no sources with text")
        return

    update_job(ctx.job_id, stage="fact_harvest")

    from backend.integrations.structured_client import get_structured_client

    # Provider-agnostic (D-034): the harvest slot is env-driven like the rest.
    client = get_structured_client(settings.model_harvest)
    harvest: dict[str, list[str]] = {}
    total_cost = 0.0

    for pkg in packages:
        try:
            facts, cost = harvest_source(
                client=client,
                source_id=pkg.source_id,
                title=pkg.title or "Untitled",
                text=pkg.content or "",
                mode=getattr(pkg.analysis_mode, "value", str(pkg.analysis_mode)),
                ceiling=_ceiling_for(pkg),
            )
        except Exception as e:
            logger.warning(f"[{ctx.job_id}] Harvest failed for {pkg.source_id}: {e}")
            ctx.add_warning(f"Fact harvest failed for {pkg.source_id}: {e}")
            continue

        harvest[pkg.source_id] = facts
        total_cost += cost
        logger.info(f"[{ctx.job_id}] {pkg.source_id}: harvested {len(facts)} facts")

    ctx.harvest = harvest
    ctx.harvest_inventory = build_inventory(harvest)
    if ctx.cost_tracker and total_cost:
        ctx.add_cost("fact_harvest", total_cost)

    with_numbers = sum(1 for fact in ctx.harvest_inventory if fact["has_number"])
    logger.info(
        f"[{ctx.job_id}] Fact harvest: {len(ctx.harvest_inventory)} facts from "
        f"{len(harvest)} sources, {with_numbers} carrying numbers, ${total_cost:.2f}"
    )


def _ceiling_for(package: Any) -> str:
    """Read the confidence ceiling that applies to a source's analysis mode.

    Args:
        package: A source identity package.

    Returns:
        The ceiling name, defaulting to MEDIUM when the mode is unknown.
    """
    from backend.models.semantic_units import AnalysisMode

    ceilings = {
        AnalysisMode.TRANSCRIPT_GROUNDED: "HIGH",
        AnalysisMode.ARTICLE_FETCHED: "HIGH",
        AnalysisMode.CAPTION_GROUNDED: "MEDIUM",
        AnalysisMode.TEXT_PROVIDED: "MEDIUM",
        AnalysisMode.OCR_EXTRACTED: "MEDIUM",
        AnalysisMode.VIDEO_ONLY: "LOW",
    }
    return ceilings.get(getattr(package, "analysis_mode", None), "MEDIUM")
