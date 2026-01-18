"""Job-related Pydantic models."""
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
import re

from pydantic import BaseModel, Field, field_validator


class JobStatus(BaseModel):
    """Job status model shared between FastAPI and Celery workers."""

    # Supabase column is "id", but we expose it as "job_id" in the API
    job_id: str = Field(alias="id")
    topic: str
    status: str
    result: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True


class CreateJobRequest(BaseModel):
    """Request model for creating a new research job."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Research prompt/topic (1-5000 characters)"
    )
    pipeline: Literal["quick", "full", "breaking_news", "investigation", "profile", "controversy"] = Field(
        ...,
        description="Pipeline type: quick, full, breaking_news, investigation, profile, or controversy"
    )
    niche: Optional[Literal["pop_culture", "political", "true_crime", "mysteries", "downfalls", "controversy"]] = Field(
        None,
        description="Category/niche overlay for specialized source selection"
    )
    options: Optional[dict[str, Any]] = Field(None, description="Optional job configuration overrides")

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and sanitize prompt to prevent injection attacks."""
        # Strip and normalize whitespace
        v = v.strip()

        # Check for minimum length after stripping
        if len(v) < 1:
            raise ValueError("Prompt cannot be empty")

        # Check for potentially malicious patterns
        dangerous_patterns = [
            (r'<script', "HTML script tags not allowed"),
            (r'javascript:', "JavaScript URLs not allowed"),
            (r'on\w+\s*=', "HTML event handlers not allowed"),
            (r'<iframe', "IFrame tags not allowed"),
        ]

        for pattern, error_msg in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(error_msg)

        return v


class CreateJobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    id: str = Field(..., alias="job_id", description="Job identifier")
    prompt: str = Field(..., description="Research prompt")
    title: Optional[str] = Field(None, description="AI-generated short title")
    pipeline: str = Field(..., description="Pipeline type (quick or full)")
    status: str
    stage: Optional[str] = Field(None, description="Current pipeline stage")
    stage_started_at: Optional[datetime] = Field(None, description="When current stage started")
    progress_percent: int = Field(..., ge=0, le=100)
    pass_detail: Optional[str] = Field(None, description="Detailed progress info (e.g., 'Analyzing video 2/5')")
    artifacts: Optional[dict[str, Any]] = Field(None, description="Job artifacts (Drive folder, docs)")
    error: Optional[str] = Field(None, description="Error message if job failed")
    warnings: Optional[list[str]] = Field(None, description="Warning messages for completed_with_warnings status")
    warning_count: Optional[int] = Field(None, description="Number of warnings (for preview without full list)")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Job last update timestamp")
    interpretations: Optional[list[dict[str, Any]]] = Field(
        None, description="Possible topic interpretations when status is 'disambiguating'"
    )
    # Document availability map for UI diagnostics
    # Example: {"doc_0": {"inline": true, "storage": false}, ...}
    documents_ready: Optional[dict[str, Any]] = Field(
        None, description="Per-document availability (inline/storage)"
    )

    class Config:
        populate_by_name = True


class SelectInterpretationRequest(BaseModel):
    """Request model for selecting interpretation(s) for a disambiguating job."""
    indices: list[int] | Literal["all"] = Field(
        ...,
        description="List of interpretation indices to research, or 'all' to research all"
    )

    @field_validator('indices')
    @classmethod
    def validate_indices(cls, v):
        """Validate indices are non-negative."""
        if isinstance(v, list):
            for idx in v:
                if not isinstance(idx, int) or idx < 0:
                    raise ValueError("Indices must be non-negative integers")
            if len(v) == 0:
                raise ValueError("Must select at least one interpretation")
        return v


