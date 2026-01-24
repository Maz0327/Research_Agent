"""
Initialize PipelineContext for iteration modes.

Creates a fresh context pre-populated with baseline data.
"""

from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.pipeline.cost_tracker import CostTracker
from .baseline_loader import BaselineData
from .metrics_tracker import MetricsTracker


def create_iteration_context(
    job_id: str,
    iteration_id: str,
    baseline: BaselineData,
    mode: str,
) -> tuple[PipelineContext, MetricsTracker]:
    """
    Create PipelineContext pre-populated with baseline data.

    Args:
        job_id: Parent job ID
        iteration_id: Iteration identifier
        baseline: Loaded baseline data
        mode: Iteration mode (more_sources, deeper, different_angle, custom)

    Returns:
        Tuple of (PipelineContext, MetricsTracker)
    """
    logger.info(f"[{job_id}] Creating iteration context for {iteration_id}, mode={mode}")

    # Create fresh context
    ctx = PipelineContext(
        job_id=job_id,
        topic=baseline["topic"],
        cost_tracker=CostTracker(),
    )

    # Set iteration metadata
    ctx.outputs["iteration_id"] = iteration_id
    ctx.outputs["iteration_mode"] = mode

    # Pre-populate with baseline data based on mode
    if mode in ("different_angle", "custom"):
        # These modes reuse baseline extractions directly
        ctx.semantic_extractions = baseline["extractions"]
        logger.debug(
            f"[{job_id}] Pre-populated {len(baseline['extractions'])} baseline extractions"
        )

    elif mode == "deeper":
        # Deeper mode will re-extract, but needs source info
        # Don't pre-populate extractions - they'll be regenerated
        ctx.outputs["baseline_extractions"] = baseline["extractions"]
        ctx.outputs["baseline_doc_0"] = baseline["doc_0"]

    elif mode == "more_sources":
        # More sources mode will add to extractions
        ctx.semantic_extractions = baseline["extractions"].copy()
        ctx.outputs["baseline_source_urls"] = baseline["source_urls"]
        logger.debug(
            f"[{job_id}] Starting with {len(baseline['extractions'])} baseline extractions"
        )

    # Create metrics tracker
    metrics = MetricsTracker()

    return ctx, metrics
