"""JSON Export: Lossless structured data for AI pipelines.

Provides a complete, machine-readable export of all research data
suitable for downstream LLM/RAG ingestion.
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from loguru import logger


@dataclass
class ResearchPacketJSON:
    """Lossless structured data export."""

    # Schema version for future compatibility
    schema_version: str = "1.0"

    # Metadata
    metadata: dict = field(default_factory=dict)

    # Core research data
    claims: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    timeline: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    validation: list = field(default_factory=list)

    # Documentary analysis
    documentary: dict = field(default_factory=dict)

    # Discovered angles
    angles: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "metadata": self.metadata,
            "claims": self.claims,
            "entities": self.entities,
            "timeline": self.timeline,
            "sources": self.sources,
            "validation": self.validation,
            "documentary": self.documentary,
            "angles": self.angles,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class JSONExporter:
    """Generate lossless JSON export from research data."""

    def export(
        self,
        job_id: str,
        topic: str,
        mode: str,
        created_at: datetime,
        claims: list,
        entities: dict,
        timeline_events: list,
        sources: list,
        validation_results: list,
        documentary_analysis: dict,
        discovered_angles: list,
    ) -> ResearchPacketJSON:
        """
        Generate structured JSON export from research data.

        Args:
            job_id: Unique job identifier
            topic: Research topic
            mode: Pipeline mode (investigation, breaking_news, etc.)
            created_at: Job creation timestamp
            claims: List of extracted claims with confidence scores
            entities: Dict of extracted entities (people, orgs, locations)
            timeline_events: List of timeline events
            sources: List of source items (web, YouTube, Reddit)
            validation_results: List of claim validation results
            documentary_analysis: Documentary intelligence output
            discovered_angles: List of discovered unique angles

        Returns:
            ResearchPacketJSON with all data structured
        """
        logger.info(f"Generating JSON export for job {job_id}")

        # Build metadata
        metadata = {
            "job_id": job_id,
            "topic": topic,
            "mode": mode,
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
            "exported_at": datetime.utcnow().isoformat(),
            "claims_count": len(claims),
            "sources_count": len(sources),
            "entities_count": sum(len(v) if isinstance(v, list) else 1 for v in entities.values()),
        }

        # Format claims with sources
        formatted_claims = self._format_claims(claims, validation_results)

        # Format entities
        formatted_entities = self._format_entities(entities)

        # Format timeline
        formatted_timeline = self._format_timeline(timeline_events)

        # Format sources with credibility tiers
        formatted_sources = self._format_sources(sources)

        # Format validation results
        formatted_validation = self._format_validation(validation_results)

        # Format angles
        formatted_angles = self._format_angles(discovered_angles)

        return ResearchPacketJSON(
            schema_version="1.0",
            metadata=metadata,
            claims=formatted_claims,
            entities=formatted_entities,
            timeline=formatted_timeline,
            sources=formatted_sources,
            validation=formatted_validation,
            documentary=documentary_analysis or {},
            angles=formatted_angles,
        )

    def _format_claims(self, claims: list, validation_results: list) -> list:
        """Format claims with validation status."""
        # Build validation lookup
        validation_lookup = {}
        for v in validation_results:
            claim_id = self._get_attr(v, "claim_id") or self._get_attr(v, "id")
            if claim_id:
                validation_lookup[claim_id] = v

        formatted = []
        for claim in claims:
            claim_id = self._get_attr(claim, "id") or self._get_attr(claim, "claim_id")
            claim_text = self._get_attr(claim, "text") or self._get_attr(claim, "claim")

            formatted_claim = {
                "id": claim_id,
                "text": claim_text,
                "confidence": self._get_attr(claim, "confidence") or self._get_attr(claim, "confidence_score") or 0.5,
                "sources": self._extract_claim_sources(claim),
                "entities": self._get_attr(claim, "entities") or [],
            }

            # Add validation if available
            if claim_id and claim_id in validation_lookup:
                val = validation_lookup[claim_id]
                formatted_claim["fact_check"] = {
                    "status": self._get_attr(val, "status") or self._get_attr(val, "result") or "unknown",
                    "evidence": self._get_attr(val, "evidence") or self._get_attr(val, "explanation") or "",
                    "sources": self._get_attr(val, "sources") or [],
                }

            formatted.append(formatted_claim)

        return formatted

    def _format_entities(self, entities: dict) -> dict:
        """Format entities by category."""
        formatted = {}
        for category, items in entities.items():
            if isinstance(items, list):
                formatted[category] = [
                    {
                        "name": self._get_attr(item, "name") or str(item),
                        "mentions": self._get_attr(item, "mentions") or self._get_attr(item, "count") or 1,
                        "first_source": self._get_attr(item, "source") or self._get_attr(item, "first_source") or None,
                    }
                    for item in items
                ]
            elif isinstance(items, dict):
                formatted[category] = items
            else:
                formatted[category] = [{"name": str(items), "mentions": 1}]
        return formatted

    def _format_timeline(self, timeline_events: list) -> list:
        """Format timeline events."""
        formatted = []
        for event in timeline_events:
            formatted.append({
                "date": self._get_attr(event, "date") or self._get_attr(event, "timestamp") or "unknown",
                "precision": self._get_attr(event, "precision") or "day",
                "event": self._get_attr(event, "description") or self._get_attr(event, "event") or self._get_attr(event, "text") or "",
                "sources": self._get_attr(event, "sources") or self._get_attr(event, "source_urls") or [],
            })
        return formatted

    def _format_sources(self, sources: list) -> list:
        """Format sources with credibility tiers."""
        formatted = []
        for source in sources:
            url = self._get_attr(source, "url") or ""
            source_type = self._get_attr(source, "type") or self._get_attr(source, "source_type") or self._infer_source_type(url)
            quality = self._get_attr(source, "quality_score") or self._get_attr(source, "score") or 0.5

            formatted.append({
                "url": url,
                "title": self._get_attr(source, "title") or "",
                "type": source_type,
                "credibility_tier": self._score_to_tier(quality),
                "published_at": self._get_attr(source, "published_at") or self._get_attr(source, "date") or None,
                "author": self._get_attr(source, "author") or None,
            })
        return formatted

    def _format_validation(self, validation_results: list) -> list:
        """Format validation results."""
        formatted = []
        for val in validation_results:
            formatted.append({
                "claim_id": self._get_attr(val, "claim_id") or self._get_attr(val, "id"),
                "status": self._get_attr(val, "status") or self._get_attr(val, "result") or "unknown",
                "confidence": self._get_attr(val, "confidence") or 0.5,
                "evidence": self._get_attr(val, "evidence") or self._get_attr(val, "explanation") or "",
                "sources": self._get_attr(val, "sources") or [],
            })
        return formatted

    def _format_angles(self, discovered_angles: list) -> list:
        """Format discovered angles."""
        if isinstance(discovered_angles, dict):
            # Handle dict format from angle discovery
            angles_list = discovered_angles.get("angles") or discovered_angles.get("discovered") or []
            if not angles_list:
                angles_list = [discovered_angles]
        else:
            angles_list = discovered_angles or []

        formatted = []
        for angle in angles_list:
            if isinstance(angle, dict):
                formatted.append({
                    "name": self._get_attr(angle, "name") or self._get_attr(angle, "angle") or "",
                    "description": self._get_attr(angle, "description") or "",
                    "confidence": self._get_attr(angle, "confidence") or 0.5,
                    "supporting_sources": self._get_attr(angle, "sources") or [],
                })
            elif isinstance(angle, str):
                formatted.append({"name": angle, "description": "", "confidence": 0.5})
        return formatted

    def _extract_claim_sources(self, claim) -> list:
        """Extract source URLs from a claim."""
        sources = self._get_attr(claim, "sources") or self._get_attr(claim, "source_urls") or []
        if isinstance(sources, str):
            return [sources]
        return [
            {"url": s.get("url") if isinstance(s, dict) else s}
            for s in sources
        ]

    def _get_attr(self, obj: Any, attr: str) -> Any:
        """Get attribute from object or dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)

    def _infer_source_type(self, url: str) -> str:
        """Infer source type from URL."""
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "video"
        if "reddit.com" in url_lower:
            return "social"
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "social"
        if any(domain in url_lower for domain in [".edu", "arxiv.org", "scholar.google"]):
            return "academic"
        if any(domain in url_lower for domain in ["nytimes.com", "bbc.com", "reuters.com", "ap.org"]):
            return "news"
        return "web"

    def _score_to_tier(self, score: float) -> str:
        """Convert quality score to credibility tier."""
        if score >= 0.8:
            return "tier_1"
        if score >= 0.5:
            return "tier_2"
        return "tier_3"
