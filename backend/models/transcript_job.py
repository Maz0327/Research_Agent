"""Transcript job request/response models."""
from datetime import datetime
from typing import Literal, Optional
import re

from pydantic import BaseModel, Field, field_validator


class TranscriptRequest(BaseModel):
    """Request model for transcript extraction."""
    video_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of YouTube video URLs to extract transcripts from"
    )
    use_whisper_fallback: bool = Field(
        True,
        description="Use OpenAI Whisper if YouTube captions unavailable ($0.006/min)"
    )
    doc_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Custom title for the output Google Doc"
    )
    preferred_languages: list[str] = Field(
        default=["en"],
        description="Preferred transcript languages in order of preference"
    )

    @field_validator('video_urls')
    @classmethod
    def validate_video_urls(cls, v: list[str]) -> list[str]:
        """Validate YouTube URLs, filtering out non-video URLs (channels, playlists)."""
        from backend.utils.validators import filter_youtube_video_urls

        # Filter to only valid video URLs, silently skip channels/playlists
        valid_urls, skipped = filter_youtube_video_urls(v)

        if not valid_urls:
            raise ValueError("No valid YouTube video URLs provided")

        return valid_urls

    @field_validator('doc_title')
    @classmethod
    def validate_doc_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate doc title to prevent injection."""
        if v is None:
            return v

        v = v.strip()

        # Check for potentially malicious patterns
        dangerous_patterns = [
            r'<script',
            r'javascript:',
            r'<iframe',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Document title contains invalid characters")

        return v


class TranscriptResultItem(BaseModel):
    """Individual transcript result."""
    video_id: str
    video_url: str
    title: Optional[str] = None
    status: Literal["available", "missing", "error"]
    source: Literal["supadata_native", "supadata_ai", "whisper", "failed"]
    text: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[int] = None


class TranscriptSyncResponse(BaseModel):
    """Response for synchronous transcript extraction (≤5 URLs)."""
    success: bool
    doc_url: str = Field(..., description="URL to the Google Doc with transcripts")
    folder_url: str = Field(..., description="URL to the Google Drive folder")
    transcripts: list[TranscriptResultItem]
    warnings: list[str] = Field(default_factory=list)
    total_videos: int
    successful_count: int
    failed_count: int


class TranscriptAsyncResponse(BaseModel):
    """Response for asynchronous transcript extraction (>5 URLs)."""
    job_id: str
    status: str = "queued"
    message: str
    total_videos: int


class TranscriptJobStatusResponse(BaseModel):
    """Response for transcript job status polling."""
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    progress_percent: int = Field(..., ge=0, le=100)
    transcripts_completed: int
    transcripts_total: int
    doc_url: Optional[str] = Field(None, description="Google Doc URL when complete")
    folder_url: Optional[str] = Field(None, description="Google Drive folder URL when complete")
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = Field(None, description="Error message if job failed")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
