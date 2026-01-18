"""Research jobs API routes."""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
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
    TextInputRequest, TextInputResponse,
    ScreenshotInputRequest, ScreenshotInputResponse,
    MixedInputRequest, MixedInputResponse, SourceAccepted,
    # Phase 6: Evolving Jobs
    AddSourcesRequest, AddSourcesResponse, ProcessPendingResponse,
    SourceStateEnum, JobSource,
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

        # If completed (with or without warnings) or failed_insufficient, include producer packet
        # failed_insufficient still has partial artifacts that may be useful
        if job.status in ("completed", "completed_with_warnings", "failed_insufficient"):
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


# =============================================================================
# Extended Input Endpoints (Phase 2B - Text and Screenshot inputs)
# =============================================================================

@router.post("/text-input", response_model=TextInputResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_text_input_job(
    request: Request,
    job_request: TextInputRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Create a semantic extraction job from user-provided text content.

    Used for paywalled articles, emails, or other text the user pastes directly.
    Analysis mode is TEXT_PROVIDED with MEDIUM confidence ceiling.
    NO QUOTES will be extracted - observations only.

    Returns job ID and word count for the content.
    """
    content = job_request.content.strip()
    word_count = len(content.split())

    # Build config_json for the job
    config_json = {
        "topic": job_request.topic,
        "job_type": "text_input",
        "input_mode": "text",
        "content": content,
        "source_label": job_request.source_label,
        "context_note": job_request.context_note,
        "platform_hint": job_request.platform_hint,
        "word_count": word_count,
        "analysis_mode": "text_provided",
        "confidence_ceiling": "MEDIUM",
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
        "Text input job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "word_count": word_count,
            "source_label": job_request.source_label,
            "ip": request.client.host if request.client else None,
            "event": "text_input_job_created",
        }
    )

    # Enqueue Celery task for semantic pipeline
    logger.info(f"Enqueuing text input job {job.job_id} ({word_count} words)")
    run_research_job.apply_async((job.job_id, job_request.topic), task_id=job.job_id)

    # Build warnings
    warnings = []
    if word_count < 100:
        warnings.append("Content is quite short - extraction may be limited")
    if word_count > 20000:
        warnings.append("Large content - processing may take longer")

    return TextInputResponse(
        job_id=job.job_id,
        word_count=word_count,
        confidence_ceiling="MEDIUM",
        warnings=warnings if warnings else None,
    )


@router.post("/screenshot-input", response_model=ScreenshotInputResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_screenshot_input_job(
    request: Request,
    topic: str = Form(..., min_length=1, max_length=500),
    platform_hint: str = Form("other"),
    context_note: Optional[str] = Form(None, max_length=500),
    screenshot: UploadFile = File(...),
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Create a semantic extraction job from a screenshot image.

    OCR extracts text from the screenshot, then semantic extraction runs.
    Analysis mode is OCR_EXTRACTED with MEDIUM confidence ceiling.
    NO QUOTES will be extracted - OCR may have errors.

    Accepts image files up to 10MB (PNG, JPG, WEBP).
    Returns job ID and extracted word count.
    """
    # Validate file type
    allowed_types = {"image/png", "image/jpeg", "image/webp", "image/jpg"}
    if screenshot.content_type not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type: {screenshot.content_type}. Allowed: PNG, JPG, WEBP"
        )

    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await screenshot.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {len(content) / 1024 / 1024:.1f}MB. Maximum: 10MB"
        )

    # Upload screenshot to Supabase Storage (cloud-compatible)
    from pathlib import Path
    from backend.integrations.supabase_storage import get_storage_client

    file_ext = Path(screenshot.filename or "image.png").suffix or ".png"
    user_id_for_storage = user.user_id if user else "anonymous"

    # Try Supabase storage first, fall back to local temp if not configured
    storage_client = get_storage_client()
    screenshot_storage_path: str | None = None
    screenshot_path: str | None = None

    if storage_client:
        try:
            screenshot_storage_path = storage_client.upload_screenshot(
                file_content=content,
                user_id=user_id_for_storage,
                file_extension=file_ext
            )
            logger.info(f"Uploaded screenshot to Supabase: {screenshot_storage_path}")
        except Exception as e:
            logger.warning(f"Supabase upload failed, falling back to local: {e}")
            storage_client = None

    # Fallback to local temp file if Supabase not available
    if not screenshot_storage_path:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "research_agent_screenshots"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{uuid.uuid4()}{file_ext}"
        with open(temp_file, "wb") as f:
            f.write(content)
        screenshot_path = str(temp_file)
        logger.info(f"Saved screenshot locally: {screenshot_path}")

    # Run OCR extraction
    # For now, we'll placeholder this and do OCR in the pipeline
    # The OCR stage will be implemented in Step 2B-4
    ocr_text = ""  # Placeholder - will be extracted in pipeline
    ocr_word_count = 0  # Placeholder

    # Build config_json for the job
    config_json = {
        "topic": topic,
        "job_type": "screenshot_input",
        "input_mode": "screenshot",
        "platform_hint": platform_hint,
        "context_note": context_note,
        "analysis_mode": "ocr_extracted",
        "confidence_ceiling": "MEDIUM",
    }

    # Store storage path (Supabase preferred) or local path as fallback
    if screenshot_storage_path:
        config_json["screenshot_storage_path"] = screenshot_storage_path
    elif screenshot_path:
        config_json["screenshot_path"] = screenshot_path

    # Store user info
    if user:
        config_json["user_email"] = user.email
        config_json["user_id"] = user.user_id

    # Create job
    user_id = user.user_id if user else None
    job = create_job(config_json=config_json, user_id=user_id)

    # Audit log
    logger.info(
        "Screenshot input job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "platform_hint": platform_hint,
            "file_size_kb": len(content) / 1024,
            "ip": request.client.host if request.client else None,
            "event": "screenshot_input_job_created",
        }
    )

    # Enqueue Celery task for OCR + semantic pipeline
    logger.info(f"Enqueuing screenshot input job {job.job_id}")
    run_research_job.apply_async((job.job_id, topic), task_id=job.job_id)

    # Build warnings
    warnings = []
    if platform_hint == "other":
        warnings.append("No platform specified - OCR extraction may be less accurate")

    return ScreenshotInputResponse(
        job_id=job.job_id,
        ocr_word_count=ocr_word_count,  # Will be updated after OCR
        confidence_ceiling="MEDIUM",
        platform_detected=platform_hint,
        warnings=warnings if warnings else None,
    )


