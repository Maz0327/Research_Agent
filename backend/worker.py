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
    # NOTE: Legacy fallbacks removed (2026-01-19 - new pipeline only)
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
        "backend.worker.run_iteration_task": {"queue": "research"},
        "backend.worker.run_booster_task": {"queue": "research"},
        "backend.worker.run_iterate_task": {"queue": "research"},
        "backend.worker.run_producer_task": {"queue": "research"},
        "backend.worker.run_blog_post_task": {"queue": "research"},
        "backend.worker.run_script_task": {"queue": "research"},
        "backend.worker.run_social_kit_task": {"queue": "research"},
        "backend.worker.run_claim_extraction_job": {"queue": "research"},
    },
    task_default_queue="research",
    task_default_exchange="research",
    task_default_routing_key="research",
    # Phase 1.5: Extended timeouts for Gemini video processing
    # Default 30 min for long video analysis
    task_time_limit=1800,  # 30 min hard limit
    task_soft_time_limit=1500,  # 25 min soft limit (allows cleanup)
)


# NOTE: Slack integration removed (2026-01-19 - New pipeline only)


@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(
    job_id: str,
    topic: str,
    slack_payload: Optional[dict] = None,  # DEPRECATED: kept for backward compatibility
    enable_parallel: bool = True,  # DEPRECATED: no longer used
) -> dict:
    """
    Research job task - USER-SUPPLIED SOURCES ONLY (New Pipeline).

    Updated 2026-01-19: Legacy discovery pipeline removed.
    This task now ONLY processes user-supplied sources (mixed-input mode).
    Topic-based discovery is no longer supported.

    Pipeline stages:
    1. Source Identity (resolve analysis modes from user inputs)
    2. Semantic Extraction (Gemini - per source, isolated)
    3. Semantic Validation (confidence ceilings, quote verification)
    4. Gap Analysis (identify missing coverage)
    5. Semantic Synthesis (cross-source themes, tensions)
    6. Document Assembly (Doc 20/21/22)
    7. Completion (artifact manifest, Supabase storage)

    Args:
        job_id: Unique identifier for the research job
        topic: Research topic/title (for labeling only)
        slack_payload: DEPRECATED - ignored
        enable_parallel: DEPRECATED - ignored

    Returns:
        Dictionary with job results
    """
    from backend.pipeline.context import PipelineContext
    from backend.pipeline.cost_tracker import CostTracker

    logger.info(f"Starting research job {job_id} for topic: {topic}")

    # Create pipeline context with cost tracker
    ctx = PipelineContext(
        job_id=job_id,
        topic=topic,
        cost_tracker=CostTracker(mode="full"),
    )

    try:
        job = get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # ONLY mixed-input jobs are supported (user-supplied sources)
        if job.config_json.get("input_mode") != "mixed":
            # Legacy topic-based jobs are no longer supported
            logger.error(f"[{job_id}] Legacy topic-based job rejected - only mixed-input supported")
            update_job(
                job_id,
                status="failed",
                stage="error",
                error="Legacy topic-based discovery is no longer supported. Use /video-analysis, /text-input, /screenshot-input, or /mixed-input endpoints.",
            )
            return {
                "job_id": job_id,
                "status": "failed",
                "error": "Legacy topic-based discovery not supported",
            }

        logger.info(f"[{job_id}] Running semantic-only pipeline (user-supplied sources)")
        return _run_mixed_input_job(ctx, job)

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

        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


