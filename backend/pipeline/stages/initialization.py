"""Pipeline initialization and completion stages."""
from loguru import logger

from backend.pipeline.context import PipelineContext
from backend.state import get_job, update_job
from .helpers import post_slack_message


def stage_0_initialize(ctx: PipelineContext) -> None:
    """Initialize job and send start notification."""
    update_job(
        ctx.job_id,
        status="running",
        stage="initializing",
        progress_percent=0,
    )
    post_slack_message(ctx, f"Started research job: `{ctx.job_id}`\nTopic: {ctx.topic}")


def stage_10_completion(ctx: PipelineContext) -> dict:
    """Mark job complete and send notifications."""
    logger.info(f"[{ctx.job_id}] Stage 10: Completing job")

    # Get cost summary for final output
    cost_summary = ctx.get_cost_summary()

    # Add cost and quality gate stats to outputs
    final_outputs = dict(ctx.outputs)
    if cost_summary:
        final_outputs["cost_summary"] = cost_summary
    if ctx.quality_gate_stats:
        final_outputs["quality_gate_stats"] = ctx.quality_gate_stats

    update_job(
        ctx.job_id,
        status="completed",
        stage="completed",
        progress_percent=100,
        partial_outputs=final_outputs,
        warnings_append=ctx.warnings,
    )

    # Build completion message
    if ctx.folder_url:
        message = (
            f"Research job `{ctx.job_id}` completed!\n\n"
            f"Drive folder: {ctx.folder_url}\n"
            f"Claims extracted: {len(ctx.claims)}\n"
            f"Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
        )
        if ctx.warnings:
            message += f"\n{len(ctx.warnings)} warnings (see job details)"
    else:
        message = (
            f"Research job `{ctx.job_id}` completed!\n\n"
            f"Drive upload failed, but results are available via API\n"
            f"Claims extracted: {len(ctx.claims)}\n"
            f"Sources: {len(ctx.web_sources)} web, {len(ctx.youtube_videos)} YouTube videos"
        )

    post_slack_message(ctx, message)

    result = {
        "job_id": ctx.job_id,
        "status": "completed",
        "folder_url": ctx.folder_url,
        "doc_urls": ctx.doc_urls,
        "claims_count": len(ctx.claims),
        "sources_count": len(ctx.web_sources),
        "youtube_videos_count": len(ctx.youtube_videos),
        "warnings_count": len(ctx.warnings),
        "cost_summary": cost_summary,
        "quality_gate_stats": ctx.quality_gate_stats,
    }

    logger.info(f"Research job {ctx.job_id} completed successfully (cost: ${cost_summary.get('total_cost', 0):.4f})")
    return result
