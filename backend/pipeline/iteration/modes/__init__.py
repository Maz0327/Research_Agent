"""
Iteration mode dispatcher.

Routes iteration requests to appropriate mode handlers.

Mode naming (canonical as of 2026-03-12):
  expand_sources — formerly more_sources (alias still accepted for backward compatibility)
  deeper         — re-extract with more depth
  different_angle — same data, new perspective
  custom         — user-defined freeform
  deep_dive      — formerly Booster; handled via unified Iterate system in Phase 3
"""

from typing import Any

from loguru import logger

from backend.pipeline.context import PipelineContext
from ..baseline_loader import BaselineData
from ..metrics_tracker import MetricsTracker


def run_iteration_mode(
    mode: str,
    ctx: PipelineContext,
    baseline: BaselineData,
    metrics: MetricsTracker,
    user_prompt: str = "",
    max_new_sources: int = 4,
    angle: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Dispatch to appropriate mode handler.

    Args:
        mode: Iteration mode (expand_sources, deeper, different_angle, custom).
              'more_sources' accepted as alias for expand_sources.
        ctx: Pipeline context
        baseline: Loaded baseline data
        metrics: Metrics tracker
        user_prompt: User-provided prompt (for custom mode)
        max_new_sources: Maximum new sources (for expand_sources mode)
        angle: Specific angle (for different_angle mode)

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts

    Raises:
        ValueError: If mode is unknown or required parameter missing
    """
    job_id = ctx.job_id
    logger.info(f"[{job_id}] Running iteration mode: {mode}")

    # expand_sources: canonical name. more_sources: backward-compatible alias.
    if mode in ("expand_sources", "more_sources"):
        from .more_sources import run_more_sources

        return run_more_sources(ctx, baseline, max_new_sources, metrics)

    elif mode == "deeper":
        from .deeper import run_deeper

        return run_deeper(ctx, baseline, metrics)

    elif mode == "different_angle":
        if not angle:
            raise ValueError("different_angle mode requires 'angle' parameter")
        from .different_angle import run_different_angle

        return run_different_angle(ctx, baseline, angle, metrics)

    elif mode == "custom":
        if not user_prompt:
            raise ValueError("custom mode requires 'user_prompt' parameter")
        from .custom import run_custom

        return run_custom(ctx, baseline, user_prompt, metrics)

    elif mode == "deep_dive":
        # deep_dive needs full artifacts_dict — handled at the Celery task level.
        raise ValueError(
            "deep_dive mode must be dispatched via run_iterate_task, not run_iteration_mode directly. "
            "Use POST /jobs/{job_id}/iterate with {'mode': 'deep_dive'}."
        )

    else:
        raise ValueError(f"Unknown iteration mode: {mode}")
