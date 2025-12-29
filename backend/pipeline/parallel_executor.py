"""Parallel execution for pipeline stages.

Enables concurrent execution of I/O-bound stages to improve performance.
Uses ThreadPoolExecutor for parallelism since stages are I/O-bound (API calls).

Parallelization Strategy:
- Group 1 (After Source Discovery):
  - Track A: YouTube Enumeration → Transcripts (sequential)
  - Track B: Web Capture (parallel)
  - Track C: Reddit Collection (parallel)

- Group 2 (After Claim Extraction):
  - Timeline Extraction (parallel)
  - Entity Extraction (parallel)
  - Claim Validation (parallel)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional
from loguru import logger

from backend.pipeline.context import PipelineContext


def run_parallel_stages(
    ctx: PipelineContext,
    stages: List[Callable[[PipelineContext], None]],
    stage_names: Optional[List[str]] = None,
    max_workers: int = 3,
) -> Dict[str, Optional[Exception]]:
    """
    Run multiple pipeline stages in parallel.

    Args:
        ctx: Pipeline context (shared, thread-safe for reads)
        stages: List of stage functions to run
        stage_names: Optional names for logging
        max_workers: Maximum concurrent threads

    Returns:
        Dict mapping stage name to exception (None if successful)
    """
    if not stages:
        return {}

    names = stage_names or [f"stage_{i}" for i in range(len(stages))]
    results: Dict[str, Optional[Exception]] = {}

    logger.info(f"[{ctx.job_id}] Running {len(stages)} stages in parallel: {names}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {}
        for stage_func, name in zip(stages, names):
            future = executor.submit(_run_stage_safely, ctx, stage_func, name)
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                error = future.result()
                results[name] = error
                if error:
                    logger.warning(f"[{ctx.job_id}] Parallel stage '{name}' failed: {error}")
                else:
                    logger.info(f"[{ctx.job_id}] Parallel stage '{name}' completed")
            except Exception as e:
                results[name] = e
                logger.error(f"[{ctx.job_id}] Parallel stage '{name}' raised: {e}")

    successful = sum(1 for e in results.values() if e is None)
    logger.info(f"[{ctx.job_id}] Parallel execution complete: {successful}/{len(stages)} succeeded")

    return results


def _run_stage_safely(
    ctx: PipelineContext,
    stage_func: Callable[[PipelineContext], None],
    stage_name: str,
) -> Optional[Exception]:
    """Run a stage with exception handling."""
    try:
        stage_func(ctx)
        return None
    except Exception as e:
        ctx.add_warning(f"{stage_name} failed: {str(e)}")
        return e


def run_collection_stages_parallel(ctx: PipelineContext) -> None:
    """
    Run collection stages in parallel after source discovery.

    Parallel tracks:
    - Track A: YouTube → Transcripts (sequential within track)
    - Track B: Web Capture
    - Track C: Reddit Collection
    """
    from backend.pipeline.stages import (
        stage_4_youtube_enumeration,
        stage_5_transcripts,
        stage_6_web_capture,
        stage_6_5_reddit,
    )

    def youtube_track(ctx: PipelineContext) -> None:
        """YouTube enumeration followed by transcript fetching."""
        stage_4_youtube_enumeration(ctx)
        stage_5_transcripts(ctx)

    stages = [youtube_track, stage_6_web_capture, stage_6_5_reddit]
    names = ["youtube_track", "web_capture", "reddit_collection"]

    run_parallel_stages(ctx, stages, names, max_workers=3)


def run_extraction_stages_parallel(ctx: PipelineContext) -> None:
    """
    Run extraction stages in parallel after claim extraction.

    All work on the same inputs (claims, transcripts, web_sources).
    """
    from backend.pipeline.stages import (
        stage_7_5_timeline,
        stage_7_6_entities,
        stage_8_validation,
    )

    stages = [stage_7_5_timeline, stage_7_6_entities, stage_8_validation]
    names = ["timeline_extraction", "entity_extraction", "claim_validation"]

    run_parallel_stages(ctx, stages, names, max_workers=3)
