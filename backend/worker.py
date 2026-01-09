"""Celery worker configuration and task definitions."""
from typing import Optional

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
from loguru import logger

from backend.config import get_settings
from backend.state import get_job, update_job
from backend.services.error_logger import log_exception
from backend.pipeline.stage_runner import (
    run_stage_with_recovery,
    StageGroup,
    fallback_web_capture_skip,
    fallback_reddit_skip,
    fallback_transcripts_skip,
    fallback_youtube_skip,
    fallback_drive_upload_skip,
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
        "backend.worker.run_gemini_video_job": {"queue": "research"},
    },
    task_default_queue="research",
    task_default_exchange="research",
    task_default_routing_key="research",
    # Phase 1.5: Extended timeouts for Gemini video processing
    # Default 30 min for long video analysis
    task_time_limit=1800,  # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit (allows cleanup)
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

        # Stage 0-3: Sequential initialization and discovery (critical - no fallback)
        stage_0_initialize(ctx)
        stage_1_planning(ctx)

        # Update cost tracker mode while preserving existing costs from stage 0-1
        if ctx.job_config and ctx.cost_tracker:
            ctx.cost_tracker.update_mode(ctx.job_config.mode.value)

        # Research mapping and source discovery (critical for pipeline)
        run_stage_with_recovery(stage_2_research_mapping, ctx, "research_mapping", critical=True)
        run_stage_with_recovery(stage_3_source_shortlist, ctx, "source_shortlist", critical=True)
        run_stage_with_recovery(stage_3_5_quality_gate, ctx, "quality_gate")

        # Collection stages - use fallbacks for graceful degradation
        collection_group = StageGroup("collection")
        if enable_parallel:
            logger.info(f"[{job_id}] Running collection stages in parallel")
            run_collection_stages_parallel(ctx)
        else:
            collection_group.run(
                stage_4_youtube_enumeration, ctx, "youtube_enumeration",
                fallback_fn=fallback_youtube_skip
            )
            collection_group.run(
                stage_5_transcripts, ctx, "transcripts",
                fallback_fn=fallback_transcripts_skip
            )
            collection_group.run(
                stage_6_web_capture, ctx, "web_capture",
                fallback_fn=fallback_web_capture_skip
            )
            collection_group.run(
                stage_6_5_reddit, ctx, "reddit",
                fallback_fn=fallback_reddit_skip
            )

        # Stage 7: Claim extraction (must wait for all sources)
        run_stage_with_recovery(stage_7_extraction, ctx, "claim_extraction")

        # Extraction stages - can degrade gracefully
        extraction_group = StageGroup("extraction")
        if enable_parallel:
            logger.info(f"[{job_id}] Running extraction stages in parallel")
            run_extraction_stages_parallel(ctx)
        else:
            extraction_group.run(stage_7_5_timeline, ctx, "timeline_extraction")
            extraction_group.run(stage_7_6_entities, ctx, "entity_extraction")
            extraction_group.run(stage_8_validation, ctx, "validation")

        # Stage 8.5+: Sequential synthesis and output
        run_stage_with_recovery(stage_8_5_angle_discovery, ctx, "angle_discovery")
        run_stage_with_recovery(stage_8_6_documentary_intelligence, ctx, "documentary_intelligence")
        run_stage_with_recovery(
            stage_9_drive_upload, ctx, "drive_upload",
            fallback_fn=fallback_drive_upload_skip
        )

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

    # Get original user prompt to preserve question context
    original_prompt = ""
    if job.config_json:
        original_prompt = job.config_json.get("prompt", "") or job.config_json.get("topic", "")

    for i, idx in enumerate(selected_indices):
        if idx >= len(interpretations):
            ctx.add_warning(f"Invalid interpretation index: {idx}")
            continue

        interp = interpretations[idx]
        interpretation_topic = interp.get("topic", "")
        label = interp.get("label", f"Interpretation {idx + 1}")

        # Use LLM to generate natural clarified prompt
        # E.g., "What fan theories exist about 'the barney show'?" + {topic: "Barney the Dinosaur", ...}
        # -> "What fan theories exist about Barney the Dinosaur (the children's TV show, 1992-2010)?"
        from backend.integrations.openai_client import generate_clarified_prompt
        if original_prompt and interpretation_topic:
            refined_topic = generate_clarified_prompt(original_prompt, interp)
        else:
            # Fallback to interpretation topic or original
            refined_topic = interpretation_topic or original_prompt or ctx.topic

        logger.info(f"[{ctx.job_id}] Processing interpretation {i + 1}/{len(selected_indices)}: {label}")
        post_slack_message(ctx, f"📚 Researching: {label}")

        # Update context with refined topic and interpretation info
        ctx.topic = refined_topic
        ctx.interpretation_index = i + 1  # 1-based index for folder naming
        ctx.interpretation_label = label

        # Re-run planning for refined topic to get proper subreddits and config
        # This ensures topic-specific subreddits are used, not defaults
        from backend.integrations.openai_client import plan_job
        try:
            result = plan_job(refined_topic)
            if result.get("is_ambiguous"):
                # Refined topic shouldn't be ambiguous, use default config
                logger.warning(f"[{ctx.job_id}] Refined topic still ambiguous, using default config")
                ctx.job_config = _safe_default_config(refined_topic)
            else:
                ctx.job_config = result.get("config", _safe_default_config(refined_topic))
            logger.info(f"[{ctx.job_id}] Re-planned for refined topic: {refined_topic}")
            if hasattr(ctx.job_config, 'reddit') and ctx.job_config.reddit.subreddits:
                logger.info(f"[{ctx.job_id}] Using subreddits: {ctx.job_config.reddit.subreddits}")
        except Exception as plan_error:
            logger.warning(f"[{ctx.job_id}] Re-planning failed, using default: {plan_error}")
            ctx.job_config = _safe_default_config(refined_topic)

        try:
            # Run pipeline stages for this interpretation
            # Skip stage_0 (already initialized) and stage_1 (already planned)
            run_stage_with_recovery(stage_2_research_mapping, ctx, "research_mapping", critical=True)
            run_stage_with_recovery(stage_3_source_shortlist, ctx, "source_shortlist", critical=True)
            run_stage_with_recovery(stage_3_5_quality_gate, ctx, "quality_gate")

            # Collection stages - with fallbacks
            if enable_parallel:
                run_collection_stages_parallel(ctx)
            else:
                run_stage_with_recovery(
                    stage_4_youtube_enumeration, ctx, "youtube_enumeration",
                    fallback_fn=fallback_youtube_skip
                )
                run_stage_with_recovery(
                    stage_5_transcripts, ctx, "transcripts",
                    fallback_fn=fallback_transcripts_skip
                )
                run_stage_with_recovery(
                    stage_6_web_capture, ctx, "web_capture",
                    fallback_fn=fallback_web_capture_skip
                )
                run_stage_with_recovery(
                    stage_6_5_reddit, ctx, "reddit",
                    fallback_fn=fallback_reddit_skip
                )

            # Extraction
            run_stage_with_recovery(stage_7_extraction, ctx, "claim_extraction")

            # Extraction stages
            if enable_parallel:
                run_extraction_stages_parallel(ctx)
            else:
                run_stage_with_recovery(stage_7_5_timeline, ctx, "timeline_extraction")
                run_stage_with_recovery(stage_7_6_entities, ctx, "entity_extraction")
                run_stage_with_recovery(stage_8_validation, ctx, "validation")

            # Synthesis
            run_stage_with_recovery(stage_8_5_angle_discovery, ctx, "angle_discovery")
            run_stage_with_recovery(stage_8_6_documentary_intelligence, ctx, "documentary_intelligence")

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
    run_stage_with_recovery(
        stage_9_drive_upload, ctx, "drive_upload",
        fallback_fn=fallback_drive_upload_skip
    )

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


