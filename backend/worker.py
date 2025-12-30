"""Celery worker configuration and task definitions."""
from typing import Optional

from celery import Celery
from loguru import logger

from backend.config import get_settings
from backend.models.job_config import JobConfig
from backend.state import get_job, update_job
from backend.services.error_logger import log_exception
from backend.pipeline.document_helpers import (
    generate_master_index,
    generate_transcripts_md,
    generate_web_extracts_md,
    generate_evidence_table_md,
)

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "research_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Fix deprecation warning for Celery 5.3+/6.0 compatibility
    broker_connection_retry_on_startup=True,
    task_routes={
        "backend.worker.run_research_job": {"queue": "research"},
    },
    task_default_queue="research",
    task_default_exchange="research",
    task_default_routing_key="research",
)


def _post_slack_message(slack_payload: Optional[dict], message: str) -> None:
    """Helper to post Slack message if payload is provided."""
    if slack_payload and slack_payload.get("response_url"):
        try:
            from backend.integrations.slack import post_slack_message
            post_slack_message(slack_payload["response_url"], message)
        except Exception as e:
            # Log but don't fail the job if Slack notification fails
            logger.warning(f"[Slack] Failed to post message to {slack_payload.get('response_url')}: {e}")


@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(
    job_id: str,
    topic: str,
    slack_payload: Optional[dict] = None,
    enable_parallel: bool = True,
) -> dict:
    """
    Research job task that runs through all stages of the research pipeline.

    Pipeline (with parallelization):
    0. Initialization + Cost Tracker
    1. Planning (OpenAI)
    2. Research mapping (Perplexity)
    3. Source shortlist (Perplexity)
    3.5. Quality Gate (Deterministic filtering)

    [PARALLEL GROUP 1 - Collection]:
    - Track A: YouTube enumeration → Transcripts
    - Track B: Web capture
    - Track C: Reddit collection

    7. Claim extraction

    [PARALLEL GROUP 2 - Extraction]:
    - Timeline extraction
    - Entity extraction
    - Claim validation

    8.5. Angle discovery
    8.6. Documentary intelligence
    9. Drive upload
    10. Completion

    Args:
        job_id: Unique identifier for the research job
        topic: Research topic string (from Slack or API)
        slack_payload: Optional Slack payload for posting updates
        enable_parallel: Enable parallel stage execution (default: True)

    Returns:
        Dictionary with research results including Drive folder URL
    """
    from backend.pipeline.context import PipelineContext
    from backend.pipeline.cost_tracker import CostTracker
    from backend.pipeline.stages import (
        stage_0_initialize,
        stage_1_planning,
        stage_2_research_mapping,
        stage_3_source_shortlist,
        stage_3_5_quality_gate,
        stage_4_youtube_enumeration,
        stage_5_transcripts,
        stage_6_web_capture,
        stage_6_5_reddit,
        stage_7_extraction,
        stage_7_5_timeline,
        stage_7_6_entities,
        stage_8_validation,
        stage_8_5_angle_discovery,
        stage_8_6_documentary_intelligence,
        stage_9_drive_upload,
        stage_10_completion,
        post_slack_message,
    )
    from backend.pipeline.stages.planning import DisambiguationRequired
    from backend.pipeline.parallel_executor import (
        run_collection_stages_parallel,
        run_extraction_stages_parallel,
    )

    logger.info(f"Starting research job {job_id} for topic: {topic}")

    # Create pipeline context with cost tracker
    ctx = PipelineContext(
        job_id=job_id,
        topic=topic,
        slack_payload=slack_payload,
        cost_tracker=CostTracker(mode="full"),  # Mode updated after planning
    )

    try:
        # Check if this is a resumed job after disambiguation
        job = get_job(job_id)
        if job and job.selected_interpretations is not None and job.interpretations:
            # Resumed job: process selected interpretations sequentially
            logger.info(f"[{job_id}] Resuming after disambiguation with {len(job.selected_interpretations)} interpretations")
            return _run_disambiguated_job(ctx, job, enable_parallel)

        # Stage 0-3: Sequential initialization and discovery
        stage_0_initialize(ctx)
        stage_1_planning(ctx)

        # Update cost tracker mode while preserving existing costs from stage 0-1
        if ctx.job_config and ctx.cost_tracker:
            ctx.cost_tracker.update_mode(ctx.job_config.mode.value)

        stage_2_research_mapping(ctx)
        stage_3_source_shortlist(ctx)
        stage_3_5_quality_gate(ctx)

        # Parallel Group 1: Collection stages
        if enable_parallel:
            logger.info(f"[{job_id}] Running collection stages in parallel")
            run_collection_stages_parallel(ctx)
        else:
            stage_4_youtube_enumeration(ctx)
            stage_5_transcripts(ctx)
            stage_6_web_capture(ctx)
            stage_6_5_reddit(ctx)

        # Stage 7: Claim extraction (must wait for all sources)
        stage_7_extraction(ctx)

        # Parallel Group 2: Extraction stages
        if enable_parallel:
            logger.info(f"[{job_id}] Running extraction stages in parallel")
            run_extraction_stages_parallel(ctx)
        else:
            stage_7_5_timeline(ctx)
            stage_7_6_entities(ctx)
            stage_8_validation(ctx)

        # Stage 8.5+: Sequential synthesis and output
        stage_8_5_angle_discovery(ctx)
        stage_8_6_documentary_intelligence(ctx)
        stage_9_drive_upload(ctx)

        # Log cost summary
        cost_summary = ctx.get_cost_summary()
        logger.info(f"[{job_id}] Cost summary: ${cost_summary.get('total_cost', 0):.4f}")

        return stage_10_completion(ctx)

    except DisambiguationRequired as e:
        # Job paused for user disambiguation - this is not an error
        logger.info(f"[{job_id}] Paused for disambiguation: {len(e.interpretations)} interpretations")
        return {
            "job_id": job_id,
            "status": "disambiguating",
            "interpretations": e.interpretations,
        }

    except Exception as e:
        logger.exception(f"Fatal error in research job {job_id}: {e}")

        # Log error to database for admin tracking
        job = get_job(job_id)
        user_id = None
        user_email = None
        current_stage = "unknown"
        if job:
            user_id = job.user_id
            user_email = job.config_json.get("user_email") if job.config_json else None
            current_stage = job.stage or "unknown"

        log_exception(
            exception=e,
            job_id=job_id,
            user_id=user_id,
            user_email=user_email,
            stage=current_stage,
        )

        # Update job status to failed
        update_job(
            job_id,
            status="failed",
            stage="error",
            progress_percent=0,
            warnings_append=ctx.warnings + [f"Fatal error: {str(e)}"],
        )

        # Post error message to Slack
        post_slack_message(ctx, f"❌ Research job `{job_id}` failed: {str(e)}")

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


