"""Research jobs API routes."""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user, get_optional_user
from backend.auth.ban_check import get_active_user, get_optional_active_user
from backend.auth.admin import is_admin
from backend.models.job import (
    CreateJobRequest, CreateJobResponse, JobStatusResponse,
    SelectInterpretationRequest, PreviewJobRequest, PreviewJobResponse,
    VideoAnalysisRequest, VideoAnalysisResponse, VideoAnalysisStatusResponse,
)
from backend.state import create_job, get_job, update_job, list_jobs
from backend.utils.validators import ValidationError, validate_video_job_inputs
from backend.worker import run_research_job, run_gemini_video_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Input validation constants
MAX_PROMPT_LENGTH = 2000  # Maximum characters for prompt
MAX_SUBREDDITS = 10  # Maximum number of custom subreddits
SUBREDDIT_PATTERN = re.compile(r'^[a-zA-Z0-9_]{2,21}$')  # Valid subreddit name pattern

# Allowed keys for job options (security: prevent arbitrary config injection)
ALLOWED_JOB_OPTIONS = {
    "source_count",      # Number of sources to collect
    "depth",             # Research depth level
    "custom_subreddits", # Override default subreddits
    "time_window_hours", # Time window for breaking_news mode
    "entity_focus",      # Specific entity to focus on
    "niche",             # Niche overlay to apply
}

# Pipeline budget configurations
PIPELINE_BUDGETS = {
    "quick": {
        "max_web_urls": 20,
        "max_transcription_minutes": 60,
        "max_claims_to_validate": 10,
        "max_validation_links_per_claim": 3,
    },
    "full": {
        "max_web_urls": 50,
        "max_transcription_minutes": 120,
        "max_claims_to_validate": 25,
        "max_validation_links_per_claim": 6,
    },
    "breaking_news": {
        "max_web_urls": 15,
        "max_transcription_minutes": 30,
        "max_claims_to_validate": 8,
        "max_validation_links_per_claim": 4,
    },
    "investigation": {
        "max_web_urls": 40,
        "max_transcription_minutes": 100,
        "max_claims_to_validate": 20,
        "max_validation_links_per_claim": 6,
    },
    "profile": {
        "max_web_urls": 25,
        "max_transcription_minutes": 60,
        "max_claims_to_validate": 12,
        "max_validation_links_per_claim": 5,
    },
    "controversy": {
        "max_web_urls": 30,
        "max_transcription_minutes": 80,
        "max_claims_to_validate": 15,
        "max_validation_links_per_claim": 5,
    },
}


def _validate_subreddits(subreddits: list) -> list[str]:
    """Validate and sanitize list of subreddit names."""
    if not isinstance(subreddits, list):
        raise ValueError("custom_subreddits must be a list")
    if len(subreddits) > MAX_SUBREDDITS:
        raise ValueError(f"Maximum {MAX_SUBREDDITS} custom subreddits allowed")

    validated = []
    for sr in subreddits:
        if not isinstance(sr, str):
            raise ValueError(f"Invalid subreddit name type: {type(sr).__name__}")
        sr_clean = sr.strip().lower()
        # Remove r/ prefix if present
        if sr_clean.startswith("r/"):
            sr_clean = sr_clean[2:]
        if not SUBREDDIT_PATTERN.match(sr_clean):
            raise ValueError(f"Invalid subreddit name: '{sr}'. Must be 2-21 alphanumeric characters or underscores.")
        validated.append(sr_clean)
    return validated


