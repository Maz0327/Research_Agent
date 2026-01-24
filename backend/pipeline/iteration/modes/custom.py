"""
Iteration mode: custom

Apply user-provided custom instructions to synthesis.
Does NOT re-extract - uses baseline extractions directly.
"""

from typing import Any

from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.gap_analysis import stage_gap_analysis
from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis
from backend.pipeline.stages.document_assembly import stage_document_assembly
from backend.state import update_job
from ..baseline_loader import BaselineData
from ..metrics_tracker import MetricsTracker


def run_custom(
    ctx: PipelineContext,
    baseline: BaselineData,
    user_prompt: str,
    metrics: MetricsTracker,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Apply custom user instructions to synthesis.

    This mode does NOT re-extract sources - it uses baseline extractions
    and applies user's custom prompt during synthesis.

    Args:
        ctx: Pipeline context (pre-populated with baseline extractions)
        baseline: Baseline data
        user_prompt: User-provided custom instruction
        metrics: Metrics tracker

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts
    """
    job_id = ctx.job_id
    iteration_id = ctx.outputs.get("iteration_id", "unknown")
    logger.info(f"[{job_id}] Running custom iteration with prompt: '{user_prompt[:50]}...'")

    # Update progress
    update_job(
        job_id,
        iteration_progress_percent=20,
        pass_detail="Applying custom instructions",
    )

    # 1. Context already has baseline extractions from context_initializer
    # Store user prompt in context for potential use
    ctx.outputs["iteration_user_prompt"] = user_prompt

    # Append custom instruction to topic for synthesis context
    original_topic = ctx.topic
    ctx.topic = f"{original_topic}\n\nCustom focus: {user_prompt}"

    # 2. Re-run gap analysis
    update_job(job_id, iteration_progress_percent=40, pass_detail="Analyzing gaps with custom focus")
    stage_gap_analysis(ctx)
    metrics.record_llm_call(tokens_in=500, tokens_out=200)  # Estimate

    # 3. Re-run synthesis with custom context
    update_job(job_id, iteration_progress_percent=60, pass_detail="Synthesizing with custom instructions")
    stage_semantic_synthesis(ctx)
    metrics.record_llm_call(tokens_in=2000, tokens_out=1500)  # Estimate

    # 4. Document assembly
    update_job(job_id, iteration_progress_percent=80, pass_detail="Assembling iteration documents")
    result = stage_document_assembly(ctx)

    # Restore original topic
    ctx.topic = original_topic

    # Extract docs
    doc_0 = result["source_ledger"].to_dict()
    doc_1 = result["jump_start"].to_dict()
    doc_2 = result["semantic_brief"].to_dict()

    # Add iteration metadata to docs
    doc_0["iteration_id"] = iteration_id
    doc_0["iteration_mode"] = "custom"
    doc_1["iteration_id"] = iteration_id
    doc_2["iteration_id"] = iteration_id
    doc_2["iteration_custom_prompt"] = user_prompt[:200]  # Truncate for storage

    logger.info(f"[{job_id}] Iteration {iteration_id} (custom) complete")

    return doc_0, doc_1, doc_2
