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
    TextInputRequest, TextInputResponse,
    ScreenshotInputRequest, ScreenshotInputResponse,
    MixedInputRequest, MixedInputResponse, SourceAccepted,
    # Phase 6: Evolving Jobs
    AddSourcesRequest, AddSourcesResponse, ProcessPendingResponse,
    SourceStateEnum, JobSource,
    # Claim Extraction
    ClaimExtractionRequest, ClaimExtractionResponse,
)
from backend.state import create_job, get_job, update_job, list_jobs, archive_job
from backend.worker import run_research_job, run_claim_extraction_job

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


# =============================================================================
# DEPRECATED: Legacy Topic-Based Job Creation (2026-01-19)
# =============================================================================
# This endpoint has been deprecated in favor of source-first endpoints:
# - POST /jobs/video-analysis
# - POST /jobs/text-input
# - POST /jobs/screenshot-input
# - POST /jobs/mixed-input
# =============================================================================

@router.post("", response_model=CreateJobResponse, deprecated=True)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_job_endpoint(
    request: Request,
    job_request: CreateJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """DEPRECATED: Legacy topic-based job creation.

    This endpoint is deprecated as of 2026-01-19.
    Please use one of the following source-first endpoints instead:
    - POST /jobs/video-analysis - For YouTube video analysis
    - POST /jobs/text-input - For text/document analysis
    - POST /jobs/screenshot-input - For image analysis
    - POST /jobs/mixed-input - For multiple source types
    """
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Legacy topic-based job creation is deprecated",
            "deprecated_since": "2026-01-19",
            "alternatives": [
                {"endpoint": "POST /jobs/video-analysis", "use_for": "YouTube video analysis"},
                {"endpoint": "POST /jobs/text-input", "use_for": "Text/document analysis"},
                {"endpoint": "POST /jobs/screenshot-input", "use_for": "Image analysis"},
                {"endpoint": "POST /jobs/mixed-input", "use_for": "Multiple source types"},
            ],
        }
    )


# =============================================================================
# Claim Extraction Endpoints
# =============================================================================

@router.post("/claim-extraction", response_model=ClaimExtractionResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_claim_extraction_job(
    request: Request,
    job_request: ClaimExtractionRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    Create a claim extraction job from multiple input types.

    Accepts:
    - YouTube video URLs (transcripts analyzed for claims)
    - Article URLs (fetched and analyzed)
    - User-provided text (directly analyzed)
    - Screenshots (OCR + vision analysis)

    Extracts ALL claims (explicit and implied) without verification.
    Output: ClaimsDocument stored and displayed like Doc 0/1/2.
    """
    # Count sources
    video_count = len(job_request.video_urls) if job_request.video_urls else 0
    article_count = len(job_request.article_urls) if job_request.article_urls else 0
    text_count = len(job_request.text_inputs) if job_request.text_inputs else 0
    screenshot_count = len(job_request.screenshots) if job_request.screenshots else 0
    total_sources = video_count + article_count + text_count + screenshot_count

    if total_sources == 0:
        raise HTTPException(status_code=422, detail="At least one source must be provided")

    # Build config_json for the job
    config_json = {
        "title": job_request.title,
        "model": job_request.model,
        "job_type": "claim_extraction",
        "video_urls": job_request.video_urls or [],
        "article_urls": job_request.article_urls or [],
        "text_inputs": [t.model_dump() for t in job_request.text_inputs] if job_request.text_inputs else [],
        "screenshots": [s.model_dump() for s in job_request.screenshots] if job_request.screenshots else [],
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
        "Claim extraction job created",
        extra={
            "job_id": job.job_id,
            "user_id": user_id or "anonymous",
            "video_count": video_count,
            "article_count": article_count,
            "text_count": text_count,
            "screenshot_count": screenshot_count,
            "total_sources": total_sources,
            "model": job_request.model,
            "ip": request.client.host if request.client else None,
            "event": "claim_extraction_job_created",
        }
    )

    # Enqueue Celery task
    logger.info(f"Enqueuing claim extraction job {job.job_id} for {total_sources} sources")
    run_claim_extraction_job.apply_async((job.job_id,), task_id=job.job_id)

    return ClaimExtractionResponse(
        job_id=job.job_id,
        source_count=total_sources,
        video_count=video_count,
        article_count=article_count,
        text_count=text_count,
        screenshot_count=screenshot_count,
        warnings=None,
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
    # doc_3 = Creator Brief (auto-generated, new)
    # doc_4 = Producer Packet (optional, formerly doc_3)
    # booster = DEPRECATED: use Iterate deep_dive mode
    valid_doc_types = {"doc_0", "doc_1", "doc_2", "doc_3", "doc_4", "booster"}
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

    # Map doc_type to path field, inline field, and optional markdown field
    # doc_3 = Creator Brief (auto-generated core document)
    # doc_4 = Producer Packet (optional, user-triggered; formerly doc_3)
    # booster = DEPRECATED (deep_dive via Iterate)
    doc_mapping = {
        "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger", "markdown_field": None},
        "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start", "markdown_field": None},
        "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief", "markdown_field": None},
        "doc_3": {"path_field": "doc_3_path", "inline_field": "creator_brief", "markdown_field": "creator_brief_md"},
        "doc_4": {"path_field": "doc_4_path", "inline_field": "producer_packet", "markdown_field": "producer_packet_md"},
        "booster": {"path_field": None, "inline_field": None, "markdown_field": "booster_expansion_md"},
    }

    mapping = doc_mapping[doc_type]
    storage_path = artifacts_dict.get(mapping["path_field"]) if mapping["path_field"] else None
    inline_data = artifacts_dict.get(mapping["inline_field"]) if mapping["inline_field"] else None
    markdown_content = artifacts_dict.get(mapping["markdown_field"]) if mapping["markdown_field"] else None

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

    # Check for flat markdown field first (producer_packet_md, booster_expansion_md)
    if markdown_content:
        logger.info(f"Returning markdown content for {doc_type} of job {job_id}")
        return {
            "data": {},
            "markdown": markdown_content,
        }

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
# DEPRECATED: Deep Research Booster Endpoint
# ARCHIVED: 2026-03-12 — Phase 1.3.1
# Migration: Use POST /jobs/{job_id}/iterate with {"mode": "deep_dive"} instead.
# Handler logic archived at: backend/archive/booster_stage_archived.py
# =============================================================================

@router.post("/{job_id}/booster")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_job_booster(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """DEPRECATED: This endpoint is no longer active.

    Use POST /jobs/{job_id}/iterate with body {"mode": "deep_dive"} instead.
    The deep_dive mode replaces the Booster — same output, unified API.
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "POST /jobs/{job_id}/booster is deprecated. "
            "Use POST /jobs/{job_id}/iterate with {\"mode\": \"deep_dive\"} instead. "
            "The deep_dive mode provides the same research directions output through the unified Iterate system."
        ),
    )