def _run_disambiguated_job(ctx, job, enable_parallel: bool) -> dict:
    """
    Process a job resumed after disambiguation.

    Runs the pipeline for each selected interpretation sequentially,
    aggregating results into a single output.

    Args:
        ctx: PipelineContext with job_id and basic setup
        job: JobRecord with selected_interpretations and interpretations
        enable_parallel: Enable parallel stage execution

    Returns:
        Dictionary with aggregated research results
    """
    from backend.pipeline.stages import (
        stage_2_research_mapping,
        stage_3_source_shortlist,
        stage_3_5_quality_gate,
        stage_4_youtube_enumeration,
        stage_5_transcripts,
        stage_6_web_capture,
        stage_6_5_reddit,
        stage_7_extraction,
        stage_7_5_timeline,
        stage_7_6_entities,
        stage_8_validation,
        stage_8_5_angle_discovery,
        stage_8_6_documentary_intelligence,
        stage_9_drive_upload,
        stage_10_completion,
        post_slack_message,
    )
    from backend.pipeline.parallel_executor import (
        run_collection_stages_parallel,
        run_extraction_stages_parallel,
    )
    from backend.integrations.openai_client import _safe_default_config

    selected_indices = job.selected_interpretations or []
    interpretations = job.interpretations or []

    logger.info(f"[{ctx.job_id}] Processing {len(selected_indices)} interpretations")

    # Update status to running
    update_job(ctx.job_id, status="running", stage="processing_interpretations")

    all_results = []

    for i, idx in enumerate(selected_indices):
        if idx >= len(interpretations):
            ctx.add_warning(f"Invalid interpretation index: {idx}")
            continue

        interp = interpretations[idx]
        refined_topic = interp.get("topic", ctx.topic)
        label = interp.get("label", f"Interpretation {idx + 1}")

        logger.info(f"[{ctx.job_id}] Processing interpretation {i + 1}/{len(selected_indices)}: {label}")
        post_slack_message(ctx, f"📚 Researching: {label}")

        # Update context with refined topic
        ctx.topic = refined_topic

        # Create job config for this interpretation
        ctx.job_config = _safe_default_config(refined_topic)

        try:
            # Run pipeline stages for this interpretation
            # Skip stage_0 (already initialized) and stage_1 (already planned)
            stage_2_research_mapping(ctx)
            stage_3_source_shortlist(ctx)
            stage_3_5_quality_gate(ctx)

            # Collection stages
            if enable_parallel:
                run_collection_stages_parallel(ctx)
            else:
                stage_4_youtube_enumeration(ctx)
                stage_5_transcripts(ctx)
                stage_6_web_capture(ctx)
                stage_6_5_reddit(ctx)

            # Extraction
            stage_7_extraction(ctx)

            # Extraction stages
            if enable_parallel:
                run_extraction_stages_parallel(ctx)
            else:
                stage_7_5_timeline(ctx)
                stage_7_6_entities(ctx)
                stage_8_validation(ctx)

            # Synthesis
            stage_8_5_angle_discovery(ctx)
            stage_8_6_documentary_intelligence(ctx)

            all_results.append({
                "label": label,
                "topic": refined_topic,
                "status": "completed",
            })

        except Exception as e:
            logger.error(f"[{ctx.job_id}] Failed to process interpretation '{label}': {e}")
            ctx.add_warning(f"Interpretation '{label}' failed: {str(e)}")
            all_results.append({
                "label": label,
                "topic": refined_topic,
                "status": "failed",
                "error": str(e),
            })

    # Upload combined results
    stage_9_drive_upload(ctx)

    # Log cost summary
    cost_summary = ctx.get_cost_summary()
    logger.info(f"[{ctx.job_id}] Cost summary: ${cost_summary.get('total_cost', 0):.4f}")

    return stage_10_completion(ctx)