class PreviewJobRequest(BaseModel):
    """Request model for previewing a job before creation."""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Research prompt/topic (1-5000 characters)"
    )
    pipeline: Literal["quick", "full", "breaking_news", "investigation", "profile", "controversy"] = Field(
        ...,
        description="Pipeline type"
    )
    niche: Optional[Literal["pop_culture", "political", "true_crime", "mysteries", "downfalls", "controversy"]] = Field(
        None,
        description="Category/niche overlay"
    )

    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate and sanitize prompt."""
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Prompt cannot be empty")
        return v


class PreviewJobResponse(BaseModel):
    """Response model for job preview showing interpreted plan."""
    is_ambiguous: bool = Field(..., description="Whether topic needs disambiguation")
    interpretations: Optional[list[dict[str, Any]]] = Field(
        None, description="Possible interpretations if ambiguous"
    )
    interpreted_topic: Optional[str] = Field(None, description="How we understood the topic")
    mode: Optional[str] = Field(None, description="Research mode that will be used")
    niche: Optional[str] = Field(None, description="Category/niche applied")
    subreddits: Optional[list[str]] = Field(None, description="Reddit communities to search")
    source_types: Optional[list[str]] = Field(None, description="Types of sources to collect")


# =============================================================================
# Video Analysis Models (URL-first Gemini extraction)
# =============================================================================

class VideoAnalysisRequest(BaseModel):
    """Request model for URL-first video analysis job.

    This is the new primary input model for the Gemini pivot.
    User provides YouTube URLs directly instead of a topic.
    """
    video_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of YouTube video URLs to analyze (1-10 videos)"
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional title for the research project"
    )
    model: Literal["gemini-2.5-flash", "gemini-2.5-pro"] = Field(
        "gemini-2.5-flash",
        description="Gemini model to use (flash is faster/cheaper, pro is more accurate)"
    )

    @field_validator('video_urls')
    @classmethod
    def validate_video_urls(cls, v: list[str]) -> list[str]:
        """Validate YouTube URLs."""
        from backend.utils.validators import validate_youtube_url, ValidationError as ValidatorError

        validated_urls = []
        for url in v:
            try:
                validated_url, _ = validate_youtube_url(url.strip())
                validated_urls.append(validated_url)
            except ValidatorError as e:
                raise ValueError(str(e))

        # Check for duplicates
        if len(validated_urls) != len(set(validated_urls)):
            raise ValueError("Duplicate video URLs not allowed")

        return validated_urls


class VideoAnalysisResponse(BaseModel):
    """Response model for video analysis job creation."""
    job_id: str
    estimated_cost: float = Field(..., description="Estimated cost in USD")
    total_duration_minutes: float = Field(..., description="Total video duration in minutes")
    video_count: int = Field(..., description="Number of videos to analyze")
    warnings: Optional[list[str]] = Field(None, description="Cost or duration warnings")


class VideoAnalysisStatusResponse(BaseModel):
    """Response model for video analysis job status."""
    job_id: str
    status: str
    progress_percent: int = Field(..., ge=0, le=100)
    current_video: Optional[int] = Field(None, description="Current video being processed (1-indexed)")
    total_videos: Optional[int] = Field(None, description="Total videos in job")
    clips_count: Optional[int] = Field(None, description="Number of clips extracted so far")
    quotes_count: Optional[int] = Field(None, description="Number of quotes extracted so far")
    error: Optional[str] = Field(None, description="Error message if job failed")
    created_at: Optional[datetime] = None
    # Results available when completed
    producer_packet: Optional[dict[str, Any]] = Field(
        None, description="Full ProducerPacket when job completes"
    )


# =============================================================================
# Extended Input Models (Phase 2B - Text and Screenshot inputs)
# =============================================================================

class TextInputRequest(BaseModel):
    """Request model for user-provided text input job.

    Used for paywalled articles, emails, or other text content the user
    pastes directly. Analysis mode is TEXT_PROVIDED with MEDIUM confidence.

    Quotes ARE allowed but carry warnings. If source metadata is provided
    (source_url, author, title), the warning acknowledges user verification.
    Without metadata, warnings recommend user verify source and accuracy.
    """
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Research topic for this content"
    )
    content: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="User-provided text content (50-50000 characters)"
    )
    source_label: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="What this content is (e.g., 'WSJ Article', 'Internal Email')"
    )
    # Source metadata - if provided, quote warnings are less severe
    source_url: Optional[str] = Field(
        None,
        max_length=2000,
        description="URL of the original source (not verified by system)"
    )
    author: Optional[str] = Field(
        None,
        max_length=200,
        description="Author name (not verified by system)"
    )
    publication_date: Optional[str] = Field(
        None,
        max_length=50,
        description="Publication date (not verified by system)"
    )
    context_note: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional context about the content (e.g., 'From paywall, may be incomplete')"
    )
    platform_hint: Optional[Literal["reddit", "twitter", "forum", "email", "article", "other"]] = Field(
        None,
        description="Hint about content origin for better processing"
    )

    @property
    def has_source_metadata(self) -> bool:
        """True if user provided any source identification info."""
        return bool(self.source_url or self.author)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and sanitize content."""
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Content must be at least 50 characters")
        return v


