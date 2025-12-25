"""Celery worker configuration and task definitions."""
from typing import Optional

from celery import Celery
from loguru import logger

from backend.config import get_settings
from backend.models.job_config import JobConfig
from backend.state import get_job, update_job
from backend.services.error_logger import log_exception

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
) -> dict:
    """
    Research job task that runs through all stages of the research pipeline.

    Stages:
    0. Initialization
    1. Planning (OpenAI)
    2. Research mapping (Perplexity)
    3. Source shortlist (Perplexity)
    4. YouTube enumeration
    5. Transcript fetching
    6. Web capture (Jina → Trafilatura → Playwright)
    6.5. Reddit collection
    7. Claim extraction
    7.5. Timeline extraction
    7.6. Entity extraction
    8. Claim validation
    8.5. Angle discovery
    8.6. Documentary intelligence
    9. Drive upload
    10. Completion

    Args:
        job_id: Unique identifier for the research job
        topic: Research topic string (from Slack or API)
        slack_payload: Optional Slack payload for posting updates

    Returns:
        Dictionary with research results including Drive folder URL
    """
    from backend.pipeline.context import PipelineContext
    from backend.pipeline.stages import (
        stage_0_initialize,
        stage_1_planning,
        stage_2_research_mapping,
        stage_3_source_shortlist,
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

    logger.info(f"Starting research job {job_id} for topic: {topic}")

    # Create pipeline context
    ctx = PipelineContext(
        job_id=job_id,
        topic=topic,
        slack_payload=slack_payload,
    )

    try:
        # Execute all stages sequentially
        stage_0_initialize(ctx)
        stage_1_planning(ctx)
        stage_2_research_mapping(ctx)
        stage_3_source_shortlist(ctx)
        stage_4_youtube_enumeration(ctx)
        stage_5_transcripts(ctx)
        stage_6_web_capture(ctx)
        stage_6_5_reddit(ctx)
        stage_7_extraction(ctx)
        stage_7_5_timeline(ctx)
        stage_7_6_entities(ctx)
        stage_8_validation(ctx)
        stage_8_5_angle_discovery(ctx)
        stage_8_6_documentary_intelligence(ctx)
        stage_9_drive_upload(ctx)
        return stage_10_completion(ctx)

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


def _generate_master_index(job_config: JobConfig, outputs: dict) -> str:
    """
    Generate master index document markdown.
    
    Args:
        job_config: Job configuration
        outputs: Dictionary of output markdown strings
        
    Returns:
        Master index markdown string
    """
    lines = [
        "# Master Index",
        "",
        f"**Topic:** {job_config.topic}",
        f"**Mode:** {job_config.mode.value}",
        "",
        "## Documents",
        "",
        "- [01 Research Map](#01-research-map)",
        "- [02 Source Shortlist](#02-source-shortlist)",
        "- [03 YouTube Index](#03-youtube-index)",
        "- [04 Transcripts](#04-transcripts)",
        "- [05 Web Extracts](#05-web-extracts)",
        "- [06 Quote Bank](#06-quote-bank)",
        "- [07 Claims Ledger](#07-claims-ledger)",
        "- [08 Evidence Table](#08-evidence-table)",
        "- [09 Missing Angles](#09-missing-angles)",
        "",
    ]
    return "\n".join(lines)


def _generate_transcripts_md(transcripts: list) -> str:
    """
    Generate transcripts markdown document.
    
    Args:
        transcripts: List of TranscriptItem objects
        
    Returns:
        Transcripts markdown string
    """
    if not transcripts:
        return "# Transcripts\n\n*No transcripts available.*"
    
    lines = ["# Transcripts", ""]
    for transcript in transcripts:
        lines.append(f"## {transcript.video_id}")
        lines.append(f"**URL:** {transcript.video_url}")
        lines.append(f"**Status:** {transcript.status.value}")
        if transcript.text:
            lines.append(f"\n{transcript.text}\n")
        else:
            lines.append(f"*{transcript.error_message or 'Transcript not available'}*\n")
        lines.append("---\n")
    
    return "\n".join(lines)


def _generate_web_extracts_md(web_sources: list) -> str:
    """
    Generate web extracts markdown document.

    Args:
        web_sources: List of SourceItem objects with captured content

    Returns:
        Web extracts markdown string
    """
    if not web_sources:
        return "# Web Extracts\n\n*No web sources available.*"

    lines = ["# Web Extracts", ""]
    for source in web_sources:
        lines.append(f"## {source.title}")
        lines.append(f"**URL:** {source.url}")
        lines.append(f"**Type:** {source.source_type.value}")
        if source.published_at:
            lines.append(f"**Published:** {source.published_at}")
        if source.text:
            lines.append(f"\n{source.text[:2000]}...")  # Limit extract length
        else:
            lines.append("*Content not available*")
        if source.notes:
            lines.append(f"\n*Note: {source.notes}*")
        lines.append("\n---\n")

    return "\n".join(lines)


def _generate_evidence_table_md(evidence_records: list) -> str:
    """
    Generate evidence table markdown document.

    Args:
        evidence_records: List of EvidenceRecord objects

    Returns:
        Evidence table markdown string
    """
    if not evidence_records:
        return "# Evidence Table\n\n*No evidence records available.*"

    lines = [
        "# Evidence Table",
        "",
        "| Claim ID | Status | Evidence For | Evidence Against | Notes |",
        "|----------|--------|--------------|------------------|-------|",
    ]

    for record in evidence_records:
        claim_id = record.claim_id if hasattr(record, 'claim_id') else str(record.get('claim_id', 'N/A'))
        status = record.status.value if hasattr(record, 'status') else str(record.get('status', 'Unproven'))

        # Format evidence for
        evidence_for = []
        for_list = record.evidence_for if hasattr(record, 'evidence_for') else record.get('evidence_for', [])
        for citation in for_list:
            url = citation.url if hasattr(citation, 'url') else citation.get('url', '')
            if url:
                evidence_for.append(f"[Link]({url})")
        evidence_for_str = ", ".join(evidence_for) if evidence_for else "-"

        # Format evidence against
        evidence_against = []
        against_list = record.evidence_against if hasattr(record, 'evidence_against') else record.get('evidence_against', [])
        for citation in against_list:
            url = citation.url if hasattr(citation, 'url') else citation.get('url', '')
            if url:
                evidence_against.append(f"[Link]({url})")
        evidence_against_str = ", ".join(evidence_against) if evidence_against else "-"

        # Format notes (truncate and escape pipes)
        notes = record.notes if hasattr(record, 'notes') else record.get('notes', '')
        notes_str = (notes or "-")[:100].replace("|", "\\|").replace("\n", " ")

        lines.append(f"| {claim_id} | {status} | {evidence_for_str} | {evidence_against_str} | {notes_str} |")

    lines.append("")
    lines.append(f"**Total claims validated:** {len(evidence_records)}")

    # Summary statistics
    verified = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Verified')
    debunked = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Debunked')
    unproven = sum(1 for r in evidence_records if (r.status.value if hasattr(r, 'status') else r.get('status', '')) == 'Unproven')

    lines.append(f"- Verified: {verified}")
    lines.append(f"- Debunked: {debunked}")
    lines.append(f"- Unproven: {unproven}")

    return "\n".join(lines)


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
