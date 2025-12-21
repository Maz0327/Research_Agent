"""FastAPI application main module."""
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Maximum request body size (10 MB)
MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024

from backend.app.routes import router as slack_router
from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user, get_optional_user, require_admin
from backend.auth.admin import is_admin
from backend.config import get_settings
from backend.models.job import CreateJobRequest, CreateJobResponse, JobStatusResponse
from backend.models.transcript_job import (
    TranscriptRequest,
    TranscriptSyncResponse,
    TranscriptAsyncResponse,
    TranscriptJobStatusResponse,
)
from backend.models.user_settings import (
    UserSettingsUpdate,
    UserSettingsResponse,
    FolderValidationRequest,
    FolderValidationResponse,
    UsernameCheckRequest,
    UsernameCheckResponse,
)
from backend.state import create_job, get_job, update_job, list_jobs
from backend.state.settings_store import get_or_create_settings, update_user_settings
from backend.worker import run_research_job, run_transcript_job

settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Research Agent API",
    description="Cloud-based research backend for aggregating content from multiple sources",
    version="0.1.0",
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS middleware
cors_origins = []
if settings.frontend_origins:
    # Parse comma-separated origins
    cors_origins = [origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()]

# Add CORS middleware (only if origins are configured)
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,  # Explicit list, no wildcard
        allow_credentials=True,  # Allow auth headers
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods only
        allow_headers=["Content-Type", "Authorization"],  # Explicit headers only
    )
    logger.info(f"CORS enabled for origins: {cors_origins}")
else:
    logger.warning("FRONTEND_ORIGINS not set - CORS middleware not configured")

# Request body size limit middleware
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Reject requests with bodies larger than MAX_REQUEST_SIZE_BYTES."""
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_SIZE_BYTES:
                logger.warning(
                    f"Request rejected: body size {content_length} exceeds limit "
                    f"{MAX_REQUEST_SIZE_BYTES} bytes"
                )
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
        except ValueError:
            pass  # Invalid content-length header, let the request through
    return await call_next(request)


# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"  # Prevent caching of sensitive data
    response.headers["Content-Security-Policy"] = "default-src 'self'"  # Basic CSP

    # Only add HSTS in production
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# Include routers
app.include_router(slack_router, tags=["slack"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.environment,
    }


# =============================================================================
# Authentication Endpoints
# =============================================================================


@app.get("/auth/me")
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """
    Get the current authenticated user's information.

    Requires a valid Supabase JWT token in the Authorization header.

    Returns:
        User info including user_id, email, and role
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
    }


# =============================================================================
# User Settings Endpoints
# =============================================================================


@app.get("/settings", response_model=UserSettingsResponse)
async def get_settings_endpoint(user: AuthUser = Depends(get_current_user)):
    """
    Get the current user's settings.

    Creates default settings if none exist.

    Requires authentication.

    Returns:
        User settings including Drive folder, pipeline preferences, notifications
    """
    settings = get_or_create_settings(user.user_id)
    return UserSettingsResponse.from_settings(settings)


@app.put("/settings", response_model=UserSettingsResponse)
@limiter.limit("30/minute")
async def update_settings_endpoint(
    request: Request,
    settings_update: UserSettingsUpdate,
    user: AuthUser = Depends(get_current_user),
):
    """
    Update the current user's settings.

    Only provided fields will be updated. Omitted fields remain unchanged.

    Requires authentication.

    Args:
        settings_update: Fields to update

    Returns:
        Updated user settings
    """
    updated = update_user_settings(user.user_id, settings_update)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update settings")

    logger.info(
        "Settings updated",
        extra={
            "user_id": user.user_id,
            "updated_fields": list(settings_update.model_dump(exclude_none=True).keys()),
            "event": "settings_updated",
        }
    )

    return UserSettingsResponse.from_settings(updated)