class TextInputResponse(BaseModel):
    """Response model for text input job creation."""
    job_id: str
    word_count: int = Field(..., description="Word count of provided content")
    confidence_ceiling: str = Field(
        "MEDIUM",
        description="Maximum confidence level for claims (TEXT_PROVIDED mode)"
    )
    warnings: Optional[list[str]] = Field(None, description="Processing warnings")


class ScreenshotInputRequest(BaseModel):
    """Request model for screenshot-based input job.

    Used for screenshots of social media, forums, etc. OCR extracts text
    then semantic extraction runs. Analysis mode is OCR_EXTRACTED with
    MEDIUM confidence. NO QUOTES allowed - OCR may have errors.
    """
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Research topic for this screenshot content"
    )
    platform_hint: Literal["reddit", "twitter", "forum", "other"] = Field(
        "other",
        description="Platform this screenshot is from (helps OCR extraction)"
    )
    context_note: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional context about the screenshot"
    )

    # Note: The actual image file is handled as UploadFile in the endpoint,
    # not in the Pydantic model. This model is for the form data.


class ScreenshotInputResponse(BaseModel):
    """Response model for screenshot input job creation."""
    job_id: str
    ocr_word_count: int = Field(..., description="Word count extracted via OCR")
    confidence_ceiling: str = Field(
        "MEDIUM",
        description="Maximum confidence level for claims (OCR_EXTRACTED mode)"
    )
    platform_detected: Optional[str] = Field(None, description="Platform detected from content")
    warnings: Optional[list[str]] = Field(None, description="OCR or processing warnings")


# =============================================================================
# Mixed-Input Models (Phase 5 - Multi-Source Support)
# =============================================================================

