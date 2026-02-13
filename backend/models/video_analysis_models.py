"""Video analysis models for Phase 3 pipeline - Content analysis and research assistance.

These models support:
- ContentBlueprint: Structure analysis of videos (reverse-engineering)
- GapAnalysis: Cross-video analysis of what's missing
- ResearchStarter: Actionable research starting points
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# Phase 3: Full Research Assistant Pipeline - Content Analysis Models
# =============================================================================

@dataclass
class ActSection:
    """A section/act in the video's narrative structure."""
    name: str  # "Setup", "Conflict", "Resolution"
    timestamp_start: str  # MM:SS
    timestamp_end: str  # MM:SS
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "description": self.description,
        }


@dataclass
class OpenLoop:
    """A re-engagement point (open loop) in the video."""
    timestamp: str
    technique: str  # "question", "tease", "cliffhanger"
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "technique": self.technique,
            "description": self.description,
        }


@dataclass
class ContentBlueprint:
    """Structure analysis of a video for reverse-engineering.

    Phase 3: Helps creators understand what makes a video work.
    Per-video analysis - not cross-video.
    
    H-013: Includes parse_error flag to signal incomplete/failed parsing.
    """
    video_url: str
    title: str

    # Hook Analysis (first 10-30 seconds)
    # M-004: Renamed comment to clarify this is the END of the hook
    hook_timestamp: str  # END timestamp of hook (start is always 0:00)
    hook_technique: str  # "Pattern interrupt", "Provocative question", etc.
    hook_description: str

    # Narrative Structure
    structure_type: str  # "3-act villain origin", "story circle", "problem-solution"
    act_breakdown: List[ActSection] = field(default_factory=list)

    # Re-engagement Points
    open_loops: List[OpenLoop] = field(default_factory=list)

    # Visual/Style
    pacing: str = "medium"  # "high-energy", "lo-fi", "documentary"
    editing_style: str = "standard"

    # Source Tracing
    likely_primary_sources: List[str] = field(default_factory=list)
    referenced_materials: List[str] = field(default_factory=list)
    
    # H-013: Error tracking - True if LLM response parsing failed
    parse_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_url": self.video_url,
            "title": self.title,
            "hook": {
                "timestamp": self.hook_timestamp,
                "technique": self.hook_technique,
                "description": self.hook_description,
            },
            "narrative": {
                "structure_type": self.structure_type,
                "acts": [a.to_dict() for a in self.act_breakdown],
            },
            "open_loops": [o.to_dict() for o in self.open_loops],
            "style": {
                "pacing": self.pacing,
                "editing_style": self.editing_style,
            },
            "sources": {
                "likely_primary_sources": self.likely_primary_sources,
                "referenced_materials": self.referenced_materials,
            },
            "parse_error": self.parse_error,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# Content Blueprint: {self.title}",
            f"**Video:** {self.video_url}",
            "",
            "## Hook Analysis",
            f"**Timestamp:** 0:00 - {self.hook_timestamp}",
            f"**Technique:** {self.hook_technique}",
            f"**Description:** {self.hook_description}",
            "",
            "## Narrative Structure",
            f"**Type:** {self.structure_type}",
            "",
        ]

        for act in self.act_breakdown:
            lines.append(f"### {act.name} [{act.timestamp_start} - {act.timestamp_end}]")
            lines.append(act.description)
            lines.append("")

        lines.extend([
            "## Re-engagement Points (Open Loops)",
            "",
        ])
        for loop in self.open_loops:
            lines.append(f"- **[{loop.timestamp}]** {loop.technique}: {loop.description}")

        lines.extend([
            "",
            "## Visual Style",
            f"- **Pacing:** {self.pacing}",
            f"- **Editing:** {self.editing_style}",
            "",
            "## Likely Sources Used",
        ])
        for source in self.likely_primary_sources:
            lines.append(f"- {source}")

        if self.referenced_materials:
            lines.extend([
                "",
                "## Referenced Materials",
            ])
            for ref in self.referenced_materials:
                lines.append(f"- {ref}")

        return "\n".join(lines)


@dataclass
class MissingPerspective:
    """A perspective that's missing from the analyzed videos."""
    perspective: str  # "skeptic", "victim", "expert"
    why_important: str
    suggested_search: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "perspective": self.perspective,
            "why_important": self.why_important,
            "suggested_search": self.suggested_search,
        }