@app.post("/settings/validate-folder", response_model=FolderValidationResponse)
@limiter.limit("10/minute")
async def validate_folder_endpoint(
    request: Request,
    folder_request: FolderValidationRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Validate that a Google Drive folder is accessible.

    Extracts folder ID from URL and checks if the service account can access it.

    Requires authentication.

    Args:
        folder_request: Folder URL to validate

    Returns:
        Validation result with folder details
    """
    import re

    # Extract folder ID from URL
    url_pattern = r'https?://drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)'
    match = re.match(url_pattern, folder_request.folder_url)

    if not match:
        return FolderValidationResponse(
            valid=False,
            error="Invalid Google Drive folder URL format"
        )

    folder_id = match.group(1)

    # Try to access the folder using Google Drive API
    try:
        from googleapiclient.errors import HttpError
        from backend.integrations.google_drive_docs import build_oauth_credentials, _get_drive_service
        from backend.config import require_google_oauth, MissingRequiredSettingError

        # Check OAuth is configured
        try:
            settings = require_google_oauth()
        except MissingRequiredSettingError as e:
            logger.error(f"OAuth not configured: {e}")
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                accessible=False,
                error="Google Drive not configured. Contact admin to set up OAuth credentials."
            )

        # Build credentials
        try:
            creds = build_oauth_credentials(settings)
            logger.info(f"OAuth credentials built successfully, valid={creds.valid}")
        except Exception as cred_error:
            logger.exception(f"Failed to build OAuth credentials: {type(cred_error).__name__}: {cred_error}")
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                accessible=False,
                error=f"OAuth credentials error: {type(cred_error).__name__}. Check server logs."
            )

        drive_service = _get_drive_service(creds)

        # Get folder metadata
        folder = drive_service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType"
        ).execute()

        # Verify it's actually a folder
        if folder.get("mimeType") != "application/vnd.google-apps.folder":
            return FolderValidationResponse(
                valid=False,
                folder_id=folder_id,
                error="URL does not point to a folder"
            )

        logger.info(f"Folder validated successfully: {folder.get('name')} ({folder_id})")
        return FolderValidationResponse(
            valid=True,
            folder_id=folder_id,
            folder_name=folder.get("name"),
            accessible=True
        )

    except HttpError as e:
        # Handle specific Google API errors
        status_code = e.resp.status if hasattr(e, 'resp') else 'unknown'
        logger.error(f"Drive API HttpError for folder {folder_id}: status={status_code}, reason={e.reason if hasattr(e, 'reason') else str(e)}")

        if status_code == 404:
            error_msg = "Folder not found. Please check the URL and ensure the folder exists."
        elif status_code == 403:
            error_msg = "Cannot access folder. Please share it with your account or make it accessible."
        else:
            error_msg = f"Google Drive API error ({status_code}). Please try again."

        return FolderValidationResponse(
            valid=False,
            folder_id=folder_id,
            accessible=False,
            error=error_msg
        )

    except Exception as e:
        # Log the ACTUAL error for debugging
        logger.exception(f"Unexpected error validating folder {folder_id} for user {user.user_id}: {type(e).__name__}: {e}")

        return FolderValidationResponse(
            valid=False,
            folder_id=folder_id,
            accessible=False,
            error=f"Validation error: {type(e).__name__}. Check server logs for details."
        )


@app.get("/settings/oauth-status")
@limiter.limit("10/minute")
async def get_oauth_status(
    request: Request,
    user: AuthUser = Depends(get_current_user),
):
    """
    Check if Google OAuth is properly configured.

    Returns the status of Google Drive integration.

    Requires authentication.
    """
    from backend.integrations.google_drive_docs import validate_oauth_config

    is_valid, message = validate_oauth_config()

    return {
        "connected": is_valid,
        "message": message,
    }


@app.get("/settings/check-username", response_model=UsernameCheckResponse)
@limiter.limit("30/minute")
async def check_username_availability(
    request: Request,
    username: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Check if a username is available.

    Validates format and checks database for uniqueness.
    The current user's own username is always considered available.

    Requires authentication.

    Args:
        username: Username to check

    Returns:
        Availability status and normalized username
    """
    import re

    # Normalize username
    username = username.strip().lower()

    # Validate format
    if len(username) < 3:
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must be at least 3 characters"
        )

    if len(username) > 30:
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must be at most 30 characters"
        )

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return UsernameCheckResponse(
            available=False,
            username=username,
            error="Username must start with a letter and contain only letters, numbers, and underscores"
        )

    # Check if this is the user's current username
    from backend.state.settings_store import check_username_available

    is_available = check_username_available(username, user.user_id)

    return UsernameCheckResponse(
        available=is_available,
        username=username,
        error=None if is_available else "Username is already taken"
    )


