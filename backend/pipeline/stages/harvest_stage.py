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

Source isolation holds (Architecture Rule 1): one call per source, no source
ever sees another.
"""

import re
from typing import Any, Optional

from loguru import logger

from backend.config import get_settings
from backend.pipeline.context import PipelineContext
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

Extract 10 to 40 facts depending on how much the text actually contains.
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


def harvest_source(
    client: Any,
    source_id: str,
    title: str,
    text: str,
    mode: str = "article_fetched",
    ceiling: str = "MEDIUM",
    max_chars: Optional[int] = None,
) -> tuple[list[str], float]:
    """Harvest one source's facts in a single structured call.

    Args:
        client: A client exposing `generate_structured(prompt, schema, system,
            max_tokens)`.
        source_id: The source's stable ID.
        title: Source title, for the identity lock.
        text: The source's raw text.
        mode: Analysis mode value, for the identity lock.
        ceiling: Confidence ceiling for the source's mode.
        max_chars: Characters of text to send; defaults to the configured value.

    Returns:
        Tuple of (facts, cost in dollars).
    """
    settings = get_settings()
    limit = max_chars or settings.harvest_max_chars

    prompt = (
        _identity_block(source_id, title, mode, ceiling)
        + f"\nTEXT FROM: {title}\n\n{text[:limit]}"
    )

    data, usage = client.generate_structured(
        prompt=prompt,
        schema=HARVEST_SCHEMA,
        system=HARVEST_SYSTEM,
        max_tokens=8_000,
    )

    facts = [fact.strip() for fact in data.get("facts", []) if fact and fact.strip()]
    return facts, float(usage.get("cost", 0.0) or 0.0)


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

    from backend.integrations.anthropic_client import get_anthropic_client

    client = get_anthropic_client(model=settings.model_harvest)
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