@dataclass
class CoverageBlindSpot:
    """A topic mentioned but not explored in the videos."""
    topic: str
    where_mentioned: str  # Video title/timestamp
    why_explore: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "where_mentioned": self.where_mentioned,
            "why_explore": self.why_explore,
        }


@dataclass
class Contradiction:
    """A contradiction between sources - opportunity for original content."""
    claim_a: str
    source_a: str
    claim_b: str
    source_b: str
    opportunity: str  # How to use this in their video

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_a": self.claim_a,
            "source_a": self.source_a,
            "claim_b": self.claim_b,
            "source_b": self.source_b,
            "opportunity": self.opportunity,
        }


@dataclass
class GapAnalysis:
    """Cross-video analysis of what's missing.

    Phase 3: Helps creators know what perspectives and topics are unexplored.
    
    H-013: Includes parse_error flag to signal incomplete/failed parsing.
    """
    # Missing Perspectives
    missing_perspectives: List[MissingPerspective] = field(default_factory=list)

    # Unanswered Questions
    unanswered_questions: List[str] = field(default_factory=list)

    # Coverage Blind Spots
    mentioned_but_unexplored: List[CoverageBlindSpot] = field(default_factory=list)

    # Contradictions (opportunity for original content)
    contradictions: List[Contradiction] = field(default_factory=list)
    
    # H-013: Error tracking - True if LLM response parsing failed
    parse_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "missing_perspectives": [p.to_dict() for p in self.missing_perspectives],
            "unanswered_questions": self.unanswered_questions,
            "mentioned_but_unexplored": [b.to_dict() for b in self.mentioned_but_unexplored],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "parse_error": self.parse_error,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Gap Analysis",
            "",
            "## Missing Perspectives",
            "",
        ]

        if self.missing_perspectives:
            for p in self.missing_perspectives:
                lines.append(f"### {p.perspective}")
                lines.append(f"**Why important:** {p.why_important}")
                lines.append(f"**Search suggestion:** `{p.suggested_search}`")
                lines.append("")
        else:
            lines.append("*No major missing perspectives identified.*")
            lines.append("")

        lines.extend([
            "## Unanswered Questions",
            "",
        ])
        for q in self.unanswered_questers:
            lines.append(f"- {q}")

        lines.extend([
            "",
            "## Topics Mentioned But Not Explored",
            "",
        ])
        for blind in self.mentioned_but_unexplored:
            lines.append(f"### {blind.topic}")
            lines.append(f"**Where mentioned:** {blind.where_mentioned}")
            lines.append(f"**Why explore:** {blind.why_explore}")
            lines.append("")

        if self.contradictions:
            lines.extend([
                "## Contradictions (Opportunity)",
                "",
            ])
            for i, c in enumerate(self.contradictions, 1):
                lines.append(f"### Contradiction {i}")
                lines.append(f"**Source A ({c.source_a}):** {c.claim_a}")
                lines.append(f"**Source B ({c.source_b}):** {c.claim_b}")
                lines.append(f"**Opportunity:** {c.opportunity}")
                lines.append("")

        return "\n".join(lines)


@dataclass
class SearchQuery:
    """A specific search query for additional research."""
    query: str
    platform: str  # "google", "reddit", "youtube", "academic"
    why: str
    # Citation tracking: references to clips/quotes that support this suggestion
    based_on: List[str] = field(default_factory=list)  # e.g., ["CLIP_3", "QUOTE_7"]
    confidence: str = "medium"  # "high" | "medium" | "speculative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "platform": self.platform,
            "why": self.why,
            "based_on": self.based_on,
            "confidence": self.confidence,
        }


@dataclass
class SourceSuggestion:
    """A suggested source type to find."""
    source_type: str  # "documentary", "podcast", "academic_paper", etc.
    description: str
    why_helpful: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "description": self.description,
            "why_helpful": self.why_helpful,
        }


@dataclass
class RabbitHole:
    """An interesting tangent worth exploring."""
    topic: str
    mentioned_in: str  # Video title/timestamp
    potential_angle: str
    # Citation tracking: references to clips/quotes that support this suggestion
    based_on: List[str] = field(default_factory=list)  # e.g., ["CLIP_3", "QUOTE_7"]
    confidence: str = "speculative"  # Rabbit holes are inherently speculative

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "mentioned_in": self.mentioned_in,
            "potential_angle": self.potential_angle,
            "based_on": self.based_on,
            "confidence": self.confidence,
        }


