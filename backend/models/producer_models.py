"""Producer Packet models (Doc 3) - Creative interpretation layer.

Based on: docs/authoritative/spec/Document_Output_Format.md (Doc 3 schema)
Phase: 8

Doc 3 is an OPTIONAL creative interpretation layer that:
- Provides narrative angles and story options
- Suggests hooks, titles, thumbnails
- Assesses risks and suggests interviews
- Is explicitly labeled as creative interpretation
- Does NOT modify Doc 0/1/2
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from backend.utils.markdown_helpers import (
    github_alert,
    sensitivity_icon,
    section_header,
    creative_notice_block,
    escape_pipe,
)


class HookType(str, Enum):
    """Types of opening hooks."""
    COLD_OPEN = "cold_open"
    PROVOCATIVE_QUESTION = "provocative_question"
    SURPRISING_FACT = "surprising_fact"
    PERSONAL_STORY = "personal_story"
    SCENE_SETTING = "scene_setting"


class StructureType(str, Enum):
    """Documentary structure types."""
    CHRONOLOGICAL = "chronological"
    THEMATIC = "thematic"
    MYSTERY_REVEAL = "mystery_reveal"
    COMPARE_CONTRAST = "compare_contrast"
    PROBLEM_SOLUTION = "problem_solution"


class TitleTone(str, Enum):
    """Title tone options."""
    SERIOUS = "serious"
    PROVOCATIVE = "provocative"
    CURIOUS = "curious"
    URGENT = "urgent"


class SensitivityLevel(str, Enum):
    """Content sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class StoryCore:
    """Central narrative elements."""
    central_question: str
    one_sentence_pitch: str
    why_this_matters: str
    target_audience: str
    emotional_arc: str

    def to_dict(self) -> dict:
        return {
            "central_question": self.central_question,
            "one_sentence_pitch": self.one_sentence_pitch,
            "why_this_matters": self.why_this_matters,
            "target_audience": self.target_audience,
            "emotional_arc": self.emotional_arc,
        }


@dataclass
class NarrativeAngle:
    """A potential narrative approach."""
    angle_id: str
    title: str
    description: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    best_for: str = ""
    key_sources: list[str] = field(default_factory=list)
    confidence: str = ""  # "strong", "moderate", or "speculative"

    def to_dict(self) -> dict:
        return {
            "angle_id": self.angle_id,
            "title": self.title,
            "description": self.description,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "best_for": self.best_for,
            "key_sources": self.key_sources,
            "confidence": self.confidence,
        }


@dataclass
class OpeningHook:
    """An opening hook option."""
    hook_type: HookType
    content: str
    tone: str
    source_basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hook_type": self.hook_type.value,
            "content": self.content,
            "tone": self.tone,
            "source_basis": self.source_basis,
        }


@dataclass
class StructureOption:
    """A documentary structure option."""
    structure_type: StructureType
    description: str
    section_breakdown: list[str] = field(default_factory=list)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "structure_type": self.structure_type.value,
            "description": self.description,
            "section_breakdown": self.section_breakdown,
            "pros": self.pros,
            "cons": self.cons,
        }


@dataclass
class KeyMoment:
    """A compelling moment from sources."""
    moment: str
    source_id: str
    timestamp: Optional[str] = None
    why_compelling: str = ""
    potential_use: str = ""

    def to_dict(self) -> dict:
        return {
            "moment": self.moment,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "why_compelling": self.why_compelling,
            "potential_use": self.potential_use,
        }


@dataclass
class TitleOption:
    """A title option."""
    title: str
    subtitle: Optional[str] = None
    tone: TitleTone = TitleTone.SERIOUS
    seo_considerations: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "tone": self.tone.value,
            "seo_considerations": self.seo_considerations,
        }


@dataclass
class ThumbnailConcept:
    """A thumbnail concept."""
    concept: str
    visual_elements: list[str] = field(default_factory=list)
    text_overlay: Optional[str] = None
    emotional_appeal: str = ""

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "visual_elements": self.visual_elements,
            "text_overlay": self.text_overlay,
            "emotional_appeal": self.emotional_appeal,
        }


@dataclass
class RiskAssessment:
    """Content risk assessment."""
    sensitivity_level: SensitivityLevel
    potential_issues: list[str] = field(default_factory=list)
    mitigation_suggestions: list[str] = field(default_factory=list)
    legal_considerations: list[str] = field(default_factory=list)
    ethical_considerations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sensitivity_level": self.sensitivity_level.value,
            "potential_issues": self.potential_issues,
            "mitigation_suggestions": self.mitigation_suggestions,
            "legal_considerations": self.legal_considerations,
            "ethical_considerations": self.ethical_considerations,
        }


@dataclass
class InterviewCandidate:
    """A person to potentially interview."""
    name: str
    role: str
    why_relevant: str
    potential_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "why_relevant": self.why_relevant,
            "potential_questions": self.potential_questions,
        }