@router.post("", response_model=CreateJobResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_job_endpoint(
    request: Request,
    job_request: CreateJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Create a new research job."""
    # Validate and clean prompt
    prompt = job_request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    # Validate prompt length
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )

    # Build config_json
    config_json = {
        "topic": prompt,
        "prompt": prompt,
        "pipeline": job_request.pipeline,
    }

    # Add niche if specified (for source selection guidance)
    if job_request.niche:
        config_json["niche"] = job_request.niche

    # Apply pipeline-specific settings
    pipeline = job_request.pipeline
    if pipeline in PIPELINE_BUDGETS:
        config_json["budgets"] = PIPELINE_BUDGETS[pipeline]
        if pipeline in ("breaking_news", "investigation", "profile", "controversy"):
            config_json["mode"] = pipeline

    # Merge additional options (validated against allowlist)
    if job_request.options:
        invalid_keys = set(job_request.options.keys()) - ALLOWED_JOB_OPTIONS
        if invalid_keys:
            logger.warning(
                "Invalid job options rejected",
                extra={
                    "invalid_keys": list(invalid_keys),
                    "user_id": user.user_id if user else None,
                    "event": "invalid_job_options",
                }
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid options: {', '.join(sorted(invalid_keys))}. "
                       f"Allowed options: {', '.join(sorted(ALLOWED_JOB_OPTIONS))}"
            )

        # Validate custom_subreddits if provided
        if "custom_subreddits" in job_request.options:
            try:
                validated_subreddits = _validate_subreddits(job_request.options["custom_subreddits"])
                job_request.options["custom_subreddits"] = validated_subreddits
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

        config_json.update(job_request.options)

    # Store user info for Drive sharing
    if user:
        config_json["user_email"] = user.email
        config_json["user_id"] = user.user_id

    # Create job
    user_id = user.user_id if user else None
    job = create_job(config_json=config_json, user_id=user_id)

    # Audit log
    logger.info(
        "Job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "user_email": user.email if user else None,
            "pipeline": job_request.pipeline,
            "ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "event": "job_created",
        }
    )

    # Enqueue Celery task
    logger.info(f"Enqueuing research job {job.job_id} for prompt: {prompt[:50]}...")
    # Use job_id as Celery task_id to enable reliable cancellation
    run_research_job.apply_async((job.job_id, prompt), task_id=job.job_id)

    return CreateJobResponse(job_id=job.job_id)


# =============================================================================
# Video Analysis Endpoint (URL-first Gemini extraction - PRIMARY FLOW)
# =============================================================================

@router.post("/video-analysis", response_model=VideoAnalysisResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_video_analysis_job(
    request: Request,
    job_request: VideoAnalysisRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Create a new video analysis job (URL-first Gemini extraction).

    This is the PRIMARY job creation endpoint for the Gemini pivot.
    User provides YouTube URLs directly → Gemini extracts clips/quotes.

    Returns estimated cost and job ID for polling.
    """
    # Validate video URLs and get cost estimate
    validation = validate_video_job_inputs(
        video_urls=job_request.video_urls,
        video_durations=None,  # Will estimate based on count
        model=job_request.model,
    )

    if not validation.valid:
        raise HTTPException(status_code=422, detail=validation.error)

    # Build config_json for the job
    config_json = {
        "video_urls": job_request.video_urls,
        "model": job_request.model,
        "title": job_request.title or f"Video Analysis ({len(job_request.video_urls)} videos)",
        "job_type": "video_analysis",  # Distinguish from topic-based jobs
    }

    # Store user info
    if user:
        config_json["user_email"] = user.email
        config_json["user_id"] = user.user_id

    # Create job
    user_id = user.user_id if user else None
    job = create_job(config_json=config_json, user_id=user_id)

    # Audit log
    logger.info(
        "Video analysis job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "video_count": len(job_request.video_urls),
            "model": job_request.model,
            "estimated_cost": validation.estimated_cost,
            "ip": request.client.host if request.client else None,
            "event": "video_analysis_job_created",
        }
    )

    # Enqueue Celery task
    logger.info(f"Enqueuing Gemini video job {job.job_id} for {len(job_request.video_urls)} videos")
    run_gemini_video_job.apply_async((job.job_id,), task_id=job.job_id)

    return VideoAnalysisResponse(
        job_id=job.job_id,
        estimated_cost=validation.estimated_cost,
        total_duration_minutes=validation.total_duration_minutes,
        video_count=len(job_request.video_urls),
        warnings=validation.warnings if validation.warnings else None,
    )


@router.get("/video-analysis/{job_id}", response_model=VideoAnalysisStatusResponse)
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_video_analysis_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get the status of a video analysis job."""
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

    # Extract progress info from config_json
    current_video = job.config_json.get("current_video") if job.config_json else None
    total_videos = len(job.config_json.get("video_urls", [])) if job.config_json else None

    # Extract clips/quotes counts from artifacts
    clips_count = None
    quotes_count = None
    producer_packet = None

    if job.artifacts:
        artifacts_dict = job.artifacts.model_dump(exclude_none=True) if hasattr(job.artifacts, "model_dump") else {}
        clips = artifacts_dict.get("clips", [])
        quotes = artifacts_dict.get("quotes", [])
        clips_count = len(clips) if clips else None
        quotes_count = len(quotes) if quotes else None

        # If completed, include full producer packet
        if job.status == "completed":
            producer_packet = artifacts_dict

    # Extract error
    error = None
    if job.status == "failed":
        if job.warnings:
            error = job.warnings[-1]

    return VideoAnalysisStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_video=current_video,
        total_videos=total_videos,
        clips_count=clips_count,
        quotes_count=quotes_count,
        error=error,
        created_at=job.created_at,
        producer_packet=producer_packet,
    )


@router.post("/preview", response_model=PreviewJobResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])  # Same rate limit as job creation
async def preview_job_endpoint(
    request: Request,
    preview_request: PreviewJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Preview how a research job will be interpreted before creating it.

    Returns the interpreted plan including topic understanding, mode,
    subreddits, and source types. If topic is ambiguous, returns
    possible interpretations for user selection.
    """
    from backend.integrations.openai_client import plan_job

    prompt = preview_request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="Prompt cannot be empty")

    # Validate prompt length
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Prompt exceeds maximum length of {MAX_PROMPT_LENGTH} characters"
        )

    try:
        # Get the interpreted plan from OpenAI
        result = plan_job(prompt)

        # Check for disambiguation
        if result.get("is_ambiguous"):
            return PreviewJobResponse(
                is_ambiguous=True,
                interpretations=result.get("interpretations", [])
            )

        # Extract config details for preview
        config = result.get("config")
        if not config:
            raise HTTPException(status_code=500, detail="Failed to generate job plan")

        # Determine effective niche (user override or LLM detection)
        effective_niche = preview_request.niche or getattr(config, "niche", None)

        # Determine effective mode (from pipeline selection)
        effective_mode = preview_request.pipeline

        # Get subreddits from config
        subreddits = []
        if hasattr(config, "reddit") and config.reddit:
            subreddits = getattr(config.reddit, "subreddits", []) or []

        # Determine source types based on mode
        source_types = ["web", "news"]
        if effective_mode in ("investigation", "profile", "controversy"):
            source_types.extend(["youtube", "reddit"])
        elif effective_mode == "breaking_news":
            source_types.extend(["news", "reddit"])
        else:
            source_types.extend(["youtube", "reddit"])

        return PreviewJobResponse(
            is_ambiguous=False,
            interpreted_topic=getattr(config, "topic", prompt),
            mode=effective_mode,
            niche=effective_niche,
            subreddits=subreddits,
            source_types=list(set(source_types))
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        # Return a basic preview on error
        return PreviewJobResponse(
            is_ambiguous=False,
            interpreted_topic=prompt,
            mode=preview_request.pipeline,
            niche=preview_request.niche,
            subreddits=[],
            source_types=["web", "news", "youtube", "reddit"]
        )


@router.get("")
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_jobs_endpoint(
    request: Request,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
    limit: int = 50,
    offset: int = 0,
):
    """List all jobs for the current user."""
    user_id = user.user_id if user else None
    jobs = list_jobs(user_id=user_id, limit=limit, offset=offset)

    jobs_data = []
    for job in jobs:
        prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
        pipeline = job.config_json.get("pipeline", "full")

        artifacts_dict = None
        if job.artifacts:
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
            if not artifacts_dict:
                artifacts_dict = None

        # Extract progress detail from config_json for Gemini video jobs
        pass_detail = None
        if job.config_json:
            pass_detail = job.config_json.get("pass_detail")
        
        jobs_data.append({
            "id": job.job_id,
            "prompt": prompt,
            "title": job.title,
            "pipeline": pipeline,
            "status": job.status,
            "stage": job.stage,
            "stage_started_at": job.stage_started_at.isoformat() if job.stage_started_at else None,
            "progress_percent": job.progress_percent,
            "pass_detail": pass_detail,
            "artifacts": artifacts_dict,
            "error": job.warnings[-1] if job.status == "failed" and job.warnings else None,
            "created_at": job.created_at.isoformat(),
        })

    return {"jobs": jobs_data}


@router.get("/{job_id}", response_model=JobStatusResponse)
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_job_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get the status of a research job."""
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

    prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
    pipeline = job.config_json.get("pipeline", "full")

    # Extract error from warnings
    error = None
    if job.status == "failed":
        fatal_errors = [w for w in job.warnings if w.startswith("Fatal error:")]
        if fatal_errors:
            error = fatal_errors[-1].replace("Fatal error: ", "")
        elif job.warnings:
            error = job.warnings[-1]

    artifacts_dict = None
    if job.artifacts:
        artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        if not artifacts_dict:
            artifacts_dict = None

    # Include interpretations if job is disambiguating
    interpretations = None
    if job.status == "disambiguating" and job.interpretations:
        interpretations = job.interpretations

    # Extract pass_detail from config_json
    pass_detail = None
    if job.config_json:
        pass_detail = job.config_json.get("pass_detail")

    return JobStatusResponse(
        job_id=job.job_id,
        prompt=prompt,
        title=job.title,
        pipeline=pipeline,
        status=job.status,
        stage=job.stage,
        stage_started_at=job.stage_started_at,
        progress_percent=job.progress_percent,
        pass_detail=pass_detail,
        artifacts=artifacts_dict,
        error=error,
        created_at=job.created_at,
        updated_at=None,
        interpretations=interpretations,
    )


@router.post("/{job_id}/cancel")
@limiter.limit(RATE_LIMITS["jobs_cancel"])
async def cancel_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Cancel a running or queued research job."""
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner or admin can cancel
    if job.user_id != user.user_id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this job")

    if job.status not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'. Only queued or running jobs can be cancelled."
        )

    # Revoke Celery task
    try:
        from backend.worker import celery_app
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        logger.info(f"Revoked Celery task for job {job_id}")
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task for job {job_id}: {e}")

    update_job(job_id, status="cancelled", stage="cancelled")

    logger.info(
        "Job cancelled",
        extra={"job_id": job_id, "cancelled_by": user.user_id, "event": "job_cancelled"}
    )

    return {"message": "Job cancelled successfully", "job_id": job_id}