def _run_mixed_input_job(ctx, job) -> dict:
    """
    Process a mixed-input job (Phase 5).

    Skips discovery stages (0-6.5) since sources are user-provided.
    Runs semantic pipeline directly with provided videos, articles, and text.

    Args:
        ctx: PipelineContext with job_id and topic
        job: JobRecord with config_json containing mixed inputs

    Returns:
        Dictionary with research results
    """
    from backend.pipeline.stages import (
        stage_semantic_extraction,
        stage_semantic_validation,
        stage_gap_analysis,
        stage_semantic_synthesis,
        stage_distillation,
        stage_document_assembly,
        stage_10_completion,
    )
    from backend.pipeline.stages.creator_brief_stage import run_creator_brief_stage
    from backend.pipeline.stages.duplicate_detection import stage_duplicate_detection
    from backend.pipeline.stages.harvest_stage import stage_harvest
    from backend.pipeline.stages.source_identity import (
        build_source_identity_from_video,
        build_source_identity_from_article,
        build_source_identity_from_text,
        build_source_identity_from_screenshot,
        _merge_supadata_metadata,
    )
    from backend.integrations.supadata_client import fetch_video_metadata
    from backend.integrations.web_capture import (
        _fetch_url_content,
        _extract_text_with_trafilatura,
        extract_byline_from_html,
        extract_title_from_html,
        fetch_via_wayback,
    )
    from backend.integrations.gemini_client import GeminiClient
    import base64
    import tempfile
    import os

    config = job.config_json or {}
    job_id = ctx.job_id

    logger.info(f"[{job_id}] Running mixed-input semantic pipeline")

    # Update status
    update_job(job_id, status="running", stage="source_identity", progress_percent=5)

    try:
        # Build source identity packages from provided inputs
        # Pre-assign indices by input type so source_ids are deterministic even in parallel
        video_urls = config.get("video_urls", [])
        article_urls = config.get("article_urls", [])
        video_offset = 0
        article_offset = len(video_urls)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        # --- Process videos in parallel (transcript acquisition is the bottleneck) ---
        def _fetch_video(args: tuple) -> tuple:
            """Returns (orig_idx, pkg_or_None, warning_or_None)."""
            orig_idx, url = args
            source_index = video_offset + orig_idx
            try:
                video_data = {"url": url}
                pkg = build_source_identity_from_video(video_data, source_index)
                try:
                    metadata = fetch_video_metadata(url)
                    if metadata:
                        _merge_supadata_metadata(pkg, metadata)
                        logger.info(f"[{job_id}] Metadata merged: title={pkg.title[:50]}...")
                except Exception as meta_err:
                    logger.warning(f"[{job_id}] Metadata fetch failed (non-blocking): {meta_err}")
                return orig_idx, pkg, None
            except Exception as e:
                return orig_idx, None, f"Failed to process video {url}: {e}"

        video_pkgs: list = [None] * len(video_urls)
        if video_urls:
            logger.info(f"[{job_id}] Processing {len(video_urls)} videos in parallel")
            with ThreadPoolExecutor(max_workers=min(len(video_urls), 5)) as executor:
                futures = {
                    executor.submit(_fetch_video, (i, url)): i
                    for i, url in enumerate(video_urls)
                }
                for future in as_completed(futures):
                    orig_idx, pkg, warning = future.result()
                    video_pkgs[orig_idx] = (pkg, warning)

        source_counter = 1
        for orig_idx, result in enumerate(video_pkgs):
            if result is None:
                continue
            pkg, warning = result
            if pkg is not None:
                ctx.source_identity_packages.append(pkg)
                source_counter += 1
            elif warning:
                ctx.add_warning(warning)
                logger.warning(f"[{job_id}] {warning}")

        # --- Process articles in parallel (HTTP fetch + extraction is the bottleneck) ---
        def _extract_from_html(html: str, url: str) -> tuple[Optional[str], Optional[str], dict]:
            """Pull text, title, and byline out of fetched HTML."""
            return (
                _extract_text_with_trafilatura(html, url),
                extract_title_from_html(html, url),
                extract_byline_from_html(html, url),
            )

        def _fetch_article(args: tuple) -> tuple:
            """Returns (orig_idx, pkg_or_None, warning_or_None)."""
            orig_idx, url = args
            source_index = article_offset + orig_idx
            try:
                from backend.utils.content_filter import (
                    filter_content_or_warn,
                    needs_fetch_fallback,
                )

                text_content: Optional[str] = None
                article_title: Optional[str] = None
                byline: dict = {"creator": None, "published": None, "sitename": None}
                route = "direct"

                # Route 1: direct HTTP fetch.
                html_content, status_code, error_msg = _fetch_url_content(url)
                if html_content:
                    text_content, article_title, byline = _extract_from_html(html_content, url)

                # A fetch can "succeed" and still return nothing usable: a
                # navigation-only page (Perseus 503, 08-17) or a JS shell
                # (Substack). Both look like content to everything downstream.
                fallback_needed, reason = needs_fetch_fallback(text_content or "")
                if html_content is None:
                    fallback_needed = True
                    reason = f"HTTP {status_code or 'error'}: {error_msg}"

                # Route 2: Jina Reader renders the page.
                if fallback_needed:
                    logger.info(f"[{job_id}] Falling back for {url[:50]} ({reason})")
                    try:
                        from backend.integrations.jina_reader_client import JinaReaderClient

                        jina_content = JinaReaderClient().extract(url).get("content", "")
                        if jina_content and not needs_fetch_fallback(jina_content)[0]:
                            text_content = jina_content
                            route = "jina"
                            fallback_needed = False
                            for line in jina_content.splitlines():
                                stripped = line.strip()
                                if stripped.startswith("# "):
                                    article_title = article_title or stripped[2:].strip()
                                    break
                            logger.info(
                                f"[{job_id}] Jina recovered {len(jina_content)} chars for {url[:50]}"
                            )
                    except Exception as jina_err:
                        logger.warning(f"[{job_id}] Jina fallback failed for {url[:50]}: {jina_err}")

                # Route 3: the Internet Archive still has what the live page lost.
                if fallback_needed:
                    archived_html, snapshot_url = fetch_via_wayback(url)
                    if archived_html:
                        archived_text, archived_title, archived_byline = _extract_from_html(
                            archived_html, url
                        )
                        if archived_text and not needs_fetch_fallback(archived_text)[0]:
                            text_content = archived_text
                            article_title = article_title or archived_title
                            byline = {
                                key: byline.get(key) or archived_byline.get(key)
                                for key in ("creator", "published", "sitename")
                            }
                            route = f"wayback ({snapshot_url})"
                            fallback_needed = False

                if fallback_needed or not text_content:
                    return orig_idx, None, f"No usable content for {url}: {reason}"

                filtered = filter_content_or_warn(
                    text_content,
                    source_id=f"SRC_{source_index + 1}",
                    url=url,
                )
                if filtered is None:
                    return orig_idx, None, f"Blocked content detected from {url} — skipped"

                article_data: dict = {"url": url, "content": filtered}
                if article_title:
                    article_data["title"] = article_title
                if byline["creator"]:
                    article_data["author"] = byline["creator"]
                if byline["published"]:
                    article_data["published"] = byline["published"]
                if byline["sitename"]:
                    article_data["sitename"] = byline["sitename"]
                pkg = build_source_identity_from_article(article_data, source_index)
                logger.info(
                    f"[{job_id}] Article fetched via {route}: {len(filtered)} chars from {url[:50]}"
                )
                return orig_idx, pkg, None
            except Exception as e:
                return orig_idx, None, f"Failed to process article {url}: {e}"

        article_pkgs: list = [None] * len(article_urls)
        if article_urls:
            logger.info(f"[{job_id}] Processing {len(article_urls)} articles in parallel")
            with ThreadPoolExecutor(max_workers=min(len(article_urls), 5)) as executor:
                futures = {
                    executor.submit(_fetch_article, (i, url)): i
                    for i, url in enumerate(article_urls)
                }
                for future in as_completed(futures):
                    orig_idx, pkg, warning = future.result()
                    article_pkgs[orig_idx] = (pkg, warning)

        for orig_idx, result in enumerate(article_pkgs):
            if result is None:
                continue
            pkg, warning = result
            if pkg is not None:
                ctx.source_identity_packages.append(pkg)
                source_counter += 1
            elif warning:
                ctx.add_warning(warning)
                logger.warning(f"[{job_id}] {warning}")

        # Process text inputs
        for text_input in config.get("text_inputs", []):
            logger.info(f"[{job_id}] Building identity for text: {text_input.get('title', 'Untitled')}")
            try:
                # build_source_identity_from_text expects (content, source_label, source_index, context_note, platform_hint)
                pkg = build_source_identity_from_text(
                    content=text_input.get("content", ""),
                    source_label=text_input.get("title", "User-provided text"),
                    source_index=source_counter - 1,
                    platform_hint=text_input.get("platform_hint"),
                )
                ctx.source_identity_packages.append(pkg)
                source_counter += 1
            except Exception as e:
                ctx.add_warning(f"Failed to process text input: {e}")
                logger.warning(f"[{job_id}] Text processing failed: {e}")

        # Process screenshots with OCR
        for screenshot in config.get("screenshots", []):
            filename = screenshot.get("filename", "screenshot.png")
            logger.info(f"[{job_id}] Processing screenshot with OCR: {filename}")
            try:
                # Decode base64 to temp file
                base64_data = screenshot.get("base64", "")
                if not base64_data:
                    ctx.add_warning(f"No base64 data for screenshot {filename}")
                    continue

                # Handle data URL format if present
                if "," in base64_data:
                    base64_data = base64_data.split(",", 1)[1]

                # Decode and save to temp file
                image_bytes = base64.b64decode(base64_data)

                # Determine file extension
                ext = os.path.splitext(filename)[1].lower() or ".png"
                if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    ext = ".png"

                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
                    tmp_file.write(image_bytes)
                    temp_path = tmp_file.name

                try:
                    # Run OCR with Gemini Vision
                    gemini_client = GeminiClient()
                    ocr_prompt = (
                        "Extract all visible text from this image. "
                        "Return the text exactly as it appears, preserving formatting. "
                        "If there is no readable text, respond with 'NO_TEXT_FOUND'."
                    )
                    ocr_result = gemini_client.analyze_image(temp_path, ocr_prompt)
                    ocr_text = ocr_result.get("text", "").strip()

                    if ocr_text == "NO_TEXT_FOUND" or not ocr_text:
                        ctx.add_warning(f"No text extracted from screenshot {filename}")
                        logger.warning(f"[{job_id}] No text in screenshot {filename}")
                        continue

                    logger.info(f"[{job_id}] OCR extracted {len(ocr_text)} chars from {filename}")

                    # Build source identity from OCR text
                    platform_hint = screenshot.get("platform_hint", "other")
                    pkg = build_source_identity_from_screenshot(
                        ocr_text=ocr_text,
                        source_index=source_counter - 1,
                        platform_hint=platform_hint,
                        original_image_path=temp_path,
                    )
                    ctx.source_identity_packages.append(pkg)
                    source_counter += 1

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

            except Exception as e:
                ctx.add_warning(f"Failed to process screenshot {filename}: {e}")
                logger.warning(f"[{job_id}] Screenshot OCR failed: {e}")

        # Check we have at least one source
        if not ctx.source_identity_packages:
            raise ValueError("No valid sources after processing - all inputs failed")

        logger.info(f"[{job_id}] Built {len(ctx.source_identity_packages)} source identity packages")

        # Mark syndicated copies before anything counts sources, so four
        # printings of one wire story never read as four sources agreeing.
        stage_duplicate_detection(ctx)

        # Run semantic pipeline stages
        update_job(job_id, stage="semantic_extraction", progress_percent=20)
        run_stage_with_recovery(stage_semantic_extraction, ctx, "semantic_extraction")

        update_job(job_id, stage="semantic_validation", progress_percent=35)
        run_stage_with_recovery(stage_semantic_validation, ctx, "semantic_validation")

        # Dense per-source facts. Extraction abstracts; this keeps the concrete
        # material, and its inventory is what the Briefing's coverage gate
        # checks the finished document against.
        run_stage_with_recovery(stage_harvest, ctx, "fact_harvest")

        update_job(job_id, stage="gap_analysis", progress_percent=50)
        run_stage_with_recovery(stage_gap_analysis, ctx, "gap_analysis")

        update_job(job_id, stage="semantic_synthesis", progress_percent=65)
        run_stage_with_recovery(stage_semantic_synthesis, ctx, "semantic_synthesis")

        # Claim Graph distillation. Non-critical while the legacy documents are
        # still the primary output: a Claude outage should degrade to the old
        # docs plus a recorded warning rather than fail the whole job. This
        # flips to critical=True at P8, when legacy docs retire and every
        # document projects from the graph.
        update_job(job_id, stage="distillation", progress_percent=72)
        run_stage_with_recovery(stage_distillation, ctx, "distillation")

        update_job(job_id, stage="document_assembly", progress_percent=80)
        run_stage_with_recovery(stage_document_assembly, ctx, "document_assembly")

        # Stage F: Creator Brief assembly (Doc 3) — non-fatal
        run_stage_with_recovery(run_creator_brief_stage, ctx, "creator_brief")

        # NOTE: Drive upload removed (2026-01-19 - outputs go to Supabase Storage)

        # Completion (stores docs in artifacts, exports in Supabase Storage)
        update_job(job_id, stage="completion", progress_percent=95)
        return stage_10_completion(ctx)

    except Exception as e:
        logger.exception(f"[{job_id}] Mixed-input job failed: {e}")
        update_job(
            job_id,
            status="failed",
            error=str(e),
            warnings=ctx.warnings,
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


# NOTE: _run_disambiguated_job removed (2026-01-19)
# Disambiguation relied on legacy topic-based discovery which is no longer supported.
# The select-interpretation endpoint now returns 410 Gone.


# =============================================================================
# Transcript Extraction Task
# =============================================================================

@celery_app.task(name="backend.worker.run_transcript_job")
def run_transcript_job(job_id: str) -> dict:
    """
    Celery task for async transcript extraction.

    Updated 2026-01-19: Stores transcripts in Supabase Storage instead of Drive.

    Processes large batches of YouTube videos (>5) in the background.
    Updates job progress as each video is processed.

    Args:
        job_id: Unique identifier for the transcript job

    Returns:
        Dict with job_id, status, and storage path
    """
    from datetime import datetime
    from backend.services.transcript_service import (
        extract_single_transcript,
        format_transcripts_for_doc,
    )
    from backend.integrations.supabase_storage import get_storage_client
    from backend.models.job_record import Artifacts
    import json

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
        # Update progress (5% start, 85% for extraction, 10% for storage)
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

    # Stage: Store transcripts in Supabase Storage
    logger.info(f"[{job_id}] Storing transcripts")
    update_job(job_id, stage="storing_transcripts", progress_percent=90)

    try:
        if not doc_title:
            doc_title = f"YouTube Transcripts - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        content = format_transcripts_for_doc(transcripts)

        # Store in Supabase Storage
        storage_client = get_storage_client()
        storage_path = None
        signed_url = None

        if storage_client:
            try:
                upload_result = storage_client.upload_attachment(
                    job_id=job_id,
                    filename="transcripts.md",
                    content=content,
                    expires_in=3600,
                )
                storage_path = upload_result["storage_path"]
                signed_url = upload_result["signed_url"]
                logger.info(f"[{job_id}] Transcripts stored at {storage_path}")
            except Exception as storage_error:
                warnings.append(f"Storage upload failed: {storage_error}")
                logger.warning(f"[{job_id}] Storage upload failed: {storage_error}")

        # Build artifacts with transcript data
        artifacts = Artifacts(
            artifact_manifest={
                "transcripts": {
                    "present": True,
                    "title": doc_title,
                    "storage_path": storage_path,
                    "video_count": total,
                    "available_count": sum(1 for t in transcripts if t.status == "available"),
                },
            },
        )

        # Also store transcript content inline for immediate access
        update_job(
            job_id,
            status="completed",
            progress_percent=100,
            stage="completed",
            artifacts=artifacts,
            warnings=warnings,
            partial_outputs={"transcripts_md": content},
        )

        logger.info(f"[{job_id}] Transcript job completed")

        return {
            "job_id": job_id,
            "status": "completed",
            "storage_path": storage_path,
            "signed_url": signed_url,
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Failed to store transcripts: {e}")
        warnings.append(f"Failed to store transcripts: {str(e)}")

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


# =============================================================================
# Evolving Job Task (Phase 6 - Add Sources to Completed Jobs)
# =============================================================================

@celery_app.task(
    name="backend.worker.process_evolving_job",
    bind=True,
    max_retries=3,
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def process_evolving_job(self, job_id: str, user_id: str) -> dict:
    """
    Process pending sources for an evolving job.

    Per EXTENDED_SPECIFICATIONS.md Part 2, this task:
    1. Retrieves original extractions from completed job
    2. Extracts each pending source (isolation preserved)
    3. Validates new extractions
    4. Runs cross-reference stage (old vs new comparison)
    5. Generates addendum sections
    6. Appends to existing docs
    7. Updates source statuses

    Original document content is preserved (frozen).
    New content is appended in a clearly marked addendum section.

    Args:
        job_id: ID of the evolving job
        user_id: ID of the user who triggered the task

    Returns:
        Dict with job_id, status, and summary of changes
    """
    from backend.pipeline.context import PipelineContext
    from backend.pipeline.cost_tracker import CostTracker
    from backend.pipeline.stage_runner import run_stage_with_recovery
    from backend.pipeline.stages.source_identity import (
        build_source_identity_from_video,
        build_source_identity_from_article,
        build_source_identity_from_text,
        _merge_supadata_metadata,
    )
    from backend.integrations.supadata_client import fetch_video_metadata
    from backend.pipeline.stages import (
        stage_semantic_extraction,
        stage_semantic_validation,
        stage_gap_analysis,
    )
    from backend.pipeline.stages.cross_reference import stage_cross_reference
    from backend.models.semantic_units import SemanticExtractionResult

    logger.info(f"[{job_id}] Starting evolving job processing")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    config = job.config_json or {}
    pending_sources = config.get("pending_sources", [])
    pending_text_inputs = config.get("pending_text_inputs", [])

    if not pending_sources:
        logger.warning(f"[{job_id}] No pending sources to process")
        update_job(job_id, status="completed", stage="no_pending_sources")
        return {"job_id": job_id, "status": "completed", "message": "No pending sources"}

    logger.info(f"[{job_id}] Processing {len(pending_sources)} pending sources")

    # Create pipeline context for evolving job
    ctx = PipelineContext(
        job_id=job_id,
        topic=config.get("topic", ""),
        cost_tracker=CostTracker(mode="full"),
    )

    # Mark context as evolving job
    ctx.is_evolving_job = True

    try:
        # Update status
        update_job(
            job_id,
            status="running",
            stage="evolving_source_identity",
            progress_percent=10,
        )

        # Build source identity packages for pending sources
        text_inputs_by_title = {ti.get("title"): ti for ti in pending_text_inputs}

        for i, source_data in enumerate(pending_sources):
            source_id = source_data.get("source_id")
            source_type = source_data.get("source_type")
            url = source_data.get("url")
            title = source_data.get("title")

            # Extract source index from source_id (e.g., "SRC_3" -> 2)
            # Fall back to loop index if source_id format doesn't match
            try:
                source_index = int(source_id.replace("SRC_", "")) - 1 if source_id else i
            except (ValueError, AttributeError):
                source_index = i

            logger.info(f"[{job_id}] Building identity for {source_type}: {url or title}")

            try:
                if source_type == "youtube":
                    video_data = {"url": url, "title": title} if title else {"url": url}
                    pkg = build_source_identity_from_video(video_data, source_index)

                    # Fetch and merge Supadata metadata for title/creator/duration
                    try:
                        metadata = fetch_video_metadata(url)
                        if metadata:
                            _merge_supadata_metadata(pkg, metadata)
                            logger.info(f"[{job_id}] Metadata merged: title={pkg.title[:50]}...")
                    except Exception as meta_err:
                        logger.warning(f"[{job_id}] Metadata fetch failed (non-blocking): {meta_err}")

                elif source_type == "article":
                    article_data = {"url": url, "title": title} if title else {"url": url}
                    pkg = build_source_identity_from_article(article_data, source_index)
                elif source_type == "user_text":
                    # Get content from pending_text_inputs
                    text_input = text_inputs_by_title.get(title, {})
                    pkg = build_source_identity_from_text(
                        content=text_input.get("content", ""),
                        source_label=title or "User-provided text",
                        source_index=source_index,
                        platform_hint=text_input.get("platform_hint"),
                    )
                else:
                    ctx.add_warning(f"Unknown source type: {source_type}")
                    continue

                ctx.source_identity_packages.append(pkg)

            except Exception as e:
                ctx.add_warning(f"Failed to process source {source_id}: {e}")
                logger.warning(f"[{job_id}] Source processing failed: {e}")

        # Check we have at least one source
        if not ctx.source_identity_packages:
            raise ValueError("No valid sources after processing - all inputs failed")

        logger.info(
            f"[{job_id}] Built {len(ctx.source_identity_packages)} "
            f"source identity packages for pending sources"
        )

        # Stage 1: Extract new sources
        update_job(job_id, stage="evolving_extraction", progress_percent=25)
        run_stage_with_recovery(stage_semantic_extraction, ctx, "semantic_extraction")

        # Stage 2: Validate new extractions
        update_job(job_id, stage="evolving_validation", progress_percent=40)
        run_stage_with_recovery(stage_semantic_validation, ctx, "semantic_validation")

        # Stage 3: Gap analysis for new sources
        update_job(job_id, stage="evolving_gap_analysis", progress_percent=55)
        run_stage_with_recovery(stage_gap_analysis, ctx, "gap_analysis")

        # Load original extractions from job artifacts
        # These would have been stored when the original job completed
        original_extractions = _load_original_extractions(job)
        ctx.original_extractions = original_extractions

        # Stage 4: Cross-reference (compare new vs original)
        update_job(job_id, stage="cross_reference", progress_percent=70)
        run_stage_with_recovery(stage_cross_reference, ctx, "cross_reference")

        # Stage 5: Build and store addendum
        update_job(job_id, stage="addendum_assembly", progress_percent=85)
        _build_and_store_addendum(ctx, job)

        # Clear pending sources from config
        config_update = job.config_json.copy() if job.config_json else {}
        config_update["pending_sources"] = []
        config_update["pending_text_inputs"] = []

        # Track which sources were processed
        processed_source_ids = [s.get("source_id") for s in pending_sources]
        config_update["last_addendum_sources"] = processed_source_ids

        # Update job status
        update_job(
            job_id,
            status="completed",
            stage="evolving_complete",
            progress_percent=100,
            config_json=config_update,
        )

        # Get summary
        cross_ref = getattr(ctx, "cross_reference_notes", None)
        summary = {
            "sources_processed": len(ctx.source_identity_packages),
            "extractions_created": len(getattr(ctx, "semantic_extractions", [])),
            "supports_found": len(cross_ref.supports) if cross_ref else 0,
            "contradicts_found": len(cross_ref.contradicts) if cross_ref else 0,
            "new_tensions": len(cross_ref.new_tensions) if cross_ref else 0,
            "new_gaps": len(cross_ref.new_gaps) if cross_ref else 0,
        }

        logger.info(
            f"[{job_id}] Evolving job complete: "
            f"{summary['sources_processed']} sources, "
            f"{summary['supports_found']} supports, "
            f"{summary['contradicts_found']} contradicts"
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "summary": summary,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Evolving job timed out after 25 minutes")
        update_job(
            job_id,
            status="failed",
            stage="timeout",
            error="Processing timed out. Try adding fewer sources.",
        )
        return {"job_id": job_id, "status": "failed", "error": "Timed out"}

    except Exception as e:
        logger.exception(f"[{job_id}] Evolving job failed: {e}")
        update_job(
            job_id,
            status="failed",
            stage="error",
            error=str(e),
            warnings_append=ctx.warnings + [f"Evolving job error: {str(e)}"],
        )
        return {"job_id": job_id, "status": "failed", "error": str(e)}


def _load_original_extractions(job) -> list:
    """
    Load original semantic extractions from job artifacts.

    Extractions are stored when the original job completes.
    This function reconstructs SemanticExtractionResult objects.
    """
    from backend.models.semantic_units import (
        SemanticExtractionResult,
        AnalysisMode,
        ConfidenceLevel,
        Quote,
        Claim,
        KeyPoint,
        Theme,
        Tension,
    )

    extractions = []

    # Check if extractions are stored in artifacts
    if not job.artifacts:
        logger.warning(f"[{job.job_id}] No artifacts found for original job")
        return extractions

    # Get stored extractions data
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else {}
    stored_extractions = artifacts_dict.get("semantic_extractions", [])

    for ext_data in stored_extractions:
        try:
            # Reconstruct the extraction result
            extraction = SemanticExtractionResult(
                source_id=ext_data.get("source_id", ""),
                analysis_mode=AnalysisMode(ext_data.get("analysis_mode", "text_provided")),
            )

            # Reconstruct key points
            for kp_data in ext_data.get("key_points", []):
                kp = KeyPoint(
                    key_point_id=kp_data.get("key_point_id", ""),
                    statement=kp_data.get("statement", ""),
                    source_ids=kp_data.get("source_ids", []),
                    confidence=ConfidenceLevel(kp_data.get("confidence", "medium")),
                )
                extraction.key_points.append(kp)

            # Reconstruct themes
            for t_data in ext_data.get("themes", []):
                theme = Theme(
                    theme_id=t_data.get("theme_id", ""),
                    label=t_data.get("label", ""),
                    description=t_data.get("description", ""),
                    related_key_points=t_data.get("related_key_points", []),
                )
                extraction.themes.append(theme)

            # Reconstruct tensions
            for ten_data in ext_data.get("tensions", []):
                tension = Tension(
                    tension_id=ten_data.get("tension_id", ""),
                    description=ten_data.get("description", ""),
                    involved_key_points=ten_data.get("involved_key_points", []),
                )
                extraction.tensions.append(tension)

            extractions.append(extraction)

        except Exception as e:
            logger.warning(f"Failed to reconstruct extraction: {e}")

    logger.info(f"[{job.job_id}] Loaded {len(extractions)} original extractions")
    return extractions


def _build_and_store_addendum(ctx, job) -> None:
    """
    Build addendum section and store in job artifacts.

    This function:
    1. Creates AddendumSection with new content
    2. Appends to existing documents
    3. Stores updated documents in artifacts
    """
    from datetime import datetime, timezone
    from backend.models.document_outputs import AddendumSection
    from backend.models.job_record import Artifacts

    # Get new extractions
    new_extractions = getattr(ctx, "semantic_extractions", [])
    cross_ref = getattr(ctx, "cross_reference_notes", None)

    # Build addendum section
    addendum = AddendumSection(
        added_at=datetime.now(timezone.utc).isoformat(),
        source_ids=[pkg.source_id for pkg in ctx.source_identity_packages],
    )

    # Populate from new extractions
    for extraction in new_extractions:
        addendum.new_key_points.extend(extraction.key_points)
        addendum.new_themes.extend(extraction.themes)
        addendum.new_tensions.extend(extraction.tensions)

    # Add gaps from gap analysis
    addendum.new_gaps = getattr(ctx, "identified_gaps", [])

    # Add cross-reference notes
    addendum.cross_reference = cross_ref

    # Store addendum in context
    ctx.addendum_sections = addendum

    # Get existing artifacts
    existing_artifacts = job.artifacts.model_dump(exclude_none=True) if job.artifacts else {}

    # Store new extractions for future evolving jobs
    new_extractions_data = [e.to_dict() for e in new_extractions]

    # Append to existing extractions
    all_extractions = existing_artifacts.get("semantic_extractions", [])
    all_extractions.extend(new_extractions_data)

    # Store addendum
    addendums = existing_artifacts.get("addendums", [])
    addendums.append(addendum.to_dict())

    # Update artifacts
    artifacts_update = {
        **existing_artifacts,
        "semantic_extractions": all_extractions,
        "addendums": addendums,
        "last_addendum_at": datetime.now(timezone.utc).isoformat(),
    }

    # Create updated artifacts object
    updated_artifacts = Artifacts(**artifacts_update)

    # Store in job
    update_job(
        ctx.job_id,
        artifacts=updated_artifacts,
    )

    logger.info(
        f"[{ctx.job_id}] Stored addendum with "
        f"{len(addendum.new_key_points)} key points, "
        f"{len(addendum.new_themes)} themes, "
        f"{len(addendum.new_gaps)} gaps"
    )


# =============================================================================
# Deep Research Booster Task (Phase 7)
# =============================================================================

@celery_app.task(
    name="backend.worker.run_booster",
    bind=True,
    max_retries=2,
    time_limit=600,  # 10 min hard limit
    soft_time_limit=540,  # 9 min soft limit
)
def run_booster_task(self, job_id: str, user_id: str, run_id: str = None) -> dict:
    """
    Run Deep Research Booster for a completed job.

    Per GAPS_AND_BOOSTER_SPEC.md Part 2, this task:
    1. Generates a Context Bundle from job output (auto-generated)
    2. Calls Gemini with booster prompt (higher temp for creativity)
    3. Validates output for grounding (gap_id/theme_id references)
    4. Appends "Deep Research Expansion" section to Doc 1

    CRITICAL: The booster produces DIRECTIONS, not FACTS.
    Booster failure does NOT affect existing documents.

    V2 Run Abstraction: When run_id is provided, booster output is stored
    in run-scoped storage under jobs/{job_id}/runs/{run_id}/booster_output.json.

    Prerequisites:
    - Job must be in 'completed' or 'completed_with_warnings' status
    - Doc 1 (JumpStartDirections) must exist
    - Doc 2 (SemanticBrief) must exist

    Args:
        job_id: ID of the completed job
        user_id: ID of the user who triggered the booster
        run_id: Optional run ID for run-scoped storage (V2)

    Returns:
        Dict with job_id, status, cost, and summary
    """
    from backend.pipeline.booster.context_bundle_generator import generate_context_bundle
    from backend.pipeline.stages.booster_stage import run_booster, booster_output_to_dict
    from backend.pipeline.booster.expansion_builder import build_booster_expansion_markdown

    logger.info(f"[{job_id}] Starting Deep Research Booster")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    # Verify job status (main pipeline must be completed)
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status not in ("completed", "completed_with_warnings"):
        error_msg = f"Job must be completed to run booster. Current: {job_status}"
        logger.error(f"[{job_id}] {error_msg}")
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    # Check if booster is already running (prevent duplicate runs)
    booster_status = job.booster_status if hasattr(job, "booster_status") else None
    if booster_status == "running":
        error_msg = "Booster is already running for this job"
        logger.warning(f"[{job_id}] {error_msg}")
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    # Get artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Verify required docs exist
    jump_start = artifacts_dict.get("jump_start")
    semantic_brief = artifacts_dict.get("semantic_brief")
    extractions = artifacts_dict.get("semantic_extractions", [])

    # Check for storage paths if inline data missing
    doc_1_path = artifacts_dict.get("doc_1_path")
    doc_2_path = artifacts_dict.get("doc_2_path")

    if not jump_start and doc_1_path:
        try:
            from backend.integrations.supabase_storage import get_storage_client
            storage = get_storage_client()
            if storage:
                jump_start_raw = storage.download_document(doc_1_path)
                # Storage wraps docs in {"data": {...}, "markdown": "..."} - unwrap if needed
                if isinstance(jump_start_raw, dict) and "data" in jump_start_raw:
                    jump_start = jump_start_raw["data"]
                    logger.info(f"[{job_id}] Unwrapped jump_start from storage wrapper")
                else:
                    jump_start = jump_start_raw
                artifacts_dict["jump_start"] = jump_start
                logger.info(f"[{job_id}] Fetched jump_start from storage")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to fetch jump_start: {e}")

    if not semantic_brief and doc_2_path:
        try:
            from backend.integrations.supabase_storage import get_storage_client
            storage = get_storage_client()
            if storage:
                semantic_brief_raw = storage.download_document(doc_2_path)
                # Storage wraps docs in {"data": {...}, "markdown": "..."} - unwrap if needed
                if isinstance(semantic_brief_raw, dict) and "data" in semantic_brief_raw:
                    semantic_brief = semantic_brief_raw["data"]
                    logger.info(f"[{job_id}] Unwrapped semantic_brief from storage wrapper")
                else:
                    semantic_brief = semantic_brief_raw
                artifacts_dict["semantic_brief"] = semantic_brief
                logger.info(f"[{job_id}] Fetched semantic_brief from storage")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to fetch semantic_brief: {e}")

    if not jump_start or not semantic_brief:
        error_msg = "Doc 1 (JumpStartDirections) and Doc 2 (SemanticBrief) must exist"
        logger.error(f"[{job_id}] {error_msg}")
        # Restore to completed status (booster failure doesn't affect core docs)
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    try:
        # Update booster status (DO NOT modify job.status - it must stay "completed")
        from datetime import datetime, timezone
        update_job(
            job_id,
            booster_status="running",
            booster_started_at=datetime.now(timezone.utc),
            booster_progress_percent=0,
            booster_error=None,  # Clear any previous error
        )

        # Generate context bundle (auto-generated, user provides nothing)
        logger.info(f"[{job_id}] Generating context bundle")
        bundle = generate_context_bundle(
            job_id=job_id,
            jump_start=jump_start,
            semantic_brief=semantic_brief,
            extractions=extractions,
        )

        logger.info(
            f"[{job_id}] Context bundle: "
            f"{len(bundle.themes)} themes, "
            f"{len(bundle.gaps)} gaps, "
            f"{len(bundle.tensions)} tensions"
        )

        # Run booster (calls Gemini with higher temperature)
        logger.info(f"[{job_id}] Running booster generation")
        booster_output, cost, warnings = run_booster(bundle)

        # Build expansion markdown for Doc 1
        expansion_md = build_booster_expansion_markdown(booster_output)

        # Update jump_start with booster expansion
        booster_dict = booster_output_to_dict(booster_output)  # Cache to avoid redundant calls
        updated_jump_start = jump_start.copy() if isinstance(jump_start, dict) else {}
        updated_jump_start["booster_expansion"] = booster_dict
        updated_jump_start["booster_expansion_md"] = expansion_md

        # Merge booster items into research threads (if threads exist)
        from backend.pipeline.stages.document_assembly import merge_booster_into_threads_dict
        updated_jump_start = merge_booster_into_threads_dict(
            updated_jump_start, booster_dict
        )

        # Summary for partial_outputs
        booster_summary = {
            "perspectives_count": len(booster_output.missing_perspectives),
            "source_directions_count": len(booster_output.primary_source_directions),
            "queries_count": len(booster_output.suggested_search_queries),
            "questions_count": len(booster_output.research_questions),
            "total_directions": booster_output.total_directions,
            "cost": cost,
            "warnings": warnings,
        }

        # V2 Run-scoped storage vs V1 job-level storage
        if run_id:
            # V2: Store in run-scoped path
            from backend.pipeline.runs.storage import store_run_booster
            from backend.models.run_models import (
                ensure_runs_migrated, RunBoosterExpansion, RunStatus
            )

            output_path, md_path = store_run_booster(
                job_id, run_id, booster_dict, expansion_md
            )

            # Update run in artifacts.runs with booster data
            runs = ensure_runs_migrated(
                artifacts_dict,
                job_created_at=job.created_at if hasattr(job, "created_at") else None,
                job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
                user_id=user_id,
            )

            # Find and update the target run
            for run in runs:
                if run.run_id == run_id:
                    run.booster_expansion = RunBoosterExpansion(
                        status=RunStatus.COMPLETED,
                        completed_at=datetime.now(timezone.utc),
                        output=booster_dict,
                        markdown=expansion_md,
                    )
                    break

            # Store runs back in artifacts + persist merged jump_start
            updated_artifacts = artifacts_dict.copy()
            updated_artifacts["runs"] = [r.model_dump() for r in runs]
            updated_artifacts["jump_start"] = updated_jump_start

            logger.info(f"[{job_id}] Booster stored in run-scoped path: {output_path}")
        else:
            # V1: Store at job level (legacy)
            updated_artifacts = artifacts_dict.copy()
            updated_artifacts["jump_start"] = updated_jump_start
            updated_artifacts["booster_output"] = booster_dict
            updated_artifacts["booster_expansion_md"] = expansion_md

        # Store partial_outputs in config_json
        config = job.config_json.copy() if job.config_json else {}
        config["booster_summary"] = booster_summary

        # Update job - mark booster completed (DO NOT modify job.status)
        update_job(
            job_id,
            # DO NOT set status - job.status must remain "completed"
            partial_artifacts=updated_artifacts,  # Use partial_artifacts for atomic merge
            config_json=config,
            warnings_append=warnings if warnings else None,
            # Booster tracking
            booster_status="completed",
            booster_completed_at=datetime.now(timezone.utc),
            booster_progress_percent=100,
        )

        logger.info(
            f"[{job_id}] Booster complete: "
            f"{booster_output.total_directions} directions, "
            f"cost=${cost:.4f}, {len(warnings)} warnings"
        )

        return {
            "job_id": job_id,
            "status": "success",
            "cost": cost,
            "warnings": warnings,
            "summary": booster_summary,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Booster timed out after 9 minutes")
        # Mark booster failed (DO NOT modify job.status - core docs remain accessible)
        update_job(
            job_id,
            booster_status="failed",
            booster_completed_at=datetime.now(timezone.utc),
            booster_error="Booster timed out after 9 minutes",
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Booster timed out",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Booster failed: {e}")
        # Mark booster failed (DO NOT modify job.status - core docs remain accessible)
        update_job(
            job_id,
            booster_status="failed",
            booster_completed_at=datetime.now(timezone.utc),
            booster_error=str(e)[:500],  # Truncate long errors
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# UNIFIED ITERATE TASK (Phase 3 — all 5 modes through one Celery task)
# =============================================================================

@celery_app.task(
    name="backend.worker.run_iterate_task",
    bind=True,
    max_retries=1,
    time_limit=1200,   # 20 min hard limit
    soft_time_limit=1080,  # 18 min soft limit
)
def run_iterate_task(self, job_id: str, iterate_id: str, user_id: str, params: dict) -> dict:
    """
    Unified Iterate task — dispatches to mode handler and stores new document versions.

    Supported modes:
      deep_dive       — gap analysis + search directions; new Doc 1 version
      expand_sources  — add sources, re-run pipeline; new Doc 0/1/2/3 versions
      deeper          — re-extract with depth; new Doc 0/1/2/3 versions
      different_angle — new perspective; new Doc 2/3 versions
      custom          — user-defined; new Doc 2/3 versions

    Args:
        job_id: Completed job UUID
        iterate_id: Unique iterate ID (iter_<timestamp>)
        user_id: ID of the requesting user
        params: Mode-specific params dict (mode, new_source_urls, angle, user_prompt, etc.)

    Returns:
        Dict with job_id, iterate_id, mode, status, versions_created
    """
    from datetime import datetime, timezone
    from backend.pipeline.version_manager import store_document_version

    mode = params.get("mode", "")
    logger.info(f"[{job_id}] Iterate task start: mode={mode}, iterate_id={iterate_id}")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Iterate: job not found")
        return {"job_id": job_id, "iterate_id": iterate_id, "status": "failed", "error": "Job not found"}

    artifacts = job.artifacts
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    start_time = datetime.now(timezone.utc)
    versions_created: list[str] = []

    # Update iteration status to running (DO NOT modify job.status - it must stay "completed")
    update_job(
        job_id,
        iteration_status="running",
        iteration_started_at=start_time,
        iteration_error=None,  # Clear any previous error
    )

    try:
        # ── DEEP DIVE ────────────────────────────────────────────────────────
        if mode == "deep_dive":
            from backend.pipeline.context import PipelineContext
            from backend.pipeline.iteration.metrics_tracker import MetricsTracker
            from backend.pipeline.iteration.modes.deep_dive import run_deep_dive

            ctx = PipelineContext(job_id=job_id, job_config=None)
            metrics = MetricsTracker()
            updated_doc1 = run_deep_dive(ctx, artifacts_dict, metrics)

            version, _url = store_document_version(
                job_id=job_id,
                doc_type="doc_1",
                content=updated_doc1,
                trigger="deep_dive",
                markdown=updated_doc1.get("markdown"),
            )
            versions_created.append(f"doc_1 v{version}")
            logger.info(f"[{job_id}] deep_dive complete: doc_1 v{version}")

        # ── INLINE EDIT ─────────────────────────────────────────────────────
        elif mode == "inline_edit":
            from backend.pipeline.stages.inline_edit_stage import run_inline_edit

            doc_type = params.get("doc_type", "")
            section_id = params.get("section_id", "")
            edit_instruction = params.get("edit_instruction", "")

            if not doc_type or not section_id or not edit_instruction:
                raise ValueError("inline_edit requires doc_type, section_id, and edit_instruction")

            updated_doc, cost, edit_warnings = run_inline_edit(
                job_id=job_id,
                doc_type=doc_type,
                section_id=section_id,
                edit_instruction=edit_instruction,
            )

            # Update job artifacts with the edited document
            # Map doc_type to artifact key names
            _doc_artifact_keys = {
                "doc_5": ("script", "script_md", "doc_5_path"),
                "doc_6": ("social_kit", "social_kit_md", "doc_6_path"),
                "doc_7": ("blog_post", "blog_post_md", "doc_7_path"),
            }
            if doc_type in _doc_artifact_keys:
                data_key, _md_key, _path_key = _doc_artifact_keys[doc_type]
                update_job(
                    job_id,
                    partial_artifacts={data_key: updated_doc},
                )

            versions_created.append(f"{doc_type} (inline edit: {section_id})")
            logger.info(f"[{job_id}] inline_edit complete: {doc_type}/{section_id}")

        # ── OTHER MODES — delegate to existing iteration pipeline ────────────
        else:
            from backend.pipeline.iteration import (
                load_baseline,
                create_iteration_context,
                store_iteration_docs,
            )
            from backend.pipeline.iteration.modes import run_iteration_mode
            from backend.pipeline.iteration.metrics_tracker import MetricsTracker

            baseline = load_baseline(job_id, artifacts_dict)
            ctx = create_iteration_context(job_id, iterate_id, baseline, mode)
            metrics = MetricsTracker()

            doc_0, doc_1, doc_2 = run_iteration_mode(
                mode=mode,
                ctx=ctx,
                baseline=baseline,
                metrics=metrics,
                user_prompt=params.get("user_prompt", ""),
                max_new_sources=params.get("max_new_sources", 4),
                angle=params.get("angle") or None,
            )

            # Determine which docs this mode affects, then store new versions
            docs_affected = {
                "expand_sources": ["doc_0", "doc_1", "doc_2"],
                "deeper":         ["doc_0", "doc_1", "doc_2"],
                "different_angle": ["doc_1", "doc_2"],
                "custom":         ["doc_1", "doc_2"],
            }.get(mode, ["doc_1", "doc_2"])

            doc_map = {"doc_0": doc_0, "doc_1": doc_1, "doc_2": doc_2}
            for doc_type in docs_affected:
                doc_content = doc_map.get(doc_type)
                if doc_content:
                    version, _url = store_document_version(
                        job_id=job_id,
                        doc_type=doc_type,
                        content=doc_content if isinstance(doc_content, dict)
                                else {"data": doc_content},
                        trigger=mode,
                    )
                    versions_created.append(f"{doc_type} v{version}")

            # Also regenerate Creator Brief (Doc 3) for modes that touch Doc 2
            if "doc_2" in docs_affected and doc_2:
                try:
                    from backend.pipeline.stages.creator_brief_stage import run_creator_brief_stage
                    ctx.outputs["semantic_brief"] = doc_2 if isinstance(doc_2, dict) else {"data": doc_2}

                    # Populate source context so Creator Brief has proper provenance data
                    if doc_0:
                        ctx.source_ledger = doc_0 if isinstance(doc_0, dict) else {"sources": []}
                    if not getattr(ctx, "semantic_extractions", None):
                        # Pull from stored semantic_brief key_points as fallback
                        brief = doc_2 if isinstance(doc_2, dict) else {}
                        ctx.semantic_extractions = getattr(ctx, "semantic_extractions", [])

                    ctx = run_creator_brief_stage(ctx)
                    cb = ctx.outputs.get("creator_brief")
                    cb_md = ctx.outputs.get("creator_brief_md")
                    if cb:
                        version, _url = store_document_version(
                            job_id=job_id,
                            doc_type="doc_3",
                            content={"data": cb, "markdown": cb_md},
                            trigger=mode,
                            markdown=cb_md,
                        )
                        versions_created.append(f"doc_3 v{version}")
                except Exception as cb_err:
                    logger.warning(f"[{job_id}] Creator Brief re-gen skipped after {mode}: {cb_err}")

            logger.info(f"[{job_id}] {mode} complete: versions={versions_created}")

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        elapsed_r = round(elapsed, 1)

        # Store iteration record for history (Task 3.2.6)
        from backend.pipeline.version_manager import store_iteration_record
        store_iteration_record(
            job_id=job_id,
            iterate_id=iterate_id,
            mode=mode,
            versions_created=versions_created,
            elapsed_seconds=elapsed_r,
        )

        # Mark iteration completed (DO NOT modify job.status - it must stay "completed")
        update_job(
            job_id,
            iteration_status="completed",
            iteration_completed_at=datetime.now(timezone.utc),
            iteration_id=iterate_id,
        )

        return {
            "job_id": job_id,
            "iterate_id": iterate_id,
            "mode": mode,
            "status": "success",
            "versions_created": versions_created,
            "elapsed_seconds": elapsed_r,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Iterate task timed out (mode={mode})")
        update_job(job_id, iteration_status="failed", iteration_error="Iterate timed out")
        return {"job_id": job_id, "iterate_id": iterate_id, "mode": mode, "status": "failed",
                "error": "Iterate timed out"}

    except Exception as exc:
        logger.exception(f"[{job_id}] Iterate task failed (mode={mode}): {exc}")
        update_job(job_id, iteration_status="failed", iteration_error=str(exc)[:500])
        return {"job_id": job_id, "iterate_id": iterate_id, "mode": mode, "status": "failed",
                "error": str(exc)[:500]}


# =============================================================================
# PRODUCER PACKET TASK (Phase 8 - Doc 3 Generation)
# =============================================================================

@celery_app.task(
    bind=True,
    name="backend.worker.run_producer_task",
    max_retries=1,
    soft_time_limit=300,  # 5 min soft limit
)
def run_producer_task(self, job_id: str, user_id: str, run_id: str = None) -> dict:
    """
    Generate Producer Packet (Doc 3) for a completed job.

    Per RASS.md Stage G, this task:
    1. Verifies gating requirements (4+ sources, 1 high-confidence, completed)
    2. Runs 4-stage producer pipeline (Story Core → Structure → Creative → Risk)
    3. Generates creative interpretation (NOT facts)
    4. Stores Doc 3 in artifacts

    CRITICAL: Doc 3 is CREATIVE INTERPRETATION.
    Producer failure does NOT affect Doc 0/1/2.

    V2 Run Abstraction: When run_id is provided, producer packet is stored
    in run-scoped storage under jobs/{job_id}/runs/{run_id}/producer_packet.json.

    Prerequisites:
    - Job must be in 'completed' status
    - 4+ sources with at least 1 high-confidence
    - User explicitly requests (handled by endpoint)

    Args:
        job_id: ID of the completed job
        user_id: ID of the user who triggered producer packet
        run_id: Optional run ID for run-scoped storage (V2)

    Returns:
        Dict with job_id, status, cost, and summary
    """
    from backend.pipeline.producer.gating import can_generate_producer_packet
    from backend.pipeline.stages.producer_stage import run_producer_pipeline

    logger.info(f"[{job_id}] Starting Producer Packet generation")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    # Get job as dict for gating check
    if hasattr(job, "model_dump"):
        job_dict = job.model_dump(exclude_none=True)
    elif hasattr(job, "__dict__"):
        job_dict = {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
    else:
        job_dict = dict(job) if isinstance(job, dict) else {}

    # Ensure artifacts are in job_dict for gating check
    if hasattr(job, "artifacts"):
        if hasattr(job.artifacts, "model_dump"):
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        elif isinstance(job.artifacts, dict):
            artifacts_dict = job.artifacts
        else:
            artifacts_dict = {}

        # Check if we need to fetch source_ledger from storage
        source_ledger = artifacts_dict.get("source_ledger")
        doc_0_path = artifacts_dict.get("doc_0_path")

        # Determine if source_ledger has actual sources (not just structure)
        def _has_sources(sl: dict | None) -> bool:
            if not sl or not isinstance(sl, dict):
                return False
            # Check direct source_manifest
            if sl.get("source_manifest"):
                return True
            # Check nested data.source_manifest (storage format)
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            # Also check sources array (SourceLedger.to_dict() format)
            if sl.get("sources"):
                return True
            if isinstance(data, dict) and data.get("sources"):
                return True
            return False

        needs_storage_fetch = doc_0_path and not _has_sources(source_ledger)

        if needs_storage_fetch:
            # Fetch source_ledger from storage
            try:
                from backend.integrations.supabase_storage import get_storage_client
                storage = get_storage_client()
                if storage:
                    doc_0_data = storage.download_document(doc_0_path)
                    artifacts_dict["source_ledger"] = doc_0_data
                    logger.info(f"[{job_id}] Fetched source_ledger from storage for gating")
                else:
                    logger.warning(f"[{job_id}] Storage client unavailable - cannot fetch source_ledger")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to fetch source_ledger: {e}")

        job_dict["artifacts"] = artifacts_dict

        # Fetch semantic_brief (Doc 2) from storage if needed for producer pipeline
        doc_2_path = artifacts_dict.get("doc_2_path")
        semantic_brief = artifacts_dict.get("semantic_brief")

        def _has_semantic_content(sb: dict | None) -> bool:
            """Check if semantic_brief has actual content (themes/key_points)."""
            if not sb or not isinstance(sb, dict):
                return False
            # Check direct themes or key_points
            if sb.get("themes") or sb.get("key_points"):
                return True
            # Check nested data format (storage download format)
            data = sb.get("data")
            if isinstance(data, dict):
                if data.get("themes") or data.get("key_points"):
                    return True
            return False

        needs_doc2_fetch = doc_2_path and not _has_semantic_content(semantic_brief)

        if needs_doc2_fetch:
            try:
                from backend.integrations.supabase_storage import get_storage_client
                storage = get_storage_client()
                if storage:
                    doc_2_data = storage.download_document(doc_2_path)
                    artifacts_dict["semantic_brief"] = doc_2_data
                    job_dict["artifacts"] = artifacts_dict
                    logger.info(f"[{job_id}] Fetched semantic_brief from storage for producer")
                else:
                    logger.warning(f"[{job_id}] Storage client unavailable - cannot fetch semantic_brief")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to fetch semantic_brief: {e}")

    # Verify gating requirements
    can_generate, reason = can_generate_producer_packet(job_dict)
    if not can_generate:
        error_msg = f"Gating failed: {reason}"
        logger.error(f"[{job_id}] {error_msg}")
        return {"job_id": job_id, "status": "failed", "error": error_msg}

    try:
        # Update producer status (DO NOT modify job.status - it must stay "completed")
        from datetime import datetime, timezone
        update_job(
            job_id,
            producer_status="running",
            producer_progress_percent=10,
        )

        # Run producer pipeline
        logger.info(f"[{job_id}] Running producer pipeline")
        packet, cost, warnings = run_producer_pipeline(job_id, job_dict)

        # Summary for API response
        producer_summary = {
            "narrative_angles": len(packet.narrative_angles),
            "opening_hooks": len(packet.opening_hooks),
            "structure_options": len(packet.structure_options),
            "title_options": len(packet.title_options),
            "key_moments": len(packet.key_moments),
            "cost": cost,
            "warnings": warnings,
        }

        # Get existing artifacts
        artifacts = job.artifacts if hasattr(job, "artifacts") else None
        if artifacts and hasattr(artifacts, "model_dump"):
            artifacts_dict = artifacts.model_dump(exclude_none=True)
        elif isinstance(artifacts, dict):
            artifacts_dict = artifacts
        else:
            artifacts_dict = {}

        packet_dict = packet.to_dict()
        packet_md = packet.to_markdown()

        # V2 Run-scoped storage vs V1 job-level storage
        if run_id:
            # V2: Store in run-scoped path
            from backend.pipeline.runs.storage import store_run_producer
            from backend.models.run_models import (
                ensure_runs_migrated, RunProducerPacket, RunStatus
            )

            packet_path, md_path = store_run_producer(
                job_id, run_id, packet_dict, packet_md
            )

            # Update run in artifacts.runs with producer data
            runs = ensure_runs_migrated(
                artifacts_dict,
                job_created_at=job.created_at if hasattr(job, "created_at") else None,
                job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
                user_id=user_id,
            )

            # Find and update the target run
            for run in runs:
                if run.run_id == run_id:
                    run.producer_packet = RunProducerPacket(
                        status=RunStatus.COMPLETED,
                        completed_at=datetime.now(timezone.utc),
                        path=packet_path,
                        inline=packet_dict,
                        markdown=packet_md,
                    )
                    break

            # Store runs back in artifacts
            partial_artifacts = {"runs": [r.model_dump() for r in runs]}

            logger.info(f"[{job_id}] Producer stored in run-scoped path: {packet_path}")
        else:
            # V1: Store at job level (legacy)
            partial_artifacts = {
                "producer_packet": packet_dict,
                "producer_packet_md": packet_md,
            }

        # Store summary in config_json
        config = job.config_json.copy() if job.config_json else {}
        config["producer_summary"] = producer_summary

        # Update job - mark producer as completed (DO NOT modify job.status)
        # Use partial_artifacts for atomic merge (required when using warnings_append)
        update_job(
            job_id,
            # DO NOT change job.status - it must stay "completed"
            partial_artifacts=partial_artifacts,
            config_json=config,
            warnings_append=warnings if warnings else None,
            # Producer tracking
            producer_status="completed",
            producer_completed_at=datetime.now(timezone.utc),
            producer_progress_percent=100,
        )

        # NOTE: Drive upload removed (2026-01-19 - Doc 3 stored in artifacts)

        logger.info(
            f"[{job_id}] Producer packet complete: "
            f"{len(packet.narrative_angles)} angles, "
            f"{len(packet.title_options)} titles, "
            f"cost=${cost:.4f}, {len(warnings)} warnings"
        )

        return {
            "job_id": job_id,
            "status": "success",
            "cost": cost,
            "warnings": warnings,
            "summary": producer_summary,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Producer packet timed out after 5 minutes")
        # Mark producer as failed (DO NOT modify job.status)
        update_job(
            job_id,
            producer_status="failed",
            producer_completed_at=datetime.now(timezone.utc),
            producer_error="Producer packet timed out after 5 minutes",
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Producer packet timed out",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Producer packet failed: {e}")
        # Mark producer as failed (DO NOT modify job.status)
        update_job(
            job_id,
            producer_status="failed",
            producer_completed_at=datetime.now(timezone.utc),
            producer_error=str(e),
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# BLOG POST TASK (Doc 7 — user-triggered)
# =============================================================================

@celery_app.task(
    bind=True,
    name="backend.worker.run_blog_post_task",
    max_retries=1,
    soft_time_limit=300,  # 5 min soft limit
)
def run_blog_post_task(self, job_id: str, user_id: str) -> dict:
    """Generate Blog Post (Doc 7) for a completed job.

    Args:
        job_id: ID of the completed job.
        user_id: ID of the user who triggered blog post.

    Returns:
        Dict with job_id, status, cost, and summary.
    """
    from backend.pipeline.stages.blog_post_stage import run_blog_post_stage
    from backend.pipeline.formatters.blog_post_formatter import format_blog_post
    from backend.pipeline.version_manager import store_document_version

    logger.info(f"[{job_id}] Starting Blog Post generation")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    # Get job as dict
    if hasattr(job, "model_dump"):
        job_dict = job.model_dump(exclude_none=True)
    elif hasattr(job, "__dict__"):
        job_dict = {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
    else:
        job_dict = dict(job) if isinstance(job, dict) else {}

    # Ensure artifacts dict
    if hasattr(job, "artifacts"):
        if hasattr(job.artifacts, "model_dump"):
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        elif isinstance(job.artifacts, dict):
            artifacts_dict = job.artifacts
        else:
            artifacts_dict = {}
        job_dict["artifacts"] = artifacts_dict
    else:
        artifacts_dict = {}

    try:
        from datetime import datetime, timezone

        # Update status
        update_job(
            job_id,
            blog_post_status="running",
            blog_post_progress_percent=10,
        )

        # Run blog post stage
        blog_post, cost, warnings = run_blog_post_stage(job_id, job_dict)

        # Format as markdown
        blog_post_dict = blog_post.model_dump(mode="json")
        blog_post_md = format_blog_post(blog_post)

        # Store via version manager
        version_num, storage_path = store_document_version(
            job_id=job_id,
            doc_type="doc_7",
            content=blog_post_dict,
            trigger="initial_run",
            markdown=blog_post_md,
        )

        # Store in artifacts
        partial_artifacts = {
            "blog_post": blog_post_dict,
            "blog_post_md": blog_post_md,
            "doc_7_path": storage_path,
        }

        update_job(
            job_id,
            partial_artifacts=partial_artifacts,
            warnings_append=warnings if warnings else None,
            blog_post_status="completed",
            blog_post_completed_at=datetime.now(timezone.utc),
            blog_post_progress_percent=100,
        )

        logger.info(
            f"[{job_id}] Blog Post complete: "
            f"{len(blog_post.sections)} sections, "
            f"cost=${cost:.4f}, {len(warnings)} warnings"
        )

        return {
            "job_id": job_id,
            "status": "success",
            "cost": cost,
            "warnings": warnings,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Blog post timed out after 5 minutes")
        from datetime import datetime, timezone as _tz
        update_job(
            job_id,
            blog_post_status="failed",
            blog_post_completed_at=datetime.now(_tz.utc),
            blog_post_error="Blog post timed out after 5 minutes",
        )
        return {"job_id": job_id, "status": "failed", "error": "Blog post timed out"}

    except Exception as e:
        logger.exception(f"[{job_id}] Blog post failed: {e}")
        from datetime import datetime, timezone as _tz
        update_job(
            job_id,
            blog_post_status="failed",
            blog_post_completed_at=datetime.now(_tz.utc),
            blog_post_error=str(e),
        )
        return {"job_id": job_id, "status": "failed", "error": str(e)}


# =============================================================================
# SOCIAL KIT TASK (Doc 6 — user-triggered)
# =============================================================================

@celery_app.task(
    bind=True,
    name="backend.worker.run_social_kit_task",
    max_retries=1,
    soft_time_limit=300,
)
def run_social_kit_task(self, job_id: str, user_id: str, params: dict = None) -> dict:
    """Generate Social Media Kit (Doc 6) for a completed job.

    Args:
        job_id: ID of the completed job.
        user_id: ID of the user.
        params: Optional dict with platforms, tone.

    Returns:
        Dict with job_id, status, cost.
    """
    from backend.pipeline.stages.social_kit_stage import run_social_kit_stage
    from backend.pipeline.formatters.social_kit_formatter import format_social_kit
    from backend.pipeline.version_manager import store_document_version

    params = params or {}
    logger.info(f"[{job_id}] Starting Social Kit generation")

    job = get_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    if hasattr(job, "model_dump"):
        job_dict = job.model_dump(exclude_none=True)
    elif hasattr(job, "__dict__"):
        job_dict = {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
    else:
        job_dict = dict(job) if isinstance(job, dict) else {}

    if hasattr(job, "artifacts"):
        if hasattr(job.artifacts, "model_dump"):
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        elif isinstance(job.artifacts, dict):
            artifacts_dict = job.artifacts
        else:
            artifacts_dict = {}
        job_dict["artifacts"] = artifacts_dict

    try:
        from datetime import datetime, timezone
        update_job(job_id, social_kit_status="running", social_kit_progress_percent=10)

        kit, cost, warnings = run_social_kit_stage(
            job_id=job_id,
            job_data=job_dict,
            platforms=params.get("platforms"),
            tone=params.get("tone", "professional"),
        )

        kit_dict = kit.model_dump(mode="json")
        kit_md = format_social_kit(kit)

        version_num, storage_path = store_document_version(
            job_id=job_id, doc_type="doc_6",
            content=kit_dict, trigger="initial_run", markdown=kit_md,
        )

        partial_artifacts = {
            "social_kit": kit_dict,
            "social_kit_md": kit_md,
            "doc_6_path": storage_path,
        }

        update_job(
            job_id,
            partial_artifacts=partial_artifacts,
            warnings_append=warnings if warnings else None,
            social_kit_status="completed",
            social_kit_completed_at=datetime.now(timezone.utc),
            social_kit_progress_percent=100,
        )

        logger.info(f"[{job_id}] Social Kit complete: {len(kit.platforms)} platforms, cost=${cost:.4f}")
        return {"job_id": job_id, "status": "success", "cost": cost, "warnings": warnings}

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Social kit timed out")
        from datetime import datetime, timezone as _tz
        update_job(job_id, social_kit_status="failed", social_kit_completed_at=datetime.now(_tz.utc), social_kit_error="Timed out")
        return {"job_id": job_id, "status": "failed", "error": "Social kit timed out"}

    except Exception as e:
        logger.exception(f"[{job_id}] Social kit failed: {e}")
        from datetime import datetime, timezone as _tz
        update_job(job_id, social_kit_status="failed", social_kit_completed_at=datetime.now(_tz.utc), social_kit_error=str(e))
        return {"job_id": job_id, "status": "failed", "error": str(e)}


# =============================================================================
# SCRIPT TASK (Doc 5 — user-triggered)
# =============================================================================

@celery_app.task(
    bind=True,
    name="backend.worker.run_script_task",
    max_retries=1,
    soft_time_limit=300,
)
def run_script_task(self, job_id: str, user_id: str, params: dict = None) -> dict:
    """Generate Script (Doc 5) for a completed job.

    Args:
        job_id: ID of the completed job.
        user_id: ID of the user who triggered script.
        params: Optional dict with tone, target_length, story_arc, voice_profile_id.

    Returns:
        Dict with job_id, status, cost, and summary.
    """
    from backend.pipeline.stages.script_stage import run_script_stage
    from backend.pipeline.formatters.script_formatter import format_script
    from backend.pipeline.version_manager import store_document_version

    params = params or {}
    logger.info(f"[{job_id}] Starting Script generation")

    job = get_job(job_id)
    if not job:
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    if hasattr(job, "model_dump"):
        job_dict = job.model_dump(exclude_none=True)
    elif hasattr(job, "__dict__"):
        job_dict = {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
    else:
        job_dict = dict(job) if isinstance(job, dict) else {}

    if hasattr(job, "artifacts"):
        if hasattr(job.artifacts, "model_dump"):
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        elif isinstance(job.artifacts, dict):
            artifacts_dict = job.artifacts
        else:
            artifacts_dict = {}
        job_dict["artifacts"] = artifacts_dict

    try:
        from datetime import datetime, timezone

        update_job(job_id, script_status="running", script_progress_percent=10)

        script, cost, warnings = run_script_stage(
            job_id=job_id,
            job_data=job_dict,
            tone=params.get("tone", "conversational"),
            target_length=params.get("target_length", "medium"),
            story_arc=params.get("story_arc", ""),
            voice_profile_id=params.get("voice_profile_id"),
        )

        script_dict = script.model_dump(mode="json")
        script_md = format_script(script)

        version_num, storage_path = store_document_version(
            job_id=job_id,
            doc_type="doc_5",
            content=script_dict,
            trigger="initial_run",
            markdown=script_md,
        )

        partial_artifacts = {
            "script": script_dict,
            "script_md": script_md,
            "doc_5_path": storage_path,
        }

        update_job(
            job_id,
            partial_artifacts=partial_artifacts,
            warnings_append=warnings if warnings else None,
            script_status="completed",
            script_completed_at=datetime.now(timezone.utc),
            script_progress_percent=100,
        )

        logger.info(
            f"[{job_id}] Script complete: {len(script.sections)} sections, "
            f"{script.total_word_count} words, cost=${cost:.4f}"
        )

        return {"job_id": job_id, "status": "success", "cost": cost, "warnings": warnings}

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Script timed out")
        from datetime import datetime, timezone as _tz
        update_job(job_id, script_status="failed", script_completed_at=datetime.now(_tz.utc), script_error="Script timed out after 5 minutes")
        return {"job_id": job_id, "status": "failed", "error": "Script timed out"}

    except Exception as e:
        logger.exception(f"[{job_id}] Script failed: {e}")
        from datetime import datetime, timezone as _tz
        update_job(job_id, script_status="failed", script_completed_at=datetime.now(_tz.utc), script_error=str(e))
        return {"job_id": job_id, "status": "failed", "error": str(e)}


# =============================================================================
# V2 RUN TASK HELPER (Run Abstraction)
# =============================================================================

def _run_v2_run_task(job_id: str, run_id: str, user_id: str) -> dict:
    """
    Execute a V2 run using run mode executors.

    Args:
        job_id: Job ID
        run_id: Run ID (run_1, run_2, etc.)
        user_id: User who triggered the run

    Returns:
        Dict with job_id, run_id, status, and outputs
    """
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts
    from backend.models.run_models import (
        Run, RunType, RunStatus, RunOutputs, RunMetrics,
        ensure_runs_migrated,
    )
    from backend.pipeline.runs.modes import run_expand, run_refine, run_regenerate
    from backend.models.run_models import normalize_run_type

    logger.info(f"[{job_id}] Starting V2 run {run_id}")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": "Job not found"}

    # Get artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Get runs and find the target run
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=user_id,
    )

    target_run = None
    run_index = None
    for i, r in enumerate(runs):
        if r.run_id == run_id:
            target_run = r
            run_index = i
            break

    if target_run is None:
        error_msg = f"Run {run_id} not found in artifacts"
        logger.error(f"[{job_id}] {error_msg}")
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": error_msg}

    start_time = datetime.now(timezone.utc)

    try:
        # Update run status to running
        target_run.status = RunStatus.RUNNING
        target_run.started_at = start_time

        # Update job with running status
        update_job(
            job_id,
            iteration_status="running",
            iteration_id=run_id,
            iteration_started_at=start_time,
            iteration_progress_percent=5,
            artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
        )

        # Normalize run type (maps legacy types to canonical)
        raw_run_type = target_run.run_type
        canonical_type = normalize_run_type(raw_run_type.value)
        logger.info(f"[{job_id}] Run {run_id} type={raw_run_type.value} → canonical={canonical_type.value}")

        # Execute the appropriate run mode
        if canonical_type == RunType.EXPAND:
            outputs, metrics_dict = run_expand(
                job_id=job_id,
                run=target_run,
                user_id=user_id,
                artifacts_dict=artifacts_dict,
            )

            # Handle AWAITING_REVIEW: expand with auto-search pauses for user approval
            if target_run.status == RunStatus.AWAITING_REVIEW:
                logger.info(f"[{job_id}] Run {run_id} awaiting user review of search candidates")
                runs[run_index] = target_run
                update_job(
                    job_id,
                    iteration_status="awaiting_review",
                    iteration_id=run_id,
                    iteration_progress_percent=50,
                    artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
                )
                return {
                    "job_id": job_id,
                    "run_id": run_id,
                    "status": "awaiting_review",
                    "run_type": canonical_type.value,
                    "message": "Search candidates ready for user review",
                }

        elif canonical_type == RunType.REFINE:
            outputs, metrics_dict = run_refine(
                job_id=job_id,
                run=target_run,
                user_id=user_id,
                artifacts_dict=artifacts_dict,
            )

        elif canonical_type == RunType.REGENERATE:
            outputs, metrics_dict = run_regenerate(
                job_id=job_id,
                run=target_run,
                user_id=user_id,
                artifacts_dict=artifacts_dict,
            )

        else:
            raise ValueError(f"Unknown run type: {raw_run_type.value} (canonical: {canonical_type.value})")

        end_time = datetime.now(timezone.utc)

        # Update run with success
        target_run.status = RunStatus.COMPLETED
        target_run.completed_at = end_time
        target_run.outputs = outputs
        target_run.metrics = RunMetrics(**metrics_dict) if metrics_dict else None

        # Update runs list
        runs[run_index] = target_run

        # Update job - mark run completed (DO NOT modify job.status)
        update_job(
            job_id,
            iteration_status="completed",
            iteration_id=run_id,
            iteration_completed_at=end_time,
            iteration_progress_percent=100,
            artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
        )

        wall_time_ms = int((end_time - start_time).total_seconds() * 1000)
        logger.info(
            f"[{job_id}] Run {run_id} completed in {wall_time_ms}ms, "
            f"type={canonical_type.value}"
        )

        return {
            "job_id": job_id,
            "run_id": run_id,
            "run_index": target_run.run_index,
            "status": "success",
            "run_type": canonical_type.value,
            "wall_time_ms": wall_time_ms,
            "outputs": outputs.model_dump() if outputs else None,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Run {run_id} timed out")
        _mark_run_failed(job_id, run_id, runs, run_index, artifacts_dict, "Run timed out after 15 minutes")
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": "Run timed out"}

    except Exception as e:
        logger.exception(f"[{job_id}] Run {run_id} failed: {e}")
        _mark_run_failed(job_id, run_id, runs, run_index, artifacts_dict, str(e)[:500])
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": str(e)}


def _resume_expand_after_review(
    job_id: str,
    run_id: str,
    user_id: str,
    approved_urls: list[str],
) -> dict:
    """
    Resume an EXPAND run after the user approves search candidates.

    Called by the approve-sources API endpoint. Picks up where the expand
    executor left off: processes approved URLs, creates Doc 0 delta and
    Doc 1/2 append sections.

    Args:
        job_id: Job ID
        run_id: Run ID (run_1, run_2, etc.)
        user_id: User who approved
        approved_urls: URLs the user approved for processing

    Returns:
        Dict with job_id, run_id, status
    """
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts
    from backend.models.run_models import (
        Run, RunType, RunStatus, RunOutputs, RunMetrics,
        ensure_runs_migrated,
    )
    from backend.pipeline.runs.modes import run_expand

    logger.info(f"[{job_id}] Resuming expand run {run_id} with {len(approved_urls)} approved URLs")

    job = get_job(job_id)
    if not job:
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": "Job not found"}

    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=user_id,
    )

    target_run = None
    run_index = None
    for i, r in enumerate(runs):
        if r.run_id == run_id:
            target_run = r
            run_index = i
            break

    if target_run is None:
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": "Run not found"}

    if target_run.status != RunStatus.AWAITING_REVIEW:
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": f"Run not awaiting review (status={target_run.status.value})"}

    try:
        # Update run: inject approved URLs and set back to RUNNING
        target_run.status = RunStatus.RUNNING
        if target_run.request:
            target_run.request.new_source_urls = approved_urls

        update_job(
            job_id,
            iteration_status="running",
            iteration_id=run_id,
            iteration_progress_percent=55,
            artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
        )

        # Re-execute expand with the approved URLs
        outputs, metrics_dict = run_expand(
            job_id=job_id,
            run=target_run,
            user_id=user_id,
            artifacts_dict=artifacts_dict,
        )

        end_time = datetime.now(timezone.utc)

        target_run.status = RunStatus.COMPLETED
        target_run.completed_at = end_time
        target_run.outputs = outputs
        target_run.metrics = RunMetrics(**metrics_dict) if metrics_dict else None

        runs[run_index] = target_run

        update_job(
            job_id,
            iteration_status="completed",
            iteration_id=run_id,
            iteration_completed_at=end_time,
            iteration_progress_percent=100,
            artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
        )

        return {
            "job_id": job_id,
            "run_id": run_id,
            "status": "success",
            "run_type": "expand",
            "sources_approved": len(approved_urls),
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Resume expand {run_id} failed: {e}")
        _mark_run_failed(job_id, run_id, runs, run_index, artifacts_dict, str(e)[:500])
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": str(e)}


def _mark_run_failed(
    job_id: str,
    run_id: str,
    runs: list,
    run_index: int,
    artifacts_dict: dict,
    error_msg: str,
) -> None:
    """Mark a run as failed and update job."""
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts
    from backend.models.run_models import RunStatus, RunError

    if run_index is not None and run_index < len(runs):
        runs[run_index].status = RunStatus.FAILED
        runs[run_index].completed_at = datetime.now(timezone.utc)
        runs[run_index].error = RunError(code="run_failed", message=error_msg)

    update_job(
        job_id,
        iteration_status="failed",
        iteration_id=run_id,
        iteration_completed_at=datetime.now(timezone.utc),
        iteration_error=error_msg,
        artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
    )


# =============================================================================
# ITERATION TASK (Phase 9 - Append-Only Iteration Loop)
# =============================================================================

@celery_app.task(
    bind=True,
    name="backend.worker.run_iteration_task",
    max_retries=1,
    soft_time_limit=900,  # 15 min soft limit
    time_limit=960,  # 16 min hard limit
)
def run_iteration_task(self, job_id: str, iteration_id: str, user_id: str) -> dict:
    """
    Run an iteration on a completed job.

    Supports both V1 iterations (it_XXXX) and V2 runs (run_X).

    V1 (Legacy): APPEND-ONLY iterations under job.artifacts.iterations[].
    V2 (Run Abstraction): Run-based storage under job.artifacts.runs[].

    This task:
    1. Detects whether this is V1 or V2 based on iteration_id format
    2. For V2: Uses new run mode executors (add_sources, regenerate, etc.)
    3. For V1: Uses legacy iteration modes
    4. NEVER modifies baseline artifacts or job.status

    Args:
        job_id: ID of the completed job
        iteration_id: Iteration/run identifier (it_0001 for V1, run_1 for V2)
        user_id: ID of the user who triggered iteration

    Returns:
        Dict with job_id, iteration_id/run_id, status, and summary
    """
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts, IterationOutputs, IterationMetrics, IterationError

    # Detect V2 run vs V1 iteration
    is_v2_run = iteration_id.startswith("run_")

    if is_v2_run:
        return _run_v2_run_task(job_id, iteration_id, user_id)

    # V1 Legacy iteration handling below
    logger.info(f"[{job_id}] Starting V1 iteration {iteration_id}")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "iteration_id": iteration_id, "status": "failed", "error": "Job not found"}

    # Get artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Find the iteration
    iterations = artifacts_dict.get("iterations", [])
    iteration_index = None
    iteration_data = None
    for i, it in enumerate(iterations):
        if it.get("iteration_id") == iteration_id:
            iteration_index = i
            iteration_data = it
            break

    if iteration_data is None:
        error_msg = f"Iteration {iteration_id} not found in artifacts"
        logger.error(f"[{job_id}] {error_msg}")
        return {"job_id": job_id, "iteration_id": iteration_id, "status": "failed", "error": error_msg}

    # Get iteration request details
    request_data = iteration_data.get("request", {})
    mode = request_data.get("mode", "expand_sources")  # expand_sources = formerly more_sources
    user_prompt = request_data.get("user_prompt", "")
    max_new_sources = request_data.get("max_new_sources", 4)
    angle = request_data.get("angle")

    start_time = datetime.now(timezone.utc)

    try:
        # Update iteration status to running
        iteration_data["status"] = "running"
        iteration_data["started_at"] = start_time.isoformat()
        iterations[iteration_index] = iteration_data

        # Update job with running status
        update_job(
            job_id,
            iteration_status="running",
            iteration_id=iteration_id,
            iteration_started_at=start_time,
            iteration_progress_percent=5,
            artifacts=Artifacts(**{**artifacts_dict, "iterations": iterations}),
        )

        logger.info(f"[{job_id}] Iteration {iteration_id} mode={mode}, max_new_sources={max_new_sources}")

        # =====================================================================
        # ITERATION PIPELINE
        # =====================================================================
        from backend.pipeline.iteration import (
            load_baseline,
            create_iteration_context,
            store_iteration_docs,
        )
        from backend.pipeline.iteration.modes import run_iteration_mode

        # Get job config for topic
        config_dict = {}
        if hasattr(job, "config_json") and job.config_json:
            config_dict = job.config_json if isinstance(job.config_json, dict) else {}

        # Load baseline data from completed job
        baseline = load_baseline(job_id, artifacts_dict, config_dict)

        # Create iteration context and metrics tracker
        ctx, metrics = create_iteration_context(job_id, iteration_id, baseline, mode)

        # Run the appropriate iteration mode
        doc_0, doc_1, doc_2 = run_iteration_mode(
            mode=mode,
            ctx=ctx,
            baseline=baseline,
            metrics=metrics,
            user_prompt=user_prompt,
            max_new_sources=max_new_sources,
            angle=angle,
        )

        # Store iteration outputs to GCS
        outputs = store_iteration_docs(job_id, iteration_id, doc_0, doc_1, doc_2)

        # Finalize metrics
        final_metrics = metrics.finalize()

        end_time = datetime.now(timezone.utc)

        # Update iteration with success
        iteration_data["status"] = "completed"
        iteration_data["completed_at"] = end_time.isoformat()
        iteration_data["outputs"] = outputs.model_dump()
        iteration_data["metrics"] = final_metrics.model_dump()
        iterations[iteration_index] = iteration_data

        # Update job - mark iteration completed (DO NOT modify job.status)
        update_job(
            job_id,
            iteration_status="completed",
            iteration_id=iteration_id,
            iteration_completed_at=end_time,
            iteration_progress_percent=100,
            artifacts=Artifacts(**{**artifacts_dict, "iterations": iterations}),
        )

        logger.info(
            f"[{job_id}] Iteration {iteration_id} completed in {final_metrics.wall_time_ms}ms, "
            f"mode={mode}, llm_calls={final_metrics.llm_calls}"
        )

        return {
            "job_id": job_id,
            "iteration_id": iteration_id,
            "iteration_index": iteration_data.get("index", 0),
            "status": "success",
            "mode": mode,
            "wall_time_ms": final_metrics.wall_time_ms,
            "outputs": outputs.model_dump(),
            "metrics": final_metrics.model_dump(),
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Iteration {iteration_id} timed out after 15 minutes")
        end_time = datetime.now(timezone.utc)

        # Update iteration with error
        iteration_data["status"] = "failed"
        iteration_data["completed_at"] = end_time.isoformat()
        iteration_data["error"] = IterationError(
            message="Iteration timed out after 15 minutes",
            stack=None,
        ).model_dump()
        iterations[iteration_index] = iteration_data

        # Mark iteration failed (DO NOT modify job.status)
        update_job(
            job_id,
            iteration_status="failed",
            iteration_id=iteration_id,
            iteration_completed_at=end_time,
            iteration_error="Iteration timed out after 15 minutes",
            artifacts=Artifacts(**{**artifacts_dict, "iterations": iterations}),
        )

        return {
            "job_id": job_id,
            "iteration_id": iteration_id,
            "status": "failed",
            "error": "Iteration timed out",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Iteration {iteration_id} failed: {e}")
        end_time = datetime.now(timezone.utc)

        # Update iteration with error
        iteration_data["status"] = "failed"
        iteration_data["completed_at"] = end_time.isoformat()
        iteration_data["error"] = IterationError(
            message=str(e)[:500],
            stack=None,  # Could capture traceback here
        ).model_dump()
        iterations[iteration_index] = iteration_data

        # Mark iteration failed (DO NOT modify job.status)
        update_job(
            job_id,
            iteration_status="failed",
            iteration_id=iteration_id,
            iteration_completed_at=end_time,
            iteration_error=str(e)[:500],
            artifacts=Artifacts(**{**artifacts_dict, "iterations": iterations}),
        )

        return {
            "job_id": job_id,
            "iteration_id": iteration_id,
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# Claim Extraction Task
# =============================================================================

@celery_app.task(
    name="backend.worker.run_claim_extraction_job",
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def run_claim_extraction_job(job_id: str) -> dict:
    """
    Celery task for Claim Extraction pipeline.

    Extracts ALL claims (explicit and implied) from provided sources:
    - YouTube videos (with timestamp anchors)
    - Article URLs (with line range anchors)
    - User-provided text (with line range anchors)
    - Screenshots (with image index anchors)

    NO claim verification - extraction only.
    NO source retrieval - only analyzes provided inputs.

    Output: ClaimsDocument stored in Supabase Storage

    Args:
        job_id: Unique identifier for the claim extraction job

    Returns:
        Dict with job_id, status, claim counts, and any errors
    """
    from backend.integrations.gemini_client import GeminiClient
    from backend.integrations.supabase_storage import get_storage_client
    from backend.pipeline.claim_extraction import run_claim_extraction_pipeline
    from backend.models.job_record import Artifacts

    logger.info(f"[{job_id}] Starting Claim Extraction Pipeline")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "status": "failed", "error": "Job not found"}

    config = job.config_json or {}
    title = config.get("title", "Claim Extraction")
    model = config.get("model", "gemini-2.5-flash")

    # Extract input sources from config
    video_urls = config.get("video_urls", [])
    article_urls = config.get("article_urls", [])
    text_inputs = config.get("text_inputs", [])
    screenshots = config.get("screenshots", [])

    total_sources = len(video_urls) + len(article_urls) + len(text_inputs) + len(screenshots)

    if total_sources == 0:
        logger.error(f"[{job_id}] No sources provided")
        update_job(job_id, status="failed", stage="error", error="No sources provided")
        return {"job_id": job_id, "status": "failed", "error": "No sources provided"}

    logger.info(
        f"[{job_id}] Processing {total_sources} sources: "
        f"{len(video_urls)} videos, {len(article_urls)} articles, "
        f"{len(text_inputs)} text inputs, {len(screenshots)} screenshots"
    )

    # Update status to running
    update_job(
        job_id,
        status="running",
        stage="claim_extraction",
        progress_percent=5,
    )

    # Progress callback
    def progress_callback(current: int, total: int, status: str):
        """Update job progress during extraction."""
        try:
            progress = int(5 + (current / total) * 85)  # 5-90%
            update_job(
                job_id,
                stage=f"extracting_{current}_{total}",
                progress_percent=progress,
                config_json={
                    **config,
                    "current_source": current,
                    "total_sources": total,
                    "extraction_status": status,
                },
            )
            logger.info(f"[{job_id}] {status} ({current}/{total})")
        except Exception as e:
            logger.warning(f"[{job_id}] Progress update failed: {e}")

    try:
        # Initialize Gemini client
        client = GeminiClient()

        # Run claim extraction pipeline
        claims_doc = run_claim_extraction_pipeline(
            gemini_client=client,
            job_id=job_id,
            title=title,
            video_urls=video_urls,
            article_urls=article_urls,
            text_inputs=text_inputs,
            screenshots=screenshots,
            model=model,
            progress_callback=progress_callback,
        )

        # Store claims document in Supabase Storage
        update_job(job_id, stage="storing_results", progress_percent=90)

        storage = get_storage_client()
        claims_doc_path = None

        if storage:
            try:
                claims_doc_path = storage.upload_document(
                    job_id=job_id,
                    doc_type="claims_doc",
                    content=claims_doc.to_dict(),
                )
                logger.info(f"[{job_id}] Stored claims document at {claims_doc_path}")
            except Exception as storage_error:
                logger.warning(f"[{job_id}] Failed to store claims doc: {storage_error}")
        else:
            logger.warning(f"[{job_id}] Storage not available, storing inline")

        # Build artifacts with claims document
        artifacts = Artifacts(
            # Store path if available, otherwise store inline
            doc_0_path=claims_doc_path,  # Reuse doc_0_path for claims doc
            source_ledger=claims_doc.to_dict() if not claims_doc_path else None,
        )

        # Determine final status
        warnings = []
        final_status = "completed"

        if claims_doc.metadata.total_claims == 0:
            warnings.append("No claims extracted from provided sources")
            final_status = "completed_with_warnings"

        # Update job with results
        update_job(
            job_id,
            status=final_status,
            stage="completed",
            progress_percent=100,
            title=title,
            artifacts=artifacts,
            warnings=warnings if warnings else None,
        )

        logger.info(
            f"[{job_id}] Claim extraction completed: "
            f"{claims_doc.metadata.total_claims} claims "
            f"({claims_doc.metadata.total_explicit} explicit, "
            f"{claims_doc.metadata.total_implied} implied) "
            f"from {claims_doc.metadata.source_count} sources"
        )

        return {
            "job_id": job_id,
            "status": final_status,
            "total_claims": claims_doc.metadata.total_claims,
            "explicit_claims": claims_doc.metadata.total_explicit,
            "implied_claims": claims_doc.metadata.total_implied,
            "source_count": claims_doc.metadata.source_count,
            "claims_doc_path": claims_doc_path,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Claim extraction timed out after 25 minutes")
        update_job(
            job_id,
            status="failed",
            stage="timeout",
            error="Claim extraction timed out. Try processing fewer sources.",
            warnings=["Task exceeded 25 minute time limit"],
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "error": "Claim extraction timed out after 25 minutes",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Claim extraction failed: {e}")
        update_job(
            job_id,
            status="failed",
            stage="error",
            error=str(e),
            warnings=[f"Claim extraction failed: {str(e)}"],
        )
        return {"job_id": job_id, "status": "failed", "error": str(e)}


# =============================================================================
# Run-Scoped Claims Doc Task (V2 Claim Extractor)
# =============================================================================

@celery_app.task(
    name="backend.worker.run_claims_doc_task",
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1500,  # 25 min soft limit
)
def run_claims_doc_task(job_id: str, user_id: str, run_id: str) -> dict:
    """
    Celery task for generating Claims Document from a completed run's Doc 0.

    V2 Claim Extractor: This is a run-scoped artifact similar to producer/booster.
    It extracts claims and entities from the run's source ledger content.

    Features:
    - Anchored claims (timestamps if available, else line ranges)
    - Entity Index (people, orgs, places, unnamed)
    - Warning codes for extraction issues
    - Stored in same bucket as other docs

    Args:
        job_id: Job identifier
        user_id: User who triggered the task
        run_id: Run ID to generate claims from

    Returns:
        Dict with status, claim counts, and storage path
    """
    from backend.integrations.gemini_client import GeminiClient
    from backend.integrations.supabase_storage import get_storage_client
    from backend.pipeline.claim_extraction import run_claim_extraction_pipeline
    from backend.models.run_models import ensure_runs_migrated, RunStatus, RunClaimsDoc
    from datetime import datetime, timezone

    logger.info(f"[{job_id}] Starting Claims Doc generation for run {run_id}")

    job = get_job(job_id)
    if not job:
        logger.error(f"[{job_id}] Job not found")
        return {"job_id": job_id, "run_id": run_id, "status": "failed", "error": "Job not found"}

    # Update claims_doc status to running
    update_job(
        job_id,
        claims_doc_status="running",
        claims_doc_started_at=datetime.now(timezone.utc),
        claims_doc_progress_percent=10,
    )

    try:
        # Get artifacts and find the run
        artifacts = job.artifacts if hasattr(job, "artifacts") else None
        if not artifacts:
            raise ValueError("Job has no artifacts")

        # Migrate legacy artifacts to runs if needed
        runs = ensure_runs_migrated(
            artifacts,
            job_created_at=job.created_at if hasattr(job, "created_at") else None,
            job_completed_at=getattr(job, "completed_at", None),
            user_id=job.user_id or "system",
        )

        # Find the requested run
        target_run = None
        for run in runs:
            if run.run_id == run_id:
                target_run = run
                break

        if not target_run:
            raise ValueError(f"Run '{run_id}' not found")

        if not target_run.outputs or not target_run.outputs.has_doc_0():
            raise ValueError("Run has no Doc 0 content")

        # Load Doc 0 content
        storage = get_storage_client()
        doc_0_content = None

        if target_run.outputs.doc_0_path and storage:
            try:
                doc_0_content = storage.download_document(target_run.outputs.doc_0_path)
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to download Doc 0: {e}")

        if not doc_0_content and target_run.outputs.doc_0_inline:
            doc_0_content = target_run.outputs.doc_0_inline

        if not doc_0_content:
            raise ValueError("Could not load Doc 0 content")

        update_job(job_id, claims_doc_progress_percent=20)

        # Extract source content from Doc 0
        # Doc 0 is the Source Ledger with sources[] containing full_text, transcript, etc.
        sources = doc_0_content.get("sources", [])
        if not sources:
            raise ValueError("Doc 0 has no sources")

        # Build input lists for claim extraction
        video_urls = []
        article_urls = []
        text_inputs = []

        for source in sources:
            source_type = source.get("source_type", "").lower()
            url = source.get("url", "")

            if source_type == "youtube" or "youtube" in url or "youtu.be" in url:
                # For YouTube, we need the URL (transcript will be fetched)
                video_urls.append(url)
            elif source_type == "article" or source_type == "web":
                # For articles, check if we have the content or need to fetch
                if source.get("full_text") or source.get("article_text"):
                    text_inputs.append({
                        "title": source.get("title", url),
                        "content": source.get("full_text") or source.get("article_text", ""),
                    })
                else:
                    article_urls.append(url)
            else:
                # Text input - use any available text
                content = (
                    source.get("full_text") or
                    source.get("transcript") or
                    source.get("article_text") or
                    source.get("ocr_text", "")
                )
                if content:
                    text_inputs.append({
                        "title": source.get("title", f"Source {source.get('source_id', 'unknown')}"),
                        "content": content,
                    })

        total_sources = len(video_urls) + len(article_urls) + len(text_inputs)
        if total_sources == 0:
            raise ValueError("No extractable content found in Doc 0 sources")

        logger.info(
            f"[{job_id}] Processing {total_sources} sources: "
            f"{len(video_urls)} videos, {len(article_urls)} articles, {len(text_inputs)} text inputs"
        )

        update_job(job_id, claims_doc_progress_percent=30)

        # Progress callback
        def progress_callback(current: int, total: int, status: str):
            try:
                progress = int(30 + (current / total) * 50)  # 30-80%
                update_job(job_id, claims_doc_progress_percent=progress)
                logger.info(f"[{job_id}] Claims doc: {status} ({current}/{total})")
            except Exception as e:
                logger.warning(f"[{job_id}] Progress update failed: {e}")

        # Initialize Gemini client
        client = GeminiClient()
        model = job.config_json.get("model", "gemini-2.5-flash") if job.config_json else "gemini-2.5-flash"
        title = job.title or job.config_json.get("title", "Research") if job.config_json else "Research"

        # Run claim extraction pipeline
        claims_doc = run_claim_extraction_pipeline(
            gemini_client=client,
            job_id=job_id,
            title=f"{title} - Claims",
            video_urls=video_urls,
            article_urls=article_urls,
            text_inputs=text_inputs,
            screenshots=[],  # Screenshots from Doc 0 not supported yet
            model=model,
            progress_callback=progress_callback,
            run_id=run_id,
        )

        update_job(job_id, claims_doc_progress_percent=85)

        # Store claims document
        claims_doc_path = None
        if storage:
            try:
                claims_doc_path = storage.upload_document(
                    job_id=job_id,
                    doc_type=f"{run_id}_claims_doc",
                    content=claims_doc.to_dict(),
                )
                logger.info(f"[{job_id}] Stored claims doc at {claims_doc_path}")
            except Exception as storage_error:
                logger.warning(f"[{job_id}] Failed to store claims doc: {storage_error}")

        # Update run with claims_doc artifact
        # Note: We'd need to update the run in artifacts.runs, but for simplicity
        # we'll store the path in job-level fields for now
        warnings = [w.message for w in claims_doc.warnings] if claims_doc.warnings else []

        update_job(
            job_id,
            claims_doc_status="completed",
            claims_doc_completed_at=datetime.now(timezone.utc),
            claims_doc_progress_percent=100,
            claims_doc_error=None,
        )

        logger.info(
            f"[{job_id}] Claims doc completed: "
            f"{claims_doc.metadata.total_claims} claims, "
            f"{claims_doc.metadata.total_entities} entities "
            f"({len(warnings)} warnings)"
        )

        return {
            "job_id": job_id,
            "run_id": run_id,
            "status": "completed",
            "total_claims": claims_doc.metadata.total_claims,
            "total_entities": claims_doc.metadata.total_entities,
            "claims_doc_path": claims_doc_path,
            "warnings": warnings,
        }

    except SoftTimeLimitExceeded:
        logger.error(f"[{job_id}] Claims doc timed out after 25 minutes")
        update_job(
            job_id,
            claims_doc_status="failed",
            claims_doc_error="Claims doc generation timed out. Try with fewer sources.",
            claims_doc_completed_at=datetime.now(timezone.utc),
        )
        return {
            "job_id": job_id,
            "run_id": run_id,
            "status": "failed",
            "error": "Claims doc timed out after 25 minutes",
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Claims doc failed: {e}")
        update_job(
            job_id,
            claims_doc_status="failed",
            claims_doc_error=str(e),
            claims_doc_completed_at=datetime.now(timezone.utc),
        )
        return {
            "job_id": job_id,
            "run_id": run_id,
            "status": "failed",
            "error": str(e),
        }
