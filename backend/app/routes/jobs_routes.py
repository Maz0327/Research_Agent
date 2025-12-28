"""Research jobs API routes."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user, get_optional_user
from backend.auth.admin import is_admin
from backend.models.job import CreateJobRequest, CreateJobResponse, JobStatusResponse
from backend.state import create_job, get_job, update_job, list_jobs
from backend.worker import run_research_job

router = APIRouter(prefix="/jobs", tags=["jobs"])

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


@router.post("", response_model=CreateJobResponse)
async def create_job_endpoint(
    request: Request,
    job_request: CreateJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """Create a new research job."""
    # Validate and clean prompt
    prompt = job_request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Build config_json
    config_json = {
        "topic": prompt,
        "prompt": prompt,
        "pipeline": job_request.pipeline,
    }

    # Apply pipeline-specific settings
    pipeline = job_request.pipeline
    if pipeline in PIPELINE_BUDGETS:
        config_json["budgets"] = PIPELINE_BUDGETS[pipeline]
        if pipeline in ("breaking_news", "investigation", "profile", "controversy"):
            config_json["mode"] = pipeline

    # Merge additional options
    if job_request.options:
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


@router.get("")
async def list_jobs_endpoint(
    request: Request,
    user: Optional[AuthUser] = Depends(get_optional_user),
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
async def get_job_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_user),
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
    )


@router.post("/{job_id}/cancel")
async def cancel_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_current_user),
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
