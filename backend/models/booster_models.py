"""
Booster Models - Data structures for Deep Research Booster.

Based on: docs/authoritative/spec/GAPS_AND_BOOSTER_SPEC.md Part 2

The booster produces DIRECTIONS, not FACTS.
It tells you WHERE to look, not WHAT you'll find.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class PrimarySourceType(str, Enum):
    """Types of primary sources to search for."""
    COURT_FILING = "court_filing"
    SEC_FILING = "sec_filing"
    GOVERNMENT_RECORD = "government_record"
    ACADEMIC_PAPER = "academic_paper"
    NEWS_ARTICLE = "news_article"
    PRESS_RELEASE = "press_release"
    SOCIAL_MEDIA_ARCHIVE = "social_media_archive"
    INTERVIEW_TRANSCRIPT = "interview_transcript"
    INTERNAL_DOCUMENT = "internal_document"
    DATASET = "dataset"
    FINANCIAL_REPORT = "financial_report"
    OTHER = "other"


class PlatformSuggestion(str, Enum):
    """Platforms to search."""
    GOOGLE = "google"
    REDDIT = "reddit"
    TWITTER = "twitter"
    NEWS = "news"
    YOUTUBE = "youtube"
    ARCHIVE = "archive"  # Wayback Machine, etc.


# -----------------------------------------------------------------------------
# Context Bundle (Input to Booster)
# -----------------------------------------------------------------------------

@dataclass
class ThemeSummary:
    """Lightweight theme for context bundle."""
    theme_id: str
    label: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "description": self.description,
        }


@dataclass
class TensionSummary:
    """Lightweight tension for context bundle."""
    tension_id: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tension_id": self.tension_id,
            "description": self.description,
        }


@dataclass
class GapSummary:
    """Lightweight gap for context bundle."""
    gap_id: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "description": self.description,
        }


@dataclass
class ContextBundle:
    """
    Constrained input for Deep Research Booster.
    Auto-generated from job output. User provides nothing.

    What is NOT in the Context Bundle:
    - Full transcript text
    - Verbatim quotes
    - Doc 0 content
    - Full key point objects with claims
    - Source URLs or metadata

    This prevents the booster from having access to information
    it might hallucinate about.
    """
    # Scope (from Doc 1)
    scope_in: list[str] = field(default_factory=list)
    scope_out: list[str] = field(default_factory=list)

    # Semantic content (from extraction)
    themes: list[ThemeSummary] = field(default_factory=list)
    key_point_summaries: list[str] = field(default_factory=list)  # Statements only
    tensions: list[TensionSummary] = field(default_factory=list)
    gaps: list[GapSummary] = field(default_factory=list)

    # Metadata
    source_count: int = 0
    source_types: list[str] = field(default_factory=list)
    confidence_level: str = "medium"  # Overall job confidence

    # Job reference
    job_id: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_in": self.scope_in,
            "scope_out": self.scope_out,
            "themes": [t.to_dict() for t in self.themes],
            "key_point_summaries": self.key_point_summaries,
            "tensions": [t.to_dict() for t in self.tensions],
            "gaps": [g.to_dict() for g in self.gaps],
            "source_count": self.source_count,
            "source_types": self.source_types,
            "confidence_level": self.confidence_level,
            "job_id": self.job_id,
            "generated_at": self.generated_at,
        }


# -----------------------------------------------------------------------------
# Booster Output (Directions to explore)
# -----------------------------------------------------------------------------

@dataclass
class MissingPerspective:
    """A viewpoint or voice not represented in current sources."""
    description: str
    why_it_matters: str
    related_gaps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "why_it_matters": self.why_it_matters,
            "related_gaps": self.related_gaps,
        }


@dataclass
class PrimarySourceDirection:
    """A type of primary source that might exist and should be sought."""
    source_type: PrimarySourceType
    description: str
    search_suggestion: str
    related_gap: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "description": self.description,
            "search_suggestion": self.search_suggestion,
            "related_gap": self.related_gap,
        }


@dataclass
class SearchQuery:
    """A specific search query to find relevant sources."""
    query: str
    purpose: str
    platform_suggestion: PlatformSuggestion
    related_gap: Optional[str] = None
    related_theme: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "purpose": self.purpose,
            "platform_suggestion": self.platform_suggestion.value,
            "related_gap": self.related_gap,
            "related_theme": self.related_theme,
        }


@dataclass
class ResearchQuestion:
    """A question that would advance understanding if answered."""
    question: str
    why_it_matters: str
    related_theme: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "why_it_matters": self.why_it_matters,
            "related_theme": self.related_theme,
        }


@dataclass
class BoosterOutput:
    """
    Output that augments Doc 1. DIRECTIONS ONLY, no facts.

    Four categories of research directions:
    1. Missing perspectives to seek
    2. Primary source types to find
    3. Specific search queries to execute
    4. Research questions to investigate
    """
    missing_perspectives: list[MissingPerspective] = field(default_factory=list)
    primary_source_directions: list[PrimarySourceDirection] = field(default_factory=list)
    suggested_search_queries: list[SearchQuery] = field(default_factory=list)
    research_questions: list[ResearchQuestion] = field(default_factory=list)

    # Metadata
    booster_provider: str = "gemini"
    booster_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    context_bundle_hash: str = ""  # SHA256 for verification

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_perspectives": [mp.to_dict() for mp in self.missing_perspectives],
            "primary_source_directions": [psd.to_dict() for psd in self.primary_source_directions],
            "suggested_search_queries": [sq.to_dict() for sq in self.suggested_search_queries],
            "research_questions": [rq.to_dict() for rq in self.research_questions],
            "booster_provider": self.booster_provider,
            "booster_timestamp": self.booster_timestamp,
            "context_bundle_hash": self.context_bundle_hash,
        }

    @property
    def total_directions(self) -> int:
        """Total number of directions generated."""
        return (
            len(self.missing_perspectives)
            + len(self.primary_source_directions)
            + len(self.suggested_search_queries)
            + len(self.research_questions)
        )

    def is_empty(self) -> bool:
        """Check if booster produced no directions."""
        return self.total_directions == 0
