"""Dual Output Formatter: NotebookLM packet + Documentary Blueprint + Producer Packet.

PRD v4.3 + Phase 2: Research Agent produces three output formats:
1. NotebookLM Packet - For AI audio podcast generation
2. Documentary Blueprint - For video production
3. Producer Packet - Grounded extraction with clips, quotes, timestamps (Phase 2)

The NotebookLM packet is optimized for text-to-speech podcast creation,
the Documentary Blueprint is for video scriptwriting,
and the Producer Packet is raw grounded extraction for video editing.
"""
from typing import Dict, Any, List, Optional, TypedDict
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


# M-005: TypedDict definitions for structured claim data
class VerifiedClaim(TypedDict):
    """Structure for a claim that has a supporting quote."""
    claim: str
    quote_id: str  # Reference to ProducerQuote
    confidence: str  # "high" | "medium" | "low"
    source_video: str


class CandidateClaim(TypedDict):
    """Structure for a claim that has clip reference but no direct quote."""
    claim: str
    clip_id: str  # Reference to ProducerClip
    timestamp: str
    needs_verification: bool


# =============================================================================
# Phase 2: Producer Packet - Grounded Extraction Output
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
class ProducerPacket:
    """Grounded extraction output for video producers.

    Phase 2: Contains only grounded facts - clips, quotes, timestamps.
    No opinions, no analysis, no "why it matters".

    Quality gates (from plan):
    - clips >= 4
    - quotes >= 8
    - verified_claims >= 2
    """
    title: str
    videos_analyzed: List[Dict[str, Any]]  # Video metadata
    clips: List[ProducerClip] = field(default_factory=list)
    quotes: List[ProducerQuote] = field(default_factory=list)
    # M-005: Use TypedDict for structured claims
    verified_claims: List[VerifiedClaim] = field(default_factory=list)  # Has supporting quote
    candidate_claims: List[CandidateClaim] = field(default_factory=list)  # Clip ref only
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
        # (When transcripts are unavailable, verification is impossible)
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

    def to_markdown(self) -> str:
        """Convert to markdown for human review."""
        lines = [
            f"# Producer Packet: {self.title}",
            "",
            "## Summary",
            f"- **Videos Analyzed:** {len(self.videos_analyzed)}",
            f"- **Clips Extracted:** {len(self.clips)}",
            f"- **Quotes Extracted:** {len(self.quotes)}",
            f"- **Verified Claims:** {len(self.verified_claims)}",
            f"- **Extraction Cost:** ${self.extraction_cost:.4f}",
            "",
        ]

        # Quality gate status
        passes, failures = self.passes_quality_gate()
        if passes:
            lines.append("**Quality Gate:** ✅ PASSED")
        else:
            lines.append("**Quality Gate:** ❌ FAILED")
            for f in failures:
                lines.append(f"  - {f}")
        lines.append("")

        # Clips section
        lines.extend([
            "## Clips",
            "",
        ])
        # Sort verified first
        sorted_clips = sorted(
            self.clips,
            key=lambda c: (not c.quote_verified, c.timestamp_start)
        )
        for clip in sorted_clips:
            status = "✅" if clip.quote_verified else "⚠️"
            lines.append(
                f"### {status} {clip.clip_id} [{clip.timestamp_start}-{clip.timestamp_end}]"
            )
            lines.append(f"**Speaker:** {clip.speaker}")
            lines.append(f"> \"{clip.quote}\"")
            lines.append(f"**Type:** {clip.quote_type} | **Verified:** {clip.verification_level.value}")
            lines.append("")

        # Quotes section
        lines.extend([
            "## Quotes",
            "",
        ])
        sorted_quotes = sorted(
            self.quotes,
            key=lambda q: (not q.quote_verified, q.timestamp)
        )
        for quote in sorted_quotes:
            status = "✅" if quote.quote_verified else "⚠️"
            lines.append(f"- {status} [{quote.timestamp}] **{quote.speaker}:** \"{quote.text}\"")

        lines.append("")

        # Verified claims
        if self.verified_claims:
            lines.extend([
                "",
                "## Verified Claims",
                "",
            ])
            for claim in self.verified_claims:
                lines.append(f"- {claim.get('claim', str(claim))}")

        # Warnings
        if self.warnings:
            lines.extend([
                "",
                "## Warnings",
                "",
            ])
            for w in self.warnings:
                lines.append(f"- ⚠️ {w}")

        return "\n".join(lines)


# =============================================================================
# Phase 3: Full Research Assistant Pipeline - New Output Types
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
        for q in self.unanswered_questions:
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