# =============================================================================
# PRODUCER PACKET ENDPOINT (Doc 4 — formerly Doc 3, renamed 2026-03-12)
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
    producer_status = job.producer_status if hasattr(job, "producer_status") else None

    # Check if producer is already running (use producer_status, not job.status)
    if producer_status == "running":
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

    # Ensure artifacts are in job_dict for gating check
    # If source_ledger not inline but doc_0_path exists, fetch from storage
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts:
        if hasattr(artifacts, "model_dump"):
            artifacts_dict = artifacts.model_dump(exclude_none=True)
        elif isinstance(artifacts, dict):
            artifacts_dict = artifacts
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
        logger.debug(
            f"[{job_id}] Producer gating check: "
            f"doc_0_path={bool(doc_0_path)}, "
            f"source_ledger={bool(source_ledger)}, "
            f"has_sources={_has_sources(source_ledger)}, "
            f"needs_fetch={needs_storage_fetch}"
        )

        if needs_storage_fetch:
            # Fetch source_ledger from storage
            try:
                from backend.integrations.supabase_storage import get_storage_client
                storage = get_storage_client()
                if storage:
                    doc_0_data = storage.download_document(doc_0_path)
                    artifacts_dict["source_ledger"] = doc_0_data
                    logger.info(f"[{job_id}] Fetched source_ledger from storage for gating check")
                else:
                    logger.warning(f"[{job_id}] Storage client unavailable - cannot fetch source_ledger")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to fetch source_ledger from storage: {e}")

        job_dict["artifacts"] = artifacts_dict
    else:
        logger.warning(f"[{job_id}] No artifacts found on job record for producer gating")

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

    # Update producer status (DO NOT modify job.status - it must stay "completed")
    from datetime import datetime, timezone
    update_job(
        job_id,
        producer_status="queued",
        producer_started_at=datetime.now(timezone.utc),
        producer_progress_percent=0,
        producer_error=None,  # Clear any previous error
    )

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
        "status": "queued",  # Return producer status, not job status
        "producer_status": "queued",
        "message": "Producer Packet (Doc 3) generation started. This is creative interpretation, not factual research.",
    }


# =============================================================================
# RUN-SCOPED PRODUCER/BOOSTER ENDPOINTS (V2 Run Abstraction)
# =============================================================================

@router.post("/{job_id}/runs/{run_id}/producer")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_producer_for_run(
    request: Request,
    job_id: str,
    run_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Generate Producer Packet (Doc 3) for a specific run.

    V2 Run Abstraction: Producer outputs are scoped to individual runs.
    This allows different iterations to have their own producer packets.

    Args:
        job_id: Job ID
        run_id: Run ID (e.g., 'run_0' for baseline, 'run_1' for first iteration)
    """
    from backend.pipeline.producer.gating import can_generate_producer_packet
    from backend.models.run_models import ensure_runs_migrated, RunStatus

    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Validate run_id format
    if not run_id.startswith("run_"):
        raise HTTPException(status_code=400, detail="Invalid run ID format. Expected 'run_0', 'run_1', etc.")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to generate producer packet. Current status: '{job_status}'"
        )

    # Get artifacts and find the run
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if not artifacts:
        raise HTTPException(status_code=400, detail="Job has no artifacts")

    # Migrate legacy artifacts to runs if needed
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or "system",
    )

    # Find the requested run
    target_run = None
    for run in runs:
        if run.run_id == run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if target_run.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Run must be completed to generate producer. Current status: '{target_run.status}'"
        )

    # Check if producer already running for this run
    if target_run.producer_packet and target_run.producer_packet.status in (RunStatus.QUEUED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Producer is already {target_run.producer_packet.status.value} for run {run_id}"
        )

    # Queue producer task with run_id
    from backend.worker import run_producer_task
    from datetime import datetime, timezone

    # Update job status
    update_job(
        job_id,
        producer_status="queued",
        producer_started_at=datetime.now(timezone.utc),
        producer_progress_percent=0,
        producer_error=None,
    )

    logger.info(f"Enqueuing producer task for job {job_id} run {run_id}")
    run_producer_task.apply_async(
        (job_id, user.user_id, run_id),  # Pass run_id to worker
        task_id=f"{job_id}_{run_id}_producer"
    )

    return {
        "job_id": job_id,
        "run_id": run_id,
        "status": "queued",
        "producer_status": "queued",
        "message": f"Producer Packet for run {run_id} started.",
    }


@router.post("/{job_id}/runs/{run_id}/booster")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_booster_for_run(
    request: Request,
    job_id: str,
    run_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """DEPRECATED: This endpoint is no longer active.

    Use POST /jobs/{job_id}/iterate with body {"mode": "deep_dive"} instead.
    Archived: 2026-03-12 — Phase 1.3.1
    """
    raise HTTPException(
        status_code=410,
        detail=(
            "POST /jobs/{job_id}/runs/{run_id}/booster is deprecated. "
            "Use POST /jobs/{job_id}/iterate with {\"mode\": \"deep_dive\"} instead."
        ),
    )


# =============================================================================
# CLAIMS DOC ENDPOINT (V2 - Claim Extractor)
# =============================================================================

@router.post("/{job_id}/runs/{run_id}/claims-doc")
@limiter.limit(RATE_LIMITS["jobs_create"])
async def generate_claims_doc_for_run(
    request: Request,
    job_id: str,
    run_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Trigger Claims Document generation for a specific run.

    V2 Claim Extractor: Extracts claims and entities from the run's
    Doc 0/source ledger content. Similar to producer/booster, this is
    a run-scoped artifact generated after the semantic run completes.

    Features:
    - Anchored claims (timestamps if available, else line ranges)
    - Entity Index (people, orgs, places, unnamed)
    - Warning codes for extraction issues

    Args:
        job_id: Job ID
        run_id: Run ID (e.g., 'run_0' for baseline, 'run_1' for first iteration)

    Returns:
        Status object with claims_doc_status
    """
    from backend.models.run_models import ensure_runs_migrated, RunStatus, RunClaimsDoc
    from datetime import datetime, timezone as tz

    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Validate run_id format
    if not run_id.startswith("run_"):
        raise HTTPException(status_code=400, detail="Invalid run ID format. Expected 'run_0', 'run_1', etc.")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to generate claims doc. Current status: '{job_status}'"
        )

    # Get artifacts and find the run
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if not artifacts:
        raise HTTPException(status_code=400, detail="Job has no artifacts")

    # Migrate legacy artifacts to runs if needed
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or "system",
    )

    # Find the requested run
    target_run = None
    for run in runs:
        if run.run_id == run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if target_run.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Run must be completed to generate claims doc. Current status: '{target_run.status}'"
        )

    # Check if run has Doc 0 outputs
    if not target_run.outputs or not target_run.outputs.has_doc_0():
        raise HTTPException(
            status_code=400,
            detail="Run must have Doc 0 (Source Ledger) to generate claims doc"
        )

    # Check if claims_doc already running for this run
    if target_run.claims_doc and target_run.claims_doc.status in (RunStatus.QUEUED, RunStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Claims doc is already {target_run.claims_doc.status.value} for run {run_id}"
        )

    # Queue claims doc task with run_id
    from backend.worker import run_claims_doc_task

    # Update job status
    update_job(
        job_id,
        claims_doc_status="queued",
        claims_doc_started_at=datetime.now(tz.utc),
        claims_doc_progress_percent=0,
        claims_doc_error=None,
    )

    logger.info(f"Enqueuing claims doc task for job {job_id} run {run_id}")
    run_claims_doc_task.apply_async(
        (job_id, user.user_id, run_id),
        task_id=f"{job_id}_{run_id}_claims_doc"
    )

    logger.info(
        "Claims doc triggered",
        extra={
            "job_id": job_id,
            "run_id": run_id,
            "user_id": user.user_id,
            "is_re_run": target_run.claims_doc is not None,
            "event": "claims_doc_triggered",
        }
    )

    return {
        "job_id": job_id,
        "run_id": run_id,
        "status": "queued",
        "claims_doc_status": "queued",
        "message": f"Claims Document for run {run_id} started.",
    }


