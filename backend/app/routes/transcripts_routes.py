"""Transcript extraction API routes."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.dependencies import get_optional_user
from backend.auth.ban_check import get_optional_active_user
from backend.models.transcript_job import (
    TranscriptRequest,
    TranscriptSyncResponse,
    TranscriptAsyncResponse,
    TranscriptJobStatusResponse,
)
from backend.state import create_job, get_job
from backend.worker import run_transcript_job

router = APIRouter(prefix="/transcripts", tags=["transcripts"])

# Process synchronously if <= this many videos
TRANSCRIPT_SYNC_THRESHOLD = 5


@router.post("")
@limiter.limit(RATE_LIMITS["transcripts_create"])
async def extract_transcripts(
    request: Request,
    transcript_request: TranscriptRequest,
):
    """
    Extract transcripts from YouTube videos.

    - For 1-5 videos: Processes synchronously, returns doc URL immediately
    - For 6+ videos: Creates async job, returns job_id for polling
    """
    video_count = len(transcript_request.video_urls)

    if video_count <= TRANSCRIPT_SYNC_THRESHOLD:
        # Synchronous processing for small batches
        from backend.services.transcript_service import process_transcripts_sync

        logger.info(f"Processing {video_count} videos synchronously")
        try:
            result = process_transcripts_sync(
                video_urls=transcript_request.video_urls,
                use_whisper=transcript_request.use_whisper_fallback,
                doc_title=transcript_request.doc_title,
                preferred_languages=transcript_request.preferred_languages,
            )
            return TranscriptSyncResponse(**result)
        except Exception as e:
            logger.exception(f"Transcript extraction failed: {e}")
            raise HTTPException(status_code=500, detail="Transcript extraction failed")

    else:
        # Async processing for large batches
        config_json = {
            "pipeline": "transcript_only",
            "video_urls": transcript_request.video_urls,
            "use_whisper_fallback": transcript_request.use_whisper_fallback,
            "doc_title": transcript_request.doc_title,
            "preferred_languages": transcript_request.preferred_languages,
            "transcripts_completed": 0,
        }

        job = create_job(config_json=config_json)
        logger.info(f"Created async transcript job {job.job_id} for {video_count} videos")

        # Use deterministic task_id for reliable revocation
        run_transcript_job.apply_async((job.job_id,), task_id=job.job_id)

        return TranscriptAsyncResponse(
            job_id=job.job_id,
            status="queued",
            message=f"Processing {video_count} videos in background",
            total_videos=video_count,
        )


@router.get("/{job_id}", response_model=TranscriptJobStatusResponse)
@limiter.limit(RATE_LIMITS["transcripts_get"])
async def get_transcript_job_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get the status of an async transcript extraction job."""
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization check
    if job.user_id is not None:
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view this job",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Verify it's a transcript job
    if job.config_json.get("pipeline") != "transcript_only":
        raise HTTPException(status_code=400, detail="Not a transcript job")

    # Extract error from warnings
    error = None
    if job.status == "failed" and job.warnings:
        error = job.warnings[-1]

    # Get artifact URLs
    doc_url = None
    folder_url = None
    if job.artifacts:
        folder_url = job.artifacts.drive_folder_url
        if job.artifacts.doc_urls:
            doc_url = job.artifacts.doc_urls[0] if isinstance(job.artifacts.doc_urls, list) else None

    return TranscriptJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        transcripts_completed=job.config_json.get("transcripts_completed", 0),
        transcripts_total=len(job.config_json.get("video_urls", [])),
        doc_url=doc_url,
        folder_url=folder_url,
        warnings=job.warnings,
        error=error,
        created_at=job.created_at,
    )