@dataclass
class InterviewSuggestions:
    """Interview suggestions."""
    people_to_contact: list[InterviewCandidate] = field(default_factory=list)
    expert_perspectives_needed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "people_to_contact": [p.to_dict() for p in self.people_to_contact],
            "expert_perspectives_needed": self.expert_perspectives_needed,
        }


@dataclass
class BRollSuggestion:
    """B-roll footage suggestion."""
    description: str
    purpose: str
    source_options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "purpose": self.purpose,
            "source_options": self.source_options,
        }


@dataclass
class StoryLandscape:
    """Story landscape analysis — R8: competitive framing with specifics.

    Three categories:
    - saturated: Angles already done by many. Each has: angle, who_covered_it, why_avoid, trend
    - emerging: Angles gaining traction. Each has: angle, evidence, window, trend
    - untold: Angles nobody has covered. Each has: angle, why_untold, risk, trend
    """
    saturated_angles: list[dict] = field(default_factory=list)
    emerging_angles: list[dict] = field(default_factory=list)
    untold_angles: list[dict] = field(default_factory=list)
    landscape_summary: str = ""
    # Backward compatibility
    common_angles: list[str] = field(default_factory=list)
    fresh_angles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "saturated_angles": self.saturated_angles,
            "emerging_angles": self.emerging_angles,
            "untold_angles": self.untold_angles,
            "landscape_summary": self.landscape_summary,
            "common_angles": self.common_angles,
            "fresh_angles": self.fresh_angles,
        }


# ---------------------------------------------------------------------------
# Production Blueprint dataclasses (P5)
# ---------------------------------------------------------------------------


class ClipType(str, Enum):
    """Clip type classification for clip sheet."""
    THIRD_PARTY = "third_party"       # ✅ Usable third-party footage
    ORIGINAL_SKIP = "original_skip"   # ❌ Original creator content — skip
    NEEDS_REVIEW = "needs_review"     # ⚠️ Unclear rights — review needed


@dataclass
class Beat:
    """A single beat within an act."""
    beat_number: int
    description: str
    duration_note: str = ""           # e.g. "2:00 - 5:00" or "~3 min"
    source_references: list[str] = field(default_factory=list)
    notes: str = ""
    # R9: Asset requirements per beat
    required_assets: list[str] = field(default_factory=list)  # What you need (footage, graphics, etc.)
    asset_difficulty: str = ""  # "easy" (stock), "medium" (license), "hard" (original production)

    def to_dict(self) -> dict:
        return {
            "beat_number": self.beat_number,
            "description": self.description,
            "duration_note": self.duration_note,
            "source_references": self.source_references,
            "notes": self.notes,
            "required_assets": self.required_assets,
            "asset_difficulty": self.asset_difficulty,
        }


@dataclass
class Act:
    """An act in the documentary structure."""
    act_number: int
    title: str
    purpose: str = ""
    beats: list[Beat] = field(default_factory=list)
    approximate_duration: str = ""    # e.g. "0:00 - 5:00"

    def to_dict(self) -> dict:
        return {
            "act_number": self.act_number,
            "title": self.title,
            "purpose": self.purpose,
            "beats": [b.to_dict() for b in self.beats],
            "approximate_duration": self.approximate_duration,
        }


@dataclass
class ActStructure:
    """Full act structure for the documentary."""
    acts: list[Act] = field(default_factory=list)
    total_estimated_duration: str = ""
    structure_rationale: str = ""

    def to_dict(self) -> dict:
        return {
            "acts": [a.to_dict() for a in self.acts],
            "total_estimated_duration": self.total_estimated_duration,
            "structure_rationale": self.structure_rationale,
        }


@dataclass
class ClipSheetEntry:
    """An entry in the clip sheet."""
    description: str = ""
    source_id: str = ""
    timestamp: str = ""
    clip_type: ClipType = ClipType.NEEDS_REVIEW
    clip_type_reasoning: str = ""
    suggested_use: str = ""           # Which act/beat
    legal_notes: str = ""
    # R10: Clip scoring
    relevance_score: int = 0          # 1-5 relevance to recommended angle
    suggested_beat: str = ""          # Which beat this fits (e.g. "Act 1, Beat 2")
    alternative_if_unavailable: str = ""  # Fallback search term

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "source_id": self.source_id,
            "timestamp": self.timestamp,
            "clip_type": self.clip_type.value,
            "clip_type_reasoning": self.clip_type_reasoning,
            "suggested_use": self.suggested_use,
            "legal_notes": self.legal_notes,
            "relevance_score": self.relevance_score,
            "suggested_beat": self.suggested_beat,
            "alternative_if_unavailable": self.alternative_if_unavailable,
        }