@dataclass
class NotebookLMPacket:
    """Output format for NotebookLM AI podcast generation."""
    title: str
    summary: str  # 2-3 sentence overview
    key_facts: List[str]  # Bullet points of verified facts
    timeline_narrative: str  # Chronological story in prose
    quotes: List[Dict[str, str]]  # Notable quotes with attribution
    controversy_summary: Optional[str] = None  # If applicable
    open_questions: List[str] = field(default_factory=list)
    sources_summary: str = ""  # Brief overview of source types

    def to_markdown(self) -> str:
        """Convert to markdown for NotebookLM ingestion."""
        lines = [
            f"# {self.title}",
            "",
            "## Overview",
            self.summary,
            "",
            "## Key Facts",
        ]

        for fact in self.key_facts:
            lines.append(f"- {fact}")

        lines.extend([
            "",
            "## Timeline",
            self.timeline_narrative,
            "",
            "## Notable Quotes",
        ])

        for quote in self.quotes:
            speaker = quote.get("speaker", "Unknown")
            text = quote.get("text", "")
            lines.append(f'> "{text}" - {speaker}')
            lines.append("")

        if self.controversy_summary:
            lines.extend([
                "## Controversy",
                self.controversy_summary,
                "",
            ])

        if self.open_questions:
            lines.extend([
                "## Open Questions",
            ])
            for q in self.open_questions:
                lines.append(f"- {q}")

        lines.extend([
            "",
            "## Sources",
            self.sources_summary,
        ])

        return "\n".join(lines)


@dataclass
class DocumentaryBlueprint:
    """Output format for video documentary production."""
    title: str
    logline: str  # One sentence hook
    three_act_structure: Dict[str, Any]
    interview_subjects: List[Dict[str, Any]]
    b_roll_suggestions: List[str]
    graphics_needed: List[str]
    music_tone: str
    estimated_runtime: str
    production_notes: Dict[str, Any]

    def to_markdown(self) -> str:
        """Convert to markdown blueprint."""
        lines = [
            f"# Documentary Blueprint: {self.title}",
            "",
            f"**Logline:** {self.logline}",
            f"**Estimated Runtime:** {self.estimated_runtime}",
            f"**Music Tone:** {self.music_tone}",
            "",
            "## Three-Act Structure",
            "",
        ]

        # Act 1
        act1 = self.three_act_structure.get("act_1", {})
        lines.extend([
            "### Act 1: Setup",
            f"**Hook:** {act1.get('hook', 'TBD')}",
            "",
            "**Key Players:**",
        ])
        for player in act1.get("key_players", []):
            lines.append(f"- {player}")

        # Act 2
        act2 = self.three_act_structure.get("act_2", {})
        lines.extend([
            "",
            "### Act 2: Investigation",
            "",
            "**Revelations:**",
        ])
        for rev in act2.get("revelations", []):
            lines.append(f"- {rev}")

        lines.extend([
            "",
            "**Conflicts:**",
        ])
        for conflict in act2.get("conflicts", []):
            lines.append(f"- {conflict}")

        # Act 3
        act3 = self.three_act_structure.get("act_3", {})
        lines.extend([
            "",
            "### Act 3: Resolution",
            f"**Climax:** {act3.get('climax', 'TBD')}",
            "",
            "**Verified Conclusions:**",
        ])
        for conclusion in act3.get("conclusions", []):
            lines.append(f"- {conclusion}")

        # Interview subjects
        lines.extend([
            "",
            "## Interview Subjects",
            "",
        ])
        for subject in self.interview_subjects:
            lines.append(f"### {subject.get('name', 'Unknown')}")
            lines.append(f"**Priority:** {subject.get('priority', 'Medium')}")
            lines.append("**Suggested Questions:**")
            for q in subject.get("questions", []):
                lines.append(f"- {q}")
            lines.append("")

        # B-roll
        lines.extend([
            "## B-Roll Suggestions",
            "",
        ])
        for broll in self.b_roll_suggestions:
            lines.append(f"- {broll}")

        # Graphics
        lines.extend([
            "",
            "## Graphics Needed",
            "",
        ])
        for graphic in self.graphics_needed:
            lines.append(f"- {graphic}")

        # Production notes
        lines.extend([
            "",
            "## Production Notes",
            "",
        ])
        for key, value in self.production_notes.items():
            lines.append(f"**{key.replace('_', ' ').title()}:** {value}")

        return "\n".join(lines)