# =============================================================================
# ITERATION LOOP ENDPOINT (Phase 9)
# =============================================================================

@router.post("/{job_id}/iterate", deprecated=True)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_job_iteration(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """DEPRECATED: V1 iteration endpoint archived 2026-03-11.

    Use POST /jobs/{job_id}/runs (V2 Run Abstraction) instead.
    Full implementation archived to backend/archive/deprecated_route_handlers.py.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "message": "V1 iteration endpoint is deprecated",
            "deprecated_since": "2026-01-26",
            "archived": "2026-03-11",
            "alternative": "POST /jobs/{job_id}/runs",
            "archive_location": "backend/archive/deprecated_route_handlers.py",
        },
    )


# =============================================================================
# V2 RUN-BASED ITERATION ENDPOINT (Run Abstraction)
# =============================================================================

from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from typing import List


class CreateRunRequest(PydanticBaseModel):
    """Request to create a new run (V2 iteration).

    Run types:
    - expand: Add new sources + append findings to Doc 0/1/2
    - refine: Re-analyze existing sources from new angle, append to Doc 1/2
    - regenerate: Full rewrite of Doc 1/2 from all sources

    Legacy types are still accepted and mapped:
    - add_sources → expand
    - fix_weak → refine
    - counter → expand
    - angle → refine
    """
    run_type: str = PydanticField(
        ...,
        description="Run type: expand, refine, regenerate (legacy: add_sources, fix_weak, counter, angle)"
    )
    parent_run_id: str = PydanticField(
        default="run_0",
        description="Parent run ID to build on (default: baseline)"
    )
    user_prompt: str = PydanticField(
        default="",
        description="User guidance for the run (required for refine, optional for expand)"
    )
    # EXPAND type fields
    new_source_urls: List[str] = PydanticField(
        default_factory=list,
        description="URLs to add (for expand type with manual search)"
    )
    max_new_sources: int = PydanticField(
        default=4,
        ge=1, le=10,
        description="Max sources for auto-search (for expand type)"
    )
    search_mode: str = PydanticField(
        default="manual",
        description="'manual' for user-provided URLs, 'auto' for grounded search"
    )
    trust_mode: bool = PydanticField(
        default=False,
        description="Skip user review of search candidates (default: require review)"
    )
    # Legacy fields (kept for backward compatibility)
    gap_ids: List[str] = PydanticField(
        default_factory=list,
        description="[Legacy] Gap IDs to address"
    )
    claim_ids: List[str] = PydanticField(
        default_factory=list,
        description="[Legacy] Claim IDs to find counters for"
    )
    perspective: str = PydanticField(
        default="",
        description="[Legacy] New angle to explore"
    )


class CreateRunResponse(PydanticBaseModel):
    """Response after creating a run."""
    job_id: str
    run_id: str
    run_index: int
    run_type: str
    parent_run_id: str
    status: str
    message: str


class RunStatusResponse(PydanticBaseModel):
    """Response for run status polling."""
    job_id: str
    run_id: str
    run_index: int
    run_type: str
    parent_run_id: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: int = 0
    error: Optional[dict] = None
    outputs: Optional[dict] = None
    metrics: Optional[dict] = None


@router.post("/{job_id}/runs", response_model=CreateRunResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def create_run(
    request: Request,
    job_id: str,
    run_request: CreateRunRequest,
    user: AuthUser = Depends(get_active_user),
):
    """
    Create a new run (V2 iteration) on a completed job.

    Run types:
    - expand: Add new sources + append findings to Doc 0/1/2
    - refine: Re-analyze existing sources from new angle, append to Doc 1/2
    - regenerate: Full rewrite of Doc 1/2 from all sources

    Legacy types are accepted and mapped automatically:
    - add_sources → expand, fix_weak → refine, counter → expand, angle → refine

    CRITICAL:
    - jobs.status remains 'completed' after run starts
    - Run failure does NOT affect parent run documents
    - EXPAND/REFINE runs produce APPEND-ONLY sections (originals untouched)
    - Only REGENERATE replaces existing Doc 1/2

    Returns run_id and status. Poll job status for completion.
    """
    from datetime import datetime, timezone
    from backend.models.run_models import (
        Run, RunType, RunStatus, RunRequest, RunOutputs,
        ensure_runs_migrated, create_iteration_run,
        normalize_run_type,
    )

    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Validate and normalize run_type
    valid_run_types = ["expand", "refine", "regenerate", "add_sources", "fix_weak", "counter", "angle"]
    if run_request.run_type not in valid_run_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid run_type. Must be one of: expand, refine, regenerate"
        )

    # Normalize to canonical type (handles legacy mappings)
    run_type = normalize_run_type(run_request.run_type)

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner only
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Job must be completed
    job_status = job.status if hasattr(job, "status") else job.get("status")
    if job_status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be completed to create run. Current status: '{job_status}'"
        )

    # Check if another run/iteration is in progress
    iteration_status = job.iteration_status if hasattr(job, "iteration_status") else None
    if iteration_status in ("running", "queued", "awaiting_review"):
        raise HTTPException(
            status_code=409,
            detail="Another run/iteration is already in progress for this job"
        )

    # Get artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    if artifacts and hasattr(artifacts, "model_dump"):
        artifacts_dict = artifacts.model_dump(exclude_none=True)
    elif isinstance(artifacts, dict):
        artifacts_dict = artifacts
    else:
        artifacts_dict = {}

    # Get or migrate runs
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or user.user_id,
    )

    if not runs:
        raise HTTPException(
            status_code=400,
            detail="No baseline run found. Job must have completed baseline documents."
        )

    # Find parent run
    parent_run = None
    for run in runs:
        if run.run_id == run_request.parent_run_id:
            parent_run = run
            break

    if not parent_run:
        raise HTTPException(
            status_code=404,
            detail=f"Parent run '{run_request.parent_run_id}' not found"
        )

    if parent_run.status != RunStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Parent run must be completed. Current status: '{parent_run.status}'"
        )

    # Calculate next run index
    next_index = max(r.run_index for r in runs) + 1
    new_run_id = f"run_{next_index}"

    # Validate REFINE requires user_prompt
    if run_type == RunType.REFINE and not run_request.user_prompt:
        raise HTTPException(
            status_code=400,
            detail="REFINE runs require a user_prompt describing the analysis angle"
        )

    # Build run request
    now = datetime.now(timezone.utc)
    new_run_request = RunRequest(
        user_prompt=run_request.user_prompt or None,
        # EXPAND fields
        new_source_urls=run_request.new_source_urls if run_request.new_source_urls else None,
        max_new_sources=run_request.max_new_sources if run_type == RunType.EXPAND else None,
        search_mode=run_request.search_mode if run_type == RunType.EXPAND else None,
        trust_mode=run_request.trust_mode if run_type == RunType.EXPAND else False,
        # Legacy fields (kept for backward compat)
        gap_ids=run_request.gap_ids if run_request.gap_ids else None,
        claim_ids=run_request.claim_ids if run_request.claim_ids else None,
        perspective=run_request.perspective or None,
        requested_by=user.user_id,
        requested_at=now,
    )

    # Create new run
    new_run = Run(
        run_id=new_run_id,
        run_index=next_index,
        run_type=run_type,
        parent_run_id=parent_run.run_id,
        status=RunStatus.QUEUED,
        request=new_run_request,
        created_at=now,
    )

    # Append to runs list
    runs.append(new_run)

    # Update artifacts with new runs
    from backend.models.job_record import Artifacts
    updated_artifacts = Artifacts(**{
        **artifacts_dict,
        "runs": [r.model_dump() for r in runs],
    })

    # Update job with run tracking
    try:
        update_job(
            job_id,
            iteration_status="queued",  # Reuse iteration tracking for now
            iteration_id=new_run_id,
            iteration_started_at=now,
            iteration_progress_percent=0,
            iteration_error=None,
            artifacts=updated_artifacts,
        )
    except Exception as e:
        error_str = str(e).lower()
        if "unique" in error_str or "duplicate" in error_str or "23505" in error_str:
            logger.warning(f"Concurrent run creation blocked for job {job_id}: {e}")
            raise HTTPException(
                status_code=409,
                detail="Another run is already in progress (concurrent request blocked)"
            )
        raise

    # Queue run task (reuse iteration task for now, will be updated)
    from backend.worker import run_iteration_task
    logger.info(f"Enqueuing run task for job {job_id}, run {new_run_id}")
    run_iteration_task.apply_async(
        (job_id, new_run_id, user.user_id),
        task_id=f"{job_id}_{new_run_id}"
    )

    # Audit log
    logger.info(
        "Run created",
        extra={
            "job_id": job_id,
            "run_id": new_run_id,
            "run_index": next_index,
            "run_type": run_request.run_type,
            "parent_run_id": parent_run.run_id,
            "user_id": user.user_id,
            "event": "run_created",
        }
    )

    return CreateRunResponse(
        job_id=job_id,
        run_id=new_run_id,
        run_index=next_index,
        run_type=run_request.run_type,
        parent_run_id=parent_run.run_id,
        status="queued",
        message=f"Run {new_run_id} ({run_request.run_type}) started. Parent run documents unchanged.",
    )


@router.get("/{job_id}/runs/{run_id}", response_model=RunStatusResponse)
@limiter.limit(RATE_LIMITS["jobs_status"])
async def get_run_status(
    request: Request,
    job_id: str,
    run_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Get status of a specific run.

    Used for polling run progress during execution.
    Returns run status, progress, outputs (if completed), and error (if failed).
    """
    from backend.models.run_models import ensure_runs_migrated

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

    # Get artifacts
    artifacts = job.artifacts if hasattr(job, "artifacts") else None

    # Get or migrate runs
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or user.user_id,
    )

    # Find the requested run
    target_run = None
    for run in runs:
        if run.run_id == run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    # Get progress from job iteration tracking (reused for runs)
    progress_percent = 0
    if hasattr(job, "iteration_id") and job.iteration_id == run_id:
        progress_percent = getattr(job, "iteration_progress_percent", 0) or 0

    # Format timestamps
    def fmt_ts(ts):
        if ts is None:
            return None
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
        return str(ts)

    # Build response
    return RunStatusResponse(
        job_id=job_id,
        run_id=target_run.run_id,
        run_index=target_run.run_index,
        run_type=target_run.run_type.value if hasattr(target_run.run_type, "value") else str(target_run.run_type),
        parent_run_id=target_run.parent_run_id,
        status=target_run.status.value if hasattr(target_run.status, "value") else str(target_run.status),
        created_at=fmt_ts(target_run.created_at),
        started_at=fmt_ts(target_run.started_at),
        completed_at=fmt_ts(target_run.completed_at),
        progress_percent=progress_percent,
        error=target_run.error.model_dump() if target_run.error and hasattr(target_run.error, "model_dump") else (target_run.error if isinstance(target_run.error, dict) else None),
        outputs=target_run.outputs.model_dump() if target_run.outputs and hasattr(target_run.outputs, "model_dump") else (target_run.outputs if isinstance(target_run.outputs, dict) else None),
        metrics=target_run.metrics.model_dump() if target_run.metrics and hasattr(target_run.metrics, "model_dump") else (target_run.metrics if isinstance(target_run.metrics, dict) else None),
    )