@dataclass
class ContentAngle:
    """A unique angle for the creator's own video."""
    angle: str
    differentiator: str
    why_unique: str
    # Citation tracking: references to clips/quotes that support this angle
    based_on: List[str] = field(default_factory=list)  # e.g., ["CLIP_3", "QUOTE_7"]
    confidence: str = "medium"  # "high" | "medium" | "speculative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "angle": self.angle,
            "differentiator": self.differentiator,
            "why_unique": self.why_unique,
            "based_on": self.based_on,
            "confidence": self.confidence,
        }


@dataclass
class ResearchStarter:
    """Actionable research starting points.

    Phase 3: Gives creators a jump start on additional research.
    No rabbit holes - bounded, focused suggestions.
    
    H-013: Includes parse_error flag to signal incomplete/failed parsing.
    """
    # Search Queries (exact terms)
    search_queries: List[SearchQuery] = field(default_factory=list)

    # Source Type Suggestions
    source_suggestions: List[SourceSuggestion] = field(default_factory=list)

    # Rabbit Holes (interesting tangents)
    rabbit_holes: List[RabbitHole] = field(default_factory=list)

    # Content Angles (what makes YOUR video different)
    content_angles: List[ContentAngle] = field(default_factory=list)
    
    # H-013: Error tracking - True if LLM response parsing failed
    parse_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "search_queries": [q.to_dict() for q in self.search_queries],
            "source_suggestions": [s.to_dict() for s in self.source_suggestions],
            "rabbit_holes": [r.to_dict() for r in self.rabbit_holes],
            "content_angles": [a.to_dict() for a in self.content_angles],
            "parse_error": self.parse_error,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Research Starter Kit",
            "",
            "## Search Queries",
            "",
            "Copy these exact queries to search:",
            "",
        ]

        # Group by platform
        platforms = {}
        for q in self.search_queries:
            if q.platform not in platforms:
                platforms[q.platform] = []
            platforms[q.platform].append(q)

        for platform, queries in platforms.items():
            lines.append(f"### {platform.title()}")
            for q in queries:
                lines.append(f"- `{q.query}` — {q.why}")
            lines.append("")

        lines.extend([
            "## Suggested Source Types",
            "",
        ])
        for s in self.source_suggestions:
            lines.append(f"### {s.source_type.replace('_', ' ').title()}")
            lines.append(f"**What to find:** {s.description}")
            lines.append(f"**Why helpful:** {s.why_helpful}")
            lines.append("")

        if self.rabbit_holes:
            lines.extend([
                "## Interesting Tangents (Rabbit Holes)",
                "",
            ])
            for r in self.rabbit_holes:
                lines.append(f"### {r.topic}")
                lines.append(f"**Mentioned in:** {r.mentioned_in}")
                lines.append(f"**Potential angle:** {r.potential_angle}")
                lines.append("")

        if self.content_angles:
            lines.extend([
                "## Unique Angles for YOUR Video",
                "",
            ])
            for a in self.content_angles:
                lines.append(f"### {a.angle}")
                lines.append(f"**What makes it different:** {a.differentiator}")
                lines.append(f"**Why it's unique:** {a.why_unique}")
                lines.append("")

        return "\n".join(lines)


# =============================================================================
# Legacy Producer Packet v1 (for backward compatibility during migration)
# These are only used in worker.py for legacy video analysis jobs
# =============================================================================

class VerificationLevel(str, Enum):
    """Verification status for clips and quotes."""
    VERIFIED = "verified"  # Quote found in transcript, timestamp confirmed
    PROBABLE = "probable"  # High confidence but not exact match
    UNVERIFIED = "unverified"  # Extracted but not cross-verified


class TriageLevel(str, Enum):
    """Quality triage levels for producer packets.
    
    Provides nuanced assessment beyond pass/fail quality gate.
    """
    READY = "ready"           # 6+ clips, 12+ quotes, 4+ verified claims
    USABLE = "usable"         # Meets minimums but low verification
    THIN = "thin"             # Below minimums but has some content
    FAILED = "failed"         # Nothing usable