# =============================================================================
# Transcript Extraction Task
# =============================================================================

@celery_app.task(name="backend.worker.run_transcript_job")
def run_transcript_job(job_id: str) -> dict:
    """
    Celery task for async transcript extraction.

    Processes large batches of YouTube videos (>5) in the background.
    Updates job progress as each video is processed.

    Args:
        job_id: Unique identifier for the transcript job

    Returns:
        Dict with job_id, status, and doc_url
    """
    from datetime import datetime
    from backend.services.transcript_service import (
        extract_single_transcript,
        format_transcripts_for_doc,
    )
    from backend.integrations.google_drive_docs import create_transcript_doc
    from backend.models.job_record import Artifacts

    logger.info(f"[{job_id}] Starting transcript extraction job")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    video_urls = job.config_json.get("video_urls", [])
    use_whisper = job.config_json.get("use_whisper_fallback", True)
    doc_title = job.config_json.get("doc_title")
    preferred_languages = job.config_json.get("preferred_languages", ["en"])

    total = len(video_urls)
    logger.info(f"[{job_id}] Processing {total} videos")

    # Update status to running
    update_job(job_id, status="running", stage="extracting_transcripts", progress_percent=5)

    transcripts = []
    warnings = []

    # Process each video
    for i, url in enumerate(video_urls):
        # Update progress (5% start, 85% for extraction, 10% for doc generation)
        progress = 5 + int(((i + 1) / total) * 80)

        try:
            result = extract_single_transcript(
                url,
                use_whisper=use_whisper,
                preferred_languages=preferred_languages,
            )
            transcripts.append(result)

            if result.status != "available":
                warnings.append(f"Transcript unavailable for {url}: {result.error_message}")

            logger.info(f"[{job_id}] Processed {i + 1}/{total}: {result.status}")

        except Exception as e:
            logger.error(f"[{job_id}] Error processing {url}: {e}")
            warnings.append(f"Error processing {url}: {str(e)}")
            from backend.models.transcript_job import TranscriptResultItem
            from backend.integrations.transcripts import _extract_video_id
            transcripts.append(TranscriptResultItem(
                video_id=_extract_video_id(url) or "",
                video_url=url,
                status="error",
                source="failed",
                error_message=str(e),
            ))

        # Update job progress
        update_job(
            job_id,
            progress_percent=progress,
            config_json={**job.config_json, "transcripts_completed": i + 1},
        )

    # Stage: Generate Google Doc
    logger.info(f"[{job_id}] Generating Google Doc")
    update_job(job_id, stage="generating_document", progress_percent=90)

    try:
        if not doc_title:
            doc_title = f"YouTube Transcripts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        content = format_transcripts_for_doc(transcripts)

        # Get user info from job for Drive sharing
        user_email = None
        user_id_for_drive = None
        if job and job.config_json:
            user_email = job.config_json.get("user_email")
            user_id_for_drive = job.config_json.get("user_id")

        drive_result = create_transcript_doc(
            doc_title,
            content,
            user_email=user_email,
            user_id=user_id_for_drive,
        )

        # Update job with success
        artifacts = Artifacts(
            drive_folder_url=drive_result["folder_url"],
            doc_urls=[drive_result["doc_url"]],
        )

        update_job(
            job_id,
            status="completed",
            progress_percent=100,
            stage="completed",
            artifacts=artifacts,
            warnings=warnings,
        )

        logger.info(f"[{job_id}] Transcript job completed: {drive_result['doc_url']}")

        return {
            "job_id": job_id,
            "status": "completed",
            "doc_url": drive_result["doc_url"],
            "folder_url": drive_result["folder_url"],
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Failed to create Google Doc: {e}")
        warnings.append(f"Failed to create Google Doc: {str(e)}")

        update_job(
            job_id,
            status="failed",
            warnings=warnings,
        )

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }
