"""Tests for Blog Post (Doc 7) models."""
import pytest

from backend.models.blog_post_models import (
    BlogPostDocument,
    BlogSection,
    BlogPostGuardrails,
)


def _make_section(section_id: str, heading: str = "Test Section") -> dict:
    """Create a minimal valid section dict."""
    return {
        "section_id": section_id,
        "heading": heading,
        "body": "This is the body of the section with enough content to pass validation.",
        "claim_ids": ["CLM_1"],
        "source_ids": ["SRC_1"],
    }


def _make_blog_post(**overrides) -> dict:
    """Create a minimal valid blog post dict."""
    base = {
        "document_type": "blog_post",
        "job_id": "test-job-123",
        "generated_at": "2026-03-15T00:00:00Z",
        "topic": "Test Topic",
        "source_count": 3,
        "title": "A Compelling Blog Post Title",
        "subtitle": "An optional subtitle",
        "meta_description": "This is a meta description for SEO, kept under 160 characters.",
        "estimated_reading_time": "5 min read",
        "sections": [
            _make_section("SECT_1", "Introduction"),
            _make_section("SECT_2", "Main Point"),
            _make_section("SECT_3", "Supporting Evidence"),
        ],
        "conclusion": "This is the conclusion paragraph that wraps everything up nicely.",
        "call_to_action": "Subscribe for more insights.",
        "seo_keywords": ["test", "blog", "research"],
        "description_sources": [
            {"source_id": "SRC_1", "title": "Source One", "url": "https://example.com"},
        ],
        "guardrails": {
            "no_new_facts_ack": True,
            "all_facts_reference_doc2": True,
            "all_facts_reference_doc0": True,
        },
    }
    base.update(overrides)
    return base


class TestBlogPostDocument:
    """Test BlogPostDocument validation."""

    def test_valid_blog_post(self):
        """A valid blog post should parse without errors."""
        data = _make_blog_post()
        doc = BlogPostDocument(**data)
        assert doc.document_type == "blog_post"
        assert doc.job_id == "test-job-123"
        assert len(doc.sections) == 3
        assert doc.title == "A Compelling Blog Post Title"

    def test_sequential_section_ids(self):
        """Section IDs must be sequential SECT_1..SECT_N."""
        data = _make_blog_post(sections=[
            _make_section("SECT_1"),
            _make_section("SECT_3"),  # Skipped SECT_2
            _make_section("SECT_4"),
        ])
        with pytest.raises(ValueError, match="sequential IDs"):
            BlogPostDocument(**data)

    def test_minimum_sections(self):
        """Must have at least 3 sections."""
        data = _make_blog_post(sections=[
            _make_section("SECT_1"),
            _make_section("SECT_2"),
        ])
        with pytest.raises(ValueError):
            BlogPostDocument(**data)

    def test_meta_description_max_length(self):
        """Meta description must be <= 160 chars."""
        data = _make_blog_post(meta_description="x" * 161)
        with pytest.raises(ValueError):
            BlogPostDocument(**data)

    def test_optional_fields(self):
        """Subtitle and CTA can be None."""
        data = _make_blog_post(subtitle=None, call_to_action=None)
        doc = BlogPostDocument(**data)
        assert doc.subtitle is None
        assert doc.call_to_action is None

    def test_all_claim_ids(self):
        """all_claim_ids() should collect from all sections."""
        data = _make_blog_post(sections=[
            _make_section("SECT_1"),
            {**_make_section("SECT_2"), "claim_ids": ["CLM_2", "CLM_3"]},
            _make_section("SECT_3"),
        ])
        doc = BlogPostDocument(**data)
        assert doc.all_claim_ids() == {"CLM_1", "CLM_2", "CLM_3"}

    def test_all_source_ids(self):
        """all_source_ids() should collect from sections and description_sources."""
        data = _make_blog_post(sections=[
            {**_make_section("SECT_1"), "source_ids": ["SRC_1"]},
            {**_make_section("SECT_2"), "source_ids": ["SRC_2"]},
            {**_make_section("SECT_3"), "source_ids": ["SRC_3"]},
        ])
        doc = BlogPostDocument(**data)
        # SRC_1 from both section and description_sources
        assert doc.all_source_ids() == {"SRC_1", "SRC_2", "SRC_3"}


class TestBlogSection:
    """Test BlogSection validation."""

    def test_valid_section(self):
        """A valid section should parse."""
        section = BlogSection(**_make_section("SECT_1"))
        assert section.section_id == "SECT_1"

    def test_heading_min_length(self):
        """Heading must be at least 3 chars."""
        with pytest.raises(ValueError):
            BlogSection(
                section_id="SECT_1",
                heading="Hi",
                body="This is enough body text for the validator.",
                claim_ids=[],
                source_ids=[],
            )
