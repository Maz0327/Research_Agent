"""Output format exporters for Research Agent.

Provides structured data exports beyond the core NotebookLM and Documentary outputs:
- JSON: Lossless structured data for AI pipelines
- BibTeX/RIS: Academic citation formats
- Chapters: Podcast chapter timestamps
- Clips: Short-form video clip suggestions
- Social: Social media content kit
- Brief: Human-readable research analysis document
"""
from backend.pipeline.formats.json_export import ResearchPacketJSON, JSONExporter
from backend.pipeline.formats.citation_export import CitationExporter
from backend.pipeline.formats.chapter_export import ChapterMarker, ChapterExporter
from backend.pipeline.formats.clip_export import ClipSuggestion, ClipExporter
from backend.pipeline.formats.social_export import SocialContentKit, SocialExporter
from backend.pipeline.formats.brief_export import ResearchBrief, BriefExporter
from backend.pipeline.formats.export_manager import ExportManager

__all__ = [
    "ResearchPacketJSON",
    "JSONExporter",
    "CitationExporter",
    "ChapterMarker",
    "ChapterExporter",
    "ClipSuggestion",
    "ClipExporter",
    "SocialContentKit",
    "SocialExporter",
    "ResearchBrief",
    "BriefExporter",
    "ExportManager",
]
