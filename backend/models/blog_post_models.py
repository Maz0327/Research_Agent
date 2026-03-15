"""Blog Post (Doc 7) data models.

The Blog Post is a long-form SEO-friendly article generated from research.
It distills Doc 2 (Semantic Brief) claims and Doc 0 (Source Ledger) data
into a structured blog article with full provenance.

Provenance chain (enforced):
  Every section.claim_ids → must exist in Doc 2
  Every section.source_ids → must exist in Doc 0
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class BlogSection(BaseModel):
    """A section of the blog post with provenance."""
    section_id: str = Field(..., description="SECT_1, SECT_2, ...")
    heading: str = Field(..., min_length=3, description="Section heading")
    body: str = Field(..., min_length=20, description="Section body in markdown")
    claim_ids: list[str] = Field(
        default_factory=list,
        description="claim_ids from Doc 2 referenced in this section"
    )
    source_ids: list[str] = Field(
        default_factory=list,
        description="source_ids from Doc 0 referenced in this section"
    )


class BlogPostGuardrails(BaseModel):
    """Provenance acknowledgments — all must be True or the post is invalid."""
    no_new_facts_ack: bool = Field(
        True, description="No facts introduced beyond Doc 0 content"
    )
    all_facts_reference_doc2: bool = Field(
        True, description="All claim_ids reference Doc 2"
    )
    all_facts_reference_doc0: bool = Field(
        True, description="All source_ids reference Doc 0"
    )


class BlogPostDocument(BaseModel):
    """Blog Post — Doc 7.

    A long-form SEO-friendly article generated from research data.
    Every claim traces to Doc 2 and every source to Doc 0.
    """
    document_type: Literal["blog_post"] = "blog_post"
    job_id: str
    generated_at: str = Field(..., description="ISO datetime string")
    topic: str = Field(..., description="The research topic")
    source_count: int = Field(..., ge=1, description="Number of sources in the job")
    title: str = Field(..., min_length=10, description="Blog post title")
    subtitle: Optional[str] = Field(None, description="Optional subtitle")
    meta_description: str = Field(
        ...,
        max_length=160,
        description="SEO meta description, max 160 chars"
    )
    estimated_reading_time: str = Field(..., description="e.g. '5 min read'")
    sections: list[BlogSection] = Field(
        ...,
        min_length=3,
        max_length=12,
        description="3-12 content sections"
    )
    conclusion: str = Field(..., min_length=20, description="Conclusion paragraph")
    call_to_action: Optional[str] = Field(None, description="Optional CTA")
    seo_keywords: list[str] = Field(
        default_factory=list,
        description="SEO keywords for the article"
    )
    description_sources: list[dict] = Field(
        default_factory=list,
        description="Sources for attribution (DescriptionSource dicts)"
    )
    guardrails: BlogPostGuardrails = Field(
        default_factory=BlogPostGuardrails
    )

    @field_validator("sections")
    @classmethod
    def validate_section_ids(cls, v: list[BlogSection]) -> list[BlogSection]:
        """Ensure section_ids are sequential (SECT_1 through SECT_N)."""
        expected = {f"SECT_{i}" for i in range(1, len(v) + 1)}
        actual = {s.section_id for s in v}
        if actual != expected:
            raise ValueError(
                f"sections must have sequential IDs SECT_1..SECT_{len(v)}, got {sorted(actual)}"
            )
        return v

    def all_claim_ids(self) -> set[str]:
        """Return all claim_ids referenced in this blog post."""
        ids: set[str] = set()
        for s in self.sections:
            ids.update(s.claim_ids)
        return ids

    def all_source_ids(self) -> set[str]:
        """Return all source_ids referenced in this blog post."""
        ids: set[str] = set()
        for s in self.sections:
            ids.update(s.source_ids)
        for ds in self.description_sources:
            if ds.get("source_id"):
                ids.add(ds["source_id"])
        return ids
