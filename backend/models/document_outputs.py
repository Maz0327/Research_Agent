"""
Document Outputs - The 3-Document Model for Research Agent.

Based on: docs/authoritative/spec/Document_Output_Format.md

Canonical Documents:
- Doc 0: Source Ledger (Canonical Data Layer)
- Doc 1: Jump-Start (Research Direction Layer)
- Doc 2: Semantic Research Brief (80% Output)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    SpeculativeObservation,
    Tension,
    Theme,
)


class SourceStatus(str, Enum):
    """Status of a source in the ledger."""
    INGESTED = "ingested"
    FAILED = "failed"
    PARTIAL = "partial"


class TriageLevel(str, Enum):
    """Overall document quality assessment."""
    READY = "ready"  # Full quality, all checks pass
    USABLE = "usable"  # Minor issues, still useful
    THIN = "thin"  # Limited content, use with caution
    DEGRADED = "degraded"  # Significant limitations
    FAILED = "failed"  # Cannot produce meaningful output


# -----------------------------------------------------------------------------
# DOC 0: SOURCE LEDGER (Canonical Data Layer)
# -----------------------------------------------------------------------------

@dataclass
class TranscriptProvenance:
    """
    Metadata describing how transcript was acquired for video sources.

    Transcript Acquisition Order (LOCKED):
    1. Supadata (primary) → transcript_grounded
    2. Whisper (if Supadata fails) → transcript_grounded
    3. YouTube captions (if Whisper fails) → caption_grounded
    4. None (if all fail) → video_only
    """
    transcript_source: str  # "supadata", "whisper", "youtube_captions", "none"
    transcript_status: str  # "success", "failed"
    captions_status: str  # "success", "missing", "failed"
    gemini_analysis_mode: AnalysisMode
    quote_verification: bool
    timestamp_grounding: bool
    semantic_precision: ConfidenceLevel  # high, medium, low
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcript_source": self.transcript_source,
            "transcript_status": self.transcript_status,
            "captions_status": self.captions_status,
            "gemini_analysis_mode": self.gemini_analysis_mode.value,
            "verification_capabilities": {
                "quote_verification": self.quote_verification,
                "timestamp_grounding": self.timestamp_grounding,
                "semantic_precision": self.semantic_precision.value,
            },
            "notes": self.notes,
        }


@dataclass
class SourceEntry:
    """
    A single source entry in the Source Ledger.

    Per-Source Section includes:
    - Metadata (type, title, creator, etc.)
    - Skim Summary (3-6 bullets)
    - Extracted Index (claims, entities, themes)
    - Full Source Text (canonical)
    - Transcript Provenance (for video)
    """
    source_id: str
    source_type: str  # "youtube", "article", "reddit", etc.
    title: str
    url: str
    status: SourceStatus = SourceStatus.INGESTED

    # Metadata
    creator: Optional[str] = None
    published: Optional[str] = None
    duration: Optional[str] = None  # For video
    word_count: Optional[int] = None  # For text

    # Skim Summary (3-6 bullets describing content)
    skim_summary: list[str] = field(default_factory=list)

    # Extracted Index references
    claim_ids: list[str] = field(default_factory=list)
    entity_names: list[str] = field(default_factory=list)
    theme_ids: list[str] = field(default_factory=list)

    # Full Source Text (canonical)
    full_text: Optional[str] = None
    full_text_unavailable_reason: Optional[str] = None  # For degraded sources

    # Transcript Provenance (video sources only)
    transcript_provenance: Optional[TranscriptProvenance] = None

    # Failure info
    failure_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "status": self.status.value,
            "creator": self.creator,
            "published": self.published,
            "duration": self.duration,
            "word_count": self.word_count,
            "skim_summary": self.skim_summary,
            "extracted_index": {
                "claim_ids": self.claim_ids,
                "entity_names": self.entity_names,
                "theme_ids": self.theme_ids,
            },
            "full_text": self.full_text,
            "full_text_unavailable_reason": self.full_text_unavailable_reason,
            "transcript_provenance": (
                self.transcript_provenance.to_dict()
                if self.transcript_provenance else None
            ),
            "failure_reason": self.failure_reason,
        }

    def to_markdown(self) -> str:
        """Render source entry as markdown section."""
        lines = [
            f"### SOURCE: {self.source_id}",
            f"Type: {self.source_type}",
            f"Title: {self.title}",
        ]

        if self.creator:
            lines.append(f"Creator: {self.creator}")
        if self.published:
            lines.append(f"Published: {self.published}")
        if self.duration:
            lines.append(f"Duration: {self.duration}")
        if self.word_count:
            lines.append(f"Word Count: {self.word_count:,}")

        lines.append(f"URL: {self.url}")
        lines.append("")

        if self.skim_summary:
            lines.append("#### Skim Summary")
            for bullet in self.skim_summary:
                lines.append(f"- {bullet}")
            lines.append("")

        if self.full_text:
            lines.append("#### FULL SOURCE TEXT (Canonical)")
            lines.append(self.full_text)
        elif self.full_text_unavailable_reason:
            lines.extend([
                "#### FULL SOURCE TEXT (Canonical)",
                "FULL SOURCE TEXT UNAVAILABLE",
                "",
                f"Reason: {self.full_text_unavailable_reason}",
                f"Analysis Mode: {self.transcript_provenance.gemini_analysis_mode.value if self.transcript_provenance else 'unknown'}",
                "",
                "This source was analyzed without verbatim transcript text.",
                "All extracted content should be treated as approximate.",
            ])

        if self.transcript_provenance:
            tp = self.transcript_provenance
            lines.extend([
                "",
                "#### Transcript Provenance",
                f"Source: {tp.transcript_source.title()} | Mode: {tp.gemini_analysis_mode.value}",
                f"Verification: {'Full quote verification available' if tp.quote_verification else 'Limited verification'}",
            ])

        return "\n".join(lines)


@dataclass
class SourceLedger:
    """
    Doc 0: Source Ledger (Canonical Data Layer)

    Purpose:
    - Preserve 100% of full context
    - Act as the single source of truth
    - Enable verification, recall, and re-orientation

    Guarantees:
    - No information appears elsewhere unless it exists here
    - All other documents must reference this document
    """
    topic: str  # Scope Lock sentence
    sources: list[SourceEntry] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": "source_ledger",
            "topic": self.topic,
            "source_manifest": [
                {
                    "source_id": s.source_id,
                    "type": s.source_type,
                    "title": s.title,
                    "status": s.status.value,
                }
                for s in self.sources
            ],
            "sources": [s.to_dict() for s in self.sources],
            "created_at": self.created_at,
        }

    def to_markdown(self) -> str:
        """Render full Source Ledger as markdown."""
        lines = [
            "# SOURCE LEDGER",
            f"Topic: {self.topic}",
            "",
            "## SOURCE MANIFEST",
            "| Source ID | Type | Title | Status |",
            "|-----------|------|-------|--------|",
        ]

        for s in self.sources:
            lines.append(f"| {s.source_id} | {s.source_type} | {s.title[:40]}... | {s.status.value} |")

        lines.extend(["", "---", "", "## SOURCES", ""])

        for source in self.sources:
            lines.append(source.to_markdown())
            lines.extend(["", "---", ""])

        return "\n".join(lines)

    @property
    def ingested_count(self) -> int:
        return sum(1 for s in self.sources if s.status == SourceStatus.INGESTED)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.sources if s.status == SourceStatus.FAILED)


# -----------------------------------------------------------------------------
# DOC 1: JUMP-START (Research Direction Layer)
# -----------------------------------------------------------------------------

@dataclass
class ResearchDirection:
    """A prioritized research direction with guidance."""
    priority: int  # 1 = highest
    what_to_look_for: str
    example_queries: list[str] = field(default_factory=list)
    why_it_matters: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "what_to_look_for": self.what_to_look_for,
            "example_queries": self.example_queries,
            "why_it_matters": self.why_it_matters,
        }


@dataclass
class VerificationItem:
    """An item that needs verification."""
    item_id: str
    description: str
    status: str = "pending"  # "pending", "verified", "unverifiable"
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "description": self.description,
            "status": self.status,
            "notes": self.notes,
        }


@dataclass
class JumpStartDirections:
    """
    Doc 1: Jump-Start (Research Direction Layer)

    Purpose:
    - Reduce activation energy
    - Answer: "What do I have, what's missing, where do I go next?"

    Guarantees:
    - Always produced, even if thin
    - Useful without any external APIs
    - May be augmented by Deep Research Booster
    """
    # Scope Lock
    scope_in: list[str] = field(default_factory=list)  # What this research covers
    scope_out: list[str] = field(default_factory=list)  # What is out of scope

    # Current Corpus Overview
    source_count: int = 0
    perspectives_represented: list[str] = field(default_factory=list)
    time_span_covered: Optional[str] = None

    # What We Know
    key_points: list[KeyPoint] = field(default_factory=list)

    # What Is Unclear or Disputed
    tensions: list[Tension] = field(default_factory=list)

    # Gaps (What's Missing)
    gaps: list[Gap] = field(default_factory=list)

    # Suggested Research Directions
    research_directions: list[ResearchDirection] = field(default_factory=list)

    # Verification Checklist
    verification_items: list[VerificationItem] = field(default_factory=list)

    # Top 3 Next Steps (MANDATORY)
    next_steps: list[str] = field(default_factory=list)

    # Metadata
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": "jump_start",
            "scope_lock": {
                "in": self.scope_in,
                "out": self.scope_out,
            },
            "corpus_overview": {
                "source_count": self.source_count,
                "perspectives_represented": self.perspectives_represented,
                "time_span_covered": self.time_span_covered,
            },
            "key_points": [kp.to_dict() for kp in self.key_points],
            "tensions": [t.to_dict() for t in self.tensions],
            "gaps": [g.to_dict() for g in self.gaps],
            "research_directions": [rd.to_dict() for rd in self.research_directions],
            "verification_items": [vi.to_dict() for vi in self.verification_items],
            "next_steps": self.next_steps,
            "confidence": self.confidence.value,
            "warnings": self.warnings,
            "created_at": self.created_at,
        }

    def to_markdown(self) -> str:
        """Render Jump-Start as markdown."""
        lines = [
            "# JUMP-START RESEARCH BRIEF",
            "",
            "## SCOPE LOCK",
            "This research covers:",
        ]

        for item in self.scope_in:
            lines.append(f"- IN: {item}")
        for item in self.scope_out:
            lines.append(f"- OUT: {item}")

        lines.extend([
            "",
            "---",
            "",
            "## CURRENT CORPUS OVERVIEW",
            f"- Number of sources: {self.source_count}",
            f"- Perspectives represented: {', '.join(self.perspectives_represented)}",
            f"- Time span covered: {self.time_span_covered or 'Not specified'}",
            "",
            "---",
            "",
            "## WHAT WE KNOW (From Current Sources)",
        ])

        for kp in self.key_points:
            lines.append(f"- {kp.key_point_id}: {kp.statement}")

        lines.extend(["", "---", "", "## WHAT IS UNCLEAR OR DISPUTED"])

        for t in self.tensions:
            lines.append(f"- {t.tension_id}: {t.description}")

        lines.extend(["", "---", "", "## GAPS (What's Missing)"])

        for g in self.gaps:
            lines.append(f"- {g.gap_id}: {g.description}")
            lines.append(f"  Why it matters: {g.why_expected}")

        lines.extend(["", "---", "", "## SUGGESTED RESEARCH DIRECTIONS"])

        for rd in self.research_directions:
            lines.extend([
                f"### Priority {rd.priority}",
                f"- What to look for: {rd.what_to_look_for}",
                f"- Example queries: {', '.join(rd.example_queries)}",
                f"- Why this matters: {rd.why_it_matters}",
                "",
            ])

        lines.extend(["---", "", "## TOP 3 NEXT STEPS (MANDATORY)"])

        for i, step in enumerate(self.next_steps[:3], 1):
            lines.append(f"{i}. {step}")

        return "\n".join(lines)


# -----------------------------------------------------------------------------
# DOC 2: SEMANTIC RESEARCH BRIEF (80% Output)
# -----------------------------------------------------------------------------

@dataclass
class ConfidenceAssessment:
    """Overall confidence assessment with reasoning."""
    level: ConfidenceLevel
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level.value,
            "reasoning": self.reasoning,
        }


@dataclass
class SemanticBrief:
    """
    Doc 2: Semantic Research Brief (80% Output)

    Purpose:
    - Deliver deep understanding, not conclusions
    - This is what a strong human researcher would hand off

    Guarantees:
    - Every section cites source identifiers
    - Confidence and uncertainty are visible
    - Skimmable before detailed
    """
    # Semantic Core (What This Is Really About)
    semantic_core: str  # 2-4 sentences describing underlying issue
    semantic_core_based_on: list[str] = field(default_factory=list)  # KeyPoint IDs

    # Key Themes
    themes: list[Theme] = field(default_factory=list)

    # Key Points
    key_points: list[KeyPoint] = field(default_factory=list)

    # Tensions & Contradictions
    tensions: list[Tension] = field(default_factory=list)

    # Gaps & Weaknesses
    gaps: list[Gap] = field(default_factory=list)

    # Confidence Assessment
    confidence: ConfidenceAssessment = field(
        default_factory=lambda: ConfidenceAssessment(level=ConfidenceLevel.MEDIUM)
    )

    # Speculative Observations (Optional, explicitly labeled)
    speculative_observations: list[SpeculativeObservation] = field(default_factory=list)

    # Quality indicators
    triage: TriageLevel = TriageLevel.USABLE
    warnings: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": "semantic_brief",
            "semantic_core": {
                "text": self.semantic_core,
                "based_on": self.semantic_core_based_on,
            },
            "themes": [t.to_dict() for t in self.themes],
            "key_points": [kp.to_dict() for kp in self.key_points],
            "tensions": [t.to_dict() for t in self.tensions],
            "gaps": [g.to_dict() for g in self.gaps],
            "confidence_assessment": self.confidence.to_dict(),
            "speculative_observations": [so.to_dict() for so in self.speculative_observations],
            "triage": self.triage.value,
            "warnings": self.warnings,
            "created_at": self.created_at,
        }

    def to_markdown(self) -> str:
        """Render Semantic Brief as markdown."""
        lines = ["# SEMANTIC RESEARCH BRIEF", ""]

        # Warning banner for degraded output
        if self.triage in (TriageLevel.THIN, TriageLevel.DEGRADED):
            lines.extend([
                "> **Warning:** This brief is based on limited or one-sided sources.",
                "",
            ])

        lines.extend([
            "## SEMANTIC CORE (What This Is Really About)",
            self.semantic_core,
            "",
            "---",
            "",
            "## KEY THEMES",
        ])

        for theme in self.themes:
            lines.extend([
                f"### {theme.theme_id}: {theme.label}",
                f"Description: {theme.description}",
                "",
                "Supporting Key Points:",
            ])
            for kp_id in theme.related_key_points:
                lines.append(f"- {kp_id}")
            lines.append("")

        lines.extend(["---", "", "## KEY POINTS"])

        for kp in self.key_points:
            lines.extend([
                f"- {kp.key_point_id}: {kp.statement}",
                f"  Sources: {', '.join(kp.source_ids)}",
                "",
            ])

        if self.tensions:
            lines.extend(["---", "", "## TENSIONS & CONTRADICTIONS"])
            for t in self.tensions:
                lines.extend([
                    f"- {t.tension_id}:",
                    f"  Description: {t.description}",
                    f"  Involved Points: {', '.join(t.involved_key_points)}",
                    "",
                ])

        lines.extend(["---", "", "## GAPS & WEAKNESSES"])

        for g in self.gaps:
            lines.extend([
                f"- {g.gap_id}:",
                f"  Why it matters: {g.why_expected}",
                f"  What would help: {g.suggested_research_direction or 'Not specified'}",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## CONFIDENCE ASSESSMENT",
            f"Overall Confidence: {self.confidence.level.value.title()}",
            "",
            "Reasoning:",
        ])

        for reason in self.confidence.reasoning:
            lines.append(f"- {reason}")

        if self.speculative_observations:
            lines.extend([
                "",
                "---",
                "",
                "## SPECULATIVE OBSERVATIONS (OPTIONAL)",
                "> These are hypotheses, not conclusions.",
                "",
            ])
            for so in self.speculative_observations:
                lines.extend([
                    f"- {so.text}",
                    f"  Based on: {', '.join(so.based_on)}",
                    "",
                ])

        return "\n".join(lines)

    def passes_minimum_depth(self) -> tuple[bool, list[str]]:
        """
        Check if brief meets minimum depth requirements.

        Returns (passes, list of issues).
        """
        issues = []

        # Minimum: 8+ key points
        if len(self.key_points) < 8:
            issues.append(f"Only {len(self.key_points)} key points (minimum 8)")

        # Minimum: 4+ themes
        if len(self.themes) < 4:
            issues.append(f"Only {len(self.themes)} themes (minimum 4)")

        # Minimum: 5+ gaps
        if len(self.gaps) < 5:
            issues.append(f"Only {len(self.gaps)} gaps (minimum 5)")

        # Each theme must reference ≥2 key points
        for theme in self.themes:
            if len(theme.related_key_points) < 2:
                issues.append(
                    f"Theme {theme.theme_id} has only {len(theme.related_key_points)} "
                    "key points (minimum 2)"
                )

        return len(issues) == 0, issues