# =============================================================================
# Research Job Endpoints
# =============================================================================


@app.post("/jobs", response_model=CreateJobResponse)
@limiter.limit("10/hour")
async def create_job_endpoint(
    request: Request,
    job_request: CreateJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """
    Create a new research job.

    Optionally accepts authentication. If authenticated, the job is associated
    with the user and only they can view it (when RLS is enabled).

    Args:
        request: FastAPI Request object (for rate limiting)
        job_request: Job creation request with prompt, pipeline, and optional options
        user: Optional authenticated user

    Returns:
        Job creation response with job_id
    """
    # Validate and clean prompt
    prompt = job_request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Build config_json with prompt and pipeline settings
    config_json = {
        "topic": prompt,  # Worker expects "topic" field
        "prompt": prompt,  # API exposes "prompt"
        "pipeline": job_request.pipeline,
    }

    # Apply pipeline-specific defaults
    if job_request.pipeline == "quick":
        # Quick pipeline: lower budgets for faster results
        config_json["budgets"] = {
            "max_web_urls": 20,
            "max_transcription_minutes": 60,
            "max_claims_to_validate": 10,
            "max_validation_links_per_claim": 3,
        }
    elif job_request.pipeline == "full":
        # Full pipeline: higher budgets for comprehensive results
        config_json["budgets"] = {
            "max_web_urls": 50,
            "max_transcription_minutes": 120,
            "max_claims_to_validate": 25,
            "max_validation_links_per_claim": 6,
        }
    elif job_request.pipeline == "breaking_news":
        # Breaking news: fast-turnaround coverage of current events
        config_json["mode"] = "breaking_news"
        config_json["budgets"] = {
            "max_web_urls": 15,
            "max_transcription_minutes": 30,
            "max_claims_to_validate": 8,
            "max_validation_links_per_claim": 4,
        }
    elif job_request.pipeline == "investigation":
        # Investigation: deep-dive investigative reporting
        config_json["mode"] = "investigation"
        config_json["budgets"] = {
            "max_web_urls": 40,
            "max_transcription_minutes": 100,
            "max_claims_to_validate": 20,
            "max_validation_links_per_claim": 6,
        }
    elif job_request.pipeline == "profile":
        # Profile: character-driven biographical storytelling
        config_json["mode"] = "profile"
        config_json["budgets"] = {
            "max_web_urls": 25,
            "max_transcription_minutes": 60,
            "max_claims_to_validate": 12,
            "max_validation_links_per_claim": 5,
        }
    elif job_request.pipeline == "controversy":
        # Controversy: balanced multi-perspective analysis
        config_json["mode"] = "controversy"
        config_json["budgets"] = {
            "max_web_urls": 30,
            "max_transcription_minutes": 80,
            "max_claims_to_validate": 15,
            "max_validation_links_per_claim": 5,
        }

    # Merge any additional options
    if job_request.options:
        config_json.update(job_request.options)

    # Store user info in config_json for Drive sharing
    if user:
        config_json["user_email"] = user.email
        config_json["user_id"] = user.user_id

    # Create job in Supabase with status="queued", progress_percent=0, artifacts=null, error=null
    # (These defaults are set by JobRecord model)
    user_id = user.user_id if user else None
    job = create_job(config_json=config_json, user_id=user_id)

    # Audit log: Job creation
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
    logger.info(f"Enqueuing research job {job.job_id} for prompt: {prompt[:50]}... (pipeline: {job_request.pipeline}, user: {user_id or 'anonymous'})")
    run_research_job.delay(job.job_id, prompt)
    
    return CreateJobResponse(job_id=job.job_id)


@app.get("/jobs")
@limiter.limit("30/minute")
async def list_jobs_endpoint(
    request: Request,
    user: Optional[AuthUser] = Depends(get_optional_user),
    limit: int = 50,
    offset: int = 0,
):
    """
    List all jobs for the current user.

    If authenticated, returns only the user's jobs (enforced by RLS).
    If not authenticated, returns empty list.

    Args:
        limit: Maximum number of jobs to return (default 50)
        offset: Number of jobs to skip for pagination (default 0)

    Returns:
        List of job summaries with id, prompt, pipeline, status, progress, created_at, artifacts
    """
    # Get user_id if authenticated
    user_id = user.user_id if user else None

    # List jobs (RLS policies will enforce filtering on Supabase side)
    jobs = list_jobs(user_id=user_id, limit=limit, offset=offset)

    # Convert JobRecord objects to API response format
    jobs_data = []
    for job in jobs:
        # Extract prompt and pipeline from config_json
        prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
        pipeline = job.config_json.get("pipeline", "full")

        # Convert artifacts to dict
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


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
@limiter.limit("60/minute")
async def get_job_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """
    Get the status of a research job.

    Requires authentication if the job has an owner (user_id is set).
    Anonymous jobs can be viewed by anyone.

    Args:
        job_id: Unique identifier for the research job
        user: Optional authenticated user

    Returns:
        Job status response with status, progress_percent, artifacts, and error

    Raises:
        HTTPException: 401 if authentication required but not provided
        HTTPException: 403 if user doesn't own the job
        HTTPException: 404 if job not found
    """
    # Validate job_id format to prevent path traversal
    import uuid
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization check: if job has an owner, verify access
    if job.user_id is not None:
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view this job",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if job.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )
    
    # Extract prompt and pipeline from config_json
    prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
    pipeline = job.config_json.get("pipeline", "full")
    
    # Extract error from warnings if status is failed
    error = None
    if job.status == "failed":
        # Look for fatal error in warnings (worker appends "Fatal error: ...")
        fatal_errors = [w for w in job.warnings if w.startswith("Fatal error:")]
        if fatal_errors:
            error = fatal_errors[-1].replace("Fatal error: ", "")
        elif job.warnings:
            # Fallback to last warning
            error = job.warnings[-1]
    
    # Convert artifacts to dict (will be None if empty)
    artifacts_dict = None
    if job.artifacts:
        artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        # Return None if artifacts dict is empty
        if not artifacts_dict:
            artifacts_dict = None
    
    return JobStatusResponse(
        job_id=job.job_id,  # Will be aliased to "id" in response
        prompt=prompt,
        pipeline=pipeline,
        status=job.status,
        progress_percent=job.progress_percent,
        artifacts=artifacts_dict,
        error=error,
        created_at=job.created_at,
        updated_at=None,  # TODO: Add updated_at tracking to JobRecord
    )


@app.post("/jobs/{job_id}/cancel")
@limiter.limit("10/minute")
async def cancel_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_current_user),
):
    """
    Cancel a running or queued research job.

    Users can only cancel their own jobs. Admins can cancel any job.

    Args:
        job_id: Unique identifier for the research job
        user: The authenticated user

    Returns:
        Success message with job ID

    Raises:
        HTTPException: 400 if job cannot be cancelled (already completed/failed)
        HTTPException: 403 if user doesn't own the job and is not admin
        HTTPException: 404 if job not found
    """
    import uuid

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

    # Check if job can be cancelled
    if job.status not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'. Only queued or running jobs can be cancelled."
        )

    # Attempt to revoke Celery task
    try:
        from backend.worker import celery_app
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        logger.info(f"Revoked Celery task for job {job_id}")
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task for job {job_id}: {e}")
        # Continue anyway - we'll update the status

    # Update job status to cancelled
    update_job(job_id, status="cancelled", stage="cancelled")

    logger.info(
        "Job cancelled",
        extra={
            "job_id": job_id,
            "cancelled_by": user.user_id,
            "event": "job_cancelled",
        }
    )

    return {"message": "Job cancelled successfully", "job_id": job_id}


