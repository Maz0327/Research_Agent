"""Job configuration models."""
from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResearchMode(str, Enum):
    """Research mode determines the focus of the investigation."""
    CLAIMS_EVIDENCE = "claims_evidence"
    TIMELINE = "timeline"
    QUICK_BRIEF = "quick_brief"
    INVESTIGATION = "investigation"


class TimeWindow(BaseModel):
    """Time window for filtering sources by date."""
    start: Optional[date] = Field(None, description="Start date (inclusive)")
    end: Optional[date] = Field(None, description="End date (inclusive)")

    class Config:
        json_schema_extra = {
            "example": {
                "start": "2024-01-01",
                "end": "2024-12-31",
            }
        }


class YouTubeConfig(BaseModel):
    """YouTube source configuration."""
    channels: list[str] = Field(default_factory=list, description="Channel IDs or handles to search")
    include_livestreams: bool = Field(False, description="Include live streams in results")
    exclude_shorts: bool = Field(True, description="Exclude YouTube Shorts")
    max_videos: int = Field(10, ge=1, le=50, description="Maximum videos to fetch per channel")
    fetch_transcripts: bool = Field(True, description="Fetch transcripts for videos")

    class Config:
        json_schema_extra = {
            "example": {
                "channels": ["UCX6OQ3DkcsbYNE6H8uQQuVA", "@channel_handle"],
                "include_livestreams": False,
                "exclude_shorts": True,
                "max_videos": 10,
                "fetch_transcripts": True,
            }
        }


class SourcesConfig(BaseModel):
    """Source type selection configuration."""
    web: bool = Field(True, description="Include general web search results")
    include_reddit_public: bool = Field(False, description="Include public Reddit threads")
    include_news: bool = Field(True, description="Include news articles")
    include_academic: bool = Field(False, description="Include academic papers")
    include_gov: bool = Field(False, description="Include government/public records")

    class Config:
        json_schema_extra = {
            "example": {
                "web": True,
                "include_reddit_public": False,
                "include_news": True,
                "include_academic": False,
                "include_gov": True,
            }
        }


class BudgetsConfig(BaseModel):
    """Resource budget constraints."""
    max_web_urls: int = Field(30, ge=1, le=200, description="Maximum URLs to fetch from web search")
    max_transcription_minutes: int = Field(
        120, ge=1, le=1000, description="Maximum minutes of video to transcribe"
    )
    max_claims_to_validate: int = Field(
        20, ge=1, le=100, description="Maximum claims to run through validation"
    )
    max_validation_links_per_claim: int = Field(
        5, ge=1, le=20, description="Maximum validation sources per claim"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_web_urls": 30,
                "max_transcription_minutes": 120,
                "max_claims_to_validate": 20,
                "max_validation_links_per_claim": 5,
            }
        }


class OutputConfig(BaseModel):
    """Output configuration."""
    drive_folder_name: str = Field(
        default="Research Packets", description="Google Drive folder name for output"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "drive_folder_name": "Candace Owens Claims Analysis",
            }
        }


class JobConfig(BaseModel):
    """Complete job configuration model."""
    mode: ResearchMode = Field(
        default=ResearchMode.CLAIMS_EVIDENCE,
        description="Research mode determines investigation focus",
    )
    topic: str = Field(..., description="Research topic/question")
    time_window: TimeWindow = Field(
        default_factory=TimeWindow, description="Time window for filtering sources"
    )
    youtube: YouTubeConfig = Field(
        default_factory=YouTubeConfig, description="YouTube source configuration"
    )
    sources: SourcesConfig = Field(
        default_factory=SourcesConfig, description="Source type selection"
    )
    budgets: BudgetsConfig = Field(
        default_factory=BudgetsConfig, description="Resource budget constraints"
    )
    output: OutputConfig = Field(
        default_factory=OutputConfig, description="Output configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "claims_evidence",
                "topic": "Candace Owens Charlie Kirk claims",
                "time_window": {
                    "start": "2024-01-01",
                    "end": None,
                },
                "youtube": {
                    "channels": ["UCX6OQ3DkcsbYNE6H8uQQuVA"],
                    "include_livestreams": False,
                    "exclude_shorts": True,
                    "max_videos": 10,
                    "fetch_transcripts": True,
                },
                "sources": {
                    "web": True,
                    "include_reddit_public": False,
                    "include_news": True,
                    "include_academic": False,
                    "include_gov": True,
                },
                "budgets": {
                    "max_web_urls": 30,
                    "max_transcription_minutes": 120,
                    "max_claims_to_validate": 20,
                    "max_validation_links_per_claim": 5,
                },
                "output": {
                    "drive_folder_name": "Candace Owens Claims Analysis",
                },
            }
        }