# =============================================================================
# Mixed-Input Endpoint (Phase 5 - Multi-Source Support)
# =============================================================================

@router.post("/mixed-input", response_model=MixedInputResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_mixed_input_job(
    request: Request,
    job_request: MixedInputRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Create a semantic extraction job with mixed input sources.

    Accepts any combination of:
    - YouTube video URLs → TRANSCRIPT_GROUNDED or VIDEO_ONLY mode
    - Article URLs → ARTICLE_FETCHED mode
    - User-provided text → TEXT_PROVIDED mode

    At least one input required. Maximum 20 total sources.
    Each source extracted in isolation, then synthesized together.

    Returns job ID and details of accepted sources.
    """
    from backend.pipeline.utils.url_dedup import deduplicate_urls

    # Deduplicate URLs
    unique_video_urls, video_dupes = deduplicate_urls(job_request.video_urls)
    unique_article_urls, article_dupes = deduplicate_urls(job_request.article_urls)
    duplicates_removed = len(video_dupes) + len(article_dupes)

    # Build sources_accepted list and assign source IDs
    sources_accepted = []
    source_counter = 1

    # Videos
    for url in unique_video_urls:
        sources_accepted.append(SourceAccepted(
            source_id=f"SRC_{source_counter}",
            source_type="youtube",
            url=url,
            title=None,  # Will be resolved in pipeline
        ))
        source_counter += 1

    # Articles
    for url in unique_article_urls:
        sources_accepted.append(SourceAccepted(
            source_id=f"SRC_{source_counter}",
            source_type="article",
            url=url,
            title=None,  # Will be resolved in pipeline
        ))
        source_counter += 1

    # Text inputs
    for text_input in job_request.text_inputs:
        sources_accepted.append(SourceAccepted(
            source_id=f"SRC_{source_counter}",
            source_type="user_text",
            url=None,
            title=text_input.title,
        ))
        source_counter += 1

    # Screenshots
    for screenshot in job_request.screenshots:
        sources_accepted.append(SourceAccepted(
            source_id=f"SRC_{source_counter}",
            source_type="screenshot",
            url=None,
            title=screenshot.filename,
        ))
        source_counter += 1

    # Build config_json for the job
    config_json = {
        "topic": job_request.topic,
        "job_type": "mixed_input",
        "input_mode": "mixed",
        "video_urls": unique_video_urls,
        "article_urls": unique_article_urls,
        "text_inputs": [
            {
                "title": ti.title,
                "content": ti.content,
                "platform_hint": ti.platform_hint,
            }
            for ti in job_request.text_inputs
        ],
        "screenshots": [
            {
                "filename": s.filename,
                "base64": s.base64,
                "platform_hint": s.platform_hint,
            }
            for s in job_request.screenshots
        ],
        "source_count": len(sources_accepted),
        "duplicates_removed": duplicates_removed,
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
        "Mixed input job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "video_count": len(unique_video_urls),
            "article_count": len(unique_article_urls),
            "text_count": len(job_request.text_inputs),
            "duplicates_removed": duplicates_removed,
            "ip": request.client.host if request.client else None,
            "event": "mixed_input_job_created",
        }
    )

    # Enqueue Celery task for semantic pipeline
    logger.info(
        f"Enqueuing mixed input job {job.job_id} "
        f"({len(sources_accepted)} sources)"
    )
    run_research_job.apply_async((job.job_id, job_request.topic), task_id=job.job_id)

    # Build warnings
    warnings = []
    if duplicates_removed > 0:
        warnings.append(f"{duplicates_removed} duplicate URL(s) removed")
    if len(unique_video_urls) > 5:
        warnings.append("Many videos - processing may take longer")
    if len(sources_accepted) > 10:
        warnings.append("Large source count - synthesis may be complex")

    return MixedInputResponse(
        job_id=job.job_id,
        status="pending",
        source_count=len(sources_accepted),
        sources_accepted=sources_accepted,
        duplicates_removed=duplicates_removed,
        warnings=warnings if warnings else None,
    )


# =============================================================================
# Evolving Jobs Endpoints (Phase 6 - Add Sources to Completed Jobs)
# =============================================================================

@router.post("/{job_id}/sources", response_model=AddSourcesResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def add_sources_to_job(
    request: Request,
    job_id: str,
    add_request: AddSourcesRequest,
    user: AuthUser = Depends(get_active_user),
):
    """
    Add new sources to an existing completed job.

    The job must be in 'completed' status. New sources are:
    1. Added with status 'pending'
    2. Either processed immediately (process_immediately=True)
    3. Or batched with other pending sources (default, 60s timeout)

    Original document content is preserved (frozen).
    New content is appended in a clearly marked addendum section.
    Cross-references link new content to original analysis.
    """
    from datetime import datetime

    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only (no anonymous)
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    if job.status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add sources to job with status '{job.status}'. "
                   f"Job must be completed first."
        )

    # Deduplicate URLs against each other and existing sources
    from backend.pipeline.utils.url_dedup import deduplicate_urls

    unique_video_urls, video_dupes = deduplicate_urls(add_request.video_urls)
    unique_article_urls, article_dupes = deduplicate_urls(add_request.article_urls)
    duplicates_removed = len(video_dupes) + len(article_dupes)

    # Check if URLs already exist in the job
    existing_urls = set()
    if job.config_json:
        existing_urls.update(job.config_json.get("video_urls", []))
        existing_urls.update(job.config_json.get("article_urls", []))

    already_in_job = []
    new_video_urls = []
    for url in unique_video_urls:
        if url in existing_urls:
            already_in_job.append(url)
        else:
            new_video_urls.append(url)

    new_article_urls = []
    for url in unique_article_urls:
        if url in existing_urls:
            already_in_job.append(url)
        else:
            new_article_urls.append(url)

    # Build list of new sources with source IDs
    # Continue numbering from existing source count
    existing_count = job.config_json.get("source_count", 0) if job.config_json else 0
    source_counter = existing_count + 1
    new_sources = []

    for url in new_video_urls:
        new_sources.append(JobSource(
            source_id=f"SRC_{source_counter}",
            source_type="youtube",
            url=url,
            title=None,  # Will be resolved in pipeline
            status=SourceStateEnum.PENDING,
            added_at=datetime.utcnow(),
            is_original=False,  # Mark as addendum source
        ))
        source_counter += 1

    for url in new_article_urls:
        new_sources.append(JobSource(
            source_id=f"SRC_{source_counter}",
            source_type="article",
            url=url,
            title=None,
            status=SourceStateEnum.PENDING,
            added_at=datetime.utcnow(),
            is_original=False,
        ))
        source_counter += 1

    for text_input in add_request.text_inputs:
        new_sources.append(JobSource(
            source_id=f"SRC_{source_counter}",
            source_type="user_text",
            url=None,
            title=text_input.title,
            status=SourceStateEnum.PENDING,
            added_at=datetime.utcnow(),
            is_original=False,
        ))
        source_counter += 1

    # Validation: at least one new source
    if not new_sources:
        detail = "No new sources to add."
        if already_in_job:
            detail += f" {len(already_in_job)} URL(s) already in job."
        raise HTTPException(status_code=422, detail=detail)

    # Update job config with pending sources
    config_update = job.config_json.copy() if job.config_json else {}
    pending_sources = config_update.get("pending_sources", [])
    pending_sources.extend([s.model_dump() for s in new_sources])
    config_update["pending_sources"] = pending_sources
    config_update["source_count"] = source_counter - 1

    # Store text inputs for later extraction
    if add_request.text_inputs:
        pending_text_inputs = config_update.get("pending_text_inputs", [])
        pending_text_inputs.extend([
            {
                "title": ti.title,
                "content": ti.content,
                "platform_hint": ti.platform_hint,
            }
            for ti in add_request.text_inputs
        ])
        config_update["pending_text_inputs"] = pending_text_inputs

    # Update job status
    new_status = "sources_pending"
    if add_request.process_immediately:
        new_status = "processing"

    update_job(
        job_id,
        config_json=config_update,
        status=new_status,
        stage="sources_added",
    )

    # Audit log
    logger.info(
        "Sources added to evolving job",
        extra={
            "job_id": job_id,
            "user_id": user.user_id,
            "sources_added": len(new_sources),
            "video_count": len(new_video_urls),
            "article_count": len(new_article_urls),
            "text_count": len(add_request.text_inputs),
            "duplicates_removed": duplicates_removed + len(already_in_job),
            "process_immediately": add_request.process_immediately,
            "event": "evolving_job_sources_added",
        }
    )

    # If process_immediately, trigger processing now
    if add_request.process_immediately:
        from backend.worker import process_evolving_job
        logger.info(f"Immediately processing pending sources for job {job_id}")
        process_evolving_job.apply_async(
            (job_id, user.user_id),
            task_id=f"{job_id}_evolving"
        )

    # Build warnings
    warnings = []
    if duplicates_removed > 0:
        warnings.append(f"{duplicates_removed} duplicate URL(s) removed")
    if already_in_job:
        warnings.append(f"{len(already_in_job)} URL(s) already in job")

    return AddSourcesResponse(
        job_id=job_id,
        sources_added=len(new_sources),
        pending_count=len(pending_sources),
        status=new_status,
        batch_timeout_seconds=60,
        warnings=warnings if warnings else None,
    )


@router.post("/{job_id}/process-pending", response_model=ProcessPendingResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def process_pending_sources(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Trigger processing of pending sources for an evolving job.

    Call this endpoint when:
    - User has added sources with process_immediately=False
    - User wants to start processing before the batch timeout

    This endpoint:
    1. Validates job has pending sources
    2. Updates job status to 'processing'
    3. Enqueues the evolving job worker task
    """
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must have pending sources
    if job.status not in ("sources_pending", "completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process sources for job with status '{job.status}'"
        )

    # Check for pending sources in config
    pending_sources = []
    if job.config_json:
        pending_sources = job.config_json.get("pending_sources", [])

    if not pending_sources:
        raise HTTPException(
            status_code=400,
            detail="No pending sources to process"
        )

    # Update job status
    update_job(
        job_id,
        status="processing",
        stage="evolving_extraction",
    )

    # Enqueue worker task
    from backend.worker import process_evolving_job
    logger.info(f"Processing {len(pending_sources)} pending sources for job {job_id}")
    process_evolving_job.apply_async(
        (job_id, user.user_id),
        task_id=f"{job_id}_evolving"
    )

    # Audit log
    logger.info(
        "Processing triggered for evolving job",
        extra={
            "job_id": job_id,
            "user_id": user.user_id,
            "pending_count": len(pending_sources),
            "event": "evolving_job_processing_triggered",
        }
    )

    return ProcessPendingResponse(
        job_id=job_id,
        status="processing",
        pending_count=len(pending_sources),
    )


# =============================================================================
# Document Retrieval Endpoint (for lazy loading)
# =============================================================================

@router.get("/{job_id}/documents/{doc_type}")
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_document(
    request: Request,
    job_id: str,
    doc_type: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Get document content - returns signed URL for storage jobs, inline data for legacy.

    Args:
        job_id: Job UUID
        doc_type: Document type ("doc_0", "doc_1", "doc_2", "doc_3")

    Returns:
        Storage jobs: {"url": "signed_url", "expires_in": 3600}
        Legacy jobs: {"data": {...}, "markdown": "..."}
    """
    from backend.integrations.supabase_storage import get_storage_client

    # Validate doc_type
    valid_doc_types = {"doc_0", "doc_1", "doc_2", "doc_3"}
    if doc_type not in valid_doc_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type: {doc_type}. Valid: {', '.join(sorted(valid_doc_types))}"
        )

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

    # Get artifacts
    artifacts = job.artifacts
    if not artifacts:
        raise HTTPException(status_code=404, detail="No artifacts found for this job")

    if hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Map doc_type to path field and inline field
    doc_mapping = {
        "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger"},
        "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start"},
        "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief"},
        "doc_3": {"path_field": "doc_3_path", "inline_field": "producer_packet"},
    }

    mapping = doc_mapping[doc_type]
    storage_path = artifacts_dict.get(mapping["path_field"])
    inline_data = artifacts_dict.get(mapping["inline_field"])

    # Try storage path first (new jobs)
    if storage_path:
        storage_client = get_storage_client()
        if storage_client:
            try:
                signed_url = storage_client.get_document_url(storage_path, expires_in=3600)
                if signed_url:
                    logger.info(f"Returning signed URL for {doc_type} of job {job_id}")
                    return {
                        "url": signed_url,
                        "expires_in": 3600,
                        "storage_path": storage_path,
                    }
            except Exception as e:
                logger.warning(f"Failed to get signed URL for {storage_path}: {e}")
                # Fall through to inline data

    # Fall back to inline data (legacy jobs or storage failure)
    if inline_data:
        logger.info(f"Returning inline data for {doc_type} of job {job_id}")
        # Inline data already has {data, markdown} structure
        if isinstance(inline_data, dict):
            return {
                "data": inline_data.get("data", inline_data),
                "markdown": inline_data.get("markdown"),
            }
        return {"data": inline_data, "markdown": None}

    raise HTTPException(status_code=404, detail=f"Document {doc_type} not found for this job")


# =============================================================================
# Deep Research Booster Endpoint (Phase 7)
# =============================================================================

@router.post("/{job_id}/booster")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_job_booster(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Trigger Deep Research Booster for a completed job.

    Prerequisites:
    - Job must be in 'completed' or 'completed_with_warnings' status
    - Doc 1 (JumpStartDirections) and Doc 2 (SemanticBrief) must exist

    The booster expands Doc 1 with additional research directions,
    search queries, and perspectives to investigate.

    CRITICAL: The booster produces DIRECTIONS, not FACTS.
    Booster failure does NOT affect existing documents.

    Returns status and message. Poll job status for completion.
    """
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status == "running_booster":
        raise HTTPException(
            status_code=409,
            detail="Booster is already running for this job"
        )

    if job_status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to run booster. Current status: '{job_status}'"
        )

    # Verify required docs exist
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    jump_start = artifacts_dict.get("jump_start")
    semantic_brief = artifacts_dict.get("semantic_brief")

    if not jump_start or not semantic_brief:
        raise HTTPException(
            status_code=400,
            detail="Doc 1 (JumpStartDirections) and Doc 2 (SemanticBrief) must exist to run booster"
        )

    # Check if booster already ran (warn but allow)
    booster_output = artifacts_dict.get("booster_output")
    if booster_output:
        logger.warning(f"[{job_id}] Booster re-run requested (previous output exists)")

    # Update status
    update_job(job_id, status="running_booster", stage="booster")

    # Queue booster task
    from backend.worker import run_booster_task
    logger.info(f"Enqueuing booster task for job {job_id}")
    run_booster_task.apply_async(
        (job_id, user.user_id),
        task_id=f"{job_id}_booster"
    )

    # Audit log
    logger.info(
        "Booster triggered",
        extra={
            "job_id": job_id,
            "user_id": user.user_id,
            "is_re_run": booster_output is not None,
            "event": "booster_triggered",
        }
    )

    return {
        "job_id": job_id,
        "status": "running_booster",
        "message": "Deep Research Booster started. Results will append to Doc 1 (Jump-Start Directions).",
    }


# =============================================================================
# PRODUCER PACKET ENDPOINT (Phase 8 - Doc 3)
# =============================================================================

@router.post("/{job_id}/producer-packet")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def generate_producer_packet(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Generate Producer Packet (Doc 3) for a completed job.

    Prerequisites (V10 Gating):
    - Job must be in 'completed' status
    - 4+ sources in job
    - At least 1 source with high confidence ceiling
    - User explicitly requests (this endpoint)

    Doc 3 contains CREATIVE INTERPRETATION:
    - Story core and narrative angles
    - Opening hooks and structure options
    - Title options and thumbnail concepts
    - Risk assessment and interview suggestions

    CRITICAL: Doc 3 is NOT factual research. It's creative guidance.
    Producer failure does NOT affect Doc 0/1/2.

    Returns status and message. Poll job status for completion.
    """
    from backend.pipeline.producer.gating import can_generate_producer_packet

    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status == "running_producer":
        raise HTTPException(
            status_code=409,
            detail="Producer packet is already being generated for this job"
        )

    if job_status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to generate producer packet. Current status: '{job_status}'"
        )

    # Get job as dict for gating check
    if hasattr(job, "model_dump"):
        job_dict = job.model_dump(exclude_none=True)
    elif hasattr(job, "__dict__"):
        job_dict = {k: v for k, v in job.__dict__.items() if not k.startswith("_")}
    else:
        job_dict = {}

    # Add sources from job record
    if hasattr(job, "sources"):
        job_dict["sources"] = job.sources

    # Check gating requirements
    can_generate, reason = can_generate_producer_packet(job_dict)
    if not can_generate:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot generate producer packet: {reason}"
        )

    # Get existing artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Check if producer packet already exists (warn but allow re-run)
    producer_packet = artifacts_dict.get("producer_packet")
    if producer_packet:
        logger.warning(f"[{job_id}] Producer packet re-run requested (previous output exists)")

    # Update status
    update_job(job_id, status="running_producer", stage="producer")

    # Queue producer task
    from backend.worker import run_producer_task
    logger.info(f"Enqueuing producer task for job {job_id}")
    run_producer_task.apply_async(
        (job_id, user.user_id),
        task_id=f"{job_id}_producer"
    )

    # Audit log
    logger.info(
        "Producer packet triggered",
        extra={
            "job_id": job_id,
            "user_id": user.user_id,
            "is_re_run": producer_packet is not None,
            "event": "producer_triggered",
        }
    )

    return {
        "job_id": job_id,
        "status": "running_producer",
        "message": "Producer Packet (Doc 3) generation started. This is creative interpretation, not factual research.",
    }


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
        # Check job_type first (for video analysis), then pipeline
        pipeline = job.config_json.get("job_type") or job.config_json.get("pipeline", "full")

        artifacts_dict = None
        if job.artifacts:
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
            if not artifacts_dict:
                artifacts_dict = None

        # Extract progress detail from config_json for Gemini video jobs
        pass_detail = None
        if job.config_json:
            pass_detail = job.config_json.get("pass_detail")
        
        # Extract error for failed jobs, warnings for completed_with_warnings
        error = None
        warnings_list = None
        warning_count = None
        if job.status == "failed" and job.warnings:
            error = job.warnings[-1]
        elif job.status == "completed_with_warnings" and job.warnings:
            warnings_list = job.warnings
            warning_count = len(job.warnings)
        elif job.status == "failed_insufficient" and job.warnings:
            error = job.warnings[-1] if job.warnings else "Insufficient data to complete analysis"
            warning_count = len(job.warnings) if job.warnings else 0

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
            "error": error,
            "warnings": warnings_list,
            "warning_count": warning_count,
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
    # Check job_type first (for video analysis), then pipeline
    pipeline = job.config_json.get("job_type") or job.config_json.get("pipeline", "full")

    # Extract error and warnings based on status
    error = None
    warnings_list = None
    warning_count = None
    if job.status == "failed":
        fatal_errors = [w for w in job.warnings if w.startswith("Fatal error:")]
        if fatal_errors:
            error = fatal_errors[-1].replace("Fatal error: ", "")
        elif job.warnings:
            error = job.warnings[-1]
    elif job.status == "completed_with_warnings" and job.warnings:
        warnings_list = job.warnings
        warning_count = len(job.warnings)
    elif job.status == "failed_insufficient" and job.warnings:
        error = job.warnings[-1] if job.warnings else "Insufficient data to complete analysis"
        warning_count = len(job.warnings) if job.warnings else 0

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
        warnings=warnings_list,
        warning_count=warning_count,
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