class MixedTextInput(BaseModel):
    """Individual text input within a mixed-input request."""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Title/label for this text content"
    )
    content: str = Field(
        ...,
        min_length=50,
        max_length=50000,
        description="Text content (50-50000 characters)"
    )
    platform_hint: Optional[Literal["reddit", "twitter", "forum", "email", "article", "other"]] = Field(
        None,
        description="Platform origin hint for better processing"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate and sanitize content."""
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Content must be at least 50 characters")
        return v


class MixedScreenshotInput(BaseModel):
    """Individual screenshot input within a mixed-input request."""
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename of the screenshot"
    )
    base64: str = Field(
        ...,
        min_length=100,
        description="Base64-encoded image data (data:image/...;base64,...)"
    )
    platform_hint: Optional[Literal["reddit", "twitter", "forum", "email", "other"]] = Field(
        None,
        description="Platform origin hint for better OCR processing"
    )


class MixedInputRequest(BaseModel):
    """Request model for mixed-input job with multiple source types.

    Accepts any combination of:
    - YouTube video URLs
    - Article URLs (for fetch + extract)
    - User-provided text snippets
    - Screenshot images (for OCR extraction)

    At least one input source required. Maximum 20 total sources.
    Each source type processed with appropriate analysis mode.
    """
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Research topic / scope lock for all sources"
    )
    video_urls: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="YouTube video URLs to analyze"
    )
    article_urls: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Article URLs to fetch and analyze"
    )
    text_inputs: list[MixedTextInput] = Field(
        default_factory=list,
        max_length=20,
        description="User-provided text snippets"
    )
    screenshots: list[MixedScreenshotInput] = Field(
        default_factory=list,
        max_length=10,
        description="Screenshot images for OCR extraction (max 10)"
    )

    @field_validator('video_urls')
    @classmethod
    def validate_video_urls(cls, v: list[str]) -> list[str]:
        """Validate YouTube URLs."""
        if not v:
            return v

        from backend.utils.validators import validate_youtube_url, ValidationError as ValidatorError

        validated_urls = []
        for url in v:
            try:
                validated_url, _ = validate_youtube_url(url.strip())
                validated_urls.append(validated_url)
            except ValidatorError as e:
                raise ValueError(f"Invalid YouTube URL: {e}")

        return validated_urls

    @field_validator('article_urls')
    @classmethod
    def validate_article_urls(cls, v: list[str]) -> list[str]:
        """Validate article URLs are properly formatted."""
        if not v:
            return v

        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'  # Domain
            r'(?:/[^\s]*)?$'  # Optional path
        )

        validated_urls = []
        for url in v:
            url = url.strip()
            if not url_pattern.match(url):
                raise ValueError(f"Invalid article URL: {url}")
            validated_urls.append(url)

        return validated_urls

    def model_post_init(self, __context) -> None:
        """Validate total source count and at least one input."""
        total = len(self.video_urls) + len(self.article_urls) + len(self.text_inputs) + len(self.screenshots)
        if total == 0:
            raise ValueError("At least one input source required")
        if total > 20:
            raise ValueError(f"Maximum 20 sources allowed, got {total}")


class SourceAccepted(BaseModel):
    """Information about an accepted source in mixed-input response."""
    source_id: str = Field(..., description="Assigned source ID (SRC_1, SRC_2, etc.)")
    source_type: str = Field(..., description="Source type (youtube, article, user_text)")
    url: Optional[str] = Field(None, description="URL if applicable")
    title: Optional[str] = Field(None, description="Title if applicable")


class MixedInputResponse(BaseModel):
    """Response model for mixed-input job creation."""
    job_id: str
    status: str = Field("pending", description="Initial job status")
    source_count: int = Field(..., description="Total sources accepted")
    sources_accepted: list[SourceAccepted] = Field(
        ..., description="Details of each accepted source"
    )
    duplicates_removed: int = Field(
        0, description="Number of duplicate URLs removed"
    )
    warnings: Optional[list[str]] = Field(None, description="Processing warnings")


# =============================================================================
# Evolving Jobs Models (Phase 6 - Add Sources to Completed Jobs)
# =============================================================================

class SourceStateEnum(str, Enum):
    """Status of individual source within a job.

    Sources can be added to completed jobs and tracked individually.
    """
    PENDING = "pending"         # Added, not yet processed
    PROCESSING = "processing"   # Currently being extracted
    PROCESSED = "processed"     # Extraction complete
    FAILED = "failed"           # Extraction failed
    EXCLUDED = "excluded"       # User removed from job


class JobSource(BaseModel):
    """Individual source within a job with status tracking.

    Used for evolving jobs where sources can be added after initial completion.
    """
    source_id: str = Field(..., description="Unique source identifier (SRC_1, SRC_2, etc.)")
    source_type: str = Field(..., description="Source type: youtube, article, user_text")
    url: Optional[str] = Field(None, description="URL if applicable")
    title: Optional[str] = Field(None, description="Title or label")
    status: SourceStateEnum = Field(SourceStateEnum.PENDING, description="Processing status")
    added_at: datetime = Field(..., description="When source was added to job")
    processed_at: Optional[datetime] = Field(None, description="When extraction completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    is_original: bool = Field(True, description="True if part of initial job, False if added later")


class AddSourcesRequest(BaseModel):
    """Request to add sources to an existing completed job.

    Job must be in 'completed' or 'completed_with_warnings' status.
    Sources are marked 'pending' until processed.
    """
    video_urls: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="YouTube video URLs to add"
    )
    article_urls: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Article URLs to add"
    )
    text_inputs: list[MixedTextInput] = Field(
        default_factory=list,
        max_length=10,
        description="User-provided text snippets to add"
    )
    process_immediately: bool = Field(
        False,
        description="If True, process now. If False, batch with other pending sources."
    )

    @field_validator('video_urls')
    @classmethod
    def validate_video_urls(cls, v: list[str]) -> list[str]:
        """Validate YouTube URLs."""
        if not v:
            return v
        from backend.utils.validators import validate_youtube_url, ValidationError as ValidatorError
        validated = []
        for url in v:
            try:
                validated_url, _ = validate_youtube_url(url.strip())
                validated.append(validated_url)
            except ValidatorError as e:
                raise ValueError(f"Invalid YouTube URL: {e}")
        return validated

    def model_post_init(self, __context) -> None:
        """Validate at least one source provided."""
        total = len(self.video_urls) + len(self.article_urls) + len(self.text_inputs)
        if total == 0:
            raise ValueError("At least one source required")
        if total > 10:
            raise ValueError(f"Maximum 10 sources per addition, got {total}")


class AddSourcesResponse(BaseModel):
    """Response after adding sources to a job."""
    job_id: str = Field(..., description="Job identifier")
    sources_added: int = Field(..., description="Number of sources added")
    pending_count: int = Field(..., description="Total pending sources awaiting processing")
    status: str = Field(..., description="Job status: sources_pending or processing")
    batch_timeout_seconds: int = Field(60, description="Seconds until auto-process if not immediate")
    warnings: Optional[list[str]] = Field(None, description="Any warnings")


class ProcessPendingResponse(BaseModel):
    """Response after triggering processing of pending sources."""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status: processing")
    pending_count: int = Field(..., description="Number of sources being processed")
