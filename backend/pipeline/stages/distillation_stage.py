"""Distillation Stage - synthesis output becomes the canonical Claim Graph.

Runs after semantic synthesis. Consumes the extracted structure (key points,
themes, tensions, gaps) plus source metadata and produces one Claim Graph that
every downstream document is then a projection of.

Based on: plans/260814-claim-graph-briefing/spec.md Section 5, EXECUTION-PLAN P1
Consumes: ctx.semantic_extractions, ctx.synthesized_themes, ctx.identified_gaps
Produces: ctx.claim_graph, ctx.outputs["claim_graph"]

Failure policy (operating contract 0.4): on schema-invalid output this stage
retries ONCE on the escalation model and then fails honestly. It never repairs
by invention and never emits a partial graph, because a downstream document
that silently drops half its evidence is worse than a job that says it failed.
"""

import json
from typing import Any, Optional

from loguru import logger
from pydantic import ValidationError

from backend.config import get_settings
from backend.models.claim_graph import (
    ClaimGraph,
    api_json_schema,
    normalize_wire_payload,
)
from backend.models.semantic_units import ConfidenceLevel
from backend.pipeline.context import PipelineContext
from backend.pipeline.formatters.briefing_formatter import render_briefing
from backend.pipeline.prompts.distillation_prompt import (
    DISTILLATION_ROLE,
    build_distillation_prompt,
)
from backend.pipeline.style_enforcer import lint_rendered_document
from backend.state import update_job

# Output ceiling for the distillation call. Measured, not guessed: a 15-claim
# graph with prose fields, story goods and holes truncated at 32K on the
# fixture, so the ceiling is doubled. Sonnet 5's tokenizer also emits roughly
# 30% more tokens for the same text than earlier models. Streaming is required
# above ~16K, which the client handles.
DISTILL_MAX_TOKENS = 64_000

# Categorical source ceilings (Architecture Rule 4) mapped onto the graph's
# 1-5 confidence grades. The best ceiling in the corpus sets the cap.
_CEILING_TO_GRADE = {
    ConfidenceLevel.HIGH: 5,
    ConfidenceLevel.MEDIUM: 4,
    ConfidenceLevel.LOW: 2,
}


def confidence_ceiling_grade(
    ceilings: list[ConfidenceLevel], verification_rate: float
) -> int:
    """Return the maximum confidence grade any claim may carry.

    The best source ceiling in the corpus sets the cap, since one strong source
    can support a strong claim. An entirely unverified corpus drops the cap by
    one so that "nothing we quoted could be checked" cannot present as settled.

    Args:
        ceilings: Per-source confidence ceilings from the analysis modes.
        verification_rate: Fraction of quotes verified, 0.0 to 1.0.

    Returns:
        Maximum allowed confidence grade, 1 to 5.
    """
    if not ceilings:
        return 2

    grade = max(_CEILING_TO_GRADE.get(c, 2) for c in ceilings)
    if verification_rate <= 0.0:
        grade -= 1
    return max(1, min(5, grade))


def build_corpus(
    topic: str,
    sources: list[dict],
    key_points: list[dict],
    themes: list[dict],
    tensions: list[dict],
    gaps: list[dict],
    semantic_core: Optional[str] = None,
) -> dict:
    """Assemble the distillation input.

    Key points are namespaced by source because their IDs are per-source and
    collide across sources. The fixture job has 40 key points sharing only 14
    distinct IDs, so a bare ID is not an identity here.

    Args:
        topic: Research topic.
        sources: Source ledger entries (source_id, title, type, status).
        key_points: Key points, each carrying its own source_ids.
        themes: Cross-source themes.
        tensions: Detected tensions.
        gaps: Identified gaps.
        semantic_core: The synthesis stage's core statement, if present.

    Returns:
        A JSON-serializable corpus dict.
    """
    namespaced_points = []
    for kp in key_points:
        source_ids = kp.get("source_ids") or []
        primary = source_ids[0] if source_ids else "UNKNOWN"
        namespaced_points.append(
            {
                # Unique across the corpus; the bare ID is not.
                "ref": f"{primary}:{kp.get('key_point_id', '?')}",
                "statement": kp.get("statement", ""),
                "source_ids": source_ids,
                "confidence": kp.get("confidence"),
            }
        )

    return {
        "topic": topic,
        "semantic_core": semantic_core,
        "sources": [
            {
                "source_id": s.get("source_id"),
                "title": s.get("title"),
                "type": s.get("source_type") or s.get("type"),
                "status": s.get("status"),
                "creator": s.get("creator"),
                "published": s.get("published"),
            }
            for s in sources
        ],
        "key_points": namespaced_points,
        "themes": [
            {
                "label": t.get("label"),
                "description": t.get("description"),
                "sources_supporting": t.get("sources_supporting") or [],
                "is_consensus": t.get("is_consensus", False),
            }
            for t in themes
        ],
        "tensions": [
            {
                "label": t.get("label"),
                "description": t.get("description"),
                "source_ids": t.get("source_ids") or [],
                "is_cross_source": t.get("is_cross_source", False),
            }
            for t in tensions
        ],
        "gaps": [
            {
                "label": g.get("label"),
                "description": g.get("description"),
                "why_expected": g.get("why_expected"),
                "suggested_research_direction": g.get("suggested_research_direction"),
            }
            for g in gaps
        ],
    }