@router.delete("/{job_id}")
@limiter.limit(RATE_LIMITS["jobs_cancel"])  # Reuse cancel rate limit
async def delete_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Soft-delete a job (marks as 'deleted' status)."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner or admin can delete
    if job.user_id != user.user_id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized to delete this job")

    # Cannot delete running/queued jobs
    if job.status in ("running", "queued"):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running or queued job. Cancel it first."
        )

    update_job(job_id, status="deleted", stage="deleted")

    logger.info(
        "Job deleted",
        extra={"job_id": job_id, "deleted_by": user.user_id, "event": "job_deleted"}
    )

    return {"message": "Job deleted successfully", "job_id": job_id}


@router.post("/{job_id}/archive")
@limiter.limit(RATE_LIMITS["jobs_cancel"])
async def archive_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Archive a job (marks as 'archived' status). Can be unarchived later."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner or admin can archive
    if job.user_id != user.user_id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized to archive this job")

    # Cannot archive running/queued jobs
    if job.status in ("running", "queued"):
        raise HTTPException(
            status_code=400,
            detail="Cannot archive a running or queued job. Cancel it first."
        )

    update_job(job_id, status="archived", stage="archived")

    logger.info(
        "Job archived",
        extra={"job_id": job_id, "archived_by": user.user_id, "event": "job_archived"}
    )

    return {"message": "Job archived successfully", "job_id": job_id}


