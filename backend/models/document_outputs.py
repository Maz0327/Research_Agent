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
from backend.utils.markdown_helpers import (
    format_internal_id,
    format_id_list,
    escape_pipe,
)


# -----------------------------------------------------------------------------
# MARKDOWN RENDERING HELPERS
# -----------------------------------------------------------------------------

def _status_emoji(status: "SourceStatus") -> str:
    """Return emoji for source status."""
    return {
        "ingested": "✅",
        "partial": "⚠️",
        "failed": "❌",
    }.get(status.value if hasattr(status, "value") else status, "❓")


def _confidence_badge(level: ConfidenceLevel) -> str:
    """Return colored badge for confidence level."""
    return {
        ConfidenceLevel.HIGH: "🟢 HIGH",
        ConfidenceLevel.MEDIUM: "🟡 MEDIUM",
        ConfidenceLevel.LOW: "🔴 LOW",
    }.get(level, "⚪ UNKNOWN")


def _type_icon(source_type: str) -> str:
    """Return icon for source type."""
    return {
        "youtube": "📺",
        "article": "📄",
        "reddit": "💬",
        "text": "📝",
        "screenshot": "🖼️",
    }.get(source_type.lower() if source_type else "", "📎")


def _format_duration(seconds: Optional[int]) -> str:
    """Format duration in human-readable form."""
    if not seconds:
        return ""
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}h {mins}m"
    return f"{mins}m {secs}s"