def distill_corpus(
    job_id: str,
    corpus: dict,
    max_confidence_grade: int,
    verification_rate: float,
    known_source_ids: set[str],
) -> tuple[ClaimGraph, list[dict]]:
    """Run the distillation call and validate the resulting graph.

    Retries once on the escalation model if the first attempt produces output
    that does not validate. A second failure raises.

    Args:
        job_id: Job the graph belongs to.
        corpus: Output of build_corpus().
        max_confidence_grade: Ceiling on any claim's confidence grade.
        verification_rate: Fraction of quotes verified, for the prompt header.
        known_source_ids: Source IDs the graph's evidence may reference.

    Returns:
        Tuple of (validated ClaimGraph, list of per-attempt usage dicts).

    Raises:
        ValueError: If both attempts fail to produce a valid graph.
    """
    from backend.integrations.anthropic_client import (
        AnthropicError,
        SchemaInvalidError,
        get_anthropic_client,
    )

    settings = get_settings()
    schema = api_json_schema()
    prompt = build_distillation_prompt(
        topic=corpus.get("topic") or "",
        source_count=len(corpus.get("sources") or []),
        key_point_count=len(corpus.get("key_points") or []),
        verification_rate=f"{verification_rate:.0%}",
        max_confidence_grade=max_confidence_grade,
        corpus_json=json.dumps(corpus, indent=2, default=str),
    )

    attempts = [settings.model_distill, settings.model_escalation]
    usages: list[dict] = []
    failures: list[str] = []

    for index, model_id in enumerate(attempts):
        label = "distillation" if index == 0 else "escalation retry"
        try:
            client = get_anthropic_client(model=model_id)
            data, usage = client.generate_structured(
                prompt=prompt,
                schema=schema,
                system=DISTILLATION_ROLE,
                max_tokens=DISTILL_MAX_TOKENS,
                model=model_id,
            )
            usages.append(usage)

            data = normalize_wire_payload(data)
            data["job_id"] = job_id
            graph = ClaimGraph.model_validate(data)

            problems = graph.validate_against_ledger(known_source_ids)
            if problems:
                raise ValueError("; ".join(problems[:5]))

            logger.info(
                f"[{job_id}] Distillation succeeded on {label} ({model_id}): "
                f"{len(graph.claims)} claims, {len(graph.story_goods)} story goods, "
                f"{len(graph.holes)} holes"
            )
            return graph, usages

        except (SchemaInvalidError, ValidationError, ValueError) as e:
            failures.append(f"{model_id}: {e}")
            logger.warning(f"[{job_id}] {label} produced an invalid graph: {e}")
        except AnthropicError as e:
            failures.append(f"{model_id}: {e}")
            logger.error(f"[{job_id}] {label} call failed: {e}")

    raise ValueError(
        "Distillation failed on both the primary and escalation models. "
        + " | ".join(failures)
    )


def _sources_from_context(ctx: PipelineContext) -> list[dict]:
    """Build source ledger entries from identity packages."""
    sources = []
    for pkg in getattr(ctx, "source_identity_packages", []) or []:
        sources.append(
            {
                "source_id": getattr(pkg, "source_id", None),
                "title": getattr(pkg, "title", None),
                "type": getattr(pkg, "source_type", None),
                "status": "ingested"
                if getattr(pkg, "is_accessible", True)
                else "failed",
            }
        )
    return sources