# =============================================================================
# RUN: Source Review (for EXPAND with auto-search)
# =============================================================================


class SourceApprovalRequest(PydanticBaseModel):
    """Request to approve/reject search candidates."""
    approved_urls: List[str] = PydanticField(
        ..., description="URLs the user approved for processing"
    )
    rejected_urls: List[str] = PydanticField(
        default_factory=list, description="URLs the user rejected"
    )


class SourceApprovalResponse(PydanticBaseModel):
    """Response after approving search sources."""
    job_id: str
    run_id: str
    status: str
    approved_count: int
    message: str


@router.post("/{job_id}/runs/{run_id}/approve-sources", response_model=SourceApprovalResponse)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def approve_search_sources(
    request: Request,
    job_id: str,
    run_id: str,
    approval: SourceApprovalRequest,
    user: AuthUser = Depends(get_active_user),
):
    """
    Approve or reject search candidates for an EXPAND run.

    Called after grounded search produces candidates and the run
    enters AWAITING_REVIEW status. Approving resumes the run
    to process the selected sources.
    """
    from backend.models.run_models import RunStatus, ensure_runs_migrated

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

    # Get runs and find the target
    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or user.user_id,
    )

    target_run = None
    for run in runs:
        if run.run_id == run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if target_run.status != RunStatus.AWAITING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"Run is not awaiting review. Current status: '{target_run.status.value}'"
        )

    if not approval.approved_urls:
        raise HTTPException(
            status_code=400,
            detail="At least one URL must be approved to continue the run"
        )

    # Queue resume task
    from backend.worker import run_iteration_task
    logger.info(f"Resuming expand run {run_id} for job {job_id} with {len(approval.approved_urls)} approved URLs")

    # We re-use the iteration task which dispatches to _resume_expand_after_review
    # by injecting approved URLs into the run request
    from datetime import datetime, timezone
    from backend.models.job_record import Artifacts

    # Update the run's request with approved URLs
    if target_run.request:
        target_run.request.new_source_urls = approval.approved_urls
        target_run.request.search_candidates = None  # Clear candidates

    # Find run index
    run_idx = None
    for i, r in enumerate(runs):
        if r.run_id == run_id:
            run_idx = i
            break

    if run_idx is not None:
        runs[run_idx] = target_run

    artifacts_dict = artifacts.model_dump(exclude_none=True) if hasattr(artifacts, "model_dump") else (artifacts if isinstance(artifacts, dict) else {})

    update_job(
        job_id,
        iteration_status="running",
        iteration_id=run_id,
        iteration_progress_percent=55,
        artifacts=Artifacts(**{**artifacts_dict, "runs": [r.model_dump() for r in runs]}),
    )

    # Re-queue the run task (it will pick up the approved URLs)
    run_iteration_task.apply_async(
        (job_id, run_id, user.user_id),
        task_id=f"{job_id}_{run_id}_resume"
    )

    return SourceApprovalResponse(
        job_id=job_id,
        run_id=run_id,
        status="running",
        approved_count=len(approval.approved_urls),
        message=f"Processing {len(approval.approved_urls)} approved sources. Run resumed.",
    )


