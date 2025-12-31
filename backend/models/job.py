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