# =============================================================================
# Transcript Extraction Endpoints
# =============================================================================

TRANSCRIPT_SYNC_THRESHOLD = 5  # Process synchronously if <= this many videos


@app.post("/transcripts")
@limiter.limit("5/hour")
async def extract_transcripts(
    request: Request,
    transcript_request: TranscriptRequest,
):
    """
    Extract transcripts from YouTube videos.

    - For 1-5 videos: Processes synchronously, returns doc URL immediately
    - For 6+ videos: Creates async job, returns job_id for polling

    Args:
        request: FastAPI Request object (for rate limiting)
        transcript_request: Transcript extraction request with video_urls

    Returns:
        TranscriptSyncResponse for small batches, TranscriptAsyncResponse for large batches
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
            # Generic error message to prevent information disclosure
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

        # Enqueue Celery task
        run_transcript_job.delay(job.job_id)

        return TranscriptAsyncResponse(
            job_id=job.job_id,
            status="queued",
            message=f"Processing {video_count} videos in background",
            total_videos=video_count,
        )


@app.get("/transcripts/{job_id}", response_model=TranscriptJobStatusResponse)
@limiter.limit("60/minute")
async def get_transcript_job_status(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """
    Get the status of an async transcript extraction job.

    Requires authentication if the job has an owner (user_id is set).
    Anonymous jobs can be viewed by anyone.

    Args:
        job_id: Unique identifier for the transcript job
        user: Optional authenticated user

    Returns:
        TranscriptJobStatusResponse with progress and doc URL when complete

    Raises:
        HTTPException: 400 if invalid job ID format
        HTTPException: 401 if authentication required but not provided
        HTTPException: 403 if user doesn't own the job
        HTTPException: 404 if job not found
    """
    # Validate job_id format to prevent path traversal
    import uuid
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization check: if job has an owner, verify access
    if job.user_id is not None:
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="Authentication required to view this job",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if job.user_id != user.user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

    # Verify it's a transcript job
    if job.config_json.get("pipeline") != "transcript_only":
        raise HTTPException(status_code=400, detail="Not a transcript job")

    # Extract error from warnings if failed
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


# =============================================================================
# Admin Endpoints
# =============================================================================


@app.get("/admin/check")
async def check_admin_status(user: AuthUser = Depends(get_current_user)):
    """
    Check if the current user is an admin.

    Returns:
        is_admin: True if the user is an admin
    """
    return {"is_admin": is_admin(user)}


@app.get("/admin/stats")
async def get_admin_stats(user: AuthUser = Depends(require_admin)):
    """
    Get admin dashboard statistics.

    Requires admin privileges.

    Returns:
        Statistics including total users, jobs, and error counts
    """
    from datetime import datetime, timedelta
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        today = datetime.utcnow().date().isoformat()

        # Total users (from auth.users via user_settings proxy)
        users_result = supabase.table("user_settings").select("user_id", count="exact").execute()
        total_users = users_result.count or 0

        # Total jobs
        jobs_result = supabase.table("jobs").select("id", count="exact").execute()
        total_jobs = jobs_result.count or 0

        # Jobs created today
        jobs_today_result = supabase.table("jobs").select("id", count="exact").gte("created_at", f"{today}T00:00:00").execute()
        jobs_today = jobs_today_result.count or 0

        # Currently running jobs
        running_result = supabase.table("jobs").select("id", count="exact").eq("status", "running").execute()
        jobs_running = running_result.count or 0

        # Failed jobs today
        failed_today_result = supabase.table("jobs").select("id", count="exact").eq("status", "failed").gte("created_at", f"{today}T00:00:00").execute()
        jobs_failed_today = failed_today_result.count or 0

        # Unresolved errors (if error_logs table exists)
        unresolved_errors = 0
        try:
            errors_result = supabase.table("error_logs").select("id", count="exact").eq("resolved", False).execute()
            unresolved_errors = errors_result.count or 0
        except Exception:
            pass  # Table may not exist yet

        return {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "jobs_today": jobs_today,
            "jobs_running": jobs_running,
            "jobs_failed_today": jobs_failed_today,
            "unresolved_errors": unresolved_errors,
        }
    except Exception as e:
        logger.error(f"Failed to fetch admin stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@app.get("/admin/users")
async def list_admin_users(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
):
    """
    List all users with their statistics.

    Requires admin privileges.

    Args:
        page: Page number (1-indexed)
        page_size: Number of users per page

    Returns:
        Paginated list of users with job counts
    """
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        # Get user settings with job count
        result = supabase.table("user_settings").select(
            "user_id, username, created_at, is_banned",
            count="exact"
        ).range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        # Get job counts for each user
        users = []
        for row in result.data or []:
            job_count_result = supabase.table("jobs").select("id", count="exact").eq("user_id", row["user_id"]).execute()

            # Check if admin
            admin_check = supabase.table("admin_users").select("user_id").eq("user_id", row["user_id"]).execute()
            is_admin_user = len(admin_check.data or []) > 0

            users.append({
                "id": row["user_id"],
                "email": row.get("username") or f"user-{row['user_id'][:8]}",  # Use username or fallback
                "created_at": row["created_at"],
                "last_sign_in_at": None,  # Would need auth.users access
                "job_count": job_count_result.count or 0,
                "is_admin": is_admin_user,
                "is_banned": row.get("is_banned", False),
            })

        return {
            "users": users,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


@app.get("/admin/jobs")
async def list_admin_jobs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    List all jobs with filters.

    Requires admin privileges.

    Args:
        page: Page number (1-indexed)
        page_size: Number of jobs per page
        status: Filter by status
        user_id: Filter by user ID
        date_from: Filter by start date (ISO format)
        date_to: Filter by end date (ISO format)

    Returns:
        Paginated list of jobs
    """
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        # Build query
        query = supabase.table("jobs").select(
            "id, user_id, config_json, status, progress_percent, created_at, warnings",
            count="exact"
        )

        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        result = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        # Get user emails for each job
        jobs = []
        for row in result.data or []:
            config = row.get("config_json", {})

            jobs.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "user_email": config.get("user_email", "Unknown"),
                "prompt": config.get("prompt") or config.get("topic", ""),
                "pipeline": config.get("pipeline", "full"),
                "status": row["status"],
                "progress_percent": row["progress_percent"],
                "created_at": row["created_at"],
                "error": row.get("warnings", [])[-1] if row.get("warnings") else None,
            })

        return {
            "jobs": jobs,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")


@app.post("/admin/jobs/{job_id}/cancel")
async def admin_cancel_job(
    job_id: str,
    user: AuthUser = Depends(require_admin),
):
    """
    Cancel any job as admin.

    Requires admin privileges.

    Args:
        job_id: Job ID to cancel

    Returns:
        Success message
    """
    import uuid

    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    # Revoke Celery task
    try:
        from backend.worker import celery_app
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task: {e}")

    update_job(job_id, status="cancelled", stage="cancelled")

    logger.info(f"Admin {user.user_id} cancelled job {job_id}")

    return {"message": "Job cancelled successfully", "job_id": job_id}


@app.delete("/admin/jobs/{job_id}")
async def admin_delete_job(
    job_id: str,
    user: AuthUser = Depends(require_admin),
):
    """
    Delete a job as admin.

    Requires admin privileges.

    Args:
        job_id: Job ID to delete

    Returns:
        Success message
    """
    import uuid
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cancel if running
    if job.status in ("queued", "running"):
        try:
            from backend.worker import celery_app
            celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        except Exception:
            pass

    # Delete from database
    try:
        supabase = get_supabase_client()
        supabase.table("jobs").delete().eq("id", job_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")

    logger.info(f"Admin {user.user_id} deleted job {job_id}")

    return {"message": "Job deleted successfully", "job_id": job_id}


@app.post("/admin/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    admin_user: AuthUser = Depends(require_admin),
):
    """
    Ban a user.

    Requires admin privileges.

    Args:
        user_id: User ID to ban

    Returns:
        Success message
    """
    from backend.state.impl.supabase_store import get_supabase_client

    if user_id == admin_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    try:
        supabase = get_supabase_client()
        supabase.table("user_settings").update({"is_banned": True}).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to ban user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to ban user")

    logger.info(f"Admin {admin_user.user_id} banned user {user_id}")

    return {"message": "User banned successfully", "user_id": user_id}


@app.post("/admin/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    admin_user: AuthUser = Depends(require_admin),
):
    """
    Unban a user.

    Requires admin privileges.

    Args:
        user_id: User ID to unban

    Returns:
        Success message
    """
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        supabase.table("user_settings").update({"is_banned": False}).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to unban user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unban user")

    logger.info(f"Admin {admin_user.user_id} unbanned user {user_id}")

    return {"message": "User unbanned successfully", "user_id": user_id}


@app.get("/admin/errors")
async def list_error_logs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    resolved: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    List error logs with filters.

    Requires admin privileges.

    Args:
        page: Page number (1-indexed)
        page_size: Number of errors per page
        category: Filter by error category
        resolved: Filter by resolved status
        date_from: Filter by start date (ISO format)
        date_to: Filter by end date (ISO format)

    Returns:
        Paginated list of error logs
    """
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        # Build query
        query = supabase.table("error_logs").select("*", count="exact")

        if category:
            query = query.eq("error_category", category)
        if resolved is not None:
            query = query.eq("resolved", resolved)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        result = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        errors = []
        for row in result.data or []:
            errors.append({
                "id": row["id"],
                "job_id": row.get("job_id"),
                "user_id": row.get("user_id"),
                "user_email": row.get("user_email"),
                "user_message": row["user_message"],
                "error_category": row["error_category"],
                "technical_message": row["technical_message"],
                "stack_trace": row.get("stack_trace"),
                "stage": row.get("stage"),
                "created_at": row["created_at"],
                "resolved": row.get("resolved", False),
            })

        return {
            "errors": errors,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        # If error_logs table doesn't exist, return empty list
        if "error_logs" in str(e).lower() and ("not found" in str(e).lower() or "does not exist" in str(e).lower()):
            return {
                "errors": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
            }
        logger.error(f"Failed to list error logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch error logs")


@app.post("/admin/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    user: AuthUser = Depends(require_admin),
):
    """
    Mark an error as resolved.

    Requires admin privileges.

    Args:
        error_id: Error ID to resolve

    Returns:
        Success message
    """
    from datetime import datetime
    from backend.state.impl.supabase_store import get_supabase_client

    try:
        supabase = get_supabase_client()
        supabase.table("error_logs").update({
            "resolved": True,
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": user.user_id,
        }).eq("id", error_id).execute()
    except Exception as e:
        logger.error(f"Failed to resolve error {error_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve error")

    logger.info(f"Admin {user.user_id} resolved error {error_id}")

    return {"message": "Error resolved successfully", "error_id": error_id}