# =============================================================================
# NEW STAGE: transcript_acquisition (Phase 0 - Semantic-First Architecture)
# =============================================================================
#
# Position: After source discovery, BEFORE Gemini extraction
#
# Responsibilities:
# 1. Attempt Supadata transcript fetch for each video source
# 2. If Supadata fails → attempt YouTube captions fallback
# 3. Record results in transcript_provenance metadata (see backend/models/source.py)
# 4. Store transcript in Supabase Storage if available (blob storage)
# 5. Pass transcript text + analysis mode flags forward to Gemini
#
# Rules:
# - Transcript failure does NOT stop the pipeline
# - Gemini analysis ALWAYS runs regardless of transcript availability
# - Analysis mode must be passed explicitly to Gemini:
#   - "transcript_grounded" (Supadata success)
#   - "caption_grounded" (YouTube captions fallback)
#   - "video_only" (no transcript available)
#
# Integration Points:
# - Input: List of video URLs from source discovery
# - Output: List of sources with transcript_provenance populated
# - Storage: Transcripts stored as blobs in Supabase Storage
# - Forward: Gemini receives analysis_mode parameter
#
# See: RASS Section 8, Validation Rules Section 12
# =============================================================================


# =============================================================================
# Gemini Video Extraction Task (Phase 1.5)
# =============================================================================

