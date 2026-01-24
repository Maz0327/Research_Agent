"""
Iteration mode dispatcher.

Routes iteration requests to appropriate mode handlers.
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
        mode: Iteration mode (more_sources, deeper, different_angle, custom)
        ctx: Pipeline context
        baseline: Loaded baseline data
        metrics: Metrics tracker
        user_prompt: User-provided prompt (for custom mode)
        max_new_sources: Maximum new sources (for more_sources mode)
        angle: Specific angle (for different_angle mode)

    Returns:
        Tuple of (doc_0, doc_1, doc_2) dicts

    Raises:
        ValueError: If mode is unknown or required parameter missing
    """
    job_id = ctx.job_id
    logger.info(f"[{job_id}] Running iteration mode: {mode}")

    if mode == "more_sources":
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

    else:
        raise ValueError(f"Unknown iteration mode: {mode}")
