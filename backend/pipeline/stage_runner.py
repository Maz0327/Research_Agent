"""Stage runner with error recovery.

Wraps pipeline stage execution with:
- Error catching and logging
- Fallback execution
- Warning accumulation
- Graceful degradation
"""
from typing import Callable, Optional, TypeVar
from loguru import logger

from backend.pipeline.context import PipelineContext

T = TypeVar("T")


class StageResult:
    """Result of running a pipeline stage."""

    def __init__(
        self,
        success: bool,
        stage_name: str,
        used_fallback: bool = False,
        error: Optional[str] = None,
    ):
        self.success = success
        self.stage_name = stage_name
        self.used_fallback = used_fallback
        self.error = error


def run_stage_with_recovery(
    stage_fn: Callable[[PipelineContext], None],
    ctx: PipelineContext,
    stage_name: str,
    fallback_fn: Optional[Callable[[PipelineContext], None]] = None,
    critical: bool = False,
) -> StageResult:
    """
    Run a pipeline stage with error recovery.

    Args:
        stage_fn: The stage function to execute
        ctx: Pipeline context
        stage_name: Human-readable stage name for logging
        fallback_fn: Optional fallback function if primary fails
        critical: If True, re-raise exception after logging (stops pipeline)

    Returns:
        StageResult indicating success/failure and whether fallback was used
    """
    try:
        logger.info(f"[{ctx.job_id}] Running stage: {stage_name}")
        stage_fn(ctx)
        return StageResult(success=True, stage_name=stage_name)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{ctx.job_id}] Stage '{stage_name}' failed: {error_msg}")

        # Try fallback if available
        if fallback_fn:
            try:
                logger.info(f"[{ctx.job_id}] Attempting fallback for {stage_name}")
                fallback_fn(ctx)
                ctx.add_warning(f"{stage_name}: used fallback due to: {error_msg}")
                return StageResult(
                    success=True,
                    stage_name=stage_name,
                    used_fallback=True,
                )
            except Exception as fallback_e:
                fallback_error = str(fallback_e)
                logger.error(
                    f"[{ctx.job_id}] Fallback for '{stage_name}' also failed: {fallback_error}"
                )
                ctx.add_warning(f"{stage_name} failed (fallback also failed): {error_msg}")

                if critical:
                    raise

                return StageResult(
                    success=False,
                    stage_name=stage_name,
                    error=f"Primary: {error_msg}, Fallback: {fallback_error}",
                )

        # No fallback available
        ctx.add_warning(f"{stage_name} failed: {error_msg}")

        if critical:
            raise

        return StageResult(
            success=False,
            stage_name=stage_name,
            error=error_msg,
        )


def run_optional_stage(
    stage_fn: Callable[[PipelineContext], None],
    ctx: PipelineContext,
    stage_name: str,
    check_fn: Optional[Callable[[PipelineContext], bool]] = None,
) -> StageResult:
    """
    Run an optional stage only if conditions are met.

    Args:
        stage_fn: The stage function to execute
        ctx: Pipeline context
        stage_name: Human-readable stage name for logging
        check_fn: Optional function to check if stage should run

    Returns:
        StageResult (always success=True for skipped stages)
    """
    # Check if stage should run
    if check_fn and not check_fn(ctx):
        logger.info(f"[{ctx.job_id}] Skipping optional stage: {stage_name}")
        return StageResult(success=True, stage_name=stage_name)

    return run_stage_with_recovery(stage_fn, ctx, stage_name)


class StageGroup:
    """
    Group of stages that can be run sequentially with aggregate results.

    Useful for tracking overall success of related stages.
    """

    def __init__(self, name: str):
        self.name = name
        self.results: list[StageResult] = []

    def run(
        self,
        stage_fn: Callable[[PipelineContext], None],
        ctx: PipelineContext,
        stage_name: str,
        fallback_fn: Optional[Callable[[PipelineContext], None]] = None,
        critical: bool = False,
    ) -> StageResult:
        """Run a stage and track its result."""
        result = run_stage_with_recovery(
            stage_fn, ctx, stage_name, fallback_fn, critical
        )
        self.results.append(result)
        return result

    @property
    def all_succeeded(self) -> bool:
        """Check if all stages in the group succeeded."""
        return all(r.success for r in self.results)

    @property
    def any_failed(self) -> bool:
        """Check if any stage in the group failed."""
        return any(not r.success for r in self.results)

    @property
    def failed_stages(self) -> list[str]:
        """Get names of failed stages."""
        return [r.stage_name for r in self.results if not r.success]

    def summary(self) -> dict:
        """Get summary of stage group execution."""
        return {
            "group_name": self.name,
            "total_stages": len(self.results),
            "succeeded": sum(1 for r in self.results if r.success),
            "failed": sum(1 for r in self.results if not r.success),
            "used_fallback": sum(1 for r in self.results if r.used_fallback),
            "failed_stages": self.failed_stages,
        }


# Fallback implementations for common stages

def fallback_extraction_simple(ctx: PipelineContext) -> None:
    """Simple extraction fallback - just log warning."""
    logger.warning(f"[{ctx.job_id}] Using simple extraction fallback - claims may be limited")
    # Set empty claims to prevent downstream errors
    if not ctx.claims:
        ctx.claims = []


def fallback_web_capture_skip(ctx: PipelineContext) -> None:
    """Skip web capture fallback - continue without web sources."""
    logger.warning(f"[{ctx.job_id}] Web capture unavailable - continuing without web sources")
    if not ctx.web_sources:
        ctx.web_sources = []


def fallback_reddit_skip(ctx: PipelineContext) -> None:
    """Skip Reddit fallback - continue without Reddit data."""
    logger.warning(f"[{ctx.job_id}] Reddit unavailable - continuing without Reddit data")
    if not ctx.reddit_posts:
        ctx.reddit_posts = []


def fallback_transcripts_skip(ctx: PipelineContext) -> None:
    """Skip transcripts fallback - continue without transcripts."""
    logger.warning(f"[{ctx.job_id}] Transcripts unavailable - continuing without transcripts")
    if not ctx.transcripts:
        ctx.transcripts = []


def fallback_youtube_skip(ctx: PipelineContext) -> None:
    """Skip YouTube fallback - continue without YouTube videos."""
    logger.warning(f"[{ctx.job_id}] YouTube unavailable - continuing without videos")
    if not ctx.youtube_videos:
        ctx.youtube_videos = []


def fallback_drive_upload_skip(ctx: PipelineContext) -> None:
    """Skip Drive upload fallback - results will be in job record only."""
    logger.warning(f"[{ctx.job_id}] Drive upload unavailable - results in job record only")
    ctx.add_warning("Google Drive upload failed - results available via API only")