@dataclass
class ProducerClip:
    """A clip extracted from video for production use.

    Phase 2: Grounded extraction - no opinions, just facts.
    """
    clip_id: str
    video_url: str
    timestamp_start: str  # MM:SS format
    timestamp_end: str  # MM:SS format
    speaker: str
    quote: str  # Verbatim quote
    quote_type: str  # statement, question, reaction
    # Verification flags (ChatGPT refinement)
    range_verified: bool = False  # Timestamp within video bounds
    quote_verified: bool = False  # Quote found in transcript
    verification_level: VerificationLevel = VerificationLevel.UNVERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "video_url": self.video_url,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "speaker": self.speaker,
            "quote": self.quote,
            "quote_type": self.quote_type,
            "range_verified": self.range_verified,
            "quote_verified": self.quote_verified,
            "verification_level": self.verification_level.value,
        }


@dataclass
class ProducerQuote:
    """A quote extracted from video for production use."""
    quote_id: str
    video_url: str
    text: str  # Verbatim quote
    speaker: str
    timestamp: str  # MM:SS format
    # Verification
    quote_verified: bool = False
    match_score: float = 0.0  # 0-1, how well quote matches transcript

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quote_id": self.quote_id,
            "video_url": self.video_url,
            "text": self.text,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "quote_verified": self.quote_verified,
            "match_score": self.match_score,
        }


