"""Shared helper utilities for pipeline stages.

DEPRECATED: 2026-01-19 - Slack integration removed from pipeline.
This file is kept for backwards compatibility but will be removed.
"""
from loguru import logger

from backend.pipeline.context import PipelineContext


def post_slack_message(ctx: PipelineContext, message: str) -> None:
    """Post Slack message if payload is provided.

    DEPRECATED: Slack integration has been removed from the pipeline.
    This function now only logs the message and does nothing else.
    """
    logger.debug(f"[{ctx.job_id}] (Slack disabled) Would have sent: {message[:50]}...")