@router.post("/{job_id}/select-interpretation")
@limiter.limit(RATE_LIMITS["jobs_create"])  # Reuse jobs_create rate limit
async def select_interpretation(
    request: Request,
    job_id: str,
    selection: SelectInterpretationRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Select interpretation(s) for a disambiguating job and resume processing.

    When a job is paused for disambiguation (status='disambiguating'),
    this endpoint allows the user to select which interpretation(s) to research.
    """
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
                detail="Authentication required to modify this job",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Job must be in disambiguating status
    if job.status != "disambiguating":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not awaiting disambiguation. Current status: '{job.status}'"
        )

    # Job must have interpretations
    if not job.interpretations:
        raise HTTPException(
            status_code=400,
            detail="Job has no interpretations to select from"
        )

    # Determine which indices to use
    if selection.indices == "all":
        indices = list(range(len(job.interpretations)))
    else:
        # Validate indices are within bounds
        for idx in selection.indices:
            if idx >= len(job.interpretations):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid interpretation index: {idx}. Job has {len(job.interpretations)} interpretations."
                )
        indices = selection.indices

    # Update job with selected interpretations and re-queue
    prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
    update_job(
        job_id,
        selected_interpretations=indices,
        status="queued",
        stage="resuming",
    )

    # Re-enqueue Celery task
    logger.info(f"Re-enqueuing job {job_id} with {len(indices)} selected interpretations")
    # Use deterministic task_id for reliable revocation
    run_research_job.apply_async((job_id, prompt), task_id=job_id)

    # Audit log
    selected_labels = [job.interpretations[i].get("label", f"#{i}") for i in indices]
    logger.info(
        "Job resumed after disambiguation",
        extra={
            "job_id": job_id,
            "user_id": user.user_id if user else "anonymous",
            "selected_indices": indices,
            "selected_labels": selected_labels,
            "event": "job_disambiguation_resolved",
        }
    )

    return {
        "message": "Job resumed with selected interpretations",
        "job_id": job_id,
        "selected_interpretations": selected_labels,
    }


@router.get("/usage/stats")
@limiter.limit("30/minute")
async def get_usage_stats(
    request: Request,
    user: AuthUser = Depends(get_active_user),
):
    """
    Get API usage statistics for the authenticated user.

    Returns aggregated costs from completed jobs and dashboard links.
    """
    # Fetch user's completed jobs
    user_jobs = list_jobs(user_id=user.user_id, limit=100)

    # Aggregate costs from completed jobs
    total_costs = {
        "openai": 0.0,
        "perplexity": 0.0,
        "whisper": 0.0,
        "tavily": 0.0,
        "total": 0.0,
    }
    jobs_with_costs = 0

    for job in user_jobs:
        if job.status != "completed":
            continue

        # Check for cost data in outputs
        if job.outputs and hasattr(job.outputs, "__dict__"):
            outputs_dict = job.outputs.__dict__ if hasattr(job.outputs, "__dict__") else {}
        else:
            outputs_dict = {}

        # Cost summary may be stored in partial_outputs during completion
        cost_summary = None
        if hasattr(job, "config_json") and job.config_json:
            cost_summary = job.config_json.get("cost_summary")

        if cost_summary:
            jobs_with_costs += 1
            costs_by_api = cost_summary.get("costs_by_api", {})
            for api, cost in costs_by_api.items():
                if "openai" in api.lower():
                    total_costs["openai"] += cost
                elif "perplexity" in api.lower():
                    total_costs["perplexity"] += cost
                elif "whisper" in api.lower():
                    total_costs["whisper"] += cost
                elif "tavily" in api.lower():
                    total_costs["tavily"] += cost
            total_costs["total"] += cost_summary.get("total_cost", 0.0)

    # External dashboard links
    dashboards = {
        "openai": "https://platform.openai.com/usage",
        "perplexity": "https://www.perplexity.ai/settings/api",
        "google_cloud": "https://console.cloud.google.com/apis/dashboard",
        "supabase": "https://supabase.com/dashboard/project/_/settings/billing",
    }

    return {
        "total_jobs": len([j for j in user_jobs if j.status == "completed"]),
        "jobs_with_cost_tracking": jobs_with_costs,
        "estimated_costs": {k: round(v, 4) for k, v in total_costs.items()},
        "dashboards": dashboards,
        "note": "Cost estimates are approximations. Check provider dashboards for exact usage.",
    }