class SearchCandidateResponse(PydanticBaseModel):
    """Response containing search candidates awaiting review."""
    job_id: str
    run_id: str
    status: str
    candidates: List[dict]
    total_count: int


@router.get("/{job_id}/runs/{run_id}/search-candidates", response_model=SearchCandidateResponse)
@limiter.limit(RATE_LIMITS["jobs_status"])
async def get_search_candidates(
    request: Request,
    job_id: str,
    run_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Get search candidates awaiting user review for an EXPAND run.

    Returns the list of search results from grounded search that
    the user needs to approve or reject before the run continues.
    """
    from backend.models.run_models import RunStatus, ensure_runs_migrated

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

    artifacts = job.artifacts if hasattr(job, "artifacts") else None
    runs = ensure_runs_migrated(
        artifacts,
        job_created_at=job.created_at if hasattr(job, "created_at") else None,
        job_completed_at=job.completed_at if hasattr(job, "completed_at") else None,
        user_id=job.user_id or user.user_id,
    )

    target_run = None
    for run in runs:
        if run.run_id == run_id:
            target_run = run
            break

    if not target_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    # Get candidates from run request
    candidates = []
    if target_run.request and target_run.request.search_candidates:
        candidates = target_run.request.search_candidates

    return SearchCandidateResponse(
        job_id=job_id,
        run_id=run_id,
        status=target_run.status.value if hasattr(target_run.status, "value") else str(target_run.status),
        candidates=candidates,
        total_count=len(candidates),
    )


# =============================================================================
# DEPRECATED: Legacy Job Preview (2026-01-19)
# =============================================================================

@router.post("/preview", response_model=PreviewJobResponse, deprecated=True)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def preview_job_endpoint(
    request: Request,
    preview_request: PreviewJobRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """DEPRECATED: Legacy job preview endpoint.

    This endpoint is deprecated as of 2026-01-19.
    The new source-first workflow doesn't require a preview step.
    Users provide sources directly via /video-analysis, /text-input, etc.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Legacy job preview is deprecated",
            "deprecated_since": "2026-01-19",
            "reason": "Source-first workflow doesn't require preview",
            "alternatives": [
                {"endpoint": "POST /jobs/video-analysis", "use_for": "YouTube video analysis"},
                {"endpoint": "POST /jobs/text-input", "use_for": "Text/document analysis"},
                {"endpoint": "POST /jobs/screenshot-input", "use_for": "Image analysis"},
                {"endpoint": "POST /jobs/mixed-input", "use_for": "Multiple source types"},
            ],
        }
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

        # Get title from job.title or fall back to config_json.title/topic
        title = job.title or job.config_json.get("title") or job.config_json.get("topic") or prompt

        jobs_data.append({
            "id": job.job_id,
            "prompt": prompt,
            "title": title,
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
            # Booster tracking fields
            "booster_status": getattr(job, 'booster_status', None),
            "booster_started_at": getattr(job, 'booster_started_at', None).isoformat() if getattr(job, 'booster_started_at', None) else None,
            "booster_completed_at": getattr(job, 'booster_completed_at', None).isoformat() if getattr(job, 'booster_completed_at', None) else None,
            "booster_error": getattr(job, 'booster_error', None),
            "booster_progress_percent": getattr(job, 'booster_progress_percent', None),
            # Producer packet tracking fields
            "producer_status": getattr(job, 'producer_status', None),
            "producer_started_at": getattr(job, 'producer_started_at', None).isoformat() if getattr(job, 'producer_started_at', None) else None,
            "producer_completed_at": getattr(job, 'producer_completed_at', None).isoformat() if getattr(job, 'producer_completed_at', None) else None,
            "producer_error": getattr(job, 'producer_error', None),
            "producer_progress_percent": getattr(job, 'producer_progress_percent', None),
            # Iteration tracking fields
            "iteration_status": getattr(job, 'iteration_status', None),
            "iteration_id": getattr(job, 'iteration_id', None),
            "iteration_started_at": getattr(job, 'iteration_started_at', None).isoformat() if getattr(job, 'iteration_started_at', None) else None,
            "iteration_completed_at": getattr(job, 'iteration_completed_at', None).isoformat() if getattr(job, 'iteration_completed_at', None) else None,
            "iteration_error": getattr(job, 'iteration_error', None),
            "iteration_progress_percent": getattr(job, 'iteration_progress_percent', None),
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

    # Compute document availability (inline vs storage) for diagnostics/UX
    documents_ready = None
    if artifacts_dict:
        # Map doc_type to path/inline keys (keep in sync with get_document)
        doc_mapping = {
            "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger"},
            "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start"},
            "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief"},
            "doc_3": {"path_field": "doc_3_path", "inline_field": "producer_packet"},
        }
        documents_ready = {}
        for key, mapping in doc_mapping.items():
            storage_ok = bool(artifacts_dict.get(mapping["path_field"]))
            inline_ok = bool(artifacts_dict.get(mapping["inline_field"]))
            # Only include entries that are relevant/present
            if storage_ok or inline_ok:
                documents_ready[key] = {"inline": inline_ok, "storage": storage_ok}

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
        documents_ready=documents_ready,
        # Booster tracking fields
        booster_status=getattr(job, 'booster_status', None),
        booster_started_at=getattr(job, 'booster_started_at', None),
        booster_completed_at=getattr(job, 'booster_completed_at', None),
        booster_error=getattr(job, 'booster_error', None),
        booster_progress_percent=getattr(job, 'booster_progress_percent', None),
        # Producer packet tracking fields
        producer_status=getattr(job, 'producer_status', None),
        producer_started_at=getattr(job, 'producer_started_at', None),
        producer_completed_at=getattr(job, 'producer_completed_at', None),
        producer_error=getattr(job, 'producer_error', None),
        producer_progress_percent=getattr(job, 'producer_progress_percent', None),
        # Iteration tracking fields
        iteration_status=getattr(job, 'iteration_status', None),
        iteration_id=getattr(job, 'iteration_id', None),
        iteration_started_at=getattr(job, 'iteration_started_at', None),
        iteration_completed_at=getattr(job, 'iteration_completed_at', None),
        iteration_error=getattr(job, 'iteration_error', None),
        iteration_progress_percent=getattr(job, 'iteration_progress_percent', None),
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


