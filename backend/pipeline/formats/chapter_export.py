"""Chapter Export: Podcast chapter timestamps for audio/video players.

Generates chapter markers from research data for use in podcast players,
YouTube timestamps, and video editing software.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger


# Estimated speaking rate for timestamp calculation
WORDS_PER_MINUTE = 150


@dataclass
class ChapterMarker:
    """Single chapter/timestamp marker."""

    timestamp_seconds: int
    title: str
    claim_id: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp_seconds": self.timestamp_seconds,
            "timestamp_formatted": self._format_timestamp(),
            "title": self.title,
            "claim_id": self.claim_id,
            "source_url": self.source_url,
            "description": self.description,
        }

    def _format_timestamp(self) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        hours = self.timestamp_seconds // 3600
        minutes = (self.timestamp_seconds % 3600) // 60
        seconds = self.timestamp_seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class ChapterExporter:
    """Generate chapter timestamps from research data."""

    def generate_chapters(
        self,
        claims: list,
        timeline_events: list,
        topic: str,
        total_duration_seconds: Optional[int] = None,
    ) -> list[ChapterMarker]:
        """
        Generate chapter markers from claims and timeline.

        Args:
            claims: List of extracted claims
            timeline_events: List of timeline events
            topic: Research topic for intro chapter
            total_duration_seconds: Optional known duration for spacing

        Returns:
            List of ChapterMarker objects
        """
        logger.info("Generating chapter timestamps")
        chapters = []

        # Add intro chapter
        chapters.append(ChapterMarker(
            timestamp_seconds=0,
            title=f"Introduction: {self._truncate(topic, 40)}",
            description="Topic overview and context"
        ))

        # Group claims by theme for chapter structure
        claim_chapters = self._claims_to_chapters(claims)
        timeline_chapters = self._timeline_to_chapters(timeline_events)

        # Merge and sort all chapters
        all_chapters = claim_chapters + timeline_chapters
        all_chapters.sort(key=lambda c: c.timestamp_seconds)

        # If no duration provided, estimate from word count
        if total_duration_seconds is None:
            total_words = self._estimate_total_words(claims, timeline_events)
            total_duration_seconds = max(300, (total_words // WORDS_PER_MINUTE) * 60)

        # Space chapters evenly if we have them
        if all_chapters:
            # Reserve first 30 seconds for intro
            available_time = total_duration_seconds - 30
            interval = available_time // (len(all_chapters) + 1)

            for i, chapter in enumerate(all_chapters):
                chapter.timestamp_seconds = 30 + (interval * (i + 1))

        chapters.extend(all_chapters)

        # Add conclusion if we have content
        if len(chapters) > 1:
            chapters.append(ChapterMarker(
                timestamp_seconds=max(0, total_duration_seconds - 60),
                title="Conclusion & Key Takeaways",
                description="Summary of findings"
            ))

        logger.info(f"Generated {len(chapters)} chapters")
        return chapters

    def to_json(self, chapters: list[ChapterMarker], indent: int = 2) -> str:
        """Export chapters as JSON."""
        return json.dumps(
            [c.to_dict() for c in chapters],
            indent=indent,
            default=str
        )

    def to_youtube_timestamps(self, chapters: list[ChapterMarker]) -> str:
        """Export as YouTube description timestamps."""
        lines = []
        for chapter in chapters:
            timestamp = chapter.to_dict()["timestamp_formatted"]
            lines.append(f"{timestamp} {chapter.title}")
        return "\n".join(lines)

    def to_srt_chapters(self, chapters: list[ChapterMarker]) -> str:
        """Export as SRT chapter markers (for video editing)."""
        lines = []
        for i, chapter in enumerate(chapters):
            start = self._format_srt_time(chapter.timestamp_seconds)
            # End at next chapter or +10 seconds
            if i + 1 < len(chapters):
                end_seconds = chapters[i + 1].timestamp_seconds
            else:
                end_seconds = chapter.timestamp_seconds + 10
            end = self._format_srt_time(end_seconds)

            lines.append(str(i + 1))
            lines.append(f"{start} --> {end}")
            lines.append(chapter.title)
            lines.append("")

        return "\n".join(lines)

    def to_podcast_chapters_json(self, chapters: list[ChapterMarker]) -> str:
        """Export as Podcast Chapters JSON (podcasting 2.0 spec)."""
        podcast_chapters = {
            "version": "1.2.0",
            "chapters": []
        }

        for chapter in chapters:
            ch = {
                "startTime": chapter.timestamp_seconds,
                "title": chapter.title,
            }
            if chapter.source_url:
                ch["url"] = chapter.source_url
            podcast_chapters["chapters"].append(ch)

        return json.dumps(podcast_chapters, indent=2)

    def _claims_to_chapters(self, claims: list) -> list[ChapterMarker]:
        """Convert high-confidence claims to chapter markers."""
        chapters = []

        for claim in claims:
            confidence = self._get_attr(claim, "confidence") or self._get_attr(claim, "confidence_score") or 0
            if confidence < 0.7:
                continue

            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            claim_id = self._get_attr(claim, "id") or self._get_attr(claim, "claim_id")
            sources = self._get_attr(claim, "sources") or []
            source_url = sources[0] if sources else None
            if isinstance(source_url, dict):
                source_url = source_url.get("url")

            # Create chapter title from claim
            title = self._truncate(text, 50)

            chapters.append(ChapterMarker(
                timestamp_seconds=0,  # Will be recalculated
                title=title,
                claim_id=claim_id,
                source_url=source_url,
                description=text[:200] if len(text) > 200 else text
            ))

        return chapters[:8]  # Limit to 8 claim-based chapters

    def _timeline_to_chapters(self, timeline_events: list) -> list[ChapterMarker]:
        """Convert timeline events to chapter markers."""
        chapters = []

        for event in timeline_events:
            date = self._get_attr(event, "date") or self._get_attr(event, "timestamp") or "Unknown"
            description = (
                self._get_attr(event, "description") or
                self._get_attr(event, "event") or
                self._get_attr(event, "text") or ""
            )
            sources = self._get_attr(event, "sources") or self._get_attr(event, "source_urls") or []
            source_url = sources[0] if sources else None

            title = f"{date}: {self._truncate(description, 40)}"

            chapters.append(ChapterMarker(
                timestamp_seconds=0,
                title=title,
                source_url=source_url,
                description=description
            ))

        return chapters[:5]  # Limit to 5 timeline-based chapters

    def _estimate_total_words(self, claims: list, timeline_events: list) -> int:
        """Estimate total word count for duration calculation."""
        total = 0

        for claim in claims:
            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            total += len(text.split())

        for event in timeline_events:
            text = (
                self._get_attr(event, "description") or
                self._get_attr(event, "event") or ""
            )
            total += len(text.split())

        # Add overhead for narration
        return int(total * 1.5)

    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if not text:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3].rsplit(' ', 1)[0] + "..."

    def _format_srt_time(self, seconds: int) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d},000"

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