@celery_app.task(
    name="backend.worker.run_gemini_video_job",
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def run_gemini_video_job(job_id: str) -> dict:
    """
    Celery task for Full Research Assistant Pipeline.

    Phase 3 (Jan 2026) - 4-Pass Analysis:
    - Pass 1: Extraction (clips, quotes) → ProducerPacket
    - Pass 2: Structure Analysis → ContentBlueprint per video
    - Pass 3: Gap Analysis → Missing perspectives, unanswered questions
    - Pass 4: Research Starter → Actionable search queries, source suggestions

    Features:
    - Per-video error handling (partial failures don't kill job)
    - Per-pass progress updates (frontend shows "Pass 2/4: Analyzing structure...")
    - Extended timeout (30 min for long videos)

    Args:
        job_id: Unique identifier for the video extraction job

    Returns:
        Dict with job_id, status, all pipeline outputs, and errors
    """
    from backend.integrations.gemini_client import GeminiClient

    logger.info(f"[{job_id}] Starting Full Research Assistant Pipeline")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    video_urls = job.config_json.get("video_urls", [])
    model = job.config_json.get("model", "gemini-2.5-flash")
    research_topic = job.config_json.get("title", "Video Research")

    if not video_urls:
        logger.error(f"[{job_id}] No video URLs provided")
        update_job(job_id, status="failed", stage="error")
        return {"job_id": job_id, "status": "failed", "error": "No video URLs"}

    total = len(video_urls)
    logger.info(f"[{job_id}] Processing {total} videos with {model}")

    # Update status to running
    update_job(
        job_id,
        status="running",
        stage="pass_1_extraction",
        progress_percent=5,
    )

    # H-007: Progress callback with error handling
    # H-003: Progress updated per video within each pass
    def progress_callback(pass_num: int, total_passes: int, status: str, detail: str):
        """Safe progress callback that won't crash the worker."""
        try:
            # Map progress: Pass 1 = 5-25%, Pass 2 = 25-50%, Pass 3 = 50-75%, Pass 4 = 75-95%
            base_progress = 5 + ((pass_num - 1) / total_passes) * 90
            progress = int(base_progress)

            stage_names = {
                1: "pass_1_extraction",
                2: "pass_2_structure",
                3: "pass_3_gaps",
                4: "pass_4_research",
            }

            update_job(
                job_id,
                stage=stage_names.get(pass_num, f"pass_{pass_num}"),
                progress_percent=progress,
                config_json={
                    **job.config_json,
                    "current_pass": pass_num,
                    "total_passes": total_passes,
                    "pass_status": status,
                    "pass_detail": detail,
                },
            )
            logger.info(f"[{job_id}] Pass {pass_num}/{total_passes}: {detail}")
        except Exception as e:
            # H-007: Log but don't crash the worker
            logger.warning(f"[{job_id}] Progress update failed: {e}")

    try:
        client = GeminiClient()
        result = client.run_full_analysis_pipeline(
            video_urls=video_urls,
            research_topic=research_topic,
            model=model,
            progress_callback=progress_callback,
        )

        # Update job with results
        if result["status"] == "failed":
            # H-013: Include pipeline_errors in warnings for visibility
            all_warnings = [result.get("error", "Pipeline failed")]
            all_warnings.extend(result.get("pipeline_errors", []))
            update_job(
                job_id,
                status="failed",
                stage="error",
                warnings=all_warnings,
            )
            return {"job_id": job_id, "status": "failed", "error": result.get("error")}

        # Generate ProducerPacket with quality gate
        from backend.pipeline.dual_output import create_producer_packet_from_gemini, TriageLevel
        from backend.models.job_record import Artifacts

        title = job.config_json.get("title", f"Video Analysis {job_id[:8]}")

        # Build batch result format for ProducerPacket
        batch_result = {
            "clips": result.get("clips", []),
            "quotes": result.get("quotes", []),
            "results": result.get("results", []),  # Pass through video metadata
            "total_cost": result.get("total_cost", 0),
        }

        producer_packet = create_producer_packet_from_gemini(
            gemini_results=batch_result,
            title=title,
            transcripts=None,
        )

        # Check quality gate and triage level
        passes_gate, gate_issues = producer_packet.passes_quality_gate()
        triage_level, triage_reasons = producer_packet.triage()
        warnings = []

        if result.get("extraction_errors"):
            warnings.extend([e.get("error", str(e)) for e in result["extraction_errors"]])
        
        # H-013: Include pipeline_errors in warnings
        if result.get("pipeline_errors"):
            warnings.extend(result["pipeline_errors"])

        if not passes_gate:
            warnings.extend([f"Quality gate: {issue}" for issue in gate_issues])
            logger.warning(f"[{job_id}] Quality gate not passed: {gate_issues}")
            logger.info(f"[{job_id}] Triage level: {triage_level.value}, reasons: {triage_reasons}")

        # M-008: Consistent dataclass serialization pattern using safe_to_dict
        from backend.integrations.gemini_client import safe_to_dict
        
        content_blueprints_dicts = [
            safe_to_dict(bp) for bp in result.get("content_blueprints", [])
        ]
        gap_analysis_dict = safe_to_dict(result.get("gap_analysis"))
        research_starter_dict = safe_to_dict(result.get("research_starter"))

        # Build artifacts with all pipeline outputs
        # Use processed clips/quotes from producer_packet (has video_url, verification_level)
        # NOT raw clips from result (missing required fields for frontend display)
        artifacts = Artifacts(
            clips=[c.to_dict() for c in producer_packet.clips],
            quotes=[q.to_dict() for q in producer_packet.quotes],
            producer_packet=producer_packet.to_dict(),
            quality_gate_passed=passes_gate,
            # Phase 3 additions
            content_blueprints=content_blueprints_dicts,
            gap_analysis=gap_analysis_dict,
            research_starter=research_starter_dict,
        )

        # Determine appropriate final status based on triage and warnings
        final_status = "completed"
        
        # Use failed_insufficient for FAILED triage (nothing usable)
        if triage_level == TriageLevel.FAILED:
            final_status = "failed_insufficient"
            logger.warning(f"[{job_id}] Triage FAILED - marking as failed_insufficient")
        elif result.get("status") == "completed_with_errors":
            final_status = "completed_with_warnings"  # Downgrade to partial success
        elif result.get("status") == "completed_with_warnings":
            final_status = "completed_with_warnings"
        elif warnings or triage_level in (TriageLevel.THIN, TriageLevel.USABLE):
            final_status = "completed_with_warnings"
        
        # Set error message for failed_insufficient
        error_msg = None
        if final_status == "failed_insufficient":
            error_msg = f"Insufficient extraction: {'; '.join(triage_reasons + gate_issues)}"
        
        update_job(
            job_id,
            status=final_status,
            stage="completed",
            progress_percent=100,
            artifacts=artifacts,
            warnings=warnings if warnings else None,
            error=error_msg,
        )

        videos_processed = result.get("videos_processed", 0)
        videos_failed = result.get("videos_failed", 0)
        total_cost = result.get("total_cost", 0)

        logger.info(
            f"[{job_id}] Full pipeline completed: "
            f"status={final_status}, "
            f"{videos_processed} videos, "
            f"{len(result.get('clips', []))} clips, "
            f"{len(producer_packet.quotes)} quotes, "
            f"{len(content_blueprints_dicts)} blueprints, "
            f"triage={triage_level.value}, "
            f"quality_gate={'PASS' if passes_gate else 'FAIL'}, "
            f"${total_cost:.4f}"
        )

        return {
            "job_id": job_id,
            "status": final_status,
            "clips": len(result.get("clips", [])),
            "quotes": len(producer_packet.quotes),
            "content_blueprints": len(content_blueprints_dicts),
            "has_gap_analysis": gap_analysis_dict is not None,
            "has_research_starter": research_starter_dict is not None,
            "videos_processed": videos_processed,
            "videos_failed": videos_failed,
            "total_cost": total_cost,
            "quality_gate_passed": passes_gate,
            "triage_level": triage_level.value,
        }

    except SoftTimeLimitExceeded:
        # C-005: Handle Celery soft timeout (25 min) gracefully
        logger.error(f"[{job_id}] Pipeline timed out after 25 minutes")
        update_job(
            job_id,
            status="failed",
            stage="timeout",
            error="Pipeline timed out. Try processing fewer videos or shorter videos.",
            warnings=["Task exceeded 25 minute time limit"],
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Pipeline timed out after 25 minutes",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Full pipeline failed: {e}")
        update_job(
            job_id,
            status="failed",
            stage="error",
            error=str(e),
            warnings=[f"Pipeline failed: {str(e)}"],
        )
        return {"job_id": job_id, "status": "failed", "error": str(e)}
