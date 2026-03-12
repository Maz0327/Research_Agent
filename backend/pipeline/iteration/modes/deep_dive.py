"""
Deep Dive iteration mode.

Formerly: Deep Research Booster (booster_stage.py).
Renamed 2026-03-12 — Phase 3.2.3.

Produces DIRECTIONS, not facts — tells the researcher WHERE to look, not WHAT they'll find.
Output: new version of Doc 1 (Jump-Start Directions) with a "Deep Research Expansion" section.

Per GAPS_AND_BOOSTER_SPEC.md Part 2 and architecture Rule 13a:
  deep_dive — gaps/search directions (formerly Booster); affects Doc 1 only.
"""

from typing import Any

from loguru import logger

from backend.pipeline.context import PipelineContext
from ..metrics_tracker import MetricsTracker


def run_deep_dive(
    ctx: PipelineContext,
    artifacts_dict: dict[str, Any],
    metrics: MetricsTracker,
) -> dict[str, Any]:
    """
    Run Deep Dive (formerly Booster) on a completed job's documents.

    Generates gap-filling research directions from Doc 1 + Doc 2.
    Appends a 'Deep Research Expansion' section to Jump-Start Directions.

    Args:
        ctx: Pipeline context (used for job_id and logging)
        artifacts_dict: Flattened artifacts dict from the completed job
        metrics: Metrics tracker for cost/call tracking

    Returns:
        Updated Doc 1 dict with deep_dive expansion appended, in
        {"data": {...}, "markdown": "<markdown>"} format.

    Raises:
        RuntimeError: If required documents are missing or booster fails fatally.
    """
    from backend.pipeline.booster.context_bundle_generator import generate_context_bundle
    from backend.pipeline.stages.booster_stage import run_booster, booster_output_to_dict
    from backend.pipeline.booster.expansion_builder import build_booster_expansion_markdown
    from backend.integrations.supabase_storage import get_storage_client

    job_id = ctx.job_id
    logger.info(f"[{job_id}] Deep Dive mode: generating research directions")

    # Retrieve Doc 1 (jump_start) and Doc 2 (semantic_brief)
    jump_start = artifacts_dict.get("jump_start")
    semantic_brief = artifacts_dict.get("semantic_brief")
    extractions = artifacts_dict.get("semantic_extractions", [])

    # Attempt storage fallback if inline data missing
    storage = get_storage_client()
    if not jump_start and artifacts_dict.get("doc_1_path") and storage:
        try:
            raw = storage.download_document(artifacts_dict["doc_1_path"])
            jump_start = raw.get("data", raw) if isinstance(raw, dict) else raw
        except Exception as exc:
            logger.warning(f"[{job_id}] Could not download doc_1 for deep_dive: {exc}")

    if not semantic_brief and artifacts_dict.get("doc_2_path") and storage:
        try:
            raw = storage.download_document(artifacts_dict["doc_2_path"])
            semantic_brief = raw.get("data", raw) if isinstance(raw, dict) else raw
        except Exception as exc:
            logger.warning(f"[{job_id}] Could not download doc_2 for deep_dive: {exc}")

    if not jump_start:
        raise RuntimeError(f"[{job_id}] deep_dive: Doc 1 (jump_start) not available")
    if not semantic_brief:
        raise RuntimeError(f"[{job_id}] deep_dive: Doc 2 (semantic_brief) not available")

    # Build context bundle (input to booster prompt)
    context_bundle = generate_context_bundle(
        job_id=job_id,
        jump_start=jump_start,
        semantic_brief=semantic_brief,
        extractions=extractions,
    )

    # Run booster LLM call
    booster_output = run_booster(job_id=job_id, bundle=context_bundle)
    if booster_output is None:
        raise RuntimeError(f"[{job_id}] deep_dive: booster returned no output")

    # Track cost if available
    cost = getattr(booster_output, "total_cost_usd", 0.0) or 0.0
    metrics.record_llm_call(model="gemini", tokens_in=0, tokens_out=0, cost=cost)

    # Build expansion markdown
    expansion_md = build_booster_expansion_markdown(booster_output)
    booster_dict = booster_output_to_dict(booster_output)

    # Produce updated Doc 1: original data + expansion appended
    original_md = ""
    if isinstance(jump_start, dict):
        original_md = jump_start.get("markdown", "")
        jump_start_data = jump_start.get("data", jump_start)
    else:
        jump_start_data = jump_start

    combined_markdown = (original_md + "\n\n" + expansion_md).strip() if original_md else expansion_md

    updated_doc1: dict[str, Any] = {
        "data": jump_start_data,
        "markdown": combined_markdown,
        "deep_dive_expansion": booster_dict,
    }

    logger.info(f"[{job_id}] Deep Dive complete — expansion appended to Doc 1")
    return updated_doc1
