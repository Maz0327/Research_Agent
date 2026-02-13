"""Export Manager: Unified interface for all format exporters.

Provides a single entry point for generating all export formats
from pipeline context data.
"""
from datetime import datetime
from typing import Any, Optional
from loguru import logger

from backend.pipeline.formats.json_export import JSONExporter, ResearchPacketJSON
from backend.pipeline.formats.citation_export import CitationExporter
from backend.pipeline.formats.chapter_export import ChapterExporter, ChapterMarker
from backend.pipeline.formats.clip_export import ClipExporter, ClipSuggestion
from backend.pipeline.formats.social_export import SocialExporter, SocialContentKit
from backend.pipeline.formats.brief_export import BriefExporter, ResearchBrief
from backend.models.video_analysis_models import (
    LegacyProducerPacket as ProducerPacket,
    create_producer_packet_from_gemini,
)


class ExportManager:
    """Unified interface for generating all export formats."""

    def __init__(self):
        self.json_exporter = JSONExporter()
        self.citation_exporter = CitationExporter()
        self.chapter_exporter = ChapterExporter()
        self.clip_exporter = ClipExporter()
        self.social_exporter = SocialExporter()
        self.brief_exporter = BriefExporter()

    def gather_research_data(self, ctx: Any) -> dict:
        """
        Extract research data from pipeline context.

        Args:
            ctx: PipelineContext with all research data

        Returns:
            Dict with all gathered data
        """
        logger.info("Gathering research data from context")

        return {
            "job_id": getattr(ctx, "job_id", ""),
            "topic": getattr(ctx, "topic", ""),
            "mode": getattr(ctx, "mode", "full"),
            "category": getattr(ctx, "category", "auto"),
            "created_at": getattr(ctx, "created_at", datetime.utcnow()),
            "claims": getattr(ctx, "claims", []),
            "entities": getattr(ctx, "entities", {}),
            "timeline_events": getattr(ctx, "timeline_events", []),
            "sources": self._gather_sources(ctx),
            "validation_results": getattr(ctx, "validation_results", []),
            "documentary_analysis": getattr(ctx, "documentary_analysis", {}),
            "discovered_angles": getattr(ctx, "discovered_angles", []),
            "transcripts": getattr(ctx, "transcripts", []),
        }

    def _gather_sources(self, ctx: Any) -> list:
        """Gather all sources from context."""
        sources = []

        # Web sources
        web_sources = getattr(ctx, "web_sources", [])
        for s in web_sources:
            sources.append(self._normalize_source(s, "web"))

        # Video sources
        videos = getattr(ctx, "videos", []) or getattr(ctx, "youtube_videos", [])
        for v in videos:
            sources.append(self._normalize_source(v, "video"))

        # Reddit sources
        reddit_posts = getattr(ctx, "reddit_posts", [])
        for r in reddit_posts:
            sources.append(self._normalize_source(r, "social"))

        return sources

    def _normalize_source(self, source: Any, source_type: str) -> dict:
        """Normalize source to standard format."""
        if isinstance(source, dict):
            return {
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "type": source.get("type", source_type),
                "author": source.get("author"),
                "published_at": source.get("published_at") or source.get("date"),
                "quality_score": source.get("quality_score") or source.get("score", 0.5),
            }
        return {
            "url": getattr(source, "url", ""),
            "title": getattr(source, "title", ""),
            "type": source_type,
            "author": getattr(source, "author", None),
            "published_at": getattr(source, "published_at", None),
            "quality_score": getattr(source, "quality_score", 0.5),
        }

    # -------------------------------------------------------------------------
    # JSON Export
    # -------------------------------------------------------------------------

    def to_json(self, data: dict) -> str:
        """Generate lossless JSON export."""
        packet = self.json_exporter.export(
            job_id=data.get("job_id", ""),
            topic=data.get("topic", ""),
            mode=data.get("mode", "full"),
            created_at=data.get("created_at", datetime.utcnow()),
            claims=data.get("claims", []),
            entities=data.get("entities", {}),
            timeline_events=data.get("timeline_events", []),
            sources=data.get("sources", []),
            validation_results=data.get("validation_results", []),
            documentary_analysis=data.get("documentary_analysis", {}),
            discovered_angles=data.get("discovered_angles", []),
        )
        return packet.to_json()

    def get_json_packet(self, data: dict) -> ResearchPacketJSON:
        """Get JSON packet object."""
        return self.json_exporter.export(
            job_id=data.get("job_id", ""),
            topic=data.get("topic", ""),
            mode=data.get("mode", "full"),
            created_at=data.get("created_at", datetime.utcnow()),
            claims=data.get("claims", []),
            entities=data.get("entities", {}),
            timeline_events=data.get("timeline_events", []),
            sources=data.get("sources", []),
            validation_results=data.get("validation_results", []),
            documentary_analysis=data.get("documentary_analysis", {}),
            discovered_angles=data.get("discovered_angles", []),
        )

    # -------------------------------------------------------------------------
    # Citation Exports
    # -------------------------------------------------------------------------

    def to_bibtex(self, data: dict) -> str:
        """Generate BibTeX citations."""
        sources = data.get("sources", [])
        return self.citation_exporter.to_bibtex(sources)

    def to_ris(self, data: dict) -> str:
        """Generate RIS citations."""
        sources = data.get("sources", [])
        return self.citation_exporter.to_ris(sources)

    # -------------------------------------------------------------------------
    # Chapter Exports
    # -------------------------------------------------------------------------

    def to_chapters(self, data: dict) -> str:
        """Generate chapter timestamps as JSON."""
        chapters = self.get_chapters(data)
        return self.chapter_exporter.to_json(chapters)

    def get_chapters(
        self,
        data: dict,
        total_duration_seconds: Optional[int] = None,
    ) -> list[ChapterMarker]:
        """Get chapter marker objects."""
        return self.chapter_exporter.generate_chapters(
            claims=data.get("claims", []),
            timeline_events=data.get("timeline_events", []),
            topic=data.get("topic", ""),
            total_duration_seconds=total_duration_seconds,
        )

    def to_youtube_chapters(self, data: dict) -> str:
        """Generate YouTube description timestamps."""
        chapters = self.get_chapters(data)
        return self.chapter_exporter.to_youtube_timestamps(chapters)

    def to_podcast_chapters(self, data: dict) -> str:
        """Generate Podcast Chapters JSON (podcasting 2.0)."""
        chapters = self.get_chapters(data)
        return self.chapter_exporter.to_podcast_chapters_json(chapters)

    # -------------------------------------------------------------------------
    # Clip Exports
    # -------------------------------------------------------------------------

    def to_clips(self, data: dict) -> str:
        """Generate clip suggestions as JSON."""
        clips = self.get_clips(data)
        return self.clip_exporter.to_json(clips)

    def get_clips(self, data: dict) -> list[ClipSuggestion]:
        """Get clip suggestion objects."""
        return self.clip_exporter.generate_clips(
            claims=data.get("claims", []),
            sources=data.get("sources", []),
            transcripts=data.get("transcripts", []),
            discovered_angles=data.get("discovered_angles", []),
        )

    # -------------------------------------------------------------------------
    # Social Exports
    # -------------------------------------------------------------------------

    def to_social(self, data: dict) -> str:
        """Generate social content kit as JSON."""
        kit = self.get_social_kit(data)
        return self.social_exporter.to_json(kit)

    def get_social_kit(self, data: dict) -> SocialContentKit:
        """Get social content kit object."""
        return self.social_exporter.generate_kit(
            topic=data.get("topic", ""),
            claims=data.get("claims", []),
            entities=data.get("entities", {}),
            discovered_angles=data.get("discovered_angles", []),
            category=data.get("category", "auto"),
        )

    # -------------------------------------------------------------------------
    # Research Brief Exports
    # -------------------------------------------------------------------------

    def to_brief(self, data: dict) -> str:
        """Generate Research Brief markdown."""
        brief = self.get_brief(data)
        return self.brief_exporter.to_markdown(brief)

    def get_brief(self, data: dict) -> ResearchBrief:
        """Get Research Brief object."""
        return self.brief_exporter.generate_brief(
            topic=data.get("topic", ""),
            claims=data.get("claims", []),
            entities=data.get("entities", {}),
            timeline_events=data.get("timeline_events", []),
            sources=data.get("sources", []),
            validation_results=data.get("validation_results", []),
            discovered_angles=data.get("discovered_angles", []),
        )

    # -------------------------------------------------------------------------
    # Producer Packet Exports (Phase 2)
    # -------------------------------------------------------------------------

    def to_producer_packet(
        self,
        gemini_results: dict,
        title: str,
        transcripts: Optional[dict] = None,
    ) -> str:
        """Generate Producer Packet as JSON from Gemini results.

        Phase 2: Grounded extraction output for video production.

        Args:
            gemini_results: Output from GeminiClient.analyze_youtube_videos_batch()
            title: Research title
            transcripts: Optional dict of {video_url: transcript_text}

        Returns:
            JSON string of ProducerPacket
        """
        import json
        packet = self.get_producer_packet(gemini_results, title, transcripts)
        return json.dumps(packet.to_dict(), indent=2)

    def get_producer_packet(
        self,
        gemini_results: dict,
        title: str,
        transcripts: Optional[dict] = None,
    ) -> ProducerPacket:
        """Get Producer Packet object from Gemini results.

        Args:
            gemini_results: Output from GeminiClient.analyze_youtube_videos_batch()
            title: Research title
            transcripts: Optional dict of {video_url: transcript_text}

        Returns:
            ProducerPacket with clips, quotes, verification status
        """
        return create_producer_packet_from_gemini(
            gemini_results=gemini_results,
            title=title,
            transcripts=transcripts,
        )

    def to_producer_packet_markdown(
        self,
        gemini_results: dict,
        title: str,
        transcripts: Optional[dict] = None,
    ) -> str:
        """Generate Producer Packet as Markdown."""
        packet = self.get_producer_packet(gemini_results, title, transcripts)
        return packet.to_markdown()

    # -------------------------------------------------------------------------
    # All Exports at Once
    # -------------------------------------------------------------------------

    def generate_all(self, ctx: Any) -> dict:
        """
        Generate all export formats from pipeline context.

        Args:
            ctx: PipelineContext with all research data

        Returns:
            Dict with all exports as strings
        """
        logger.info("Generating all export formats")
        data = self.gather_research_data(ctx)

        exports = {
            "json": self.to_json(data),
            "bibtex": self.to_bibtex(data),
            "ris": self.to_ris(data),
            "chapters": self.to_chapters(data),
            "youtube_chapters": self.to_youtube_chapters(data),
            "podcast_chapters": self.to_podcast_chapters(data),
            "clips": self.to_clips(data),
            "social": self.to_social(data),
            "brief": self.to_brief(data),
        }

        logger.info(f"Generated {len(exports)} export formats")
        return exports

    def generate_all_from_data(self, data: dict) -> dict:
        """
        Generate all export formats from pre-gathered data.

        Args:
            data: Dict with all research data

        Returns:
            Dict with all exports as strings
        """
        return {
            "json": self.to_json(data),
            "bibtex": self.to_bibtex(data),
            "ris": self.to_ris(data),
            "chapters": self.to_chapters(data),
            "youtube_chapters": self.to_youtube_chapters(data),
            "podcast_chapters": self.to_podcast_chapters(data),
            "clips": self.to_clips(data),
            "social": self.to_social(data),
            "brief": self.to_brief(data),
        }
