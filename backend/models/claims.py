"""Claim extraction models for the Claim Extractor pipeline.

This module defines the data models for claim extraction, including:
- ClaimAnchor: Location reference (timestamp, line range, image index)
- Claim: Individual extracted claim with type, confidence, and anchor
- ClaimsDocument: Complete output document for a claim extraction job
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field


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


class TimestampAnchor(BaseModel):
    """Timestamp-based anchor for video/audio sources."""
    start_seconds: int = Field(..., description="Start time in seconds")
    end_seconds: Optional[int] = Field(None, description="End time in seconds (optional)")
    formatted: str = Field(..., description="Human-readable timestamp (e.g., '2:34' or '2:34-2:45')")


class LineRangeAnchor(BaseModel):
    """Line-based anchor for text sources."""
    start_line: int = Field(..., ge=1, description="Starting line number (1-indexed)")
    end_line: int = Field(..., ge=1, description="Ending line number (1-indexed)")
    excerpt: Optional[str] = Field(None, description="Relevant text excerpt")


class ImageAnchor(BaseModel):
    """Image-based anchor for screenshot sources."""
    image_index: int = Field(..., ge=0, description="Index of the screenshot (0-indexed)")
    region: Optional[str] = Field(None, description="Region description (e.g., 'top-left', 'center')")
    ocr_excerpt: Optional[str] = Field(None, description="Relevant OCR text excerpt")


class ClaimAnchor(BaseModel):
    """Location reference for where a claim was extracted from.

    Only one of timestamp, line_range, or image should be set,
    depending on the source type.
    """
    timestamp: Optional[TimestampAnchor] = Field(None, description="For video/audio sources")
    line_range: Optional[LineRangeAnchor] = Field(None, description="For text sources")
    image: Optional[ImageAnchor] = Field(None, description="For screenshot sources")

    def get_anchor_type(self) -> str:
        """Get the type of anchor set."""
        if self.timestamp:
            return "timestamp"
        elif self.line_range:
            return "line_range"
        elif self.image:
            return "image"
        return "unknown"


class Claim(BaseModel):
    """A single extracted claim with metadata."""
    claim_id: str = Field(..., description="Unique claim identifier (CLM_001, CLM_002, ...)")
    text: str = Field(..., description="The claim statement")
    claim_type: ClaimType = Field(..., description="Whether claim is explicit or implied")
    confidence: ConfidenceLevel = Field(..., description="Extraction confidence level")
    anchor: ClaimAnchor = Field(..., description="Location reference in source")
    source_id: str = Field(..., description="Reference to source (SRC_001, ...)")
    context: Optional[str] = Field(None, description="Surrounding context for the claim")
    tags: list[str] = Field(default_factory=list, description="Optional categorization tags")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json")


class SourceSummary(BaseModel):
    """Summary of a source that was analyzed."""
    source_id: str = Field(..., description="Unique source identifier (SRC_001, ...)")
    source_type: SourceType = Field(..., description="Type of source")
    title: str = Field(..., description="Source title or identifier")
    url: Optional[str] = Field(None, description="URL if applicable")
    claim_count: int = Field(default=0, description="Number of claims extracted")
    explicit_count: int = Field(default=0, description="Number of explicit claims")
    implied_count: int = Field(default=0, description="Number of implied claims")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump(mode="json")


class ClaimsDocumentMetadata(BaseModel):
    """Metadata for a claims document."""
    job_id: str = Field(..., description="Associated job ID")
    created_at: str = Field(..., description="ISO8601 creation timestamp")
    title: str = Field(..., description="User-provided or generated title")
    total_claims: int = Field(default=0, description="Total number of claims")
    total_explicit: int = Field(default=0, description="Total explicit claims")
    total_implied: int = Field(default=0, description="Total implied claims")
    source_count: int = Field(default=0, description="Number of sources analyzed")
    extraction_model: str = Field(default="gemini-2.5-flash", description="Model used for extraction")


class ClaimsDocument(BaseModel):
    """Complete claims extraction output document.

    This document is stored in Supabase Storage and displayed
    to users similarly to Doc 0/1/2 in the semantic pipeline.
    """
    metadata: ClaimsDocumentMetadata = Field(..., description="Document metadata")
    sources: list[SourceSummary] = Field(default_factory=list, description="Analyzed sources")
    claims: list[Claim] = Field(default_factory=list, description="All extracted claims")

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
        lines.append(f"**Total Claims:** {self.metadata.total_claims} ({self.metadata.total_explicit} explicit, {self.metadata.total_implied} implied)")
        lines.append(f"**Sources Analyzed:** {self.metadata.source_count}")
        lines.append("")

        # Sources summary
        lines.append("## Sources Analyzed")
        lines.append("")
        for src in self.sources:
            source_line = f"- **{src.title}** ({src.source_type.value})"
            if src.url:
                source_line = f"- **[{src.title}]({src.url})** ({src.source_type.value})"
            source_line += f" - {src.claim_count} claims"
            lines.append(source_line)
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

                # Anchor info
                anchor = claim.anchor
                if anchor.timestamp:
                    lines.append(f"*Timestamp: {anchor.timestamp.formatted}*")
                elif anchor.line_range:
                    lines.append(f"*Lines: {anchor.line_range.start_line}-{anchor.line_range.end_line}*")
                    if anchor.line_range.excerpt:
                        lines.append(f"*Excerpt: \"{anchor.line_range.excerpt[:100]}...\"*")
                elif anchor.image:
                    lines.append(f"*Screenshot #{anchor.image.image_index + 1}*")
                    if anchor.image.region:
                        lines.append(f"*Region: {anchor.image.region}*")

                lines.append("")

        return "\n".join(lines)

    @classmethod
    def create_empty(cls, job_id: str, title: str) -> "ClaimsDocument":
        """Create an empty claims document."""
        from datetime import timezone
        return cls(
            metadata=ClaimsDocumentMetadata(
                job_id=job_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                title=title,
            ),
            sources=[],
            claims=[],
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
