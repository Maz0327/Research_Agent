"""Angle discovery system for finding unique documentary perspectives."""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from loguru import logger
from collections import Counter


class DiscoveredAngle(BaseModel):
    """A discovered angle for documentary production."""
    angle_type: str  # untold_perspective, process_focus, temporal_shift, etc.
    title: str
    description: str
    uniqueness_score: float  # 0-1, higher is more unique
    evidence: List[str]
    key_sources_needed: List[str]
    production_notes: str
    estimated_viewer_interest: str  # low, medium, high
    competition_analysis: Dict[str, Any]


class AngleDiscovery:
    """Find unique angles for documentary production."""

    def __init__(self):
        pass

    def discover_angles(
        self,
        topic: str,
        research_data: Dict,
        existing_coverage: Optional[List[str]] = None
    ) -> Dict:
        """
        Discover unique angles for documentary production.

        This helps find perspectives that haven't been covered.
        Example: Focus on legal battles instead of the crimes themselves.
        """

        # Step 1: Analyze existing coverage
        coverage_map = self.analyze_existing_coverage(topic, existing_coverage)

        # Step 2: Identify gaps in coverage
        coverage_gaps = self.find_coverage_gaps(coverage_map, research_data)

        # Step 3: Generate angle proposals
        angles = self.generate_angle_proposals(coverage_gaps, research_data)

        # Step 4: Score angles by uniqueness and feasibility
        scored_angles = self.score_angles(angles, coverage_map)

        # Step 5: Find unexpected connections
        connections = self.discover_connections(topic, research_data)

        return {
            "discovered_angles": [angle.model_dump() for angle in scored_angles],
            "coverage_map": coverage_map,
            "unexpected_connections": connections,
            "recommended_angle": self.select_best_angle(scored_angles)
        }

    def analyze_existing_coverage(
        self,
        topic: str,
        existing_titles: Optional[List[str]] = None
    ) -> Dict:
        """Analyze what angles have been covered in existing content."""

        coverage_patterns = {
            "heavily_covered": [],
            "moderately_covered": [],
            "rarely_covered": [],
            "not_covered": []
        }

        if not existing_titles:
            # If no titles provided, analyze based on common patterns
            logger.info("No existing titles provided, using default coverage analysis")
            return coverage_patterns

        # Analyze titles and descriptions to identify common angles
        common_themes = []
        for title in existing_titles:
            title_lower = title.lower()

            # Extract themes from title
            if any(word in title_lower for word in ["crime", "murder", "killed"]):
                common_themes.append("crime_details")
            if any(word in title_lower for word in ["victim", "survivor"]):
                common_themes.append("victim_story")
            if any(word in title_lower for word in ["investigation", "detective", "police"]):
                common_themes.append("investigation_process")
            if any(word in title_lower for word in ["legal", "trial", "court", "lawyer"]):
                common_themes.append("legal_proceedings")
            if any(word in title_lower for word in ["mystery", "unsolved", "conspiracy"]):
                common_themes.append("mystery_angle")
            if any(word in title_lower for word in ["family", "mother", "father", "child"]):
                common_themes.append("family_impact")

        # Count theme frequency
        theme_counts = Counter(common_themes)

        # Categorize by frequency
        for theme, count in theme_counts.items():
            if count > len(existing_titles) * 0.5:
                coverage_patterns["heavily_covered"].append(theme)
            elif count > len(existing_titles) * 0.2:
                coverage_patterns["moderately_covered"].append(theme)
            else:
                coverage_patterns["rarely_covered"].append(theme)

        # Identify what's missing entirely
        all_possible_angles = [
            "legal_strategy", "jury_perspective", "economic_impact",
            "media_manipulation", "systemic_issues", "family_aftermath",
            "community_response", "psychological_analysis", "forensic_details",
            "political_implications", "social_media_impact", "historical_context"
        ]

        covered = set(common_themes)
        coverage_patterns["not_covered"] = [
            angle for angle in all_possible_angles
            if angle not in covered
        ]

        logger.info(f"Coverage analysis complete: {len(coverage_patterns['not_covered'])} uncovered angles found")

        return coverage_patterns

    def find_coverage_gaps(
        self,
        coverage_map: Dict,
        research_data: Dict
    ) -> List[Dict]:
        """Identify what perspectives haven't been explored."""

        gaps = []

        # Check for missing perspectives from key entities
        entities = research_data.get("entities", {})
        people = entities.get("people", [])

        # Find people who are mentioned but not featured
        for person in people:
            mentions = person.get("mentions", 0)
            if mentions > 5:  # Significant but not central
                gaps.append({
                    "type": "untold_perspective",
                    "subject": person.get("name"),
                    "reason": f"Mentioned {mentions} times but no dedicated coverage",
                    "potential": "high"
                })

        # Check for temporal gaps
        timeline = research_data.get("timeline", [])
        if timeline and len(timeline) > 10:
            # Look for periods with many events but little coverage
            gaps.append({
                "type": "temporal_gap",
                "period": "Pre-incident buildup",
                "reason": "Events leading up to main incident rarely covered",
                "potential": "high"
            })

        # Check for process gaps
        if "legal_strategy" in coverage_map.get("not_covered", []):
            gaps.append({
                "type": "process_focus",
                "subject": "Legal maneuvering",
                "reason": "Behind-the-scenes legal strategy unexplored",
                "potential": "very_high"
            })

        # Check for systemic gaps
        if "systemic_issues" in coverage_map.get("not_covered", []):
            gaps.append({
                "type": "systemic_analysis",
                "subject": "Institutional failures",
                "reason": "Broader systemic context missing",
                "potential": "high"
            })

        logger.info(f"Found {len(gaps)} coverage gaps")

        return gaps

    def generate_angle_proposals(
        self,
        coverage_gaps: List[Dict],
        research_data: Dict
    ) -> List[DiscoveredAngle]:
        """Generate specific angle proposals based on gaps."""

        proposals = []

        for gap in coverage_gaps:
            gap_type = gap.get("type")

            if gap_type == "untold_perspective":
                subject = gap.get("subject", "Unknown")
                angle = DiscoveredAngle(
                    angle_type="untold_perspective",
                    title=f"The Untold Story: {subject}'s Perspective",
                    description=f"Focus on {subject}'s role and experience in the events",
                    uniqueness_score=0.85,
                    evidence=[gap.get("reason", "")],
                    key_sources_needed=[f"Interview with {subject}", "Personal documents", "Social media history"],
                    production_notes="Requires securing exclusive interviews or obtaining personal materials",
                    estimated_viewer_interest="high",
                    competition_analysis={
                        "similar_content": [],
                        "gap_in_coverage": f"No existing content from {subject}'s perspective"
                    }
                )
                proposals.append(angle)

            elif gap_type == "process_focus":
                angle = DiscoveredAngle(
                    angle_type="process_focus",
                    title="The Legal Chess Match: Behind Closed Doors",
                    description="Focus on legal strategies and courtroom tactics rather than the crime",
                    uniqueness_score=0.92,
                    evidence=[
                        "Legal strategy angle rarely explored in detail",
                        "Rich material in court transcripts unexplored",
                        "Multiple legal experts available for commentary"
                    ],
                    key_sources_needed=["Court transcripts", "Legal expert interviews", "Attorney statements"],
                    production_notes="Use animations to explain legal concepts; interview defense attorneys and prosecutors",
                    estimated_viewer_interest="high",
                    competition_analysis={
                        "similar_content": [],
                        "gap_in_coverage": "Legal strategy angle completely unexplored"
                    }
                )
                proposals.append(angle)

            elif gap_type == "temporal_gap":
                angle = DiscoveredAngle(
                    angle_type="temporal_shift",
                    title="The Prelude: What Led to the Breaking Point",
                    description="Focus on events leading up to the incident, not the incident itself",
                    uniqueness_score=0.78,
                    evidence=[
                        "Timeline shows significant events before main incident",
                        "These events provide crucial context",
                        "Pre-incident period rarely covered in depth"
                    ],
                    key_sources_needed=["Historical records", "Early interviews", "Contemporary reports"],
                    production_notes="Use timeline graphics to show buildup; emphasize cause-and-effect",
                    estimated_viewer_interest="medium",
                    competition_analysis={
                        "similar_content": ["Some coverage of background"],
                        "gap_in_coverage": "No dedicated focus on pre-incident period"
                    }
                )
                proposals.append(angle)

            elif gap_type == "systemic_analysis":
                angle = DiscoveredAngle(
                    angle_type="system_analysis",
                    title="System Failure: How Institutions Failed",
                    description="Analyze institutional and systemic failures that enabled the events",
                    uniqueness_score=0.88,
                    evidence=[
                        "Multiple institutional touchpoints identified",
                        "Pattern of systemic issues evident",
                        "Broader implications unexplored"
                    ],
                    key_sources_needed=["Policy documents", "Expert analysis", "Comparative cases"],
                    production_notes="Use infographics to show system connections; interview policy experts",
                    estimated_viewer_interest="medium",
                    competition_analysis={
                        "similar_content": ["Some mention of failures"],
                        "gap_in_coverage": "No systematic analysis of institutional role"
                    }
                )
                proposals.append(angle)

        # Always add a media analysis angle
        proposals.append(DiscoveredAngle(
            angle_type="meta_analysis",
            title="The Story of the Story: Media Coverage Analysis",
            description="Examine how media coverage shaped public perception",
            uniqueness_score=0.82,
            evidence=[
                "Significant media coverage provides rich material",
                "Meta-analysis angles gaining popularity",
                "Reveals bias and narrative construction"
            ],
            key_sources_needed=["Media archives", "Journalism experts", "Social media data"],
            production_notes="Side-by-side comparison of different media outlets; analyze narrative evolution",
            estimated_viewer_interest="high",
            competition_analysis={
                "similar_content": ["Occasional media criticism"],
                "gap_in_coverage": "Dedicated media analysis angle rare"
            }
        ))

        logger.info(f"Generated {len(proposals)} angle proposals")

        return proposals

    def score_angles(
        self,
        angles: List[DiscoveredAngle],
        coverage_map: Dict
    ) -> List[DiscoveredAngle]:
        """Score angles by uniqueness and documentary potential."""

        for angle in angles:
            # Boost score if angle type is completely uncovered
            if angle.angle_type in coverage_map.get("not_covered", []):
                angle.uniqueness_score = min(angle.uniqueness_score * 1.2, 1.0)

            # Adjust for feasibility based on sources needed
            sources_available = len([s for s in angle.key_sources_needed if "Interview" not in s])
            if sources_available > len(angle.key_sources_needed) / 2:
                # Boost if most sources are publicly available
                angle.uniqueness_score = min(angle.uniqueness_score * 1.1, 1.0)

        # Sort by uniqueness score
        angles.sort(key=lambda x: x.uniqueness_score, reverse=True)

        logger.info(f"Scored and ranked {len(angles)} angles")

        return angles

    def discover_connections(
        self,
        topic: str,
        research_data: Dict
    ) -> List[Dict]:
        """Find unexpected connections to other topics."""

        connections = []

        # Look for economic connections
        if "economic" not in topic.lower():
            connections.append({
                "connection_type": "economic",
                "description": "Economic impact on local community",
                "relevance": "Unexplored financial consequences and economic angles"
            })

        # Look for political connections
        entities = research_data.get("entities", {})
        orgs = entities.get("organizations", [])
        if any("political" in str(org).lower() or "government" in str(org).lower() for org in orgs):
            connections.append({
                "connection_type": "political",
                "description": "Political implications and responses",
                "relevance": "Political dimension rarely examined in depth"
            })

        # Look for technological connections
        if "social media" in topic.lower() or "internet" in topic.lower():
            connections.append({
                "connection_type": "technological",
                "description": "Role of technology and social media",
                "relevance": "Digital-age implications worth exploring"
            })

        # Always suggest historical parallels
        connections.append({
            "connection_type": "historical",
            "description": "Historical precedents and patterns",
            "relevance": "Similar cases from the past provide valuable context"
        })

        logger.info(f"Discovered {len(connections)} unexpected connections")

        return connections

    def select_best_angle(self, angles: List[DiscoveredAngle]) -> Dict:
        """Select the best angle for documentary production."""

        if not angles:
            return {
                "primary": "Standard investigative approach",
                "rationale": "No unique angles identified"
            }

        # Get top angle
        best = angles[0]

        # Consider combining complementary angles
        complementary = None
        for angle in angles[1:]:
            if angle.angle_type != best.angle_type and angle.uniqueness_score > 0.8:
                complementary = angle
                break

        if complementary:
            return {
                "primary": f"{best.title} + {complementary.title}",
                "rationale": f"Combines {best.angle_type} with {complementary.angle_type} for maximum impact",
                "primary_angle": best.model_dump(),
                "secondary_angle": complementary.model_dump()
            }
        else:
            return {
                "primary": best.title,
                "rationale": f"Highest uniqueness score ({best.uniqueness_score:.2f}) with {best.estimated_viewer_interest} viewer interest",
                "primary_angle": best.model_dump()
            }
