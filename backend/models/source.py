"""Source item models for normalized source data."""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SourceType(str, Enum):
    """Type of source."""
    YOUTUBE = "youtube"
    WEB = "web"
    REDDIT = "reddit"
    NEWS = "news"
    ACADEMIC = "academic"
    GOV = "gov"
    PDF = "pdf"


# -----------------------------------------------------------------------------
# Transcript Provenance Models (Phase 0 - Semantic-First Architecture)
# -----------------------------------------------------------------------------


class VerificationCapabilities(BaseModel):
    """
    Capabilities available based on transcript source.

    These capabilities determine what assertions can be made about
    quotes, timestamps, and semantic precision for a given source.
    """
    quote_verification: bool = Field(
        default=True,
        description="Whether verbatim quote verification is possible"
    )
    timestamp_grounding: bool = Field(
        default=True,
        description="Whether precise timestamp grounding is available"
    )
    semantic_precision: Literal["high", "medium", "low"] = Field(
        default="high",
        description="Precision level for semantic claims"
    )


class TranscriptProvenance(BaseModel):
    """
    Metadata about transcript acquisition for a video source.

    This model tracks how transcripts were obtained and what verification
    capabilities are available based on the source quality. It ensures
    downstream documents can appropriately calibrate confidence and flag
    unverified claims.

    See: RASS Section 8, Operational Definitions Section 14
    """
    transcript_source: Literal["supadata", "youtube_captions", "none"] = Field(
        ...,
        description="Source of transcript: supadata (primary), youtube_captions (fallback), none (degraded)"
    )
    transcript_status: Literal["success", "failed"] = Field(
        ...,
        description="Whether transcript acquisition succeeded"
    )
    captions_status: Literal["success", "missing", "failed"] = Field(
        ...,
        description="Status of YouTube captions availability"
    )
    gemini_analysis_mode: Literal[
        "transcript_grounded",
        "caption_grounded",
        "video_only"
    ] = Field(
        ...,
        description="Analysis mode used by Gemini based on available text"
    )
    verification_capabilities: VerificationCapabilities = Field(
        default_factory=VerificationCapabilities,
        description="What verification capabilities are available"
    )
    notes: str = Field(
        default="",
        description="Human-readable explanation of fallbacks or failures"
    )

    @model_validator(mode='after')
    def validate_capabilities(self) -> "TranscriptProvenance":
        """
        Enforce capability restrictions based on transcript source.

        Rules:
        - If transcript_source = none: quote_verification = False, semantic_precision = low
        - If transcript_source = youtube_captions: semantic_precision = medium max
        """
        if self.transcript_source == "none":
            self.verification_capabilities.quote_verification = False
            self.verification_capabilities.timestamp_grounding = False
            self.verification_capabilities.semantic_precision = "low"
        elif self.transcript_source == "youtube_captions":
            if self.verification_capabilities.semantic_precision == "high":
                self.verification_capabilities.semantic_precision = "medium"
        return self

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "transcript_source": "supadata",
                    "transcript_status": "success",
                    "captions_status": "missing",
                    "gemini_analysis_mode": "transcript_grounded",
                    "verification_capabilities": {
                        "quote_verification": True,
                        "timestamp_grounding": True,
                        "semantic_precision": "high"
                    },
                    "notes": "Full Supadata transcript available"
                },
                {
                    "transcript_source": "youtube_captions",
                    "transcript_status": "failed",
                    "captions_status": "success",
                    "gemini_analysis_mode": "caption_grounded",
                    "verification_capabilities": {
                        "quote_verification": True,
                        "timestamp_grounding": True,
                        "semantic_precision": "medium"
                    },
                    "notes": "Supadata failed, using YouTube auto-captions"
                },
                {
                    "transcript_source": "none",
                    "transcript_status": "failed",
                    "captions_status": "missing",
                    "gemini_analysis_mode": "video_only",
                    "verification_capabilities": {
                        "quote_verification": False,
                        "timestamp_grounding": False,
                        "semantic_precision": "low"
                    },
                    "notes": "No transcript available - video-only analysis"
                }
            ]
        }


class SourceItem(BaseModel):
    """Normalized source item representing a single piece of content."""
    
    url: str = Field(..., description="Canonical URL of the source")
    title: str = Field(..., description="Title of the source")
    source_type: SourceType = Field(..., description="Type of source")
    published_at: Optional[datetime] = Field(
        None, description="Publication date if available"
    )
    text: Optional[str] = Field(
        None, description="Extracted text content (full text or excerpt)"
    )
    notes: Optional[str] = Field(
        None, description="Internal notes about the source"
    )
    angle: Optional[str] = Field(
        None, description="Editorial angle or bias perspective if detected"
    )
    # Phase 0: Transcript Provenance (for video sources)
    transcript_provenance: Optional[TranscriptProvenance] = Field(
        None,
        description="Transcript acquisition metadata (required for video sources)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Candace Owens on Charlie Kirk Show",
                    "source_type": "youtube",
                    "published_at": "2024-03-15T14:30:00Z",
                    "text": "Full transcript of the video...",
                    "notes": None,
                    "angle": None,
                },
                {
                    "url": "https://example.com/news/article",
                    "title": "Breaking: New Developments in Investigation",
                    "source_type": "news",
                    "published_at": "2024-03-10T08:00:00Z",
                    "text": "Article content excerpt...",
                    "notes": "High credibility source",
                    "angle": "Neutral reporting",
                },
                {
                    "url": "https://www.reddit.com/r/politics/comments/abc123",
                    "title": "Discussion about recent claims",
                    "source_type": "reddit",
                    "published_at": "2024-03-12T10:15:00Z",
                    "text": "Reddit thread content...",
                    "notes": "Public discussion thread",
                    "angle": "Mixed perspectives",
                },
                {
                    "url": "https://www.archives.gov/research/records/document.pdf",
                    "title": "Official Government Report 2024",
                    "source_type": "pdf",
                    "published_at": "2024-02-01T00:00:00Z",
                    "text": "Extracted PDF text content...",
                    "notes": "Official government document",
                    "angle": None,
                },
            ]
        }