def _units_from_context(
    ctx: PipelineContext,
) -> tuple[list[dict], list[dict], list[dict], list[ConfidenceLevel]]:
    """Aggregate key points, themes, tensions and ceilings from extractions."""
    key_points: list[dict] = []
    themes: list[dict] = []
    tensions: list[dict] = []
    ceilings: list[ConfidenceLevel] = []

    for extraction in getattr(ctx, "semantic_extractions", []) or []:
        ceilings.append(extraction.confidence_ceiling)

        for kp in extraction.key_points:
            key_points.append(
                {
                    "key_point_id": kp.key_point_id,
                    "statement": kp.statement,
                    # Fall back to the owning source so folding never loses
                    # provenance when a key point omits its source_ids.
                    "source_ids": kp.source_ids or [extraction.source_id],
                    "confidence": kp.confidence.value,
                }
            )

        for theme in extraction.themes:
            themes.append(
                {
                    "label": theme.label,
                    "description": theme.description,
                    "sources_supporting": theme.sources_supporting
                    or [extraction.source_id],
                    "is_consensus": theme.is_consensus,
                }
            )

        for tension in extraction.tensions:
            tensions.append(
                {
                    "label": tension.label,
                    "description": tension.description,
                    "source_ids": tension.source_ids or [extraction.source_id],
                    "is_cross_source": tension.is_cross_source,
                }
            )

    # Synthesis may have produced cross-source themes beyond the per-source ones.
    for theme in getattr(ctx, "synthesized_themes", []) or []:
        themes.append(
            {
                "label": getattr(theme, "label", None),
                "description": getattr(theme, "description", None),
                "sources_supporting": getattr(theme, "sources_supporting", []) or [],
                "is_consensus": getattr(theme, "is_consensus", False),
            }
        )

    return key_points, themes, tensions, ceilings


def stage_distillation(ctx: PipelineContext) -> None:
    """Pipeline stage: distill synthesis output into the Claim Graph.

    PREREQUISITE: semantic_synthesis must have run.

    Unlike gap analysis, a failure here is NOT swallowed. The graph is the
    canonical layer every downstream document derives from, so continuing
    without one would produce documents with nothing behind them.
    """
    logger.info(f"[{ctx.job_id}] Stage: Distillation")
    update_job(ctx.job_id, stage="distillation", progress_percent=72)

    extractions = getattr(ctx, "semantic_extractions", []) or []
    if not extractions:
        logger.warning(f"[{ctx.job_id}] No extractions; skipping distillation")
        ctx.add_warning("Distillation skipped: no semantic extractions available")
        return

    key_points, themes, tensions, ceilings = _units_from_context(ctx)
    gaps = [g.to_dict() for g in getattr(ctx, "identified_gaps", []) or []]
    sources = _sources_from_context(ctx)

    verification_rate = float(getattr(ctx, "verification_rate", 0.0) or 0.0)
    max_grade = confidence_ceiling_grade(ceilings, verification_rate)

    corpus = build_corpus(
        topic=ctx.topic,
        sources=sources,
        key_points=key_points,
        themes=themes,
        tensions=tensions,
        gaps=gaps,
        semantic_core=getattr(ctx, "semantic_core", None) or None,
    )

    known_source_ids = {s["source_id"] for s in sources if s.get("source_id")}

    graph, usages = distill_corpus(
        job_id=ctx.job_id,
        corpus=corpus,
        max_confidence_grade=max_grade,
        verification_rate=verification_rate,
        known_source_ids=known_source_ids,
    )

    ctx.claim_graph = graph
    ctx.outputs["claim_graph"] = graph.model_dump(mode="json")

    # Render the Briefing here rather than in a separate stage: it is a pure
    # projection of the graph we just built, with no other inputs.
    source_titles = {
        s["source_id"]: s.get("title") or "" for s in sources if s.get("source_id")
    }
    briefing_md = render_briefing(graph, source_titles)
    ctx.outputs["briefing_md"] = briefing_md

    lint = lint_rendered_document(briefing_md)
    if not lint.passes:
        # A voice-law violation is a defect in the rendered document, but it is
        # not worth discarding a valid graph over at runtime. The render test
        # is where this fails the build; here it is surfaced and carried.
        for violation in lint.errors:
            ctx.add_warning(f"Briefing lint: {violation}")
        logger.warning(
            f"[{ctx.job_id}] Briefing has {len(lint.errors)} lint errors"
        )

    total_cost = sum(u.get("cost", 0.0) for u in usages)
    ctx.add_cost("anthropic_distillation", total_cost)

    update_job(
        ctx.job_id,
        partial_outputs={
            "distillation_summary": {
                "claims": len(graph.claims),
                "story_goods": len(graph.story_goods),
                "holes": len(graph.holes),
                "max_confidence_grade": max_grade,
                "attempts": len(usages),
                "cost": total_cost,
            }
        },
    )
