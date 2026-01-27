"""Claim extraction models for the Claim Extractor pipeline.

This module defines the data models for claim extraction, including:
- ClaimAnchor: Location reference (timestamp, line range, image index)
- Claim: Individual extracted claim with type, confidence, and anchor
- ClaimsDocument: Complete output document for a claim extraction job
- Entity Index: People, organizations, places, and unnamed entities with evidence

Claim Extractor v2 Updates (2026-01-27):
- Entity Index with excerpt+anchor backed entities
- Anchor validation (no guessed timestamps)
- Warning codes for anchor coercion
- Run-scoped claims_doc generation support
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, model_validator


class ClaimType(str, Enum):
    """Type of claim - explicit or implied."""
    EXPLICIT = "explicit"  # Directly stated in the source
    IMPLIED = "implied"    # Inferred from context but not directly stated


class ConfidenceLevel(str, Enum):
    """Confidence level for extracted claims."""
    HIGH = "high"      # Clear, unambiguous claim
    MEDIUM = "medium"  # Reasonably clear but some interpretation needed
    LOW = "low"        # Significant interpretation required


class SourceType(str, Enum):
    """Type of source being analyzed."""
    YOUTUBE = "youtube"
    ARTICLE = "article"
    TEXT = "text"
    SCREENSHOT = "screenshot"


class AnchorType(str, Enum):
    """Type of anchor used for claim/entity evidence."""
    YOUTUBE_TIMESTAMP = "youtube_timestamp"  # Requires real timing from transcript_segments
    TEXT_LINE_RANGE = "text_line_range"      # Line number range in text
    IMAGE_INDEX = "image_index"              # Screenshot index with region


class WarningCode(str, Enum):
    """Warning codes for claim extraction issues."""
    TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS = "TIMESTAMP_UNAVAILABLE_USED_LINE_ANCHORS"
    TIMESTAMP_OUT_OF_BOUNDS = "TIMESTAMP_OUT_OF_BOUNDS"
    TIMESTAMP_COERCED_TO_LINE = "TIMESTAMP_COERCED_TO_LINE"
    ENTITY_MISSING_EVIDENCE = "ENTITY_MISSING_EVIDENCE"
    COREFERENCE_UNRESOLVED = "COREFERENCE_UNRESOLVED"
    CLAIM_MISSING_ANCHOR = "CLAIM_MISSING_ANCHOR"
    EMPTY_EXTRACTION = "EMPTY_EXTRACTION"


class EntityType(str, Enum):
    """Type of entity in the Entity Index."""
    PERSON = "person"
    ORG = "org"
    PLACE = "place"
    UNNAMED = "unnamed"  # "their founders", "a senior official", etc.


class TimestampAnchor(BaseModel):
    """Timestamp-based anchor for video/audio sources.

    IMPORTANT: Only use when transcript_segments with real timing are available.
    If timing is missing, use LineRangeAnchor instead.
    """
    start_seconds: int = Field(..., ge=0, description="Start time in seconds (must be >= 0)")
    end_seconds: Optional[int] = Field(None, ge=0, description="End time in seconds (optional)")
    formatted: str = Field(..., description="Human-readable timestamp (e.g., '2:34' or '2:34-2:45')")
    source_id: Optional[str] = Field(None, description="Source this anchor belongs to")


class LineRangeAnchor(BaseModel):
    """Line-based anchor for text sources."""
    start_line: int = Field(..., ge=1, description="Starting line number (1-indexed)")
    end_line: int = Field(..., ge=1, description="Ending line number (1-indexed)")
    excerpt: Optional[str] = Field(None, description="Verbatim text excerpt (required for entity evidence)")
    source_id: Optional[str] = Field(None, description="Source this anchor belongs to")


class ImageAnchor(BaseModel):
    """Image-based anchor for screenshot sources."""
    image_index: int = Field(..., ge=0, description="Index of the screenshot (0-indexed)")
    region: Optional[str] = Field(None, description="Region description (e.g., 'top-left', 'center')")
    ocr_excerpt: Optional[str] = Field(None, description="Verbatim OCR text excerpt")
    source_id: Optional[str] = Field(None, description="Source this anchor belongs to")


class ClaimAnchor(BaseModel):
    """Location reference for where a claim was extracted from.

    Only one of timestamp, line_range, or image should be set,
    depending on the source type.

    Every anchor MUST have a source_id. The source_id can be set on the
    nested anchor (TimestampAnchor, LineRangeAnchor, ImageAnchor) OR on
    this ClaimAnchor directly.
    """
    timestamp: Optional[TimestampAnchor] = Field(None, description="For video/audio sources with timing")
    line_range: Optional[LineRangeAnchor] = Field(None, description="For text sources or videos without timing")
    image: Optional[ImageAnchor] = Field(None, description="For screenshot sources")
    source_id: Optional[str] = Field(None, description="Source ID (can also be on nested anchor)")

    def get_anchor_type(self) -> AnchorType:
        """Get the type of anchor set."""
        if self.timestamp:
            return AnchorType.YOUTUBE_TIMESTAMP
        elif self.line_range:
            return AnchorType.TEXT_LINE_RANGE
        elif self.image:
            return AnchorType.IMAGE_INDEX
        return AnchorType.TEXT_LINE_RANGE  # Default to line range

    def get_source_id(self) -> Optional[str]:
        """Get source_id from anchor or nested anchor."""
        if self.source_id:
            return self.source_id
        if self.timestamp and self.timestamp.source_id:
            return self.timestamp.source_id
        if self.line_range and self.line_range.source_id:
            return self.line_range.source_id
        if self.image and self.image.source_id:
            return self.image.source_id
        return None

    def has_valid_anchor(self) -> bool:
        """Check if at least one anchor type is set."""
        return bool(self.timestamp or self.line_range or self.image)


# =============================================================================
# ENTITY INDEX MODELS (Claim Extractor v2)
# =============================================================================

class ContextEvidence(BaseModel):
    """Verbatim excerpt + anchor backing an entity or claim.

    Every entity and claim MUST have at least one ContextEvidence.
    """
    excerpt: str = Field(..., min_length=1, description="Verbatim text from source")
    anchor: ClaimAnchor = Field(..., description="Location reference for the excerpt")
    source_id: str = Field(..., description="Source ID where excerpt was found")


class Entity(BaseModel):
    """A named or described entity extracted from sources.

    Entities are excerpt+anchor backed to avoid hallucination.
    Unnamed entities (e.g., "their founders", "a senior official") are first-class.
    """
    entity_id: str = Field(..., description="Unique entity ID (ENT_001, ENT_002, ...)")
    canonical_label: str = Field(..., description="Primary name/label for the entity")
    entity_type: EntityType = Field(..., description="Type: person, org, place, unnamed")
    aliases: list[str] = Field(default_factory=list, description="Alternative names/references")
    context_summary: str = Field(
        ...,
        max_length=500,
        description="1-2 sentence summary derived ONLY from context_evidence"
    )
    context_evidence: list[ContextEvidence] = Field(
        ...,
        min_length=1,
        description=">=1 verbatim excerpt + anchor (required)"
    )
    top_anchors: list[ClaimAnchor] = Field(
        default_factory=list,
        description="Primary location references for this entity"
    )
    linked_claim_cluster_ids: list[str] = Field(
        default_factory=list,
        description="Claim cluster IDs involving this entity"
    )
    ambiguity_flags: list[str] = Field(
        default_factory=list,
        description="Flags for ambiguous references (e.g., 'last_name_only', 'role_based')"
    )


class EntityIndex(BaseModel):
    """Index of all entities extracted from sources.

    Entities are categorized by type: people, orgs, places, unnamed.
    Unresolved references are tracked separately.
    """
    people: list[Entity] = Field(default_factory=list, description="Person entities")
    orgs: list[Entity] = Field(default_factory=list, description="Organization entities")
    places: list[Entity] = Field(default_factory=list, description="Place entities")
    unnamed: list[Entity] = Field(
        default_factory=list,
        description="Unnamed/described entities (e.g., 'their founders', 'a whistleblower')"
    )
    unresolved_references: list[ContextEvidence] = Field(
        default_factory=list,
        description="Coreferences that could not be resolved (with evidence)"
    )

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        for entity_list in [self.people, self.orgs, self.places, self.unnamed]:
            for entity in entity_list:
                if entity.entity_id == entity_id:
                    return entity
        return None

    def all_entities(self) -> list[Entity]:
        """Get all entities across all categories."""
        return self.people + self.orgs + self.places + self.unnamed

    def entity_count(self) -> int:
        """Get total entity count."""
        return len(self.people) + len(self.orgs) + len(self.places) + len(self.unnamed)


# =============================================================================
# CLAIM INSTANCE AND CLUSTER (Claim Extractor v2)
# =============================================================================

class ClaimInstance(BaseModel):
    """A specific instance of a claim with verbatim excerpt and anchor.

    ClaimInstance contains the actual evidence backing a claim.
    Multiple instances can be grouped into a ClaimCluster.
    """
    instance_id: str = Field(..., description="Instance ID (INST_001, ...)")
    verbatim_excerpt: str = Field(..., min_length=1, description="Verbatim text from source")
    anchor: ClaimAnchor = Field(..., description="Location reference")
    source_id: str = Field(..., description="Source ID")
    entities_involved: list[str] = Field(
        default_factory=list,
        description="Entity IDs mentioned in this instance"
    )


class ClaimCluster(BaseModel):
    """A group of related claim instances across sources.

    ClaimCluster groups semantically similar claims that appear
    in multiple sources or multiple times in the same source.
    """
    cluster_id: str = Field(..., description="Cluster ID (CLST_001, ...)")
    canonical_claim: str = Field(..., description="Synthesized canonical claim statement")
    claim_type: ClaimType = Field(..., description="explicit or implied")
    confidence: ConfidenceLevel = Field(..., description="Aggregate confidence")
    instances: list[ClaimInstance] = Field(
        ...,
        min_length=1,
        description=">=1 claim instances with evidence"
    )
    entities_involved: list[str] = Field(
        default_factory=list,
        description="Entity IDs involved in this claim"
    )
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class Claim(BaseModel):
    """A single extracted claim with metadata.

    V2 Update: Claims now support entities_involved and verbatim_excerpt.
    For backward compatibility, the old fields are preserved.
    """
    claim_id: str = Field(..., description="Unique claim identifier (CLM_001, CLM_002, ...)")
    text: str = Field(..., description="The claim statement")
    claim_type: ClaimType = Field(..., description="Whether claim is explicit or implied")
    confidence: ConfidenceLevel = Field(..., description="Extraction confidence level")
    anchor: ClaimAnchor = Field(..., description="Location reference in source")
    source_id: str = Field(..., description="Reference to source (SRC_001, ...)")
    context: Optional[str] = Field(None, description="Surrounding context for the claim")
    tags: list[str] = Field(default_factory=list, description="Optional categorization tags")
    # V2 fields
    verbatim_excerpt: Optional[str] = Field(None, description="Verbatim text from source backing the claim")
    entities_involved: list[str] = Field(default_factory=list, description="Entity IDs involved in this claim")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json")

    def has_evidence(self) -> bool:
        """Check if claim has verbatim evidence."""
        return bool(self.verbatim_excerpt) or bool(self.anchor.line_range and self.anchor.line_range.excerpt)


class SourceSummary(BaseModel):
    """Summary of a source that was analyzed."""
    source_id: str = Field(..., description="Unique source identifier (SRC_001, ...)")
    source_type: SourceType = Field(..., description="Type of source")
    title: str = Field(..., description="Source title or identifier")
    url: Optional[str] = Field(None, description="URL if applicable")
    claim_count: int = Field(default=0, description="Number of claims extracted")
    explicit_count: int = Field(default=0, description="Number of explicit claims")
    implied_count: int = Field(default=0, description="Number of implied claims")
    # V2 fields
    timing_available: bool = Field(
        default=False,
        description="Whether transcript timing was available (for YouTube sources)"
    )
    anchor_type_used: Optional[AnchorType] = Field(
        None,
        description="Primary anchor type used for this source"
    )
    entity_count: int = Field(default=0, description="Number of entities extracted from this source")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json")


class ExtractionWarning(BaseModel):
    """A warning generated during claim extraction."""
    code: WarningCode = Field(..., description="Warning code")
    message: str = Field(..., description="Human-readable warning message")
    source_id: Optional[str] = Field(None, description="Source that triggered the warning")
    details: Optional[dict[str, Any]] = Field(None, description="Additional context")


class ClaimsDocumentMetadata(BaseModel):
    """Metadata for a claims document."""
    job_id: str = Field(..., description="Associated job ID")
    run_id: Optional[str] = Field(None, description="Run ID if generated from a semantic run")
    created_at: str = Field(..., description="ISO8601 creation timestamp")
    title: str = Field(..., description="User-provided or generated title")
    total_claims: int = Field(default=0, description="Total number of claims")
    total_explicit: int = Field(default=0, description="Total explicit claims")
    total_implied: int = Field(default=0, description="Total implied claims")
    source_count: int = Field(default=0, description="Number of sources analyzed")
    extraction_model: str = Field(default="gemini-2.5-flash", description="Model used for extraction")
    # V2 fields
    total_entities: int = Field(default=0, description="Total entities extracted")
    total_clusters: int = Field(default=0, description="Total claim clusters")
    version: str = Field(default="2.0", description="Claims document schema version")


class ClaimsDocument(BaseModel):
    """Complete claims extraction output document.

    This document is stored in Supabase Storage and displayed
    to users similarly to Doc 0/1/2 in the semantic pipeline.

    V2 Updates:
    - Entity Index with people/orgs/places/unnamed
    - Warnings for anchor issues and extraction problems
    - Claim clusters for grouping related claims
    """
    metadata: ClaimsDocumentMetadata = Field(..., description="Document metadata")
    sources: list[SourceSummary] = Field(default_factory=list, description="Analyzed sources")
    claims: list[Claim] = Field(default_factory=list, description="All extracted claims")
    # V2 fields
    entities: EntityIndex = Field(default_factory=EntityIndex, description="Entity index")
    clusters: list[ClaimCluster] = Field(default_factory=list, description="Claim clusters")
    warnings: list[ExtractionWarning] = Field(default_factory=list, description="Extraction warnings")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        """Generate markdown representation of the claims document."""
        lines = []

        # Header
        lines.append(f"# Claims Extraction: {self.metadata.title}")
        lines.append("")
        lines.append(f"**Generated:** {self.metadata.created_at}")
        lines.append(f"**Version:** {self.metadata.version}")
        lines.append(f"**Total Claims:** {self.metadata.total_claims} ({self.metadata.total_explicit} explicit, {self.metadata.total_implied} implied)")
        lines.append(f"**Total Entities:** {self.metadata.total_entities}")
        lines.append(f"**Sources Analyzed:** {self.metadata.source_count}")
        lines.append("")

        # Warnings section (if any)
        if self.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in self.warnings:
                lines.append(f"- **{warning.code.value}**: {warning.message}")
                if warning.source_id:
                    lines.append(f"  - Source: {warning.source_id}")
            lines.append("")

        # Sources summary
        lines.append("## Sources Analyzed")
        lines.append("")
        for src in self.sources:
            source_line = f"- **{src.title}** ({src.source_type.value})"
            if src.url:
                source_line = f"- **[{src.title}]({src.url})** ({src.source_type.value})"
            source_line += f" - {src.claim_count} claims, {src.entity_count} entities"
            if src.timing_available:
                source_line += " [timed]"
            lines.append(source_line)
        lines.append("")

        # Entity Index
        if self.entities.entity_count() > 0:
            lines.append("## Entity Index")
            lines.append("")

            if self.entities.people:
                lines.append("### People")
                for entity in self.entities.people:
                    lines.append(f"- **{entity.canonical_label}** ({entity.entity_id})")
                    lines.append(f"  - {entity.context_summary}")
                    if entity.aliases:
                        lines.append(f"  - Aliases: {', '.join(entity.aliases)}")
                lines.append("")

            if self.entities.orgs:
                lines.append("### Organizations")
                for entity in self.entities.orgs:
                    lines.append(f"- **{entity.canonical_label}** ({entity.entity_id})")
                    lines.append(f"  - {entity.context_summary}")
                lines.append("")

            if self.entities.places:
                lines.append("### Places")
                for entity in self.entities.places:
                    lines.append(f"- **{entity.canonical_label}** ({entity.entity_id})")
                    lines.append(f"  - {entity.context_summary}")
                lines.append("")

            if self.entities.unnamed:
                lines.append("### Unnamed/Described Entities")
                for entity in self.entities.unnamed:
                    lines.append(f"- **\"{entity.canonical_label}\"** ({entity.entity_id})")
                    lines.append(f"  - {entity.context_summary}")
                lines.append("")

        # Claims by source
        lines.append("## Extracted Claims")
        lines.append("")

        # Group claims by source
        claims_by_source: dict[str, list[Claim]] = {}
        for claim in self.claims:
            if claim.source_id not in claims_by_source:
                claims_by_source[claim.source_id] = []
            claims_by_source[claim.source_id].append(claim)

        for source in self.sources:
            source_claims = claims_by_source.get(source.source_id, [])
            if not source_claims:
                continue

            lines.append(f"### {source.title}")
            lines.append("")

            for claim in source_claims:
                # Claim type badge
                type_badge = "[EXPLICIT]" if claim.claim_type == ClaimType.EXPLICIT else "[IMPLIED]"
                conf_badge = f"({claim.confidence.value} confidence)"

                lines.append(f"**{claim.claim_id}** {type_badge} {conf_badge}")
                lines.append(f"> {claim.text}")
                lines.append("")

                # Verbatim excerpt if available
                if claim.verbatim_excerpt:
                    lines.append(f"*Excerpt: \"{claim.verbatim_excerpt[:150]}{'...' if len(claim.verbatim_excerpt) > 150 else ''}\"*")

                # Entities involved
                if claim.entities_involved:
                    lines.append(f"*Entities: {', '.join(claim.entities_involved)}*")

                # Anchor info
                anchor = claim.anchor
                if anchor.timestamp:
                    lines.append(f"*Timestamp: {anchor.timestamp.formatted}*")
                elif anchor.line_range:
                    lines.append(f"*Lines: {anchor.line_range.start_line}-{anchor.line_range.end_line}*")
                    if anchor.line_range.excerpt and not claim.verbatim_excerpt:
                        lines.append(f"*Excerpt: \"{anchor.line_range.excerpt[:100]}...\"*")
                elif anchor.image:
                    lines.append(f"*Screenshot #{anchor.image.image_index + 1}*")
                    if anchor.image.region:
                        lines.append(f"*Region: {anchor.image.region}*")

                lines.append("")

        return "\n".join(lines)

    @classmethod
    def create_empty(cls, job_id: str, title: str, run_id: Optional[str] = None) -> "ClaimsDocument":
        """Create an empty claims document."""
        from datetime import timezone
        return cls(
            metadata=ClaimsDocumentMetadata(
                job_id=job_id,
                run_id=run_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                title=title,
            ),
            sources=[],
            claims=[],
            entities=EntityIndex(),
            clusters=[],
            warnings=[],
        )

    def add_claim(self, claim: Claim) -> None:
        """Add a claim and update metadata counts."""
        self.claims.append(claim)
        self.metadata.total_claims += 1
        if claim.claim_type == ClaimType.EXPLICIT:
            self.metadata.total_explicit += 1
        else:
            self.metadata.total_implied += 1

    def add_source(self, source: SourceSummary) -> None:
        """Add a source and update metadata count."""
        self.sources.append(source)
        self.metadata.source_count += 1

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the appropriate category."""
        if entity.entity_type == EntityType.PERSON:
            self.entities.people.append(entity)
        elif entity.entity_type == EntityType.ORG:
            self.entities.orgs.append(entity)
        elif entity.entity_type == EntityType.PLACE:
            self.entities.places.append(entity)
        else:
            self.entities.unnamed.append(entity)
        self.metadata.total_entities += 1

    def add_warning(self, code: WarningCode, message: str, source_id: Optional[str] = None,
                   details: Optional[dict[str, Any]] = None) -> None:
        """Add an extraction warning."""
        self.warnings.append(ExtractionWarning(
            code=code,
            message=message,
            source_id=source_id,
            details=details,
        ))

    def add_cluster(self, cluster: ClaimCluster) -> None:
        """Add a claim cluster."""
        self.clusters.append(cluster)
        self.metadata.total_clusters += 1

    def get_warnings_by_code(self, code: WarningCode) -> list[ExtractionWarning]:
        """Get all warnings with a specific code."""
        return [w for w in self.warnings if w.code == code]
