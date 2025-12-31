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
    SelectInterpretationRequest, PreviewJobRequest, PreviewJobResponse
)
from backend.state import create_job, get_job, update_job, list_jobs
from backend.utils.validators import ValidationError
from backend.worker import run_research_job

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
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Validate prompt length
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
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
                status_code=400,
                detail=f"Invalid options: {', '.join(sorted(invalid_keys))}. "
                       f"Allowed options: {', '.join(sorted(ALLOWED_JOB_OPTIONS))}"
            )

        # Validate custom_subreddits if provided
        if "custom_subreddits" in job_request.options:
            try:
                validated_subreddits = _validate_subreddits(job_request.options["custom_subreddits"])
                job_request.options["custom_subreddits"] = validated_subreddits
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

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
    run_research_job.delay(job.job_id, prompt)

    return CreateJobResponse(job_id=job.job_id)


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
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Validate prompt length
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
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

        jobs_data.append({
            "id": job.job_id,
            "prompt": prompt,
            "pipeline": pipeline,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "artifacts": artifacts_dict,
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

    return JobStatusResponse(
        job_id=job.job_id,
        prompt=prompt,
        pipeline=pipeline,
        status=job.status,
        progress_percent=job.progress_percent,
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
    run_research_job.delay(job_id, prompt)

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
