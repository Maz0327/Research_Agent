"""Clip Export: Short-form video clip suggestions with engagement scoring.

Identifies compelling moments from research for TikTok, YouTube Shorts,
and Instagram Reels with hooks, angles, and platform-specific guidance.
"""
import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger


# Platform specifications
PLATFORM_SPECS = {
    "tiktok": {
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "hook_window": 3,
        "description": "Fast-paced, hook-driven content"
    },
    "youtube_shorts": {
        "max_duration": 60,
        "aspect_ratio": "9:16",
        "hook_window": 3,
        "description": "Discoverable short-form content"
    },
    "reels": {
        "max_duration": 90,
        "aspect_ratio": "9:16",
        "hook_window": 3,
        "description": "Visual storytelling emphasis"
    },
}

# Engagement scoring patterns
CONTROVERSY_WORDS = [
    "scandal", "leaked", "exposed", "accused", "revealed", "shocking",
    "controversial", "bombshell", "breaking", "exclusive", "secret",
    "hidden", "corruption", "affair", "fired", "arrested", "lawsuit"
]

EMOTIONAL_CUES = [
    "shocked", "angry", "emotional", "crying", "furious", "devastated",
    "heartbroken", "outraged", "stunned", "horrified", "thrilled"
]

QUOTE_PATTERNS = [
    r'"[^"]{10,}"',  # Quoted text
    r'said\s+[A-Z]',  # "said Name"
    r'according\s+to',  # Attribution
    r'claimed\s+that',  # Claims
]


@dataclass
class ClipSuggestion:
    """Single clip/moment suggestion."""

    clip_id: str
    source_url: str
    start_seconds: int
    end_seconds: int
    duration_seconds: int
    hook_text: str
    angle_description: str
    engagement_score: float
    platforms: dict = field(default_factory=dict)
    claim_ids: list = field(default_factory=list)
    keywords: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "clip_id": self.clip_id,
            "source_url": self.source_url,
            "timestamps": {
                "start_seconds": self.start_seconds,
                "end_seconds": self.end_seconds,
                "duration_seconds": self.duration_seconds,
                "start_formatted": self._format_time(self.start_seconds),
                "end_formatted": self._format_time(self.end_seconds),
            },
            "hook_text": self.hook_text,
            "angle_description": self.angle_description,
            "engagement_score": round(self.engagement_score, 2),
            "platforms": self.platforms,
            "claim_ids": self.claim_ids,
            "keywords": self.keywords,
        }

    def _format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"


