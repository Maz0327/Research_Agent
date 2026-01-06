"""Job-related Pydantic models."""
from datetime import datetime
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
    pipeline: str = Field(..., description="Pipeline type (quick or full)")
    status: str
    progress_percent: int = Field(..., ge=0, le=100)
    artifacts: Optional[dict[str, Any]] = Field(None, description="Job artifacts (Drive folder, docs)")
    error: Optional[str] = Field(None, description="Error message if job failed")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Job last update timestamp")
    interpretations: Optional[list[dict[str, Any]]] = Field(
        None, description="Possible topic interpretations when status is 'disambiguating'"
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

