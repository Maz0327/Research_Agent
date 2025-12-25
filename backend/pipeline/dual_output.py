"""Dual Output Formatter: NotebookLM packet + Documentary Blueprint.

PRD v4.3: Research Agent produces two output formats:
1. NotebookLM Packet - For AI audio podcast generation
2. Documentary Blueprint - For video production

The NotebookLM packet is optimized for text-to-speech podcast creation,
while the Documentary Blueprint is optimized for video scriptwriting.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger


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