def _github_alert(alert_type: str, content: str) -> str:
    """
    Generate GitHub-style alert block.

    Types: NOTE, TIP, IMPORTANT, WARNING, CAUTION
    """
    return f"> [!{alert_type.upper()}]\n> {content.replace(chr(10), chr(10) + '> ')}"


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

    # Syndication: set when this source is a republished copy of another one.
    # The entry stays in the ledger; it just stops counting as independent.
    duplicate_of: Optional[str] = None

    # Dense fact statements harvested from this source. The Briefing's coverage
    # gate checks the finished document against these, mechanically.
    harvest_facts: list[str] = field(default_factory=list)

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
            "duplicate_of": self.duplicate_of,
            "harvest_facts": self.harvest_facts,
            "transcript_provenance": (
                self.transcript_provenance.to_dict()
                if self.transcript_provenance else None
            ),
            "failure_reason": self.failure_reason,
        }

    def to_markdown(self) -> str:
        """Render source entry as markdown section with visual hierarchy."""
        # Get emoji indicators
        status_emoji = _status_emoji(self.status)
        type_icon = _type_icon(self.source_type)

        # Type badge with Shorts indicator
        type_label = self.source_type.upper() if self.source_type else "SOURCE"

        # Detect YouTube Shorts by URL pattern or short duration
        is_shorts = False
        if self.source_type == "youtube" and self.url:
            is_shorts = "/shorts/" in self.url
        if self.source_type == "youtube" and self.duration:
            try:
                parts = self.duration.split(":")
                if len(parts) == 2:
                    mins, secs = int(parts[0]), int(parts[1])
                    if mins == 0 and secs <= 60:
                        is_shorts = True
            except (ValueError, IndexError):
                pass

        if is_shorts:
            type_label = "SHORTS"

        # Header with emoji badges
        lines = [
            f"### {self.source_id}: {self.title}",
            "",
            f"> {type_icon} **{type_label}** | {status_emoji} {self.status.value.upper()}",
            "",
        ]

        # Metadata table (more scannable than list)
        meta_rows = []
        if self.creator:
            meta_rows.append(f"| Creator | {escape_pipe(self.creator)} |")
        if self.published:
            meta_rows.append(f"| Published | {escape_pipe(self.published)} |")
        if self.duration:
            meta_rows.append(f"| Duration | {escape_pipe(self.duration)} |")
        if self.word_count:
            meta_rows.append(f"| Words | {self.word_count:,} |")
        meta_rows.append(f"| URL | [{self.url[:50]}...]({self.url}) |" if len(self.url) > 50 else f"| URL | {self.url} |")

        if meta_rows:
            lines.extend([
                "| Field | Value |",
                "|-------|-------|",
            ])
            lines.extend(meta_rows)
            lines.append("")

        # Failure alert (prominent for failed sources)
        if self.status == SourceStatus.FAILED and self.failure_reason:
            lines.extend([
                "",
                _github_alert("CAUTION", f"**Failed:** {self.failure_reason}"),
                "",
            ])

        # Skim summary
        if self.skim_summary:
            lines.extend([
                "",
                "#### 📋 Quick Summary",
                "",
            ])
            for bullet in self.skim_summary:
                lines.append(f"- {bullet}")
            lines.append("")

        # Extracted index (counts only — no internal IDs in display)
        has_extracted = self.claim_ids or self.entity_names or self.theme_ids
        if has_extracted:
            lines.extend(["", "#### 🏷️ Extracted Index", ""])
            if self.claim_ids:
                lines.append(f"- **Claims:** {len(self.claim_ids)} extracted")
            if self.entity_names:
                lines.append(f"- **Entities:** {len(self.entity_names)} identified")
            if self.theme_ids:
                lines.append(f"- **Themes:** {len(self.theme_ids)} identified")
            lines.append("")

        # Transcript provenance (for video sources)
        if self.transcript_provenance:
            tp = self.transcript_provenance
            conf_badge = _confidence_badge(tp.semantic_precision)

            lines.extend([
                "",
                "#### 🎙️ Transcript Quality",
                "",
                f"| Attribute | Value |",
                f"|-----------|-------|",
                f"| Source | **{tp.transcript_source.title()}** |",
                f"| Mode | {tp.gemini_analysis_mode.value} |",
                f"| Quotes | {'✅ Verified' if tp.quote_verification else '⚠️ Limited'} |",
                f"| Confidence | {conf_badge} |",
                "",
            ])

        # Full source text (collapsible)
        if self.full_text:
            lines.extend([
                "",
                "<details>",
                "<summary>📄 <strong>Full Source Text</strong> (click to expand)</summary>",
                "",
                "```",
                self.full_text[:5000] + ("..." if len(self.full_text) > 5000 else ""),
                "```",
                "",
                "</details>",
            ])
        elif self.full_text_unavailable_reason:
            lines.extend([
                "",
                _github_alert("WARNING", f"Text unavailable: {self.full_text_unavailable_reason}"),
                "",
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
        """Render full Source Ledger as markdown with visual hierarchy."""
        # Count sources by status
        ingested = self.ingested_count
        failed = self.failed_count
        partial = sum(1 for s in self.sources if s.status == SourceStatus.PARTIAL)
        total = len(self.sources)

        # Count by type
        type_counts = {}
        for s in self.sources:
            t = s.source_type or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1
        type_summary = ", ".join(f"{_type_icon(k)} {v}" for k, v in type_counts.items())

        lines = [
            "# 📚 SOURCE LEDGER",
            "",
        ]

        # Executive summary card
        lines.extend([
            _github_alert(
                "NOTE",
                f"**Topic:** {self.topic}\n> \n> "
                f"**Sources:** {total} total | {ingested} ✅ | {partial} ⚠️ | {failed} ❌\n> \n> "
                f"**Types:** {type_summary}"
            ),
            "",
        ])

        # Status alert if issues
        if failed > 0:
            lines.extend([
                _github_alert("WARNING", f"{failed} source(s) failed to process. Results may be incomplete."),
                "",
            ])
        elif partial > 0:
            lines.extend([
                _github_alert("NOTE", f"{partial} source(s) partially processed."),
                "",
            ])

        lines.append("---")
        lines.append("")

        # Quick-Copy Source Links (first thing after summary for easy access)
        lines.extend([
            "## 🔗 Sources & Links",
            "",
        ])
        for i, s in enumerate(self.sources, 1):
            type_icon = _type_icon(s.source_type)
            status_emoji = _status_emoji(s.status)
            title_display = s.title[:60] + "..." if len(s.title) > 60 else s.title
            lines.append(f"{i}. {type_icon} **{title_display}** {status_emoji}")
            lines.append(f"   {s.url}")
            lines.append("")

        lines.extend(["---", ""])

        # Table of Contents
        lines.extend([
            "## 📑 Contents",
            "",
            "1. [Sources & Links](#sources--links)",
            "2. [Source Manifest](#source-manifest)",
            "3. [Detailed Analysis](#detailed-source-analysis)",
        ])
        for i, s in enumerate(self.sources, 1):
            safe_anchor = s.source_id.lower().replace("_", "-")
            lines.append(f"   - [{s.source_id}: {s.title[:30]}...](#{safe_anchor}-{s.title[:20].lower().replace(' ', '-')})")
        lines.extend(["", "---", ""])

        # Source manifest with emoji badges
        lines.extend([
            "## 📋 Source Manifest",
            "",
            "| # | ID | Type | Title | URL | Status |",
            "|--:|-----|:----:|-------|-----|:------:|",
        ])

        for i, s in enumerate(self.sources, 1):
            status_emoji = _status_emoji(s.status)
            type_icon = _type_icon(s.source_type)
            title_truncated = s.title[:40] + "..." if len(s.title) > 40 else s.title
            url_display = f"[Link]({s.url})" if s.url else "-"
            lines.append(f"| {i} | `{s.source_id}` | {type_icon} | {escape_pipe(title_truncated)} | {url_display} | {status_emoji} |")

        lines.extend(["", "---", ""])

        # Detailed sources section
        lines.extend([
            "## 🔍 Detailed Source Analysis",
            "",
        ])

        for i, source in enumerate(self.sources, 1):
            lines.append(source.to_markdown())
            if i < len(self.sources):
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


def _source_ref(source_id: str) -> str:
    """Convert source ID to natural reference (SRC_1 -> Source 1)."""
    if not source_id:
        return source_id
    parts = source_id.split("_")
    if len(parts) == 2 and parts[0] == "SRC":
        return f"Source {parts[1]}"
    return format_internal_id(source_id)


def _source_refs(source_ids: list[str]) -> str:
    """Convert list of source IDs to natural references."""
    if not source_ids:
        return ""
    return ", ".join(_source_ref(sid) for sid in source_ids)


@dataclass
class ResearchThread:
    """A thematic thread grouping related key points, gaps, and research directions."""
    theme: Theme  # Parent theme
    key_points: list[KeyPoint] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    research_directions: list[ResearchDirection] = field(default_factory=list)
    # Booster integration (populated when booster merges into threads)
    booster_search_queries: list[dict] = field(default_factory=list)
    booster_research_questions: list[dict] = field(default_factory=list)
    booster_primary_sources: list[dict] = field(default_factory=list)
    booster_missing_perspectives: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme": self.theme.to_dict(),
            "key_points": [kp.to_dict() for kp in self.key_points],
            "gaps": [g.to_dict() for g in self.gaps],
            "research_directions": [rd.to_dict() for rd in self.research_directions],
            "booster_search_queries": self.booster_search_queries,
            "booster_research_questions": self.booster_research_questions,
            "booster_primary_sources": self.booster_primary_sources,
            "booster_missing_perspectives": self.booster_missing_perspectives,
        }

    def generate_action_title(self) -> str:
        """Generate McKinsey-style action title computed from actual data.

        R1: Action titles are programmatic — never LLM-generated.
        They convey the insight in the heading itself.
        """
        source_ids = set()
        for kp in self.key_points:
            source_ids.update(kp.source_ids or [])
        src_count = len(source_ids)
        gap_count = len(self.gaps)
        consensus = "agree" if self.theme.is_consensus else "show"

        if src_count >= 2 and gap_count == 0:
            return (
                f"{self.theme.label} — {src_count} sources {consensus}, "
                f"no gaps identified"
            )
        elif src_count >= 2 and gap_count > 0:
            return (
                f"{self.theme.label} — {src_count} sources {consensus}, "
                f"but {gap_count} gap{'s' if gap_count > 1 else ''} remain"
            )
        elif src_count == 1:
            src_label = (
                _source_refs(self.key_points[0].source_ids[:1])
                if self.key_points and self.key_points[0].source_ids
                else "1 source"
            )
            return (
                f"{self.theme.label} — single-source ({src_label}), "
                f"verify independently"
            )
        else:
            return (
                f"{self.theme.label} — "
                f"{len(self.key_points)} points across sources"
            )

    def generate_evidence_label(self) -> str:
        """Generate evidence-based confidence label with reasoning.

        R4: Labels are computed from source_coverage and is_consensus,
        not generated by LLM. This ensures labels reflect actual evidence.
        """
        source_ids = set()
        for kp in self.key_points:
            source_ids.update(kp.source_ids or [])
        src_count = len(source_ids)

        if self.theme.is_consensus and src_count >= 3:
            refs = _source_refs(list(source_ids)[:4])
            return f"✅ Multi-source confirmed ({refs})"
        elif self.theme.is_consensus and src_count == 2:
            refs = _source_refs(list(source_ids))
            return f"✅ Confirmed by {refs}"
        elif src_count == 1:
            ref = _source_refs(list(source_ids)[:1])
            return f"⚠️ Single-source claim ({ref} only — verify independently)"
        elif len(self.gaps) > len(self.key_points):
            return "🔴 More gaps than findings — thin coverage"
        else:
            refs = _source_refs(list(source_ids)[:3])
            return f"🟡 Partial coverage ({refs})"

    def to_markdown(self) -> str:
        """Render a single research thread as a tree structure."""
        lines = []
        # Theme header
        lines.append(f"### {self.theme.label}")
        lines.append("")
        lines.append(f"> {self.theme.description}")
        if self.theme.is_consensus and self.theme.sources_supporting:
            lines.append(
                f"> *Consensus across {len(self.theme.sources_supporting)} sources "
                f"({_source_refs(self.theme.sources_supporting)})*"
            )
        lines.append("")

        # Key points as tree
        if self.key_points:
            lines.append("**What the sources say:**")
            lines.append("")
            for i, kp in enumerate(self.key_points):
                is_last = (i == len(self.key_points) - 1) and not self.gaps
                connector = "└─" if is_last else "├─"
                lines.append(f"  {connector} {kp.statement}")
                source_refs = _source_refs(kp.source_ids) if kp.source_ids else ""
                if source_refs:
                    indent = "     " if is_last else "  │  "
                    lines.append(f"{indent} *({source_refs})*")
            lines.append("")

        # Gaps under this thread
        if self.gaps:
            lines.append("**Gaps in this thread:**")
            lines.append("")
            for i, gap in enumerate(self.gaps):
                is_last = (i == len(self.gaps) - 1)
                connector = "└─" if is_last else "├─"
                title = gap.label if gap.label else gap.description[:60]
                lines.append(f"  {connector} **{title}**")
                indent = "     " if is_last else "  │  "
                lines.append(f"{indent} Why: {gap.why_expected}")
                # Inline research directions from this gap
                matching_rds = [
                    rd for rd in self.research_directions
                    if rd.what_to_look_for == gap.description
                ]
                for rd in matching_rds:
                    if rd.example_queries:
                        lines.append(f"{indent} Search: `{', '.join(rd.example_queries)}`")
                    if rd.why_it_matters:
                        lines.append(f"{indent} Why it matters: {rd.why_it_matters}")
                # Also check if gap itself has a suggested direction
                if not matching_rds and gap.suggested_research_direction:
                    lines.append(f"{indent} Search: `{gap.suggested_research_direction}`")
            lines.append("")

        # Booster items if present — R13: What/So What/Now What framing, R14: impact badges
        booster_items: list[tuple[str, str, dict]] = []  # (prefix, label, item)
        for item in self.booster_search_queries:
            booster_items.append(("Search", f"`{item.get('query', '')}`", item))
        for item in self.booster_research_questions:
            booster_items.append(("Question", item.get("question", ""), item))
        for item in self.booster_primary_sources:
            booster_items.append(("Find", item.get("description", ""), item))
        for item in self.booster_missing_perspectives:
            booster_items.append(("Missing voice", item.get("description", ""), item))

        if booster_items:
            # R14: Sort by impact level (critical first)
            impact_order = {"critical": 0, "important": 1, "nice_to_have": 2}
            booster_items.sort(
                key=lambda x: impact_order.get(x[2].get("impact_level", "important"), 1)
            )

            lines.append("**Deep Research Directions:**")
            lines.append("")
            for idx, (prefix, label, item) in enumerate(booster_items):
                is_last = idx == len(booster_items) - 1
                connector = "└─" if is_last else "├─"
                indent = "   " if is_last else "│  "

                # R14: Impact badge
                impact_badges = {
                    "critical": "🔴",
                    "important": "🟡",
                    "nice_to_have": "🟢",
                }
                impact = item.get("impact_level", "important")
                badge = impact_badges.get(impact, "⚪")

                lines.append(f"  {connector} {badge} **{prefix}:** {label}")

                # R13: "Why it matters" first (So What)
                why = item.get("why_it_matters") or ""
                if why:
                    lines.append(f"  {indent}  *Why it matters:* {why}")

                # Then action details (Now What)
                action = item.get("search_suggestion") or item.get("query") or ""
                if action and action != label.strip("`"):
                    lines.append(f"  {indent}  *Action:* {action}")

                # Supporting details
                for detail_key, detail_label in [
                    ("purpose", "Purpose"),
                    ("platform_suggestion", "Platform"),
                ]:
                    if item.get(detail_key):
                        lines.append(f"  {indent}  {detail_label}: {item[detail_key]}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class CrossCuttingAnalysis:
    """Cross-source claim analysis surfacing confirmation, conflicts, and single-source risk."""
    confirmed: list[dict] = field(default_factory=list)      # {statement: str, sources: [str]}
    conflicts: list[dict] = field(default_factory=list)       # {description: str, sources_a: [str], sources_b: [str]}
    single_source: list[dict] = field(default_factory=list)   # {statement: str, source: str}

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmed": self.confirmed,
            "conflicts": self.conflicts,
            "single_source": self.single_source,
        }

    def to_markdown(self) -> str:
        """Render cross-cutting analysis with visual bucketing."""
        lines = ["## 🔍 Cross-Cutting Analysis", ""]

        if self.confirmed:
            lines.append("### Confirmed by Multiple Sources")
            lines.append("")
            for item in self.confirmed:
                sources = _source_refs(item.get("sources", []))
                lines.append(f"- ✅ {item.get('statement', '')} *({sources})*")
            lines.append("")

        if self.conflicts:
            lines.append("### Claims in Conflict")
            lines.append("")
            for item in self.conflicts:
                lines.append(f"- ⚡ **{item.get('description', '')}**")
                a_refs = _source_refs(item.get("sources_a", []))
                b_refs = _source_refs(item.get("sources_b", []))
                if a_refs and b_refs:
                    lines.append(f"  Position A: {a_refs} | Position B: {b_refs}")
            lines.append("")

        if self.single_source:
            lines.append("### Single-Source Claims (Higher Risk)")
            lines.append("")
            for item in self.single_source:
                source_ref = _source_ref(item.get("source", ""))
                lines.append(f"- ⚠️ {item.get('statement', '')} *(only {source_ref})*")
            lines.append("")

        if not self.confirmed and not self.conflicts and not self.single_source:
            lines.append("*Cross-cutting analysis requires multiple sources.*")
            lines.append("")

        return "\n".join(lines)


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

    # Thematic Research Threads (groups KPs, gaps, directions by theme)
    research_threads: list[ResearchThread] = field(default_factory=list)
    cross_cutting: Optional[CrossCuttingAnalysis] = None

    # Deep Research Booster Expansion (Phase 7)
    # Added when user triggers booster on completed job
    booster_expansion: Optional[dict[str, Any]] = None  # BoosterOutput as dict
    booster_expansion_md: Optional[str] = None  # Markdown format for display

    def to_dict(self) -> dict[str, Any]:
        result = {
            "document_type": "jump_start",
            "scope_lock": {
                "in": self.scope_in,
                "out": self.scope_out,
            },
            "current_corpus": {
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
            # Thematic threads (new)
            "research_threads": [rt.to_dict() for rt in self.research_threads],
            "cross_cutting": self.cross_cutting.to_dict() if self.cross_cutting else None,
        }

        # Include booster expansion if present (Phase 7)
        if self.booster_expansion:
            result["booster_expansion"] = self.booster_expansion
        if self.booster_expansion_md:
            result["booster_expansion_md"] = self.booster_expansion_md

        return result

    def _generate_tldr(self) -> str:
        """Generate 3-5 sentence executive summary from actual data.

        R3/R15: 100% programmatic — no LLM involvement. All numbers
        come from validated pipeline data.
        """
        thread_count = len(self.research_threads)
        kp_count = len(self.key_points)
        gap_count = len(self.gaps)

        # Sentence 1: What was researched
        s1 = (
            f"Analyzed **{self.source_count} source{'s' if self.source_count != 1 else ''}** "
            f"covering **{thread_count} theme{'s' if thread_count != 1 else ''}** "
            f"with **{kp_count} key finding{'s' if kp_count != 1 else ''}**."
        )

        # Sentence 2: Consensus state
        if self.cross_cutting:
            confirmed = len(self.cross_cutting.confirmed)
            conflicts = len(self.cross_cutting.conflicts)
            if confirmed > 0 and conflicts == 0:
                s2 = (
                    f"Sources broadly agree — **{confirmed} claim{'s' if confirmed != 1 else ''} "
                    f"confirmed** across multiple sources with no active disputes."
                )
            elif confirmed > 0 and conflicts > 0:
                s2 = (
                    f"**{confirmed} claim{'s' if confirmed != 1 else ''} confirmed** "
                    f"across sources, but **{conflicts} active "
                    f"tension{'s' if conflicts != 1 else ''}** where sources disagree."
                )
            else:
                s2 = "Limited cross-source verification — most claims are single-source."
        else:
            s2 = "Single-source analysis — cross-source verification not applicable."

        # Sentence 3: Gaps
        if gap_count > 0:
            s3 = (
                f"**{gap_count} gap{'s' if gap_count != 1 else ''}** identified "
                f"where additional research would strengthen the analysis."
            )
        else:
            s3 = "No significant gaps identified in the current coverage."

        # Sentence 4: Confidence
        conf = _confidence_badge(self.confidence)
        s4 = f"Overall confidence: {conf}."

        return f"{s1}\n\n{s2}\n\n{s3} {s4}"

    def _render_consensus_meter(self) -> str:
        """Render visual consensus meter from cross-cutting analysis data.

        R2: All numbers come from CrossCuttingAnalysis which is built
        from source_coverage data. Pure code rendering, no LLM.
        """
        if not self.cross_cutting:
            return ""

        confirmed = len(self.cross_cutting.confirmed)
        conflicts = len(self.cross_cutting.conflicts)
        single = len(self.cross_cutting.single_source)
        total = confirmed + conflicts + single

        if total == 0:
            return ""

        def bar(count: int, total: int, width: int = 12) -> str:
            filled = round((count / total) * width) if total > 0 else 0
            return "\u2588" * filled + "\u2591" * (width - filled)

        pct_confirmed = round((confirmed / total) * 100) if total > 0 else 0
        pct_conflict = round((conflicts / total) * 100) if total > 0 else 0
        pct_single = round((single / total) * 100) if total > 0 else 0

        lines = [
            "### Source Agreement",
            "",
            "```",
            f"  Confirmed:     {bar(confirmed, total)} {pct_confirmed}% ({confirmed} claims)",
            f"  In Conflict:   {bar(conflicts, total)} {pct_conflict}% ({conflicts} tensions)",
            f"  Single-Source:  {bar(single, total)} {pct_single}% ({single} claims)",
            "```",
            "",
        ]
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render Jump-Start as markdown with progressive disclosure.

        R3: Progressive disclosure — TL;DR → Key Findings → Consensus → Deep Dive
        R1: Action titles on threads (programmatic)
        R2: Consensus meter (programmatic)
        R4: Evidence-strength labels (programmatic)

        Falls back to flat rendering if no research_threads exist.
        """
        conf_badge = _confidence_badge(self.confidence)

        lines = [
            "# RESEARCH BRIEF",
            "",
        ]

        # ── THREAD-BASED PROGRESSIVE DISCLOSURE ──
        if self.research_threads:

            # ── TIER 1: TL;DR ──
            lines.extend([
                "## TL;DR",
                "",
                self._generate_tldr(),
                "",
                "---",
                "",
            ])

            # ── Scope Lock ──
            lines.extend([
                "## Scope",
                "",
            ])
            scope_in_str = ", ".join(self.scope_in) if self.scope_in else "Not specified"
            scope_out_str = ", ".join(self.scope_out) if self.scope_out else "Not specified"
            lines.append(f"**In scope:** {scope_in_str}")
            lines.append("")
            lines.append(f"**Out of scope:** {scope_out_str}")
            lines.extend(["", "---", ""])

            # ── TIER 2: Key Findings (action-titled headlines) ──
            lines.extend([
                "## Key Findings",
                "",
            ])
            for thread in self.research_threads:
                action_title = thread.generate_action_title()
                evidence_label = thread.generate_evidence_label()
                lines.append(f"- **{action_title}** {evidence_label}")
            lines.extend(["", "---", ""])

            # ── TIER 3: Consensus Meter ──
            if self.cross_cutting:
                meter = self._render_consensus_meter()
                if meter:
                    lines.append(meter)
                    lines.extend(["---", ""])

            # ── TIER 4: Deep Dive (full threads) ──
            lines.extend([
                "## Deep Dive",
                "",
            ])
            for thread in self.research_threads:
                lines.append(thread.to_markdown())
                lines.extend(["---", ""])

            # Cross-cutting analysis (detailed view)
            if self.cross_cutting:
                lines.append(self.cross_cutting.to_markdown())
                lines.extend(["---", ""])

        else:
            # ── FLAT FALLBACK (backward compatibility) ──
            lines.extend([
                _github_alert(
                    "NOTE",
                    f"**Sources:** {self.source_count} | "
                    f"**Key Points:** {len(self.key_points)} | "
                    f"**Gaps:** {len(self.gaps)} | "
                    f"**Confidence:** {conf_badge}"
                ),
                "",
                "---",
                "",
            ])

            # Scope Lock
            lines.extend(["## Scope", ""])
            scope_in_str = ", ".join(self.scope_in) if self.scope_in else "Not specified"
            scope_out_str = ", ".join(self.scope_out) if self.scope_out else "Not specified"
            lines.append(f"**In scope:** {scope_in_str}")
            lines.append("")
            lines.append(f"**Out of scope:** {scope_out_str}")
            lines.extend(["", "---", ""])

            # What We Know
            lines.extend(["## What We Know", ""])
            if self.key_points:
                for kp in self.key_points[:10]:
                    source_refs = _source_refs(kp.source_ids) if kp.source_ids else ""
                    suffix = f" *({source_refs})*" if source_refs else ""
                    lines.append(f"- {kp.statement}{suffix}")
                if len(self.key_points) > 10:
                    lines.append(f"- *...and {len(self.key_points) - 10} more key points*")
            else:
                lines.append("*No key points extracted yet.*")
            lines.extend(["", "---", ""])

            # Tensions
            if self.tensions:
                lines.extend(["## Tensions & Disputes", ""])
                for t in self.tensions:
                    title = t.label if t.label else (
                        t.description[:60] + "..." if len(t.description) > 60 else t.description
                    )
                    lines.append(f"- **{title}**")
                lines.extend(["", "---", ""])

            # Gaps
            if self.gaps:
                lines.extend(["## Gaps (What's Missing)", ""])
                for g in self.gaps:
                    title = g.label if g.label else (
                        g.description[:50] + "..." if len(g.description) > 50 else g.description
                    )
                    lines.extend([
                        f"### {title}", "",
                        f"> {g.description}", "",
                        f"**Why it matters:** {g.why_expected}", "",
                    ])
                lines.extend(["---", ""])

            # Research Directions
            if self.research_directions:
                lines.extend(["## Suggested Research Directions", ""])
                for rd in self.research_directions:
                    lines.extend([
                        f"### Priority {rd.priority}: {rd.what_to_look_for}", "",
                    ])
                    if rd.example_queries:
                        lines.append(f"**Search:** `{', '.join(rd.example_queries)}`")
                        lines.append("")
                    if rd.why_it_matters:
                        lines.append(f"**Why:** {rd.why_it_matters}")
                        lines.append("")
                lines.extend(["---", ""])

        # Priority Research Queue (always shown)
        if self.research_directions:
            lines.extend(["## Priority Research Queue", ""])
            for rd in self.research_directions:
                queries = f" — Search: `{', '.join(rd.example_queries)}`" if rd.example_queries else ""
                lines.append(f"- [ ] **Priority {rd.priority}:** {rd.what_to_look_for}{queries}")
                lines.append("")
            lines.extend(["---", ""])

        # Next Steps (prominent)
        lines.extend(["## TOP 3 NEXT STEPS", ""])
        if self.next_steps:
            lines.extend([
                _github_alert("IMPORTANT", "Complete these steps to advance your research:"),
                "",
            ])
            for i, step in enumerate(self.next_steps[:3], 1):
                lines.append(f"**{i}.** {step}")
                lines.append("")
        else:
            lines.append("*No next steps defined.*")

        # Booster expansion if present — only show if threads don't have folded booster items
        has_booster_in_threads = any(
            rt.booster_search_queries or rt.booster_research_questions
            or rt.booster_primary_sources or rt.booster_missing_perspectives
            for rt in self.research_threads
        ) if self.research_threads else False

        if self.booster_expansion_md and not has_booster_in_threads:
            lines.extend([
                "", "---", "",
                "## Deep Research Booster", "",
                self.booster_expansion_md,
            ])

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

    # R6: SCQA opening (Situation-Complication-Question-Answer)
    scqa: Optional[dict] = None  # {situation, complication, question, answer}

    # R7: Theme heatmap data
    source_ids: list[str] = field(default_factory=list)  # Available source IDs
    source_coverage: Optional[dict] = None  # key_point_id → [source_ids]

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
            "scqa": self.scqa,
            "source_ids": self.source_ids,
            "source_coverage": self.source_coverage,
        }

    def _render_theme_heatmap(self) -> str:
        """Render a theme-by-source coverage heatmap.

        R7: Computed from Phase 5 source_coverage data. Pure code rendering.
        Shows which sources cover which themes at a glance.
        """
        if not self.themes or not self.source_ids or not self.source_coverage:
            return ""

        # Build theme → sources mapping
        theme_sources: dict[str, set[str]] = {}
        for theme in self.themes:
            sources_for_theme: set[str] = set()
            for kp_id in (theme.related_key_points or []):
                sources_for_theme.update(self.source_coverage.get(kp_id, []))
            theme_sources[theme.label] = sources_for_theme

        if not theme_sources:
            return ""

        # Build source labels
        src_labels = [_source_ref(sid) for sid in self.source_ids]
        total_sources = len(self.source_ids)

        lines = [
            "### Theme Coverage",
            "",
            "```",
        ]

        # Header row
        header = " " * 25
        for label in src_labels:
            header += label[:8].ljust(10)
        header += "Coverage"
        lines.append(header)

        # Theme rows
        for label, sources in theme_sources.items():
            row = f"  {label[:23].ljust(23)}"
            for sid in self.source_ids:
                row += ("\u2588\u2588" if sid in sources else "\u2591\u2591").ljust(10)
            row += f"({len(sources)}/{total_sources})"
            lines.append(row)

        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Render Semantic Brief as markdown with improved visual hierarchy.

        R5: Governing thought leads (before stats)
        R6: SCQA opening (programmatic, not LLM-generated)
        R7: Theme heatmap (from source_coverage data)
        """
        conf_badge = _confidence_badge(self.confidence.level)
        triage_emoji = {
            TriageLevel.READY: "\U0001f7e2",
            TriageLevel.USABLE: "\U0001f7e1",
            TriageLevel.THIN: "\U0001f7e0",
            TriageLevel.DEGRADED: "\U0001f534",
            TriageLevel.FAILED: "\u26d4",
        }.get(self.triage, "\u2753")

        lines = ["# SEMANTIC RESEARCH BRIEF", ""]

        # R5: GOVERNING THOUGHT — First thing the reader sees
        if self.semantic_core:
            lines.extend([
                _github_alert(
                    "IMPORTANT",
                    f"**Governing Insight:** {self.semantic_core}"
                ),
            ])
            if self.semantic_core_based_on:
                lines.append(f"> *Based on: {format_id_list(self.semantic_core_based_on)}*")
            lines.extend(["", ""])

        # R6: SCQA Opening (if built by document_assembly)
        if self.scqa and isinstance(self.scqa, dict):
            situation = self.scqa.get("situation", "")
            complication = self.scqa.get("complication", "")
            question = self.scqa.get("question", "")
            if situation and complication:
                lines.extend([
                    f"**Situation:** {situation}",
                    "",
                    f"**Complication:** {complication}",
                    "",
                ])
                if question:
                    lines.append(f"**Central Question:** {question}")
                    lines.append("")
                lines.extend(["---", ""])

        # Executive summary card
        lines.extend([
            _github_alert(
                "NOTE",
                f"**Themes:** {len(self.themes)} | "
                f"**Key Points:** {len(self.key_points)} | "
                f"**Tensions:** {len(self.tensions)} | "
                f"**Gaps:** {len(self.gaps)}\n> \n> "
                f"**Quality:** {triage_emoji} {self.triage.value.upper()} | "
                f"**Confidence:** {conf_badge}"
            ),
            "",
        ])

        # Warning banner for degraded output
        if self.triage in (TriageLevel.THIN, TriageLevel.DEGRADED):
            lines.extend([
                _github_alert("WARNING", "This brief is based on limited or one-sided sources. Use with caution."),
                "",
            ])

        if self.warnings:
            for w in self.warnings:
                lines.extend([_github_alert("CAUTION", w), ""])

        lines.extend(["---", ""])

        # Key Themes (with consensus and source attribution)
        lines.extend([
            "## 🏷️ Key Themes",
            "",
        ])
        if self.themes:
            for i, theme in enumerate(self.themes):
                # Consensus badge
                consensus_badge = " ✅ (Consensus)" if theme.is_consensus else ""
                lines.extend([
                    f"### {theme.label}{consensus_badge}",
                    "",
                    f"> {theme.description}",
                    "",
                ])
                # Source attribution
                if theme.sources_supporting:
                    source_refs = _source_refs(theme.sources_supporting)
                    lines.append(f"*Supported by: {source_refs}*")
                    lines.append("")
                lines.append(f"**Related Key Points:** {format_id_list(theme.related_key_points)}")
                lines.append("")
                # Add divider between themes (not after last one)
                if i < len(self.themes) - 1:
                    lines.append("---")
                    lines.append("")
        else:
            lines.append("*No themes identified.*")
        lines.extend(["---", ""])

        # R7: Theme Coverage Heatmap
        heatmap = self._render_theme_heatmap()
        if heatmap:
            lines.append(heatmap)
            lines.extend(["---", ""])

        # Key Points (tabular for scannability)
        lines.extend([
            "## 💡 Key Points",
            "",
            "| ID | Statement | Sources |",
            "|-----|-----------|---------|",
        ])
        for kp in self.key_points[:15]:  # Limit for readability
            stmt = kp.statement[:80] + "..." if len(kp.statement) > 80 else kp.statement
            # Format source IDs to friendly labels
            formatted_sources = [format_internal_id(sid) for sid in kp.source_ids[:3]]
            sources = ", ".join(formatted_sources)
            if len(kp.source_ids) > 3:
                sources += f" +{len(kp.source_ids) - 3}"
            lines.append(f"| {format_internal_id(kp.key_point_id)} | {escape_pipe(stmt)} | {sources} |")
        if len(self.key_points) > 15:
            lines.append(f"| ... | *{len(self.key_points) - 15} more key points* | |")
        lines.extend(["", "---", ""])

        # Tensions
        if self.tensions:
            lines.extend([
                "## ⚡ Tensions & Contradictions",
                "",
            ])
            for i, t in enumerate(self.tensions):
                # Use label if available, otherwise truncate description
                title = t.label if t.label else (t.description[:50] + "..." if len(t.description) > 50 else t.description)
                lines.extend([
                    f"### {format_internal_id(t.tension_id)}: {title}",
                    "",
                    f"> {t.description}",
                    "",
                    f"**Involved:** {format_id_list(t.involved_key_points)}",
                    "",
                ])
                # Add divider between tensions (not after last one)
                if i < len(self.tensions) - 1:
                    lines.append("---")
                    lines.append("")
            lines.append("---")
            lines.append("")

        # Gaps
        lines.extend([
            "## 🕳️ Gaps & Weaknesses",
            "",
        ])
        if self.gaps:
            for i, g in enumerate(self.gaps):
                # Use label if available, otherwise truncate description
                title = g.label if g.label else (g.description[:50] + "..." if len(g.description) > 50 else g.description)
                lines.extend([
                    f"### {format_internal_id(g.gap_id)}: {title}",
                    "",
                    f"> {g.description}",
                    "",
                    f"**Why it matters:** {g.why_expected}",
                    "",
                    f"**Suggested research:** {g.suggested_research_direction or 'Not specified'}",
                    "",
                ])
                # Add divider between gaps (not after last one)
                if i < len(self.gaps) - 1:
                    lines.append("---")
                    lines.append("")
        else:
            lines.append("*No gaps identified.*")
        lines.extend(["---", ""])

        # Confidence Assessment (prominent card)
        lines.extend([
            "## 📈 Confidence Assessment",
            "",
            _github_alert(
                "IMPORTANT",
                f"**Overall Confidence: {conf_badge}**"
            ),
            "",
            "**Reasoning:**",
            "",
        ])
        for reason in self.confidence.reasoning:
            lines.append(f"- {reason}")
        lines.extend(["", "---", ""])

        # Speculative Observations
        if self.speculative_observations:
            lines.extend([
                "## 🔮 Speculative Observations",
                "",
                _github_alert("CAUTION", "These are hypotheses, not conclusions. Treat as starting points for investigation."),
                "",
            ])
            for so in self.speculative_observations:
                lines.extend([
                    f"- **{so.text}**",
                    f"  - *Based on:* {format_id_list(so.based_on)}",
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


# -----------------------------------------------------------------------------
# DOC 3: LEGACY PRODUCER PACKET (Commented out — replaced by producer_models.py)
# The enhanced ProducerPacket, NarrativeAngle, and StructureOption classes
# now live in backend/models/producer_models.py (R1-R17 implementation).
# These legacy classes are preserved here for reference/rollback only.
# If you need gating logic, see LegacyProducerPacketGating below.
# -----------------------------------------------------------------------------

# @dataclass
# class NarrativeAngle:
#     """A potential narrative angle for content production."""
#     angle_id: str
#     description: str
#     hook: str
#     based_on: list[str] = field(default_factory=list)
#     confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
#
#     def to_dict(self) -> dict[str, Any]:
#         return {
#             "angle_id": self.angle_id,
#             "description": self.description,
#             "hook": self.hook,
#             "based_on": self.based_on,
#             "confidence": self.confidence.value,
#         }
#
#
# @dataclass
# class StructureOption:
#     """A structure option for organizing the content."""
#     structure_type: str
#     description: str
#     act_breakdown: list[str] = field(default_factory=list)
#     why_it_works: str = ""
#
#     def to_dict(self) -> dict[str, Any]:
#         return {
#             "structure_type": self.structure_type,
#             "description": self.description,
#             "act_breakdown": self.act_breakdown,
#             "why_it_works": self.why_it_works,
#         }
#
#
# @dataclass
# class ProducerPacket:
#     """Doc 3: Producer Packet (Optional Creative Layer) — LEGACY VERSION"""
#     job_id: str
#     story_core: str
#     story_core_based_on: list[str] = field(default_factory=list)
#     narrative_angles: list[NarrativeAngle] = field(default_factory=list)
#     structure_options: list[StructureOption] = field(default_factory=list)
#     opening_hooks: list[str] = field(default_factory=list)
#     title_concepts: list[str] = field(default_factory=list)
#     thumbnail_concepts: list[str] = field(default_factory=list)
#     call_to_action: list[str] = field(default_factory=list)
#     sensitivity_notes: list[str] = field(default_factory=list)
#     risk_assessment: str = ""
#     legal_considerations: list[str] = field(default_factory=list)
#     source_count: int = 0
#     high_confidence_sources: int = 0
#     verification_rate: float = 0.0
#     triage: TriageLevel = TriageLevel.USABLE
#     warnings: list[str] = field(default_factory=list)
#     created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
#     ... (to_dict, to_markdown, meets_gating_requirements methods omitted)


class LegacyProducerPacketGating:
    """
    Extracted gating logic from the legacy ProducerPacket.

    Used by test_validation_stages.py to test Doc 3 gating requirements
    without depending on the commented-out legacy dataclass.
    """

    def __init__(self, job_id: str = "", story_core: str = "",
                 source_count: int = 0, high_confidence_sources: int = 0,
                 **kwargs):
        self.job_id = job_id
        self.story_core = story_core
        self.source_count = source_count
        self.high_confidence_sources = high_confidence_sources

    def meets_gating_requirements(self) -> tuple[bool, list[str]]:
        """
        Check if the packet meets gating requirements.

        Per RASS 3.4:
        - 4+ sources
        - At least 1 high-confidence source

        Returns (passes, list of failed requirements).
        """
        failed = []

        if self.source_count < 4:
            failed.append(f"Only {self.source_count} sources (minimum 4)")

        if self.high_confidence_sources < 1:
            failed.append("No high-confidence sources (minimum 1)")

        return len(failed) == 0, failed


# -----------------------------------------------------------------------------
# ADDENDUM & CROSS-REFERENCE (Phase 6: Evolving Jobs)
# -----------------------------------------------------------------------------

@dataclass
class CrossReferenceNotes:
    """
    Connections between new and original content.

    When new sources are added to a completed job, this structure
    tracks how the new content relates to existing analysis.

    Per EXTENDED_SPECIFICATIONS.md Part 2:
    - supports: New content that reinforces existing themes/points
    - contradicts: New content that conflicts with existing points
    - new_tensions: Tensions created by cross-source comparison
    - new_gaps: Additional gaps identified from new perspective
    """
    supports: list[dict] = field(default_factory=list)
    # Format: {"new_id": "KP_5", "supports_id": "THEME_1", "reason": "..."}

    contradicts: list[dict] = field(default_factory=list)
    # Format: {"new_id": "KP_6", "contradicts_id": "KP_2", "reason": "..."}

    new_tensions: list[Tension] = field(default_factory=list)
    new_gaps: list[Gap] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supports": self.supports,
            "contradicts": self.contradicts,
            "new_tensions": [t.to_dict() for t in self.new_tensions],
            "new_gaps": [g.to_dict() for g in self.new_gaps],
        }

    def to_markdown(self) -> str:
        """Render cross-reference notes as markdown."""
        lines = ["## Cross-Reference Notes", ""]

        if self.supports:
            lines.append("### Supports Existing")
            for s in self.supports:
                lines.append(f"- {s['new_id']} **supports** {s['supports_id']}")
                if s.get("reason"):
                    lines.append(f"  Reason: {s['reason']}")
            lines.append("")

        if self.contradicts:
            lines.append("### Contradictions")
            for c in self.contradicts:
                lines.append(f"- {c['new_id']} **contradicts** {c['contradicts_id']}")
                if c.get("reason"):
                    lines.append(f"  Reason: {c['reason']}")
            lines.append("")

        if self.new_tensions:
            lines.append("### New Tensions (Cross-Source)")
            for t in self.new_tensions:
                lines.append(f"- {t.tension_id}: {t.description}")
            lines.append("")

        if self.new_gaps:
            lines.append("### New Gaps Identified")
            for g in self.new_gaps:
                lines.append(f"- {g.gap_id}: {g.description}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class AddendumSection:
    """
    Content added when new sources are added to a completed job.

    Per EXTENDED_SPECIFICATIONS.md Part 2:
    - Original document content is preserved (frozen)
    - New content is appended in a clearly marked addendum section
    - Cross-references link new content to original analysis

    This structure holds the new content for all three document types.
    """
    added_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_ids: list[str] = field(default_factory=list)

    # Doc 0: New source entries
    new_sources: list[SourceEntry] = field(default_factory=list)

    # Doc 1: New directions/gaps from new sources
    new_directions: list[ResearchDirection] = field(default_factory=list)
    new_gaps: list[Gap] = field(default_factory=list)

    # Doc 2: New semantic content
    new_key_points: list[KeyPoint] = field(default_factory=list)
    new_themes: list[Theme] = field(default_factory=list)
    new_tensions: list[Tension] = field(default_factory=list)

    # Cross-reference to original content
    cross_reference: Optional[CrossReferenceNotes] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_at": self.added_at,
            "source_ids": self.source_ids,
            "new_sources": [s.to_dict() for s in self.new_sources],
            "new_directions": [d.to_dict() for d in self.new_directions],
            "new_gaps": [g.to_dict() for g in self.new_gaps],
            "new_key_points": [kp.to_dict() for kp in self.new_key_points],
            "new_themes": [t.to_dict() for t in self.new_themes],
            "new_tensions": [t.to_dict() for t in self.new_tensions],
            "cross_reference": self.cross_reference.to_dict() if self.cross_reference else None,
        }

    def to_markdown(self) -> str:
        """Render addendum section as markdown."""
        lines = [
            "",
            "---",
            f"## Addendum: Sources Added {self.added_at[:10]}",
            f"*Sources: {', '.join(self.source_ids)}*",
            "",
        ]

        if self.new_key_points:
            lines.append("### New Key Points")
            for kp in self.new_key_points:
                lines.append(f"- {kp.key_point_id}: {kp.statement} [{', '.join(kp.source_ids)}]")
            lines.append("")

        if self.new_themes:
            lines.append("### New Themes")
            for t in self.new_themes:
                lines.append(f"- {t.theme_id}: {t.label}")
                lines.append(f"  {t.description}")
            lines.append("")

        if self.new_tensions:
            lines.append("### New Tensions")
            for t in self.new_tensions:
                lines.append(f"- {t.tension_id}: {t.description}")
            lines.append("")

        if self.new_directions:
            lines.append("### New Research Directions")
            for d in self.new_directions:
                lines.append(f"- Priority {d.priority}: {d.what_to_look_for}")
            lines.append("")

        if self.new_gaps:
            lines.append("### New Gaps Identified")
            for g in self.new_gaps:
                lines.append(f"- {g.gap_id}: {g.description}")
            lines.append("")

        if self.cross_reference:
            lines.append(self.cross_reference.to_markdown())

        return "\n".join(lines)
