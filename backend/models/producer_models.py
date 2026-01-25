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
    type_icon,
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

    def to_dict(self) -> dict:
        return {
            "angle_id": self.angle_id,
            "title": self.title,
            "description": self.description,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "best_for": self.best_for,
            "key_sources": self.key_sources,
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type": "producer_packet",
            "document_version": "2.0",
            "job_id": self.job_id,
            "generated_at": self.generated_at,
            "creative_interpretation_notice": CREATIVE_INTERPRETATION_NOTICE,
            "story_core": self.story_core.to_dict(),
            "narrative_angles": [a.to_dict() for a in self.narrative_angles],
            "opening_hooks": [h.to_dict() for h in self.opening_hooks],
            "structure_options": [s.to_dict() for s in self.structure_options],
            "key_moments": [m.to_dict() for m in self.key_moments],
            "title_options": [t.to_dict() for t in self.title_options],
            "thumbnail_concepts": [c.to_dict() for c in self.thumbnail_concepts],
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "interview_suggestions": self.interview_suggestions.to_dict() if self.interview_suggestions else None,
            "b_roll_suggestions": [b.to_dict() for b in self.b_roll_suggestions],
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
            f"| **Central Question** | {self.story_core.central_question} |",
            f"| **One-Sentence Pitch** | {self.story_core.one_sentence_pitch} |",
            f"| **Why This Matters** | {self.story_core.why_this_matters} |",
            f"| **Target Audience** | {self.story_core.target_audience} |",
            f"| **Emotional Arc** | {self.story_core.emotional_arc} |",
            "",
            "---",
            "",
        ])

        # Narrative Angles
        if self.narrative_angles:
            lines.extend([
                section_header("Narrative Angles", "📐", 2),
                "",
            ])
            for angle in self.narrative_angles:
                lines.extend([
                    f"### {angle.angle_id}: {angle.title}",
                    "",
                    f"> {angle.description}",
                    "",
                ])
                if angle.strengths or angle.weaknesses:
                    lines.append("| ✅ Strengths | ⚠️ Weaknesses |")
                    lines.append("|-------------|---------------|")
                    max_len = max(len(angle.strengths or []), len(angle.weaknesses or []))
                    for i in range(max_len):
                        s = angle.strengths[i] if i < len(angle.strengths or []) else "—"
                        w = angle.weaknesses[i] if i < len(angle.weaknesses or []) else "—"
                        lines.append(f"| {s} | {w} |")
                    lines.append("")
                if angle.best_for:
                    lines.append(f"**Best For:** {angle.best_for}")
                    lines.append("")
                if angle.key_sources:
                    lines.append(f"**Key Sources:** `{', '.join(angle.key_sources)}`")
                    lines.append("")
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
                        p = opt.pros[i] if i < len(opt.pros or []) else "—"
                        c = opt.cons[i] if i < len(opt.cons or []) else "—"
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
                subtitle = t.subtitle or "—"
                tone_label = t.tone.value.replace("_", " ").title()
                lines.append(f"| {i} | **{t.title}** | {subtitle} | {tone_label} |")
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
                lines.append(f"| {moment_text} | `{m.source_id}` | {timestamp} | {why} |")
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
                lines.append(f"| {desc} | {b.purpose} | {sources} |")
            lines.extend(["", "---", ""])

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