@router.post("/{job_id}/select-interpretation", deprecated=True)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def select_interpretation(
    request: Request,
    job_id: str,
    selection: SelectInterpretationRequest,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """
    DEPRECATED: Disambiguation is no longer supported (2026-01-19).

    This endpoint was used for topic-based discovery disambiguation.
    The new pipeline only supports user-supplied sources and does not
    require disambiguation.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Disambiguation is no longer supported",
            "deprecated_since": "2026-01-19",
            "reason": "Topic-based discovery has been removed. Use source-first endpoints (/video-analysis, /text-input, /screenshot-input, /mixed-input).",
        },
    )


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


# =============================================================================
# LAZY-LOAD API ENDPOINTS (Option B Storage Strategy - 2026-01-19)
# =============================================================================

@router.get("/{job_id}/manifest")
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_job_manifest(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get job status and artifact manifest (small payload).

    Returns only status + artifact_manifest for manifest-first UI.
    Does not include full document content.
    """
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
            raise HTTPException(status_code=401, detail="Authentication required")
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Extract artifact_manifest from artifacts
    artifact_manifest = None
    if job.artifacts:
        artifacts_dict = job.artifacts.model_dump(exclude_none=True)
        artifact_manifest = artifacts_dict.get("artifact_manifest")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "stage": job.stage,
        "progress_percent": job.progress_percent,
        "title": job.title,
        "artifact_manifest": artifact_manifest,
    }