class ClipExporter:
    """Generate clip suggestions from research data."""

    def generate_clips(
        self,
        claims: list,
        sources: list,
        transcripts: list,
        discovered_angles: list,
    ) -> list[ClipSuggestion]:
        """
        Generate clip suggestions from research data.

        Args:
            claims: List of extracted claims
            sources: List of source items (especially video sources)
            transcripts: List of transcript segments
            discovered_angles: List of discovered unique angles

        Returns:
            List of ClipSuggestion objects sorted by engagement score
        """
        logger.info("Generating clip suggestions")
        clips = []

        # Extract clips from high-engagement claims
        claim_clips = self._claims_to_clips(claims, transcripts)
        clips.extend(claim_clips)

        # Extract clips from discovered angles
        angle_clips = self._angles_to_clips(discovered_angles, sources, transcripts)
        clips.extend(angle_clips)

        # Extract clips from controversy/emotional moments
        moment_clips = self._find_compelling_moments(transcripts, sources)
        clips.extend(moment_clips)

        # Deduplicate by source+timestamp
        clips = self._deduplicate_clips(clips)

        # Sort by engagement score
        clips.sort(key=lambda c: c.engagement_score, reverse=True)

        logger.info(f"Generated {len(clips)} clip suggestions")
        return clips[:15]  # Return top 15

    def to_json(self, clips: list[ClipSuggestion], indent: int = 2) -> str:
        """Export clips as JSON."""
        return json.dumps(
            {
                "clips": [c.to_dict() for c in clips],
                "platform_specs": PLATFORM_SPECS,
                "total_clips": len(clips),
            },
            indent=indent,
            default=str
        )

    def _claims_to_clips(
        self,
        claims: list,
        transcripts: list,
    ) -> list[ClipSuggestion]:
        """Convert high-impact claims to clip suggestions."""
        clips = []
        transcript_text = self._combine_transcripts(transcripts)

        for claim in claims:
            confidence = self._get_attr(claim, "confidence") or 0
            if confidence < 0.7:
                continue

            text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            claim_id = self._get_attr(claim, "id") or self._get_attr(claim, "claim_id")
            sources = self._get_attr(claim, "sources") or []

            # Calculate engagement score
            score = self._calculate_engagement_score(text)
            if score < 0.4:
                continue

            # Find source URL (prefer video)
            source_url = self._find_video_source(sources)
            if not source_url:
                continue

            # Estimate timestamps from transcript position
            start, end = self._estimate_timestamps(text, transcript_text)

            # Generate hook from first sentence
            hook = self._generate_hook(text)

            clips.append(ClipSuggestion(
                clip_id=str(uuid.uuid4())[:8],
                source_url=source_url,
                start_seconds=start,
                end_seconds=end,
                duration_seconds=end - start,
                hook_text=hook,
                angle_description=f"Claim: {text[:100]}...",
                engagement_score=score,
                platforms=self._get_platform_guidance(end - start, score),
                claim_ids=[claim_id] if claim_id else [],
                keywords=self._extract_keywords(text),
            ))

        return clips

    def _angles_to_clips(
        self,
        discovered_angles: list,
        sources: list,
        transcripts: list,
    ) -> list[ClipSuggestion]:
        """Convert discovered angles to clip suggestions."""
        clips = []

        # Handle both list and dict format
        if isinstance(discovered_angles, dict):
            angles_list = discovered_angles.get("angles") or discovered_angles.get("discovered") or []
        else:
            angles_list = discovered_angles or []

        video_sources = [s for s in sources if self._is_video_source(s)]
        transcript_text = self._combine_transcripts(transcripts)

        for angle in angles_list:
            if isinstance(angle, dict):
                name = self._get_attr(angle, "name") or self._get_attr(angle, "angle") or ""
                description = self._get_attr(angle, "description") or ""
                angle_sources = self._get_attr(angle, "sources") or []
            elif isinstance(angle, str):
                name = angle
                description = angle
                angle_sources = []
            else:
                continue

            # Calculate engagement for angle
            combined_text = f"{name} {description}"
            score = self._calculate_engagement_score(combined_text)
            if score < 0.3:
                continue

            # Find video source
            source_url = None
            for s in angle_sources:
                url = s.get("url") if isinstance(s, dict) else s
                if self._is_video_url(url):
                    source_url = url
                    break

            if not source_url and video_sources:
                source_url = self._get_attr(video_sources[0], "url")

            if not source_url:
                continue

            # Estimate timestamps
            start, end = self._estimate_timestamps(description, transcript_text)

            clips.append(ClipSuggestion(
                clip_id=str(uuid.uuid4())[:8],
                source_url=source_url,
                start_seconds=start,
                end_seconds=end,
                duration_seconds=end - start,
                hook_text=self._generate_hook(name),
                angle_description=description[:200],
                engagement_score=score + 0.1,  # Boost angles slightly
                platforms=self._get_platform_guidance(end - start, score),
                claim_ids=[],
                keywords=self._extract_keywords(combined_text),
            ))

        return clips

    def _find_compelling_moments(
        self,
        transcripts: list,
        sources: list,
    ) -> list[ClipSuggestion]:
        """Find high-engagement moments in transcripts."""
        clips = []
        video_sources = [s for s in sources if self._is_video_source(s)]

        for transcript in transcripts:
            source_url = self._get_attr(transcript, "url") or self._get_attr(transcript, "source_url")
            if not source_url and video_sources:
                source_url = self._get_attr(video_sources[0], "url")

            if not source_url:
                continue

            text = self._get_attr(transcript, "text") or self._get_attr(transcript, "content") or ""
            segments = self._get_attr(transcript, "segments") or []

            # If we have timed segments, use them
            if segments:
                for segment in segments:
                    seg_text = self._get_attr(segment, "text") or ""
                    seg_start = self._get_attr(segment, "start") or 0
                    seg_end = self._get_attr(segment, "end") or seg_start + 30

                    score = self._calculate_engagement_score(seg_text)
                    if score >= 0.5:
                        clips.append(ClipSuggestion(
                            clip_id=str(uuid.uuid4())[:8],
                            source_url=source_url,
                            start_seconds=int(seg_start),
                            end_seconds=int(min(seg_end, seg_start + 60)),
                            duration_seconds=int(min(seg_end - seg_start, 60)),
                            hook_text=self._generate_hook(seg_text),
                            angle_description=f"Compelling moment: {seg_text[:100]}",
                            engagement_score=score,
                            platforms=self._get_platform_guidance(int(seg_end - seg_start), score),
                            claim_ids=[],
                            keywords=self._extract_keywords(seg_text),
                        ))
            else:
                # Split by sentences and find high-engagement ones
                sentences = re.split(r'[.!?]+', text)
                for i, sentence in enumerate(sentences):
                    score = self._calculate_engagement_score(sentence)
                    if score >= 0.6:
                        # Estimate position
                        start = (i * 5)  # Rough estimate
                        clips.append(ClipSuggestion(
                            clip_id=str(uuid.uuid4())[:8],
                            source_url=source_url,
                            start_seconds=start,
                            end_seconds=start + 45,
                            duration_seconds=45,
                            hook_text=self._generate_hook(sentence),
                            angle_description=f"Moment: {sentence[:100]}",
                            engagement_score=score,
                            platforms=self._get_platform_guidance(45, score),
                            claim_ids=[],
                            keywords=self._extract_keywords(sentence),
                        ))

        return clips[:10]  # Limit moment-based clips

    def _calculate_engagement_score(self, text: str) -> float:
        """Calculate engagement score for text (0-1)."""
        if not text:
            return 0.0

        score = 0.3  # Base score
        text_lower = text.lower()

        # Controversy words (+0.15 each, max 0.3)
        controversy_count = sum(1 for word in CONTROVERSY_WORDS if word in text_lower)
        score += min(0.3, controversy_count * 0.15)

        # Emotional cues (+0.1 each, max 0.2)
        emotional_count = sum(1 for cue in EMOTIONAL_CUES if cue in text_lower)
        score += min(0.2, emotional_count * 0.1)

        # Quote patterns (+0.1)
        for pattern in QUOTE_PATTERNS:
            if re.search(pattern, text):
                score += 0.1
                break

        # Numbers/stats (+0.05)
        if re.search(r'\d+%|\$\d+|million|billion', text_lower):
            score += 0.05

        # Length penalty for too short
        if len(text) < 50:
            score *= 0.7

        return min(1.0, score)

    def _generate_hook(self, text: str) -> str:
        """Generate hook text from content."""
        if not text:
            return "Watch this..."

        # Find first impactful sentence
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:
                # Limit to ~10 words
                words = sentence.split()[:10]
                hook = ' '.join(words)
                if len(hook) < len(sentence):
                    hook += "..."
                return hook

        return text[:50] + "..." if len(text) > 50 else text

    def _get_platform_guidance(self, duration: int, score: float) -> dict:
        """Get platform-specific guidance for clip."""
        guidance = {}

        for platform, spec in PLATFORM_SPECS.items():
            fits = duration <= spec["max_duration"]
            guidance[platform] = {
                "fits_duration": fits,
                "max_duration": spec["max_duration"],
                "aspect_ratio": spec["aspect_ratio"],
                "recommended": fits and score >= 0.5,
                "notes": self._get_platform_notes(platform, duration, score),
            }

        return guidance

    def _get_platform_notes(self, platform: str, duration: int, score: float) -> str:
        """Get platform-specific notes."""
        notes = []

        if duration > PLATFORM_SPECS[platform]["max_duration"]:
            notes.append(f"Trim to {PLATFORM_SPECS[platform]['max_duration']}s")

        if score >= 0.7:
            notes.append("High viral potential")
        elif score >= 0.5:
            notes.append("Good engagement potential")

        if platform == "tiktok":
            notes.append("Add trending sound")
        elif platform == "youtube_shorts":
            notes.append("Optimize title for search")
        elif platform == "reels":
            notes.append("Add visual text overlay")

        return "; ".join(notes) if notes else "Ready to use"

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Proper nouns
        keywords = list(set(words))[:5]

        # Add controversy words found
        text_lower = text.lower()
        for word in CONTROVERSY_WORDS:
            if word in text_lower and word not in [k.lower() for k in keywords]:
                keywords.append(word)
                if len(keywords) >= 8:
                    break

        return keywords

    def _estimate_timestamps(self, text: str, transcript_text: str) -> tuple[int, int]:
        """Estimate start/end timestamps for text in transcript."""
        if not transcript_text:
            return 0, 45

        # Find approximate position
        pos = transcript_text.lower().find(text[:50].lower())
        if pos == -1:
            return 0, 45

        # Estimate time based on word position
        words_before = len(transcript_text[:pos].split())
        start = (words_before // 3)  # ~3 words per second
        end = start + 45

        return max(0, start), end

    def _combine_transcripts(self, transcripts: list) -> str:
        """Combine all transcript text."""
        texts = []
        for t in transcripts:
            text = self._get_attr(t, "text") or self._get_attr(t, "content") or ""
            texts.append(text)
        return " ".join(texts)

    def _find_video_source(self, sources: list) -> Optional[str]:
        """Find first video source URL."""
        for s in sources:
            url = s.get("url") if isinstance(s, dict) else str(s)
            if self._is_video_url(url):
                return url
        return None

    def _is_video_source(self, source: Any) -> bool:
        """Check if source is a video source."""
        url = self._get_attr(source, "url") or ""
        source_type = self._get_attr(source, "type") or ""
        return source_type == "video" or self._is_video_url(url)

    def _is_video_url(self, url: str) -> bool:
        """Check if URL is a video URL."""
        if not url:
            return False
        url_lower = url.lower()
        return "youtube.com" in url_lower or "youtu.be" in url_lower

    def _deduplicate_clips(self, clips: list[ClipSuggestion]) -> list[ClipSuggestion]:
        """Remove duplicate clips by source and timestamp overlap."""
        seen = set()
        unique = []

        for clip in clips:
            key = f"{clip.source_url}_{clip.start_seconds // 30}"  # 30s buckets
            if key not in seen:
                seen.add(key)
                unique.append(clip)

        return unique

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
