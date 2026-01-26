"""
Iteration mode: different_angle

Re-synthesize with a specific angle or perspective.
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


def run_different_angle(
    ctx: PipelineContext,
    baseline: BaselineData,
    angle: str,
    metrics: MetricsTracker,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Re-synthesize with a different angle.

    This mode does NOT re-extract sources - it uses baseline extractions
    and re-runs synthesis with angle-specific focus.

    Args:
        ctx: Pipeline context (pre-populated with baseline extractions)
        baseline: Baseline data
        angle: Specific angle (e.g., "economic impact", "historical context")
        metrics: Metrics tracker

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts
    """
    job_id = ctx.job_id
    iteration_id = ctx.outputs.get("iteration_id", "unknown")
    logger.info(f"[{job_id}] Running different_angle iteration: '{angle}'")

    # Update progress
    update_job(
        job_id,
        iteration_progress_percent=20,
        pass_detail=f"Applying angle: {angle}",
    )

    # 1. Context already has baseline extractions from context_initializer
    # Inject angle into context for synthesis
    ctx.outputs["iteration_angle"] = angle

    # Modify topic to include angle focus
    original_topic = ctx.topic
    ctx.topic = f"{original_topic} (focusing on: {angle})"

    # 2. Re-run gap analysis (angle may reveal new gaps)
    update_job(job_id, iteration_progress_percent=40, pass_detail="Analyzing gaps from angle perspective")
    stage_gap_analysis(ctx)
    metrics.record_llm_call(tokens_in=500, tokens_out=200)  # Estimate

    # 3. Re-run synthesis with angle context
    update_job(job_id, iteration_progress_percent=60, pass_detail="Synthesizing with angle focus")
    stage_semantic_synthesis(ctx)
    metrics.record_llm_call(tokens_in=2000, tokens_out=1500)  # Estimate

    # 4. Document assembly
    update_job(job_id, iteration_progress_percent=80, pass_detail="Assembling iteration documents")
    result = stage_document_assembly(ctx)

    # Restore original topic for doc metadata
    ctx.topic = original_topic

    # Extract docs with markdown for frontend rendering
    doc_0 = result["source_ledger"].to_dict()
    doc_0["markdown"] = result["source_ledger"].to_markdown()
    doc_1 = result["jump_start"].to_dict()
    doc_1["markdown"] = result["jump_start"].to_markdown()
    doc_2 = result["semantic_brief"].to_dict()
    doc_2["markdown"] = result["semantic_brief"].to_markdown()

    # Add iteration metadata to docs
    doc_0["iteration_id"] = iteration_id
    doc_0["iteration_mode"] = "different_angle"
    doc_0["iteration_angle"] = angle
    doc_1["iteration_id"] = iteration_id
    doc_2["iteration_id"] = iteration_id
    doc_2["iteration_angle"] = angle

    logger.info(f"[{job_id}] Iteration {iteration_id} (different_angle: {angle}) complete")

    return doc_0, doc_1, doc_2