@router.get("/{job_id}/doc/{doc_id}")
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_job_document(
    request: Request,
    job_id: str,
    doc_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get a specific core document by ID (20, 21, or 22).

    Returns markdown content for the specified document.
    """
    # Validate doc_id
    if doc_id not in ("20", "21", "22"):
        raise HTTPException(
            status_code=400,
            detail="Invalid doc_id. Must be 20 (Source Ledger), 21 (Jump Start), or 22 (Semantic Brief)"
        )

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
            raise HTTPException(status_code=401, detail="Authentication required")
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    if not job.artifacts:
        raise HTTPException(status_code=404, detail="No artifacts available")

    artifacts_dict = job.artifacts.model_dump(exclude_none=True)

    # Map doc_id to artifact fields
    doc_mapping = {
        "20": {"inline_field": "source_ledger", "path_field": "doc_0_path", "title": "Source Ledger"},
        "21": {"inline_field": "jump_start", "path_field": "doc_1_path", "title": "Jump Start"},
        "22": {"inline_field": "semantic_brief", "path_field": "doc_2_path", "title": "Semantic Brief"},
    }

    mapping = doc_mapping[doc_id]
    markdown_content = None

    # Try inline first
    inline_data = artifacts_dict.get(mapping["inline_field"])
    if inline_data and isinstance(inline_data, dict):
        markdown_content = inline_data.get("markdown")

    # If inline is a stub or missing, try storage
    if not markdown_content or "stored in Supabase Storage" in (markdown_content or ""):
        storage_path = artifacts_dict.get(mapping["path_field"])
        if storage_path:
            try:
                from backend.integrations.supabase_storage import get_storage_client
                storage_client = get_storage_client()
                if storage_client:
                    doc_data = storage_client.download_document(storage_path)
                    markdown_content = doc_data.get("markdown")
            except Exception as e:
                logger.warning(f"Failed to fetch doc {doc_id} from storage: {e}")

    if not markdown_content:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} ({mapping['title']}) not found")

    return {
        "job_id": job_id,
        "doc_id": doc_id,
        "title": mapping["title"],
        "markdown": markdown_content,
    }


@router.get("/{job_id}/attachments")
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_job_attachments(
    request: Request,
    job_id: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Get list of available attachments with signed URLs.

    Generates fresh signed URLs if expired.
    Does NOT return attachment content, only metadata and URLs.
    """
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
            raise HTTPException(status_code=401, detail="Authentication required")
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    if not job.artifacts:
        return {"job_id": job_id, "attachments": []}

    artifacts_dict = job.artifacts.model_dump(exclude_none=True)
    manifest = artifacts_dict.get("artifact_manifest", {})
    attachments_info = manifest.get("attachments", {})

    # Get storage client for refreshing URLs
    from backend.integrations.supabase_storage import get_storage_client
    storage_client = get_storage_client()

    result_attachments = []

    # Process exports
    exports = attachments_info.get("exports", [])
    for export in exports:
        if not export.get("present"):
            continue

        attachment = {
            "name": export.get("name"),
            "storage_path": export.get("storage_path"),
            "type": "export",
        }

        # Refresh signed URL if storage client available
        if storage_client and export.get("storage_path"):
            try:
                attachment["signed_url"] = storage_client.get_signed_url(
                    export["storage_path"],
                    expires_in=3600,
                    bucket="documents"
                )
            except Exception:
                attachment["signed_url"] = export.get("signed_url")
        else:
            attachment["signed_url"] = export.get("signed_url")

        result_attachments.append(attachment)

    # Process producer packet
    producer_info = attachments_info.get("producer_packet", {})
    if producer_info.get("present"):
        result_attachments.append({
            "name": "producer_packet.json",
            "type": "producer_packet",
            "present": True,
            "note": "Producer packet is available inline in job artifacts",
        })

    # Process PDF (check if exists in storage)
    pdf_info = attachments_info.get("pdf", {})
    if pdf_info.get("present") and pdf_info.get("storage_path"):
        pdf_attachment = {
            "name": "download.pdf",
            "storage_path": pdf_info.get("storage_path"),
            "type": "pdf",
        }
        if storage_client:
            try:
                pdf_attachment["signed_url"] = storage_client.get_signed_url(
                    pdf_info["storage_path"],
                    expires_in=3600,
                    bucket="documents"
                )
            except Exception:
                pdf_attachment["signed_url"] = None
        result_attachments.append(pdf_attachment)

    return {
        "job_id": job_id,
        "attachments": result_attachments,
    }


@router.get("/{job_id}/attachments/{filename}")
@limiter.limit(RATE_LIMITS["jobs_get"])
async def get_attachment_redirect(
    request: Request,
    job_id: str,
    filename: str,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Redirect to signed URL for a specific attachment.

    Returns 302 redirect to the Supabase Storage signed URL.
    """
    from fastapi.responses import RedirectResponse

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
            raise HTTPException(status_code=401, detail="Authentication required")
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get storage client
    from backend.integrations.supabase_storage import get_storage_client
    storage_client = get_storage_client()

    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage service unavailable")

    # Build storage path and get signed URL
    storage_path = f"research/{job_id}/attachments/{filename}"

    try:
        signed_url = storage_client.get_signed_url(
            storage_path,
            expires_in=3600,
            bucket="documents"
        )
        if not signed_url:
            raise HTTPException(status_code=404, detail=f"Attachment {filename} not found")

        return RedirectResponse(url=signed_url, status_code=302)

    except Exception as e:
        logger.warning(f"Failed to get signed URL for {filename}: {e}")
        raise HTTPException(status_code=404, detail=f"Attachment {filename} not found")


@router.get("/{job_id}/download.pdf")
@limiter.limit("10/minute")  # PDF generation is expensive
async def download_job_pdf(
    request: Request,
    job_id: str,
    regenerate: bool = False,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
):
    """Generate and download PDF of core documents (20-22).

    Returns redirect to signed URL for cached PDF.
    If regenerate=True or PDF doesn't exist, generates new PDF.

    The PDF contains:
    - Doc 20: Source Ledger
    - Doc 21: Jump Start
    - Doc 22: Semantic Brief
    - Attachments Manifest page

    Note: Returns JSON error if PDF generation fails (job does not fail).
    """
    from fastapi.responses import RedirectResponse

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
            raise HTTPException(status_code=401, detail="Authentication required")
        if job.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get storage client
    from backend.integrations.supabase_storage import get_storage_client
    storage_client = get_storage_client()

    if not storage_client:
        raise HTTPException(status_code=503, detail="Storage service unavailable")

    pdf_filename = "download.pdf"
    pdf_storage_path = f"research/{job_id}/attachments/{pdf_filename}"

    # Check if PDF already exists (unless regenerate requested)
    if not regenerate:
        try:
            signed_url = storage_client.get_signed_url(
                pdf_storage_path,
                expires_in=3600,
                bucket="documents"
            )
            if signed_url:
                return RedirectResponse(url=signed_url, status_code=302)
        except Exception:
            pass  # PDF doesn't exist, will generate

    # Generate PDF
    try:
        pdf_bytes = _generate_job_pdf(job)

        # Upload to storage
        upload_result = storage_client.upload_attachment(
            job_id=job_id,
            filename=pdf_filename,
            content=pdf_bytes,
            expires_in=3600,
        )

        # Update manifest to mark PDF as present
        if job.artifacts:
            artifacts_dict = job.artifacts.model_dump(exclude_none=True)
            manifest = artifacts_dict.get("artifact_manifest", {})
            if "attachments" in manifest:
                manifest["attachments"]["pdf"] = {
                    "present": True,
                    "storage_path": upload_result["storage_path"],
                    "signed_url": upload_result["signed_url"],
                }
                # Update job with new manifest
                from backend.models.job_record import Artifacts
                artifacts_dict["artifact_manifest"] = manifest
                update_job(job_id, artifacts=Artifacts(**artifacts_dict))

        return RedirectResponse(url=upload_result["signed_url"], status_code=302)

    except Exception as e:
        logger.error(f"PDF generation failed for job {job_id}: {e}")
        # Return JSON error instead of failing
        return {
            "error": "PDF generation failed",
            "message": str(e),
            "job_id": job_id,
        }


def _generate_job_pdf(job) -> bytes:
    """Generate PDF bytes containing core documents.

    Args:
        job: JobRecord with artifacts

    Returns:
        PDF file as bytes

    Raises:
        Exception: If PDF generation fails
    """
    # Try to use markdown-pdf or reportlab
    # For now, use a simple text-based approach with reportlab
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.units import inch
        from io import BytesIO
    except ImportError:
        raise Exception("reportlab not installed - PDF generation unavailable")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
    )

    story = []

    # Title page
    topic = job.config_json.get("topic", "Research") if job.config_json else "Research"
    story.append(Paragraph(f"Research Report: {topic}", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Job ID: {job.job_id}", body_style))
    story.append(Paragraph(f"Generated: {job.created_at.isoformat()}", body_style))
    story.append(PageBreak())

    # Get document markdown from artifacts
    artifacts_dict = job.artifacts.model_dump(exclude_none=True) if job.artifacts else {}

    docs_to_include = [
        ("20", "source_ledger", "Source Ledger"),
        ("21", "jump_start", "Jump Start"),
        ("22", "semantic_brief", "Semantic Brief"),
    ]

    for doc_id, inline_field, title in docs_to_include:
        story.append(Paragraph(f"Document {doc_id}: {title}", title_style))
        story.append(Spacer(1, 0.1*inch))

        markdown_content = None
        inline_data = artifacts_dict.get(inline_field)
        if inline_data and isinstance(inline_data, dict):
            markdown_content = inline_data.get("markdown")

        if markdown_content and "stored in Supabase Storage" not in markdown_content:
            # Simple markdown to text conversion (basic)
            text = markdown_content.replace("#", "").replace("*", "").replace("`", "")
            # Split into paragraphs and add them
            for para in text.split("\n\n"):
                para = para.strip()
                if para:
                    # Escape XML special characters
                    para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    try:
                        story.append(Paragraph(para[:2000], body_style))  # Limit paragraph length
                        story.append(Spacer(1, 0.1*inch))
                    except Exception:
                        story.append(Paragraph("[Content formatting error]", body_style))
        else:
            story.append(Paragraph(f"[{title} not available]", body_style))

        story.append(PageBreak())

    # Attachments manifest page
    story.append(Paragraph("Attachments Manifest", title_style))
    manifest = artifacts_dict.get("artifact_manifest", {})
    attachments = manifest.get("attachments", {})
    exports = attachments.get("exports", [])

    if exports:
        for export in exports:
            if export.get("present"):
                story.append(Paragraph(f"• {export.get('name')}", body_style))
    else:
        story.append(Paragraph("No exports available", body_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ============================================================================
# Archive Management Endpoints
# ============================================================================

@router.get("/archived")
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_archived_jobs_endpoint(
    request: Request,
    user: Optional[AuthUser] = Depends(get_optional_active_user),
    limit: int = 50,
    offset: int = 0,
):
    """List all archived jobs for the current user."""
    user_id = user.user_id if user else None
    jobs = list_jobs(user_id=user_id, limit=limit, offset=offset, archived=True)

    jobs_data = []
    for job in jobs:
        prompt = job.config_json.get("prompt") or job.config_json.get("topic", "")
        pipeline = job.config_json.get("job_type") or job.config_json.get("pipeline", "full")
        title = job.title or job.config_json.get("title") or job.config_json.get("topic") or prompt

        jobs_data.append({
            "id": job.job_id,
            "prompt": prompt,
            "title": title,
            "pipeline": pipeline,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "archived": job.archived,
        })

    return {"jobs": jobs_data}


@router.post("/{job_id}/archive")
@limiter.limit(RATE_LIMITS["jobs_cancel"])  # Reuse cancel rate limit
async def archive_job_endpoint(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Archive a job (hide from main job list)."""
    # Validate job_id format
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

    # Cannot archive running jobs
    if job.status in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail="Cannot archive a running or queued job. Cancel it first."
        )

    updated_job = archive_job(job_id, archived=True)
    if not updated_job:
        raise HTTPException(status_code=500, detail="Failed to archive job")

    logger.info(
        "Job archived",
        extra={"job_id": job_id, "archived_by": user.user_id, "event": "job_archived"}
    )

    return {"message": "Job archived successfully", "job_id": job_id}


@router.post("/{job_id}/unarchive")
@limiter.limit(RATE_LIMITS["jobs_cancel"])  # Reuse cancel rate limit
async def unarchive_job_endpoint(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Unarchive (recover) a job back to the main job list."""
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Authorization: owner or admin can unarchive
    if job.user_id != user.user_id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Not authorized to unarchive this job")

    updated_job = archive_job(job_id, archived=False)
    if not updated_job:
        raise HTTPException(status_code=500, detail="Failed to unarchive job")

    logger.info(
        "Job unarchived",
        extra={"job_id": job_id, "unarchived_by": user.user_id, "event": "job_unarchived"}
    )

    return {"message": "Job recovered successfully", "job_id": job_id}
