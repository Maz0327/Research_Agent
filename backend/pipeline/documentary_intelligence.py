"""Documentary intelligence layer for narrative analysis."""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger


class NarrativeStructure(BaseModel):
    """Three-act documentary structure."""
    opening_hook: str
    act_1_setup: Dict[str, Any]
    act_2_investigation: Dict[str, Any]
    act_3_resolution: Dict[str, Any]


class DocumentaryIntelligence:
    """Transform research into documentary blueprint."""

    def analyze(self, research_data: Dict, doc_type: str) -> Dict:
        """
        Analyze research for documentary production.

        This is the KEY differentiator - transforms raw research into
        production-ready documentary intelligence.
        """

        # Extract documentary elements based on type
        if doc_type == "breaking_news":
            return self._analyze_breaking_news(research_data)
        elif doc_type == "investigation":
            return self._analyze_investigation(research_data)
        elif doc_type == "profile":
            return self._analyze_profile(research_data)
        elif doc_type == "controversy":
            return self._analyze_controversy(research_data)
        else:
            return self._analyze_standard(research_data)

    def _analyze_investigation(self, data: Dict) -> Dict:
        """Analysis for investigative documentary."""

        # Find the hook - most shocking revelation
        hook = self._find_shocking_moment(data)

        # Identify conflicts and controversies
        conflicts = self._extract_conflicts(data)

        # Find visual moments
        visual_moments = self._identify_visual_moments(data)

        # Build narrative structure
        narrative = self._build_narrative_arc(data, "investigation")

        # Identify key interviews needed
        interviews = self._suggest_interviews(data)

        return {
            "hook": hook,
            "narrative_structure": narrative.model_dump() if narrative else {},
            "key_conflicts": conflicts,
            "visual_moments": visual_moments,
            "interview_suggestions": interviews,
            "production_notes": self._generate_production_notes(data)
        }

    def _analyze_breaking_news(self, data: Dict) -> Dict:
        """Analysis for breaking news documentary."""
        timeline = data.get("timeline", [])

        return {
            "hook": "Breaking news situation developing in real-time",
            "timeline_focus": timeline[-10:] if timeline else [],  # Last 10 events
            "key_players": self._identify_key_players(data),
            "what_we_know": self._summarize_confirmed_facts(data),
            "what_we_dont_know": self._identify_open_questions(data),
            "production_notes": {
                "tone": "Urgent, factual",
                "pacing": "Fast",
                "update_frequency": "As events unfold"
            }
        }

    def _analyze_profile(self, data: Dict) -> Dict:
        """Analysis for profile documentary."""
        entities = data.get("entities", {})
        people = entities.get("people", [])

        main_subject = people[0] if people else {"name": "Unknown"}

        return {
            "subject": main_subject.get("name"),
            "biographical_arc": self._create_biographical_arc(data),
            "character_study": self._analyze_character(data, main_subject),
            "relationships": self._map_relationships(data),
            "defining_moments": self._identify_defining_moments(data),
            "production_notes": {
                "tone": "Personal, intimate",
                "interview_style": "One-on-one, conversational"
            }
        }

    def _analyze_controversy(self, data: Dict) -> Dict:
        """Analysis for controversy documentary."""

        sides = self._identify_opposing_sides(data)

        return {
            "competing_narratives": sides,
            "points_of_contention": self._find_disagreements(data),
            "evidence_for_each_side": self._categorize_evidence_by_side(data),
            "neutral_facts": self._extract_agreed_facts(data),
            "production_notes": {
                "tone": "Balanced, analytical",
                "structure": "Point-counterpoint"
            }
        }

    def _analyze_standard(self, data: Dict) -> Dict:
        """Standard analysis fallback."""
        return {
            "hook": self._find_shocking_moment(data),
            "narrative_structure": self._build_narrative_arc(data, "standard").model_dump() if self._build_narrative_arc(data, "standard") else {},
            "key_points": self._extract_key_points(data),
            "production_notes": self._generate_production_notes(data)
        }

    def _find_shocking_moment(self, data: Dict) -> str:
        """Find the most compelling opening moment."""
        claims = data.get("claims", [])

        shocking_claims = []
        for claim in claims:
            claim_text = str(claim.get("canonical_claim", "")).lower()

            # Score based on controversy indicators
            score = 0
            controversy_words = [
                "scandal", "leaked", "exposed", "accused", "denied",
                "covered up", "lied", "fraud", "shocking", "revealed"
            ]

            for word in controversy_words:
                if word in claim_text:
                    score += 2

            if score > 0:
                shocking_claims.append((claim, score))

        # Sort by shock value
        shocking_claims.sort(key=lambda x: x[1], reverse=True)

        if shocking_claims:
            top_claim = shocking_claims[0][0]
            quote = top_claim.get("verbatim_quote", top_claim.get("canonical_claim", ""))
            return quote

        return "Opening hook to be determined from research"

    def _extract_conflicts(self, data: Dict) -> List[Dict]:
        """Find opposing viewpoints and conflicts."""
        conflicts = []

        # Analyze validation results for contradictions
        validation = data.get("validation", [])
        for evidence in validation:
            status = evidence.get("status", "")
            if status in ["DEBUNKED", "DISPUTED"]:
                conflicts.append({
                    "type": "disputed_claim",
                    "claim": evidence.get("claim_id", "Unknown"),
                    "conflict": f"Claim has been {status.lower()} by evidence"
                })

        # Look for competing narratives in entities
        entities = data.get("entities", {})
        people = entities.get("people", [])

        if len(people) > 2:
            conflicts.append({
                "type": "multiple_perspectives",
                "parties": [p.get("name") for p in people[:5]],
                "conflict": "Multiple parties with potentially competing interests"
            })

        logger.info(f"Found {len(conflicts)} conflicts")
        return conflicts

    def _identify_visual_moments(self, data: Dict) -> List[Dict]:
        """Find moments good for video production."""
        visual_moments = []

        # Search sources for visual cues
        sources = data.get("sources", [])

        visual_keywords = [
            "showed", "displayed", "held up", "pointed", "demonstrated",
            "revealed", "unveiled", "chart", "graph", "document",
            "emotional", "angry", "cried", "laughed", "shocked",
            "video", "footage", "photo", "image"
        ]

        for source in sources[:50]:  # Limit to first 50 sources
            text = source.get("text", "")
            url = source.get("url", "")

            if not text:
                continue

            for keyword in visual_keywords:
                if keyword in text.lower():
                    # Extract context around keyword
                    index = text.lower().find(keyword)
                    context = text[max(0, index-100):min(len(text), index+100)]

                    visual_moments.append({
                        "source_url": url,
                        "keyword": keyword,
                        "context": context,
                        "production_note": f"Potential B-roll moment: {keyword}"
                    })

        logger.info(f"Found {len(visual_moments)} visual moments")
        return visual_moments[:20]  # Top 20 moments

    def _build_narrative_arc(self, data: Dict, doc_type: str) -> Optional[NarrativeStructure]:
        """Build three-act structure."""

        timeline = data.get("timeline", [])
        entities = data.get("entities", {})
        claims = data.get("claims", [])

        try:
            return NarrativeStructure(
                opening_hook=self._find_shocking_moment(data),
                act_1_setup={
                    "introduce_players": [p.get("name", "Unknown") for p in entities.get("people", [])[:5]],
                    "establish_context": [{"date": e.get("date"), "event": e.get("event")} for e in timeline[:3]] if timeline else [],
                    "set_stakes": "What's at stake in this story"
                },
                act_2_investigation={
                    "rising_action": [{"date": e.get("date"), "event": e.get("event")} for e in timeline[3:10]] if len(timeline) > 3 else [],
                    "key_revelations": [c.get("canonical_claim", str(c))[:100] for c in claims[:10]],
                    "conflicts": self._extract_conflicts(data)
                },
                act_3_resolution={
                    "climax": [{"date": e.get("date"), "event": e.get("event")} for e in timeline[-3:]] if timeline else [],
                    "verified_facts": [c for c in claims if c.get("confidence", 0) > 0.8][:5],
                    "open_questions": [c for c in claims if c.get("confidence", 0) < 0.5][:5],
                    "call_to_action": "What happens next?"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to build narrative arc: {e}")
            return None

    def _suggest_interviews(self, data: Dict) -> List[Dict]:
        """Suggest interview subjects and questions."""
        entities = data.get("entities", {})
        people = entities.get("people", [])

        interviews = []
        for person in people[:10]:  # Top 10 people
            name = person.get("name", "Unknown")
            mentions = person.get("mentions", 0)

            interviews.append({
                "subject": name,
                "relevance": f"{mentions} mentions",
                "suggested_questions": [
                    f"What is your response to claims about {name}?",
                    "Can you clarify your role in these events?",
                    "What evidence supports your position?"
                ],
                "priority": "high" if mentions > 20 else "medium" if mentions > 10 else "low"
            })

        return interviews

    def _generate_production_notes(self, data: Dict) -> Dict:
        """Generate specific production recommendations."""
        return {
            "estimated_runtime": self._estimate_runtime(data),
            "b_roll_needed": len(self._identify_visual_moments(data)),
            "graphics_needed": [
                "Timeline graphic",
                "Entity relationship diagram",
                "Claims evidence table"
            ],
            "tone": self._determine_tone(data),
            "target_audience": "General audience interested in investigative content"
        }

    def _estimate_runtime(self, data: Dict) -> str:
        """Estimate video runtime based on content."""
        claims = len(data.get("claims", []))
        timeline_events = len(data.get("timeline", []))

        if claims > 50 or timeline_events > 20:
            return "20-30 minutes (long-form)"
        elif claims > 20 or timeline_events > 10:
            return "10-15 minutes (medium)"
        else:
            return "5-10 minutes (short)"

    def _determine_tone(self, data: Dict) -> str:
        """Determine appropriate tone for documentary."""
        validation = data.get("validation", [])

        if not validation:
            return "Balanced/Informative"

        debunked_count = sum(1 for v in validation if v.get("status") == "DEBUNKED")

        if debunked_count > len(validation) / 2:
            return "Investigative/Skeptical"
        else:
            return "Balanced/Informative"

    # Helper methods for other documentary types
    def _identify_key_players(self, data: Dict) -> List[str]:
        """Identify key players in the story."""
        entities = data.get("entities", {})
        people = entities.get("people", [])
        return [p.get("name", "Unknown") for p in people[:5]]

    def _summarize_confirmed_facts(self, data: Dict) -> List[str]:
        """Get confirmed facts."""
        claims = data.get("claims", [])
        confirmed = [c.get("canonical_claim", str(c)) for c in claims if c.get("confidence", 0) > 0.8]
        return confirmed[:10]

    def _identify_open_questions(self, data: Dict) -> List[str]:
        """Get unanswered questions."""
        claims = data.get("claims", [])
        uncertain = [c.get("canonical_claim", str(c)) for c in claims if c.get("confidence", 0) < 0.5]
        return uncertain[:10]

    def _create_biographical_arc(self, data: Dict) -> Dict:
        """Create biographical timeline."""
        timeline = data.get("timeline", [])
        return {
            "early_life": timeline[:len(timeline)//3] if timeline else [],
            "career_rise": timeline[len(timeline)//3:2*len(timeline)//3] if len(timeline) > 2 else [],
            "recent_events": timeline[2*len(timeline)//3:] if len(timeline) > 2 else []
        }

    def _analyze_character(self, data: Dict, subject: Dict) -> Dict:
        """Analyze character traits."""
        return {
            "name": subject.get("name", "Unknown"),
            "mentions": subject.get("mentions", 0),
            "public_perception": "To be determined from sentiment analysis"
        }

    def _map_relationships(self, data: Dict) -> List[Dict]:
        """Map relationships between entities."""
        entities = data.get("entities", {})
        return entities.get("relationships", [])

    def _identify_defining_moments(self, data: Dict) -> List[Dict]:
        """Identify defining moments in profile."""
        timeline = data.get("timeline", [])
        # Sort by confidence/importance if available
        return timeline[:10] if timeline else []

    def _identify_opposing_sides(self, data: Dict) -> List[Dict]:
        """Identify opposing sides in controversy."""
        return [
            {"side": "Position A", "summary": "First perspective"},
            {"side": "Position B", "summary": "Opposing perspective"}
        ]

    def _find_disagreements(self, data: Dict) -> List[str]:
        """Find points of disagreement."""
        claims = data.get("claims", [])
        disputed = [c.get("canonical_claim", str(c)) for c in claims if c.get("status") == "DISPUTED"]
        return disputed[:10]

    def _categorize_evidence_by_side(self, data: Dict) -> Dict:
        """Categorize evidence by which side it supports."""
        return {
            "side_a_evidence": [],
            "side_b_evidence": [],
            "neutral_evidence": []
        }

    def _extract_agreed_facts(self, data: Dict) -> List[str]:
        """Extract facts all sides agree on."""
        claims = data.get("claims", [])
        verified = [c.get("canonical_claim", str(c)) for c in claims if c.get("confidence", 0) > 0.9]
        return verified[:10]

    def _extract_key_points(self, data: Dict) -> List[str]:
        """Extract key points from research."""
        claims = data.get("claims", [])
        return [c.get("canonical_claim", str(c))[:200] for c in claims[:10]]