@dataclass
class EnhancedBRollSuggestion:
    """Enhanced B-roll suggestion with search queries."""
    description: str
    purpose: str = ""
    search_queries: list[str] = field(default_factory=list)
    visual_style: str = ""
    duration_needed: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "purpose": self.purpose,
            "search_queries": self.search_queries,
            "visual_style": self.visual_style,
            "duration_needed": self.duration_needed,
        }


@dataclass
class ProductionNotes:
    """Production guidance notes."""
    audio_mood: str = ""
    visual_style: str = ""
    legal_flags: list[str] = field(default_factory=list)
    accessibility_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "audio_mood": self.audio_mood,
            "visual_style": self.visual_style,
            "legal_flags": self.legal_flags,
            "accessibility_notes": self.accessibility_notes,
        }


@dataclass
class ProductionBlueprint:
    """Full production blueprint — shooting script + production guide."""
    selected_angle_id: str = ""
    selected_angle_title: str = ""
    act_structure: Optional[ActStructure] = None
    clip_sheet: list[ClipSheetEntry] = field(default_factory=list)
    enhanced_b_roll: list[EnhancedBRollSuggestion] = field(default_factory=list)
    production_notes: Optional[ProductionNotes] = None

    def to_dict(self) -> dict:
        return {
            "selected_angle_id": self.selected_angle_id,
            "selected_angle_title": self.selected_angle_title,
            "act_structure": self.act_structure.to_dict() if self.act_structure else None,
            "clip_sheet": [c.to_dict() for c in self.clip_sheet],
            "enhanced_b_roll": [b.to_dict() for b in self.enhanced_b_roll],
            "production_notes": self.production_notes.to_dict() if self.production_notes else None,
        }

    def to_markdown(self) -> str:
        """Render production blueprint as markdown."""
        lines = [
            section_header("Production Blueprint", "🎬", 2),
            "",
        ]

        if self.selected_angle_title:
            lines.extend([
                github_alert(
                    "NOTE",
                    f"**Selected Angle:** {self.selected_angle_id}: {self.selected_angle_title}"
                ),
                "",
            ])

        # Act Structure
        if self.act_structure and self.act_structure.acts:
            lines.extend([
                "### 🎭 Act Structure",
                "",
            ])
            if self.act_structure.structure_rationale:
                lines.extend([
                    f"> {self.act_structure.structure_rationale}",
                    "",
                ])
            if self.act_structure.total_estimated_duration:
                lines.append(
                    f"**Estimated Duration:** {self.act_structure.total_estimated_duration}"
                )
                lines.append("")

            for act in self.act_structure.acts:
                act_label = f"ACT {act.act_number}: {act.title.upper()}"
                if act.approximate_duration:
                    act_label += f" [{act.approximate_duration}]"
                lines.extend([
                    f"#### {act_label}",
                    "",
                ])
                if act.purpose:
                    lines.append(f"*{act.purpose}*")
                    lines.append("")

                for beat in act.beats:
                    # Use tree connectors
                    is_last = beat == act.beats[-1]
                    connector = "└─" if is_last else "├─"
                    lines.append(
                        f"{connector} **Beat {beat.beat_number}:** {beat.description}"
                    )
                    indent = "   " if is_last else "│  "
                    if beat.duration_note:
                        lines.append(f"{indent} ⏱️ {beat.duration_note}")
                    if beat.source_references:
                        refs = ", ".join(beat.source_references)
                        lines.append(f"{indent} 📎 Sources: {refs}")
                    # R9: Asset requirements
                    if beat.required_assets:
                        difficulty_badge = {
                            "easy": "🟢",
                            "medium": "🟡",
                            "hard": "🔴",
                        }.get(beat.asset_difficulty.lower(), "⚪") if beat.asset_difficulty else "⚪"
                        assets_str = ", ".join(beat.required_assets)
                        lines.append(f"{indent} 🎬 Assets {difficulty_badge}: {assets_str}")
                    if beat.notes:
                        lines.append(f"{indent} 💡 {beat.notes}")
                lines.append("")
            lines.extend(["---", ""])

        # Clip Sheet — R10: with relevance scores and beat placement
        if self.clip_sheet:
            # Sort by relevance score (highest first)
            sorted_clips = sorted(
                self.clip_sheet,
                key=lambda c: c.relevance_score,
                reverse=True,
            )
            lines.extend([
                "### 🎞️ Clip Sheet",
                "",
                "| Type | Rel. | Description | Source | Beat | Timestamp | Legal |",
                "|------|------|-------------|--------|------|-----------|-------|",
            ])
            for clip in sorted_clips:
                type_icon_map = {
                    ClipType.THIRD_PARTY: "✅",
                    ClipType.ORIGINAL_SKIP: "❌",
                    ClipType.NEEDS_REVIEW: "⚠️",
                }
                icon = type_icon_map.get(clip.clip_type, "❓")
                # R10: Relevance score as stars (capped at 5)
                capped_score = min(clip.relevance_score, 5) if clip.relevance_score > 0 else 0
                rel_stars = "⭐" * capped_score if capped_score > 0 else "—"
                desc = clip.description[:45] + "..." if len(clip.description) > 45 else clip.description
                ts = clip.timestamp or "—"
                beat = clip.suggested_beat or "—"
                legal = clip.legal_notes[:25] + "..." if clip.legal_notes and len(clip.legal_notes) > 25 else (clip.legal_notes or "—")
                lines.append(
                    f"| {icon} | {rel_stars} | {escape_pipe(desc)} | `{clip.source_id}` | {escape_pipe(beat)} | {ts} | {escape_pipe(legal)} |"
                )

            # R10: Show alternatives for high-relevance clips
            high_rel_with_alt = [
                c for c in sorted_clips
                if c.relevance_score >= 4 and c.alternative_if_unavailable
            ]
            if high_rel_with_alt:
                lines.extend(["", "**Fallback alternatives for key clips:**"])
                for clip in high_rel_with_alt:
                    desc_short = clip.description[:40] + "..." if len(clip.description) > 40 else clip.description
                    lines.append(
                        f"- If *{desc_short}* unavailable → search: `{clip.alternative_if_unavailable}`"
                    )

            lines.extend(["", "---", ""])

        # Enhanced B-Roll
        if self.enhanced_b_roll:
            lines.extend([
                "### 🛒 B-Roll Shopping List",
                "",
            ])
            for i, broll in enumerate(self.enhanced_b_roll, 1):
                lines.extend([
                    f"**{i}. {broll.description}**",
                ])
                if broll.purpose:
                    lines.append(f"- Purpose: {broll.purpose}")
                if broll.search_queries:
                    for q in broll.search_queries:
                        lines.append(f"- 🔍 Search: `{q}`")
                if broll.visual_style:
                    lines.append(f"- 🎨 Style: {broll.visual_style}")
                if broll.duration_needed:
                    lines.append(f"- ⏱️ Duration: {broll.duration_needed}")
                lines.append("")
            lines.extend(["---", ""])

        # Production Notes
        if self.production_notes:
            lines.extend([
                "### 📋 Production Notes",
                "",
            ])
            pn = self.production_notes
            if pn.audio_mood:
                lines.append(f"- 🎵 **Audio:** {pn.audio_mood}")
            if pn.visual_style:
                lines.append(f"- 🎨 **Visual:** {pn.visual_style}")
            if pn.legal_flags:
                lines.append("- ⚖️ **Legal Flags:**")
                for flag in pn.legal_flags:
                    lines.append(f"  - {flag}")
            if pn.accessibility_notes:
                lines.append("- ♿ **Accessibility:**")
                for note in pn.accessibility_notes:
                    lines.append(f"  - {note}")
            lines.append("")

        return "\n".join(lines)