class DualOutputFormatter:
    """Generate both NotebookLM and Documentary outputs from research."""

    def format(
        self,
        research_data: Dict[str, Any],
        documentary_analysis: Dict[str, Any],
        title: str,
    ) -> Dict[str, str]:
        """
        Generate dual output formats.

        Args:
            research_data: Raw research data (claims, timeline, entities, etc.)
            documentary_analysis: Output from DocumentaryIntelligence
            title: Research topic/title

        Returns:
            Dict with 'notebooklm_md' and 'documentary_md' keys
        """
        logger.info(f"Generating dual output for: {title}")

        # Generate NotebookLM packet
        notebook_packet = self._create_notebook_packet(
            research_data, documentary_analysis, title
        )

        # Generate Documentary Blueprint
        doc_blueprint = self._create_documentary_blueprint(
            research_data, documentary_analysis, title
        )

        return {
            "notebooklm_md": notebook_packet.to_markdown(),
            "documentary_md": doc_blueprint.to_markdown(),
        }

    def _create_notebook_packet(
        self,
        research_data: Dict,
        doc_analysis: Dict,
        title: str,
    ) -> NotebookLMPacket:
        """Create NotebookLM-optimized packet."""

        # Extract key facts from claims
        claims = research_data.get("claims", [])
        key_facts = []
        for claim in claims[:15]:
            if isinstance(claim, dict):
                fact = claim.get("canonical_claim", str(claim))
            else:
                fact = str(claim)
            if len(fact) < 300:
                key_facts.append(fact[:200])

        # Build timeline narrative
        timeline = research_data.get("timeline", [])
        timeline_parts = []
        for event in timeline[:20]:
            if isinstance(event, dict):
                date = event.get("date", "")
                desc = event.get("event", event.get("description", ""))
                timeline_parts.append(f"{date}: {desc}")

        timeline_narrative = " ".join(timeline_parts) if timeline_parts else "Timeline to be constructed from research."

        # Extract notable quotes
        quotes = []
        sources = research_data.get("sources", [])
        for source in sources[:30]:
            if isinstance(source, dict):
                text = source.get("text", "")
                # Look for quoted text
                if '"' in text:
                    import re
                    quoted = re.findall(r'"([^"]{20,200})"', text)
                    for q in quoted[:2]:
                        quotes.append({
                            "text": q,
                            "speaker": source.get("title", "Source"),
                        })
                if len(quotes) >= 10:
                    break

        # Summary
        summary = f"This research packet covers {title}. "
        summary += f"It includes {len(claims)} verified claims, "
        summary += f"{len(timeline)} timeline events, "
        summary += f"and {len(sources)} sources."

        # Open questions
        open_questions = doc_analysis.get("what_we_dont_know", [])
        if not open_questions:
            open_questions = [
                c.get("canonical_claim", str(c))[:100]
                for c in claims
                if isinstance(c, dict) and c.get("confidence", 1) < 0.5
            ][:5]

        # Sources summary
        source_types = {}
        for s in sources:
            if isinstance(s, dict):
                stype = s.get("source_type", "unknown")
                source_types[stype] = source_types.get(stype, 0) + 1

        sources_summary = ", ".join([f"{v} {k}" for k, v in source_types.items()])

        return NotebookLMPacket(
            title=title,
            summary=summary,
            key_facts=key_facts,
            timeline_narrative=timeline_narrative,
            quotes=quotes,
            controversy_summary=doc_analysis.get("controversy_summary"),
            open_questions=open_questions,
            sources_summary=sources_summary or f"{len(sources)} sources analyzed",
        )

    def _create_documentary_blueprint(
        self,
        research_data: Dict,
        doc_analysis: Dict,
        title: str,
    ) -> DocumentaryBlueprint:
        """Create documentary production blueprint."""

        # Extract from documentary analysis
        hook = doc_analysis.get("hook", "Opening hook to be determined")
        narrative = doc_analysis.get("narrative_structure", {})

        # Three-act structure
        three_act = {
            "act_1": {
                "hook": hook[:200] if isinstance(hook, str) else str(hook)[:200],
                "key_players": doc_analysis.get("key_players", [])[:5],
                "context": narrative.get("act_1_setup", {}).get("establish_context", []),
            },
            "act_2": {
                "revelations": [
                    str(r)[:150] for r in narrative.get("act_2_investigation", {}).get("key_revelations", [])
                ][:5],
                "conflicts": [
                    c.get("conflict", str(c))[:100]
                    for c in doc_analysis.get("key_conflicts", [])
                ][:3],
            },
            "act_3": {
                "climax": str(narrative.get("act_3_resolution", {}).get("climax", "TBD"))[:200],
                "conclusions": doc_analysis.get("verified_conclusions", ["To be determined"])[:5],
            },
        }

        # Interview subjects
        interviews = doc_analysis.get("interview_suggestions", [])
        interview_subjects = []
        for interview in interviews[:5]:
            if isinstance(interview, dict):
                interview_subjects.append({
                    "name": interview.get("subject", "Unknown"),
                    "priority": interview.get("priority", "medium"),
                    "questions": interview.get("suggested_questions", [])[:3],
                })

        # B-roll suggestions
        visual_moments = doc_analysis.get("visual_moments", [])
        b_roll = [
            v.get("production_note", str(v))[:100]
            for v in visual_moments[:10]
            if isinstance(v, dict)
        ]
        if not b_roll:
            b_roll = [
                "Stock footage of relevant locations",
                "News archive footage",
                "Document close-ups",
                "Interview setup shots",
            ]

        # Production notes
        prod_notes = doc_analysis.get("production_notes", {})
        if not prod_notes:
            prod_notes = {
                "tone": "Balanced, investigative",
                "pacing": "Medium",
                "target_audience": "General audience",
            }

        return DocumentaryBlueprint(
            title=title,
            logline=hook[:150] if isinstance(hook, str) else "Documentary exploring " + title,
            three_act_structure=three_act,
            interview_subjects=interview_subjects,
            b_roll_suggestions=b_roll,
            graphics_needed=[
                "Timeline infographic",
                "Entity relationship map",
                "Key claims summary card",
                "Source credibility indicators",
            ],
            music_tone=prod_notes.get("tone", "Balanced, investigative"),
            estimated_runtime=prod_notes.get("estimated_runtime", "15-20 minutes"),
            production_notes=prod_notes,
        )


