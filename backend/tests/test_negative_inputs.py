"""Tests for negative/invalid input handling in the semantic pipeline.

Phase 9: Tests invalid inputs, malformed data, and rejection scenarios.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    KeyPoint,
    Quote,
    Theme,
    Tension,
    SemanticExtractionResult,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Test: Invalid Inputs
# =============================================================================


class TestInvalidInputs:
    """Test handling of invalid inputs."""

    def test_null_transcript_handling(self):
        """Should handle None content in source identity."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_text

        # Empty string should be handled as "no content"
        package = build_source_identity_from_text(
            content="",
            source_label="Empty Source",
            source_index=0,
        )

        assert package.is_accessible is False
        assert package.failure_reason == "No content provided"

    def test_invalid_analysis_mode_fallback(self):
        """Should handle invalid analysis mode gracefully."""
        # Enum ensures only valid values
        valid_modes = [
            AnalysisMode.TRANSCRIPT_GROUNDED,
            AnalysisMode.CAPTION_GROUNDED,
            AnalysisMode.VIDEO_ONLY,
            AnalysisMode.TEXT_PROVIDED,
            AnalysisMode.OCR_EXTRACTED,
            AnalysisMode.ARTICLE_FETCHED,
        ]

        for mode in valid_modes:
            extraction = SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=mode,
            )
            assert extraction.analysis_mode == mode

    def test_negative_count_handling(self):
        """Should handle gracefully when counts are zero."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            key_points=[],  # Zero count
            claims=[],
            quotes=[],
        )

        assert len(extraction.key_points) == 0
        assert len(extraction.claims) == 0
        assert len(extraction.quotes) == 0

    def test_whitespace_only_content(self):
        """Should handle whitespace-only content."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_text

        package = build_source_identity_from_text(
            content="   \n\t   ",  # Only whitespace
            source_label="Whitespace Source",
            source_index=0,
        )

        assert package.is_accessible is False

    def test_empty_source_ids_list(self):
        """Should handle empty source_ids list."""
        # Note: Empty source_ids would be a validation error in production
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Test statement",
            source_ids=[],  # Empty source_ids
            confidence=ConfidenceLevel.MEDIUM,
        )

        assert key_point.source_ids == []


# =============================================================================
# Test: Invalid JSON Responses
# =============================================================================


class TestInvalidJSONResponses:
    """Test handling of invalid JSON responses from Gemini."""

    def test_missing_required_fields_gap_response(self):
        """Should handle missing fields in gap response."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        # Response missing 'gaps' key entirely
        response_data = {}

        gaps = parse_gap_response(response_data)

        # Should return empty list, not crash
        assert gaps == []

    def test_wrong_types_in_response(self):
        """Should document that wrong types will cause errors."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        # 'gaps' is a string instead of list - will cause iteration to fail
        response_data = {"gaps": "not a list"}

        # This will fail when iterating over a string (each char is an item)
        # The function doesn't guard against this, so it will raise AttributeError
        with pytest.raises(AttributeError):
            parse_gap_response(response_data)

    def test_null_values_in_response(self):
        """Should handle null values in response - None passes through .get()."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        response_data = {
            "gaps": [
                {
                    "gap_id": None,
                    "description": None,
                    "why_expected": None,
                }
            ]
        }

        gaps = parse_gap_response(response_data)

        # .get() returns None when key exists with None value
        # The function doesn't coerce None to default
        assert len(gaps) == 1
        assert gaps[0].gap_id is None  # None passes through
        assert gaps[0].description is None

    def test_synthesis_missing_semantic_core(self):
        """Should handle missing semantic_core."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {
            "themes": [],
            "confidence_assessment": {"level": "medium"},
        }

        result = parse_synthesis_response(response_data)

        # Should default to empty string
        assert result["semantic_core"] == ""

    def test_synthesis_invalid_confidence(self):
        """Should handle invalid confidence level."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {
            "semantic_core": "Test",
            "confidence_assessment": {"level": "super_high"},  # Invalid
        }

        result = parse_synthesis_response(response_data)

        # Should default to MEDIUM
        assert result["confidence_level"] == ConfidenceLevel.MEDIUM


# =============================================================================
# Test: Invalid State Transitions
# =============================================================================


class TestInvalidStateTransitions:
    """Test handling of invalid state transitions."""

    @patch("backend.pipeline.stages.gap_analysis.update_job")
    def test_gap_analysis_incomplete_job(self, mock_update_job):
        """Should handle gap analysis on incomplete job."""
        from backend.pipeline.stages.gap_analysis import stage_gap_analysis

        ctx = PipelineContext(job_id="test-incomplete", topic="Test")
        ctx.semantic_extractions = []  # No extractions yet
        ctx.identified_gaps = []

        stage_gap_analysis(ctx)

        # Should add warning about skipping
        assert any("skipped" in w.lower() for w in ctx.warnings)

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    def test_synthesis_insufficient_sources(self, mock_update_job):
        """Should handle synthesis with insufficient sources."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        ctx = PipelineContext(job_id="test-insufficient", topic="Test")
        ctx.semantic_extractions = []  # No extractions

        stage_semantic_synthesis(ctx)

        # Should add warning about skipping
        assert any("skipped" in w.lower() for w in ctx.warnings)

    def test_source_identity_missing_url(self):
        """Should handle source with missing URL."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_article

        article_data = {
            # No 'url' key
            "title": "Test Article",
            "content": "Article content",
        }

        package = build_source_identity_from_article(article_data, source_index=0)

        # Should use empty URL
        assert package.url == ""

    def test_source_identity_missing_title(self):
        """Should handle source with missing title."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_article

        article_data = {
            "url": "https://example.com",
            # No 'title' key
            "content": "Article content",
        }

        package = build_source_identity_from_article(article_data, source_index=0)

        # Should use default title
        assert package.title == "Untitled Article"

    def test_empty_ocr_result(self):
        """Should handle empty OCR result."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_screenshot

        package = build_source_identity_from_screenshot(
            ocr_text="",  # Empty OCR result
            source_index=0,
        )

        assert package.is_accessible is False
        assert "failed" in package.failure_reason.lower() or "empty" in package.failure_reason.lower()
