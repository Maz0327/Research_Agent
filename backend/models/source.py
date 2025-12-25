"""Source item models for normalized source data."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of source."""
    YOUTUBE = "youtube"
    WEB = "web"
    REDDIT = "reddit"
    NEWS = "news"
    ACADEMIC = "academic"
    GOV = "gov"
    PDF = "pdf"


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

