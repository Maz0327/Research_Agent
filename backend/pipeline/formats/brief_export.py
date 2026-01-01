"""Research Brief Export: LLM-generated human-readable analysis document.

Creates a 2-5 page research brief optimized for documentary creators
who need to understand the research before writing scripts.
"""
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger


# Evidence level definitions
EVIDENCE_LEVELS = {
    "VERIFIED": "3+ credible sources agree",
    "PROBABLE": "2 sources or expert opinion",
    "SPECULATIVE": "Single source or theory",
    "DISPUTED": "Conflicting sources",
}


@dataclass
class ResearchBrief:
    """Human-readable research analysis document."""

    topic: str
    summary: str = ""                              # 60-second story
    claims_matrix: list = field(default_factory=list)  # [{claim, evidence_level, sources}]
    key_figures: list = field(default_factory=list)    # [{name, role, quotes, stance}]
    timeline: list = field(default_factory=list)       # [{date, event, sources}]
    perspectives: dict = field(default_factory=dict)   # {mainstream, alternative, unexplored}
    quotable_moments: list = field(default_factory=list)  # [{quote, source, context}]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "topic": self.topic,
            "summary": self.summary,
            "claims_matrix": self.claims_matrix,
            "key_figures": self.key_figures,
            "timeline": self.timeline,
            "perspectives": self.perspectives,
            "quotable_moments": self.quotable_moments,
        }