@dataclass
class LegacyProducerPacket:
    """Grounded extraction output for video producers (LEGACY v1).

    Phase 2: Contains only grounded facts - clips, quotes, timestamps.
    No opinions, no analysis, no "why it matters".

    DEPRECATED: Use ProducerPacket v2 from producer_models.py for new code.
    This class is kept only for backward compatibility with existing video
    analysis jobs in worker.py.
    
    Quality gates (from plan):
    - clips >= 4
    - quotes >= 8
    - verified_claims >= 2
    """
    title: str
    videos_analyzed: List[Dict[str, Any]]  # Video metadata
    clips: List[ProducerClip] = field(default_factory=list)
    quotes: List[ProducerQuote] = field(default_factory=list)
    verified_claims: List[Dict[str, Any]] = field(default_factory=list)
    candidate_claims: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extraction_cost: float = 0.0

    def passes_quality_gate(self) -> tuple[bool, List[str]]:
        """Check if packet meets quality thresholds.
        
        Accepts candidate_claims as fallback when transcripts unavailable
        (verified_claims require transcript matching which may not be possible).
        """
        failures = []

        if len(self.clips) < 4:
            failures.append(f"clips: {len(self.clips)} < 4 required")
        if len(self.quotes) < 8:
            failures.append(f"quotes: {len(self.quotes)} < 8 required")
        
        # Accept either verified claims OR candidate claims as fallback
        if len(self.verified_claims) < 2 and len(self.candidate_claims) < 6:
            failures.append(
                f"insufficient claims: {len(self.verified_claims)} verified, "
                f"{len(self.candidate_claims)} candidate (need 2+ verified OR 6+ candidate)"
            )

        return len(failures) == 0, failures

    def triage(self) -> tuple["TriageLevel", List[str]]:
        """Compute triage level with reasons.
        
        Provides nuanced quality assessment beyond pass/fail:
        - READY: Full quality, ready for production
        - USABLE: Meets minimums, spot-check recommended
        - THIN: Below minimums but has some content
        - FAILED: Nothing usable
        """
        reasons = []
        
        clip_count = len(self.clips)
        quote_count = len(self.quotes)
        verified_count = len(self.verified_claims)
        candidate_count = len(self.candidate_claims)
        
        # READY: High quality output
        if clip_count >= 6 and quote_count >= 12 and verified_count >= 4:
            return TriageLevel.READY, []
        
        # USABLE: Meets minimums with acceptable verification
        if clip_count >= 4 and quote_count >= 8:
            if verified_count >= 2 or candidate_count >= 6:
                reasons.append("Low verification - spot-check recommended")
                return TriageLevel.USABLE, reasons
        
        # THIN: Has some content but below minimums
        if clip_count >= 2 or quote_count >= 4:
            reasons.append(f"Thin extraction: {clip_count} clips, {quote_count} quotes")
            return TriageLevel.THIN, reasons
        
        # FAILED: Nothing usable
        reasons.append("Insufficient extraction")
        return TriageLevel.FAILED, reasons

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export."""
        passes, failures = self.passes_quality_gate()
        triage_level, triage_reasons = self.triage()
        return {
            "title": self.title,
            "videos_analyzed": self.videos_analyzed,
            "clips": [c.to_dict() for c in self.clips],
            "quotes": [q.to_dict() for q in self.quotes],
            "verified_claims": self.verified_claims,
            "candidate_claims": self.candidate_claims,
            "quality_gate": {
                "passes": passes,
                "failures": failures,
                "clip_count": len(self.clips),
                "quote_count": len(self.quotes),
                "verified_claim_count": len(self.verified_claims),
            },
            "triage": {
                "level": triage_level.value,
                "reasons": triage_reasons,
            },
            "warnings": self.warnings,
            "extraction_cost": self.extraction_cost,
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _verify_quote(quote: str, transcript: str, threshold: float = 0.8) -> tuple[bool, float]:
    """Verify a quote against transcript text using fuzzy matching.

    Returns (is_verified, match_score) where:
    - is_verified: True if match_score >= threshold
    - match_score: 0.0-1.0 similarity score

    Uses RapidFuzz for efficient fuzzy string matching with sliding window.
    Falls back to difflib if RapidFuzz unavailable.
    """
    if not quote or not transcript:
        return False, 0.0

    quote_lower = quote.lower().strip()
    transcript_lower = transcript.lower()

    # Exact substring match (fastest check)
    if quote_lower in transcript_lower:
        return True, 1.0

    # Try RapidFuzz for fuzzy matching
    try:
        from rapidfuzz import fuzz
        from rapidfuzz.distance import Levenshtein

        # For short quotes, use partial_ratio (good for substring matching)
        if len(quote_lower) < 50:
            score = fuzz.partial_ratio(quote_lower, transcript_lower) / 100.0
            return score >= threshold, score

        # For longer quotes, use sliding window with token_set_ratio
        best_score = 0.0
        window_size = min(len(quote_lower) * 2, len(transcript_lower))
        step = max(10, len(quote_lower) // 4)

        for i in range(0, max(1, len(transcript_lower) - len(quote_lower)), step):
            window = transcript_lower[i : i + window_size]
            score = fuzz.token_set_ratio(quote_lower, window) / 100.0
            best_score = max(best_score, score)
            if best_score >= 0.95:
                break

        return best_score >= threshold, best_score

    except ImportError:
        # Fallback to difflib if RapidFuzz not installed
        from difflib import SequenceMatcher

        best_score = 0.0
        window_size = len(quote_lower) + 50
        step_size = 10

        for i in range(0, max(1, len(transcript_lower) - len(quote_lower)), step_size):
            window = transcript_lower[i : i + window_size]
            score = SequenceMatcher(None, quote_lower, window).ratio()
            best_score = max(best_score, score)

        return best_score >= threshold, best_score


def _verify_timestamp_format(timestamp: str) -> bool:
    """Verify timestamp is in MM:SS or HH:MM:SS format."""
    import re
    if not timestamp:
        return False
    # Match MM:SS or HH:MM:SS
    return bool(re.match(r'^(\d{1,2}:)?\d{1,2}:\d{2}$', timestamp))


def create_producer_packet_from_gemini(
    gemini_results: Dict[str, Any],
    title: str,
    transcripts: Optional[Dict[str, str]] = None,
) -> LegacyProducerPacket:
    """Create a Legacy Producer Packet from Gemini video extraction results.

    DEPRECATED: This function is kept for backward compatibility with 
    existing video analysis jobs. New code should use the semantic pipeline
    and ProducerPacket v2 from producer_models.py.

    Phase 2: Converts raw Gemini output to structured Producer Packet
    with verification against transcripts.

    Args:
        gemini_results: Output from GeminiClient.analyze_youtube_videos_batch()
        title: Research title
        transcripts: Optional dict of {video_url: transcript_text} for verification

    Returns:
        LegacyProducerPacket with clips, quotes, and verification status
    """
    transcripts = transcripts or {}

    # Extract video metadata
    videos_analyzed = []
    for result in gemini_results.get("results", []):
        videos_analyzed.append({
            "url": result.get("video_url", ""),
            "title": result.get("video_info", {}).get("title", "Unknown"),
            "duration_seconds": result.get("video_info", {}).get("duration_seconds", 0),
        })

    # Convert clips
    clips = []
    raw_clips = gemini_results.get("clips", [])
    for i, raw_clip in enumerate(raw_clips):
        video_url = raw_clip.get("video_url", "")
        quote = raw_clip.get("quote", "")

        # Verify against transcript if available
        transcript = transcripts.get(video_url, "")
        quote_verified, match_score = _verify_quote(quote, transcript)

        # Check timestamp is valid format
        ts_start = raw_clip.get("timestamp_start", "00:00")
        ts_end = raw_clip.get("timestamp_end", "00:00")
        range_verified = _verify_timestamp_format(ts_start) and _verify_timestamp_format(ts_end)

        # Determine verification level
        if quote_verified and range_verified:
            level = VerificationLevel.VERIFIED
        elif match_score >= 0.8:
            level = VerificationLevel.PROBABLE
        else:
            level = VerificationLevel.UNVERIFIED

        clips.append(ProducerClip(
            clip_id=raw_clip.get("clip_id", f"CLIP_{i+1}"),
            video_url=video_url,
            timestamp_start=ts_start,
            timestamp_end=ts_end,
            speaker=raw_clip.get("speaker", "SPEAKER_A"),
            quote=quote,
            quote_type=raw_clip.get("quote_type", "statement"),
            range_verified=range_verified,
            quote_verified=quote_verified,
            verification_level=level,
        ))

    # Convert quotes
    quotes = []
    raw_quotes = gemini_results.get("quotes", [])
    for i, raw_quote in enumerate(raw_quotes):
        video_url = raw_quote.get("video_url", "")
        text = raw_quote.get("text", "")

        # Verify against transcript
        transcript = transcripts.get(video_url, "")
        quote_verified, match_score = _verify_quote(text, transcript)

        quotes.append(ProducerQuote(
            quote_id=raw_quote.get("quote_id", f"QUOTE_{i+1}"),
            video_url=video_url,
            text=text,
            speaker=raw_quote.get("speaker", "SPEAKER_A"),
            timestamp=raw_quote.get("timestamp", "00:00"),
            quote_verified=quote_verified,
            match_score=match_score,
        ))

    # Split claims into verified and candidate
    verified_claims = []
    candidate_claims = []

    # A claim is "verified" if it has a matching quote
    for quote in quotes:
        if quote.quote_verified:
            verified_claims.append({
                "claim": quote.text,
                "source": quote.speaker,
                "timestamp": quote.timestamp,
                "video_url": quote.video_url,
            })

    # Candidate claims come from clips that aren't quote-verified
    for clip in clips:
        if not clip.quote_verified:
            candidate_claims.append({
                "claim": clip.quote,
                "clip_id": clip.clip_id,
                "timestamp": clip.timestamp_start,
                "video_url": clip.video_url,
            })

    # Build warnings
    warnings = []
    for error in gemini_results.get("errors", []):
        warnings.append(f"Video failed: {error.get('video_url', 'unknown')} - {error.get('error', 'unknown error')}")

    return LegacyProducerPacket(
        title=title,
        videos_analyzed=videos_analyzed,
        clips=clips,
        quotes=quotes,
        verified_claims=verified_claims,
        candidate_claims=candidate_claims,
        warnings=warnings,
        extraction_cost=gemini_results.get("total_cost", 0.0),
    )


# Export list for explicit API surface
__all__ = [
    # Phase 3 semantic models
    "ActSection",
    "OpenLoop",
    "ContentBlueprint",
    "MissingPerspective",
    "CoverageBlindSpot",
    "Contradiction",
    "GapAnalysis",
    "SearchQuery",
    "SourceSuggestion",
    "RabbitHole",
    "ContentAngle",
    "ResearchStarter",
    # Legacy v1 models (for backward compatibility)
    "VerificationLevel",
    "TriageLevel",
    "ProducerClip",
    "ProducerQuote",
    "LegacyProducerPacket",
    # Helper functions
    "_verify_quote",
    "_verify_timestamp_format",
    "create_producer_packet_from_gemini",
]