CREATIVE_INTERPRETATION_NOTICE = (
    "This document contains creative interpretation and narrative suggestions. "
    "It is not factual research output. All content should be verified against Doc 0/1/2."
)


@dataclass
class ProducerPacket:
    """Doc 3 - Producer Packet for creative interpretation."""
    job_id: str
    generated_at: str  # ISO-8601

    # Story Core (required)
    story_core: StoryCore

    # Story Landscape & Recommendation
    story_landscape: Optional[StoryLandscape] = None
    recommended_angle_id: Optional[str] = None
    recommendation_reasoning: str = ""

    # Narrative Options (required, min 2)
    narrative_angles: list[NarrativeAngle] = field(default_factory=list)
    opening_hooks: list[OpeningHook] = field(default_factory=list)
    structure_options: list[StructureOption] = field(default_factory=list)

    # Creative Elements
    key_moments: list[KeyMoment] = field(default_factory=list)
    title_options: list[TitleOption] = field(default_factory=list)
    thumbnail_concepts: list[ThumbnailConcept] = field(default_factory=list)

    # Risk & Context (required)
    risk_assessment: Optional[RiskAssessment] = None
    interview_suggestions: Optional[InterviewSuggestions] = None
    b_roll_suggestions: list[BRollSuggestion] = field(default_factory=list)

    # Production Blueprint (optional — Stage 5)
    production_blueprint: Optional[ProductionBlueprint] = None

    # Decision Brief extensions (R11)
    risk_if_wrong: str = ""
    pivot_angle_id: Optional[str] = None
    pivot_reasoning: str = ""
    decision_criteria: list[str] = field(default_factory=list)

    # Quality Check (R12 — Stage 6 self-critique)
    quality_score: Optional[int] = None  # 0-100
    quality_issues: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": "producer_packet",
            "document_version": "2.0",
            "job_id": self.job_id,
            "generated_at": self.generated_at,
            "creative_interpretation_notice": CREATIVE_INTERPRETATION_NOTICE,
            "story_core": self.story_core.to_dict(),
            "story_landscape": self.story_landscape.to_dict() if self.story_landscape else None,
            "recommended_angle_id": self.recommended_angle_id,
            "recommendation_reasoning": self.recommendation_reasoning,
            "narrative_angles": [a.to_dict() for a in self.narrative_angles],
            "opening_hooks": [h.to_dict() for h in self.opening_hooks],
            "structure_options": [s.to_dict() for s in self.structure_options],
            "key_moments": [m.to_dict() for m in self.key_moments],
            "title_options": [t.to_dict() for t in self.title_options],
            "thumbnail_concepts": [c.to_dict() for c in self.thumbnail_concepts],
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "interview_suggestions": self.interview_suggestions.to_dict() if self.interview_suggestions else None,
            "b_roll_suggestions": [b.to_dict() for b in self.b_roll_suggestions],
            "production_blueprint": self.production_blueprint.to_dict() if self.production_blueprint else None,
            "risk_if_wrong": self.risk_if_wrong,
            "pivot_angle_id": self.pivot_angle_id,
            "pivot_reasoning": self.pivot_reasoning,
            "decision_criteria": self.decision_criteria,
            "quality_score": self.quality_score,
            "quality_issues": self.quality_issues,
        }

    def to_markdown(self) -> str:
        """Generate markdown representation with improved formatting."""
        # Count sections for summary
        section_counts = {
            "angles": len(self.narrative_angles),
            "hooks": len(self.opening_hooks),
            "structures": len(self.structure_options),
            "titles": len(self.title_options),
            "moments": len(self.key_moments),
            "thumbnails": len(self.thumbnail_concepts),
        }

        lines = [
            section_header("Producer Packet", "🎬", 1),
            "",
        ]

        # Executive summary
        lines.extend([
            github_alert(
                "NOTE",
                f"**Job:** {self.job_id} | **Generated:** {self.generated_at[:10]}\n> \n> "
                f"**Sections:** {section_counts['angles']} angles | "
                f"{section_counts['hooks']} hooks | "
                f"{section_counts['titles']} titles | "
                f"{section_counts['moments']} moments"
            ),
            "",
        ])

        # Creative interpretation notice
        lines.extend([
            creative_notice_block(),
            "",
            "---",
            "",
        ])

        # Story Core
        lines.extend([
            section_header("Story Core", "🎯", 2),
            "",
            "| Element | Content |",
            "|---------|---------|",
            f"| **Central Question** | {escape_pipe(self.story_core.central_question)} |",
            f"| **One-Sentence Pitch** | {escape_pipe(self.story_core.one_sentence_pitch)} |",
            f"| **Why This Matters** | {escape_pipe(self.story_core.why_this_matters)} |",
            f"| **Target Audience** | {escape_pipe(self.story_core.target_audience)} |",
            f"| **Emotional Arc** | {escape_pipe(self.story_core.emotional_arc)} |",
            "",
            "---",
            "",
        ])

        # Story Landscape (before angles — sets context) — R8: structured categories
        if self.story_landscape:
            lines.extend([
                section_header("Story Landscape", "🗺️", 2),
                "",
            ])
            if self.story_landscape.landscape_summary:
                lines.extend([
                    f"> {self.story_landscape.landscape_summary}",
                    "",
                ])

            # R8: Saturated angles with specifics
            if self.story_landscape.saturated_angles:
                lines.extend([
                    "### 🔴 Saturated Angles (Avoid or Differentiate)",
                    "",
                ])
                for sa in self.story_landscape.saturated_angles:
                    if isinstance(sa, dict):
                        trend_badge = "📉" if sa.get("trend") == "declining" else "📊"
                        lines.append(f"- {trend_badge} **{sa.get('angle', '')}**")
                        if sa.get("who_covered_it"):
                            lines.append(f"  - *Covered by:* {sa['who_covered_it']}")
                        if sa.get("why_avoid"):
                            lines.append(f"  - *Why avoid:* {sa['why_avoid']}")
                    else:
                        lines.append(f"- ❌ {sa}")
                lines.append("")

            # R8: Emerging angles
            if self.story_landscape.emerging_angles:
                lines.extend([
                    "### 🟡 Emerging Angles (Rising Traction)",
                    "",
                ])
                for ea in self.story_landscape.emerging_angles:
                    if isinstance(ea, dict):
                        window_badge = "⏰" if ea.get("window") == "narrow" else "🕐"
                        lines.append(f"- {window_badge} **{ea.get('angle', '')}**")
                        if ea.get("evidence"):
                            lines.append(f"  - *Evidence:* {ea['evidence']}")
                        if ea.get("window"):
                            lines.append(f"  - *Window:* {ea['window']}")
                    else:
                        lines.append(f"- 📈 {ea}")
                lines.append("")

            # R8: Untold angles
            if self.story_landscape.untold_angles:
                lines.extend([
                    "### 🟢 Untold Angles (Uncharted Territory)",
                    "",
                ])
                for ua in self.story_landscape.untold_angles:
                    if isinstance(ua, dict):
                        lines.append(f"- 💎 **{ua.get('angle', '')}**")
                        if ua.get("why_untold"):
                            lines.append(f"  - *Why untold:* {ua['why_untold']}")
                        if ua.get("risk"):
                            lines.append(f"  - *Risk:* {ua['risk']}")
                    else:
                        lines.append(f"- 💡 {ua}")
                lines.append("")

            # Backward compat: old format with common/fresh angles
            if not self.story_landscape.saturated_angles and self.story_landscape.common_angles:
                lines.extend([
                    "### ⚠️ Common Angles (Saturated — Avoid)",
                    "",
                ])
                for ca in self.story_landscape.common_angles:
                    lines.append(f"- ❌ {ca}")
                lines.append("")
            if not self.story_landscape.untold_angles and self.story_landscape.fresh_angles:
                lines.extend([
                    "### ✨ Fresh Angles (Untold — Consider)",
                    "",
                ])
                for fa in self.story_landscape.fresh_angles:
                    lines.append(f"- 💡 {fa}")
                lines.append("")

            lines.extend(["---", ""])

        # Narrative Angles
        if self.narrative_angles:
            lines.extend([
                section_header("Narrative Angles", "📐", 2),
                "",
            ])
            for angle in self.narrative_angles:
                # Confidence badge
                conf_badge = ""
                if angle.confidence:
                    conf_map = {
                        "strong": "🟢 Strong",
                        "moderate": "🟡 Moderate",
                        "speculative": "🔴 Speculative",
                    }
                    conf_badge = f" — {conf_map.get(angle.confidence.lower(), angle.confidence)}"
                # Highlight recommended angle
                is_recommended = (
                    self.recommended_angle_id
                    and angle.angle_id == self.recommended_angle_id
                )
                rec_marker = " ⭐ RECOMMENDED" if is_recommended else ""
                lines.extend([
                    f"### {angle.angle_id}: {angle.title}{conf_badge}{rec_marker}",
                    "",
                    f"> {angle.description}",
                    "",
                ])
                if angle.strengths or angle.weaknesses:
                    lines.append("| ✅ Strengths | ⚠️ Weaknesses |")
                    lines.append("|-------------|---------------|")
                    max_len = max(len(angle.strengths or []), len(angle.weaknesses or []))
                    for i in range(max_len):
                        s = escape_pipe(angle.strengths[i]) if i < len(angle.strengths or []) else "—"
                        w = escape_pipe(angle.weaknesses[i]) if i < len(angle.weaknesses or []) else "—"
                        lines.append(f"| {s} | {w} |")
                    lines.append("")
                if angle.best_for:
                    lines.append(f"**Best For:** {angle.best_for}")
                    lines.append("")
                if angle.key_sources:
                    lines.append(f"**Key Sources:** `{', '.join(angle.key_sources)}`")
                    lines.append("")

            # R11: Decision Brief (after all angles)
            if self.recommended_angle_id and self.recommendation_reasoning:
                # Find the recommended angle title
                rec_title = self.recommended_angle_id
                for angle in self.narrative_angles:
                    if angle.angle_id == self.recommended_angle_id:
                        rec_title = f"{angle.angle_id}: {angle.title}"
                        break

                # Build decision brief content
                brief_lines = [f"**⭐ RECOMMENDED: {rec_title}**\n> \n> "]
                brief_lines.append(f"{self.recommendation_reasoning}")

                if self.risk_if_wrong:
                    brief_lines.append(f"\n> \n> **Risk if wrong:** {self.risk_if_wrong}")

                if self.pivot_angle_id:
                    pivot_title = self.pivot_angle_id
                    for angle in self.narrative_angles:
                        if angle.angle_id == self.pivot_angle_id:
                            pivot_title = f"{angle.angle_id}: {angle.title}"
                            break
                    pivot_line = f"\n> \n> **Pivot to:** {pivot_title}"
                    if self.pivot_reasoning:
                        pivot_line += f" — {self.pivot_reasoning}"
                    brief_lines.append(pivot_line)

                if self.decision_criteria:
                    brief_lines.append("\n> \n> **Would change if:**")
                    for criterion in self.decision_criteria:
                        brief_lines.append(f"\n>   - {criterion}")

                lines.extend([
                    github_alert("IMPORTANT", "".join(brief_lines)),
                    "",
                ])

            lines.extend(["---", ""])

        # Opening Hooks
        if self.opening_hooks:
            lines.extend([
                section_header("Opening Hooks", "🎣", 2),
                "",
            ])
            for i, hook in enumerate(self.opening_hooks, 1):
                hook_type_label = hook.hook_type.value.replace("_", " ").title()
                lines.extend([
                    f"### Hook {i}: {hook_type_label}",
                    "",
                    f"> *\"{hook.content}\"*",
                    "",
                    f"**Tone:** {hook.tone}",
                ])
                if hook.source_basis:
                    lines.append(f"**Sources:** `{', '.join(hook.source_basis)}`")
                lines.append("")
            lines.extend(["---", ""])

        # Structure Options
        if self.structure_options:
            lines.extend([
                section_header("Structure Options", "🏗️", 2),
                "",
            ])
            for opt in self.structure_options:
                struct_label = opt.structure_type.value.replace("_", " ").title()
                lines.extend([
                    f"### {struct_label}",
                    "",
                    f"> {opt.description}",
                    "",
                ])
                if opt.section_breakdown:
                    lines.append("**Section Breakdown:**")
                    for i, section in enumerate(opt.section_breakdown, 1):
                        lines.append(f"{i}. {section}")
                    lines.append("")
                if opt.pros or opt.cons:
                    lines.append("| ✅ Pros | ⚠️ Cons |")
                    lines.append("|---------|---------|")
                    max_len = max(len(opt.pros or []), len(opt.cons or []))
                    for i in range(max_len):
                        p = escape_pipe(opt.pros[i]) if i < len(opt.pros or []) else "—"
                        c = escape_pipe(opt.cons[i]) if i < len(opt.cons or []) else "—"
                        lines.append(f"| {p} | {c} |")
                    lines.append("")
            lines.extend(["---", ""])

        # Title Options
        if self.title_options:
            lines.extend([
                section_header("Title Options", "📝", 2),
                "",
                "| # | Title | Subtitle | Tone |",
                "|--:|-------|----------|------|",
            ])
            for i, t in enumerate(self.title_options, 1):
                subtitle = escape_pipe(t.subtitle) if t.subtitle else "—"
                tone_label = t.tone.value.replace("_", " ").title()
                lines.append(f"| {i} | **{escape_pipe(t.title)}** | {subtitle} | {tone_label} |")
            lines.extend(["", "---", ""])

        # Key Moments
        if self.key_moments:
            lines.extend([
                section_header("Key Moments", "⭐", 2),
                "",
                "| Moment | Source | Timestamp | Why Compelling |",
                "|--------|--------|-----------|----------------|",
            ])
            for m in self.key_moments:
                moment_text = m.moment[:50] + "..." if len(m.moment) > 50 else m.moment
                timestamp = m.timestamp or "—"
                why = m.why_compelling[:40] + "..." if m.why_compelling and len(m.why_compelling) > 40 else (m.why_compelling or "—")
                lines.append(f"| {escape_pipe(moment_text)} | `{m.source_id}` | {timestamp} | {escape_pipe(why)} |")
            lines.extend(["", ""])
            # Add detailed breakdown below table
            lines.append("<details>")
            lines.append("<summary><strong>Detailed Moment Breakdown</strong></summary>")
            lines.append("")
            for m in self.key_moments:
                lines.extend([
                    f"**{m.moment}** [`{m.source_id}`]",
                ])
                if m.timestamp:
                    lines.append(f"- ⏱️ Timestamp: {m.timestamp}")
                if m.why_compelling:
                    lines.append(f"- 💡 Why compelling: {m.why_compelling}")
                if m.potential_use:
                    lines.append(f"- 🎬 Potential use: {m.potential_use}")
                lines.append("")
            lines.extend(["</details>", "", "---", ""])

        # Thumbnail Concepts
        if self.thumbnail_concepts:
            lines.extend([
                section_header("Thumbnail Concepts", "🖼️", 2),
                "",
            ])
            for i, c in enumerate(self.thumbnail_concepts, 1):
                lines.extend([
                    f"### Concept {i}: {c.concept}",
                    "",
                ])
                if c.visual_elements:
                    lines.append(f"- 🎨 **Visual elements:** {', '.join(c.visual_elements)}")
                if c.text_overlay:
                    lines.append(f"- 📝 **Text overlay:** \"{c.text_overlay}\"")
                if c.emotional_appeal:
                    lines.append(f"- 💭 **Emotional appeal:** {c.emotional_appeal}")
                lines.append("")
            lines.extend(["---", ""])

        # Risk Assessment
        if self.risk_assessment:
            sens_level = self.risk_assessment.sensitivity_level.value.upper()
            sens_icon = sensitivity_icon(self.risk_assessment.sensitivity_level.value)
            lines.extend([
                section_header("Risk Assessment", "⚠️", 2),
                "",
            ])
            # Sensitivity alert
            alert_type = "CAUTION" if sens_level in ("HIGH", "CRITICAL") else "WARNING" if sens_level == "MEDIUM" else "NOTE"
            lines.extend([
                github_alert(alert_type, f"**Sensitivity Level:** {sens_icon} {sens_level}"),
                "",
            ])
            if self.risk_assessment.potential_issues:
                lines.append("### ⚡ Potential Issues")
                lines.append("")
                for issue in self.risk_assessment.potential_issues:
                    lines.append(f"- {issue}")
                lines.append("")
            if self.risk_assessment.mitigation_suggestions:
                lines.append("### 🛡️ Mitigation Suggestions")
                lines.append("")
                for m in self.risk_assessment.mitigation_suggestions:
                    lines.append(f"- {m}")
                lines.append("")
            if self.risk_assessment.legal_considerations:
                lines.append("### ⚖️ Legal Considerations")
                lines.append("")
                for item in self.risk_assessment.legal_considerations:
                    lines.append(f"- {item}")
                lines.append("")
            if self.risk_assessment.ethical_considerations:
                lines.append("### 🤔 Ethical Considerations")
                lines.append("")
                for e in self.risk_assessment.ethical_considerations:
                    lines.append(f"- {e}")
                lines.append("")
            lines.extend(["---", ""])

        # Interview Suggestions
        if self.interview_suggestions:
            lines.extend([
                section_header("Interview Suggestions", "🎤", 2),
                "",
            ])
            if self.interview_suggestions.people_to_contact:
                lines.extend([
                    "### 👤 People to Contact",
                    "",
                    "| Name | Role | Why Relevant |",
                    "|------|------|--------------|",
                ])
                for p in self.interview_suggestions.people_to_contact:
                    why = p.why_relevant[:50] + "..." if len(p.why_relevant) > 50 else p.why_relevant
                    lines.append(f"| **{p.name}** | {p.role} | {why} |")
                lines.append("")
                # Detailed questions in collapsible
                lines.append("<details>")
                lines.append("<summary><strong>Interview Questions</strong></summary>")
                lines.append("")
                for p in self.interview_suggestions.people_to_contact:
                    if p.potential_questions:
                        lines.append(f"**{p.name}:**")
                        for q in p.potential_questions:
                            lines.append(f"- {q}")
                        lines.append("")
                lines.extend(["</details>", ""])
            if self.interview_suggestions.expert_perspectives_needed:
                lines.extend([
                    "### 🎓 Expert Perspectives Needed",
                    "",
                ])
                for exp in self.interview_suggestions.expert_perspectives_needed:
                    lines.append(f"- {exp}")
                lines.append("")
            lines.extend(["---", ""])

        # B-Roll Suggestions
        if self.b_roll_suggestions:
            lines.extend([
                section_header("B-Roll Suggestions", "🎞️", 2),
                "",
                "| Description | Purpose | Sources |",
                "|-------------|---------|---------|",
            ])
            for b in self.b_roll_suggestions:
                desc = b.description[:40] + "..." if len(b.description) > 40 else b.description
                sources = ", ".join(b.source_options) if b.source_options else "—"
                lines.append(f"| {escape_pipe(desc)} | {escape_pipe(b.purpose)} | {escape_pipe(sources)} |")
            lines.extend(["", "---", ""])

        # Production Blueprint
        if self.production_blueprint:
            lines.append(self.production_blueprint.to_markdown())
            lines.append("")

        # Quality score badge (R12)
        if self.quality_score is not None:
            if self.quality_score >= 90:
                q_badge = f"🟢 {self.quality_score}/100 — Publishable"
            elif self.quality_score >= 70:
                q_badge = f"🟡 {self.quality_score}/100 — Usable with light edits"
            elif self.quality_score >= 50:
                q_badge = f"🟠 {self.quality_score}/100 — Needs revision"
            else:
                q_badge = f"🔴 {self.quality_score}/100 — Significant revision needed"
            lines.extend([
                f"**Quality Score:** {q_badge}",
                "",
            ])

            # Render quality issues if any
            if self.quality_issues:
                lines.append("<details>")
                lines.append(f"<summary><strong>Quality Issues ({len(self.quality_issues)})</strong></summary>")
                lines.append("")
                for issue in self.quality_issues:
                    if isinstance(issue, dict):
                        severity = issue.get("severity", "info")
                        sev_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")
                        section = issue.get("section", "unknown")
                        desc = issue.get("description", "")
                        suggestion = issue.get("suggestion", "")
                        lines.append(f"- {sev_icon} **[{section}]** {desc}")
                        if suggestion:
                            lines.append(f"  - 💡 *{suggestion}*")
                lines.append("")
                lines.append("</details>")
                lines.append("")

        # Footer
        lines.extend([
            "",
            github_alert(
                "NOTE",
                "**Producer Packet complete.**\n> \n> "
                "This is creative interpretation, not factual research. "
                "Always verify claims independently before production."
            ),
        ])

        return "\n".join(lines)