class BriefExporter:
    """Generate LLM-synthesized research briefs."""

    def generate_brief(
        self,
        topic: str,
        claims: list,
        entities: dict,
        timeline_events: list,
        sources: list,
        validation_results: list,
        discovered_angles: list,
    ) -> ResearchBrief:
        """
        Generate research brief from pipeline data.

        Uses LLM to synthesize research into readable format.
        Falls back to structured extraction if LLM unavailable.
        """
        logger.info(f"Generating research brief for: {topic}")

        # Try LLM synthesis first
        try:
            brief = self._llm_synthesize(
                topic, claims, entities, timeline_events,
                sources, validation_results, discovered_angles
            )
            if brief:
                return brief
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}, falling back to extraction")

        # Fallback: structured extraction without LLM
        return self._extract_brief(
            topic, claims, entities, timeline_events,
            sources, validation_results, discovered_angles
        )

    def _llm_synthesize(
        self,
        topic: str,
        claims: list,
        entities: dict,
        timeline_events: list,
        sources: list,
        validation_results: list,
        discovered_angles: list,
    ) -> Optional[ResearchBrief]:
        """Use LLM to synthesize research into brief.

        Fallback chain: Gemini 2.5 Pro → GPT-4o-mini → extraction fallback
        """
        # Build input context
        claims_json = json.dumps(claims[:20], default=str)
        entities_json = json.dumps(entities, default=str)
        timeline_json = json.dumps(timeline_events[:15], default=str)
        sources_json = json.dumps([
            {"url": s.get("url", ""), "title": s.get("title", ""), "type": s.get("type", "")}
            for s in sources[:20]
        ], default=str)
        angles_json = json.dumps(discovered_angles[:5], default=str)

        prompt = f"""Synthesize the following research data into a structured brief for a content creator making a 20-60 minute YouTube documentary.

TOPIC: {topic}

CLAIMS EXTRACTED:
{claims_json}

ENTITIES (People, Organizations, Locations):
{entities_json}

TIMELINE EVENTS:
{timeline_json}

SOURCES:
{sources_json}

DISCOVERED ANGLES:
{angles_json}

OUTPUT AS JSON with this exact structure:
{{
    "summary": "2-3 paragraph narrative summary of the story - what happened, why it matters, what makes it compelling",
    "claims_matrix": [
        {{"claim": "specific claim text", "evidence_level": "VERIFIED|PROBABLE|SPECULATIVE|DISPUTED", "sources": ["source 1", "source 2"]}}
    ],
    "key_figures": [
        {{"name": "Person Name", "role": "their role in the story", "quotes": ["notable quote"], "stance": "their position/perspective"}}
    ],
    "timeline": [
        {{"date": "date or period", "event": "what happened", "sources": ["source"]}}
    ],
    "perspectives": {{
        "mainstream": "what official/mainstream sources say",
        "alternative": "alternative theories or contested narratives",
        "unexplored": "angles not yet fully covered"
    }},
    "quotable_moments": [
        {{"quote": "exact quote text", "source": "who said it", "context": "why it matters"}}
    ]
}}

Classify evidence levels honestly:
- VERIFIED: 3+ credible sources confirm
- PROBABLE: 2 sources or expert opinion supports
- SPECULATIVE: Single source or unverified theory
- DISPUTED: Sources conflict

Focus on what a documentary creator needs to understand the story."""

        # Try Gemini 2.5 Pro first
        result = self._try_gemini(prompt, topic)
        if result:
            return result

        # Fallback to GPT-4o-mini
        result = self._try_openai(prompt, topic)
        if result:
            return result

        return None

    def _try_gemini(self, prompt: str, topic: str) -> Optional[ResearchBrief]:
        """Try Gemini 2.5 Pro for brief synthesis."""
        try:
            from backend.integrations.gemini_client import GeminiClient
            client = GeminiClient()
        except Exception as e:
            logger.warning(f"Gemini client unavailable: {e}")
            return None

        try:
            response = client.generate(
                prompt=prompt,
                model="gemini-2.5-pro",
                system_instruction="You are a documentary research analyst. Output valid JSON only.",
                temperature=0.3,
                max_tokens=4096,
            )

            text = self._parse_json_response(response["text"])
            result = json.loads(text)

            logger.info(f"Gemini brief synthesis complete, cost: ${response.get('cost', 0):.4f}")
            return self._build_brief(topic, result)

        except Exception as e:
            logger.warning(f"Gemini brief generation failed: {e}, trying OpenAI fallback")
            return None

    def _try_openai(self, prompt: str, topic: str) -> Optional[ResearchBrief]:
        """Fallback to GPT-4o-mini for brief synthesis."""
        try:
            from backend.integrations.openai_client import get_openai_client
            client = get_openai_client()
            if not client:
                return None
        except Exception as e:
            logger.warning(f"OpenAI client unavailable: {e}")
            return None

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a documentary research analyst. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            result = json.loads(response.choices[0].message.content)

            logger.info("GPT-4o-mini brief synthesis complete (fallback)")
            return self._build_brief(topic, result)

        except Exception as e:
            logger.error(f"OpenAI brief generation failed: {e}")
            return None

    def _parse_json_response(self, text: str) -> str:
        """Strip markdown code blocks from JSON response."""
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return text.strip()

    def _build_brief(self, topic: str, result: dict) -> ResearchBrief:
        """Build ResearchBrief from parsed JSON result."""
        return ResearchBrief(
            topic=topic,
            summary=result.get("summary", ""),
            claims_matrix=result.get("claims_matrix", []),
            key_figures=result.get("key_figures", []),
            timeline=result.get("timeline", []),
            perspectives=result.get("perspectives", {}),
            quotable_moments=result.get("quotable_moments", []),
        )

    def _extract_brief(
        self,
        topic: str,
        claims: list,
        entities: dict,
        timeline_events: list,
        sources: list,
        validation_results: list,
        discovered_angles: list,
    ) -> ResearchBrief:
        """Extract brief from data without LLM (fallback)."""
        logger.info("Using extraction fallback for brief generation")

        # Build claims matrix from validation results
        validation_lookup = {
            self._get_attr(v, "claim_id"): v for v in validation_results
        }

        claims_matrix = []
        for claim in claims[:15]:
            claim_id = self._get_attr(claim, "id") or self._get_attr(claim, "claim_id")
            claim_text = self._get_attr(claim, "text") or self._get_attr(claim, "claim") or ""
            confidence = self._get_attr(claim, "confidence") or 0.5
            claim_sources = self._get_attr(claim, "sources") or []

            # Determine evidence level
            if claim_id and claim_id in validation_lookup:
                val = validation_lookup[claim_id]
                status = self._get_attr(val, "status") or ""
                if status in ["verified", "confirmed"]:
                    level = "VERIFIED"
                elif status in ["probable", "likely"]:
                    level = "PROBABLE"
                elif status in ["disputed", "conflicting"]:
                    level = "DISPUTED"
                else:
                    level = "SPECULATIVE"
            else:
                level = self._confidence_to_level(confidence)

            source_names = self._extract_source_names(claim_sources)

            claims_matrix.append({
                "claim": claim_text[:200],
                "evidence_level": level,
                "sources": source_names[:3],
            })

        # Extract key figures from entities
        key_figures = []
        people = entities.get("people") or entities.get("persons") or []
        for person in people[:8]:
            name = self._get_attr(person, "name") or str(person)
            role = self._get_attr(person, "role") or "Key figure"
            quotes = self._get_attr(person, "quotes") or []

            key_figures.append({
                "name": name,
                "role": role,
                "quotes": quotes[:2] if isinstance(quotes, list) else [],
                "stance": self._get_attr(person, "stance") or "Unknown",
            })

        # Build timeline
        timeline = []
        for event in timeline_events[:12]:
            date = self._get_attr(event, "date") or self._get_attr(event, "timestamp") or "Unknown"
            description = (
                self._get_attr(event, "description") or
                self._get_attr(event, "event") or
                self._get_attr(event, "text") or ""
            )
            event_sources = self._get_attr(event, "sources") or []

            timeline.append({
                "date": str(date),
                "event": description[:150],
                "sources": self._extract_source_names(event_sources)[:2],
            })

        # Build perspectives from angles
        perspectives = {
            "mainstream": "See claims marked as VERIFIED above",
            "alternative": "",
            "unexplored": "",
        }

        angles_list = self._normalize_angles(discovered_angles)
        alt_angles = []
        unexplored = []
        for angle in angles_list:
            name = self._get_attr(angle, "name") or str(angle)
            desc = self._get_attr(angle, "description") or ""
            confidence = self._get_attr(angle, "confidence") or 0.5

            if confidence < 0.5:
                unexplored.append(f"{name}: {desc[:100]}")
            else:
                alt_angles.append(f"{name}: {desc[:100]}")

        if alt_angles:
            perspectives["alternative"] = "; ".join(alt_angles[:3])
        if unexplored:
            perspectives["unexplored"] = "; ".join(unexplored[:3])

        # Extract quotable moments from claims with quotes
        quotable_moments = []
        for claim in claims:
            text = self._get_attr(claim, "text") or ""
            # Find quoted text
            import re
            quotes = re.findall(r'"([^"]{20,100})"', text)
            for quote in quotes[:2]:
                quotable_moments.append({
                    "quote": quote,
                    "source": "Extracted from research",
                    "context": text[:100],
                })

        # Generate summary
        summary = self._generate_summary(topic, claims_matrix, key_figures, timeline)

        return ResearchBrief(
            topic=topic,
            summary=summary,
            claims_matrix=claims_matrix,
            key_figures=key_figures,
            timeline=timeline,
            perspectives=perspectives,
            quotable_moments=quotable_moments[:10],
        )

    def _generate_summary(
        self,
        topic: str,
        claims_matrix: list,
        key_figures: list,
        timeline: list,
    ) -> str:
        """Generate narrative summary from extracted data."""
        parts = [f"This research covers {topic}."]

        # Add key claims
        verified = [c for c in claims_matrix if c.get("evidence_level") == "VERIFIED"]
        if verified:
            parts.append(f"Key verified findings include: {verified[0].get('claim', '')[:100]}.")

        # Add key figures
        if key_figures:
            names = [f.get("name", "") for f in key_figures[:3]]
            parts.append(f"Central figures include {', '.join(names)}.")

        # Add timeline scope
        if timeline and len(timeline) >= 2:
            start = timeline[0].get("date", "")
            end = timeline[-1].get("date", "")
            parts.append(f"The timeline spans from {start} to {end}.")

        # Add speculation note
        speculative = [c for c in claims_matrix if c.get("evidence_level") == "SPECULATIVE"]
        if speculative:
            parts.append(f"Note: {len(speculative)} claims remain speculative and require further verification.")

        return " ".join(parts)

    def to_markdown(self, brief: ResearchBrief) -> str:
        """Convert ResearchBrief to markdown format."""
        lines = [
            f"# Research Brief: {brief.topic}",
            "",
            "---",
            "",
            "## The Story in 60 Seconds",
            "",
            brief.summary or "*Summary not available*",
            "",
            "---",
            "",
            "## Claims Matrix",
            "",
            "| Claim | Evidence Level | Sources |",
            "|-------|---------------|---------|",
        ]

        for claim in brief.claims_matrix:
            claim_text = claim.get("claim", "")[:80]
            level = claim.get("evidence_level", "SPECULATIVE")
            sources = ", ".join(claim.get("sources", [])[:2]) or "—"
            lines.append(f"| {claim_text} | **{level}** | {sources} |")

        lines.extend([
            "",
            "*Evidence Levels: VERIFIED (3+ sources) > PROBABLE (2 sources) > SPECULATIVE (1 source) > DISPUTED (conflicting)*",
            "",
            "---",
            "",
            "## Key Figures",
            "",
        ])

        for figure in brief.key_figures:
            name = figure.get("name", "Unknown")
            role = figure.get("role", "")
            stance = figure.get("stance", "")
            quotes = figure.get("quotes", [])

            lines.append(f"### {name}")
            if role:
                lines.append(f"**Role:** {role}")
            if stance:
                lines.append(f"**Stance:** {stance}")
            if quotes:
                for q in quotes[:2]:
                    lines.append(f"> \"{q}\"")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## Timeline",
            "",
        ])

        for event in brief.timeline:
            date = event.get("date", "Unknown")
            text = event.get("event", "")
            sources = event.get("sources", [])
            source_str = f" *({', '.join(sources[:2])})*" if sources else ""
            lines.append(f"- **{date}**: {text}{source_str}")

        lines.extend([
            "",
            "---",
            "",
            "## Perspectives",
            "",
        ])

        perspectives = brief.perspectives
        if perspectives.get("mainstream"):
            lines.append(f"**Mainstream:** {perspectives['mainstream']}")
            lines.append("")
        if perspectives.get("alternative"):
            lines.append(f"**Alternative:** {perspectives['alternative']}")
            lines.append("")
        if perspectives.get("unexplored"):
            lines.append(f"**Unexplored Angles:** {perspectives['unexplored']}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## Quotable Moments",
            "",
        ])

        for moment in brief.quotable_moments:
            quote = moment.get("quote", "")
            source = moment.get("source", "")
            context = moment.get("context", "")
            lines.append(f"> \"{quote}\"")
            lines.append(f"> — {source}")
            if context:
                lines.append(f"> *Context: {context[:100]}*")
            lines.append("")

        lines.extend([
            "---",
            "",
            "*Generated by Research Agent*",
        ])

        return "\n".join(lines)

    def _confidence_to_level(self, confidence: float) -> str:
        """Convert confidence score to evidence level."""
        if confidence >= 0.8:
            return "VERIFIED"
        if confidence >= 0.6:
            return "PROBABLE"
        if confidence >= 0.4:
            return "SPECULATIVE"
        return "DISPUTED"

    def _extract_source_names(self, sources: list) -> list[str]:
        """Extract source names/titles from source list."""
        names = []
        for s in sources:
            if isinstance(s, dict):
                name = s.get("title") or s.get("url", "")[:50]
            else:
                name = str(s)[:50]
            if name:
                names.append(name)
        return names

    def _normalize_angles(self, discovered_angles: list) -> list:
        """Normalize angles to list of dicts."""
        if isinstance(discovered_angles, dict):
            return discovered_angles.get("angles") or discovered_angles.get("discovered") or []
        return discovered_angles or []

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
