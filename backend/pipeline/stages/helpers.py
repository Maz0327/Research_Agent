"""Shared helper utilities for pipeline stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext


def post_slack_message(ctx: PipelineContext, message: str) -> None:
    """Post Slack message if payload is provided."""
    if ctx.slack_payload and ctx.slack_payload.get("response_url"):
        try:
            from backend.integrations.slack import post_slack_message as _post
            _post(ctx.slack_payload["response_url"], message)
        except Exception as e:
            logger.warning(f"[Slack] Failed to post message: {e}")