def format_dual_output(
    research_data: Dict[str, Any],
    documentary_analysis: Dict[str, Any],
    title: str,
) -> Dict[str, str]:
    """
    Convenience function to generate dual output.

    Returns:
        Dict with 'notebooklm_md' and 'documentary_md' markdown strings
    """
    formatter = DualOutputFormatter()
    return formatter.format(research_data, documentary_analysis, title)


# =============================================================================
# Phase 2: Producer Packet Generator
# =============================================================================

def create_producer_packet_from_gemini(
    gemini_results: Dict[str, Any],
    title: str,
    transcripts: Optional[Dict[str, str]] = None,
) -> ProducerPacket:
    """Create a Producer Packet from Gemini video extraction results.

    Phase 2: Converts raw Gemini output to structured Producer Packet
    with verification against transcripts.

    Args:
        gemini_results: Output from GeminiClient.analyze_youtube_videos_batch()
        title: Research title
        transcripts: Optional dict of {video_url: transcript_text} for verification

    Returns:
        ProducerPacket with clips, quotes, and verification status
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

    return ProducerPacket(
        title=title,
        videos_analyzed=videos_analyzed,
        clips=clips,
        quotes=quotes,
        verified_claims=verified_claims,
        candidate_claims=candidate_claims,
        warnings=warnings,
        extraction_cost=gemini_results.get("total_cost", 0.0),
    )


def _verify_quote(quote: str, transcript: str, threshold: float = 0.8) -> tuple[bool, float]:
    """Verify a quote against transcript text.

    Returns (is_verified, match_score) where:
    - is_verified: True if match_score >= threshold
    - match_score: 0.0-1.0 similarity score

    Uses simple substring matching for now.
    TODO: Use fuzzy matching for better accuracy.
    """
    if not quote or not transcript:
        return False, 0.0

    quote_lower = quote.lower().strip()
    transcript_lower = transcript.lower()

    # Exact substring match
    if quote_lower in transcript_lower:
        return True, 1.0

    # Check for partial match (first 50 chars)
    quote_start = quote_lower[:50]
    if quote_start in transcript_lower:
        return True, 0.9

    # Very basic word overlap score
    quote_words = set(quote_lower.split())
    transcript_words = set(transcript_lower.split())

    if not quote_words:
        return False, 0.0

    overlap = len(quote_words & transcript_words)
    score = overlap / len(quote_words)

    return score >= threshold, score


def _verify_timestamp_format(timestamp: str) -> bool:
    """Verify timestamp is in MM:SS or HH:MM:SS format."""
    import re
    if not timestamp:
        return False
    # Match MM:SS or HH:MM:SS
    return bool(re.match(r'^(\d{1,2}:)?\d{1,2}:\d{2}$', timestamp))
