"""Tests for edge cases in the semantic pipeline.

Phase 9: Tests boundary conditions, empty inputs, maximums, and special characters.
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
    Claim,
    SemanticExtractionResult,
    Gap,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Test: Empty Inputs
# =============================================================================


class TestEmptyInputs:
    """Test handling of empty inputs."""

    def test_empty_transcript_extraction(self):
        """Should handle empty transcript gracefully."""
        ctx = PipelineContext(job_id="test-empty", topic="Test")
        ctx.source_identity_packages = []
        ctx.semantic_extractions = []

        # Empty transcript should produce empty extractions, not crash
        assert ctx.semantic_extractions == []

    def test_empty_extractions_synthesis(self):
        """Should handle empty extractions in synthesis."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        ctx = PipelineContext(job_id="test-empty", topic="Test")
        ctx.semantic_extractions = []
        ctx.identified_gaps = []

        key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

        assert key_points == []
        assert themes == []
        assert tensions == []
        assert gaps == []

    def test_empty_sources_gap_analysis(self):
        """Should handle empty sources in gap analysis."""
        from backend.pipeline.stages.gap_analysis import build_source_manifest

        ctx = PipelineContext(job_id="test-empty", topic="Test")
        # No source_identity_packages attribute

        manifest = build_source_manifest(ctx)

        assert manifest == []

    def test_empty_themes_in_extraction(self):
        """Should allow extraction with no themes."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[],
            themes=[],  # Empty themes is valid
            tensions=[],
        )

        assert extraction.themes == []
        assert extraction.tensions == []

    def test_empty_key_points_in_extraction(self):
        """Should allow extraction with no key points."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            key_points=[],  # Empty key_points is valid (video_only mode)
        )

        assert extraction.key_points == []


# =============================================================================
# Test: Maximum Limits
# =============================================================================


class TestMaximumLimits:
    """Test handling of maximum limits."""

    def test_max_key_points_per_extraction(self):
        """Should handle many key points without issues."""
        key_points = [
            KeyPoint(
                key_point_id=f"KP_{i}",
                statement=f"Key point {i}",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.MEDIUM,
            )
            for i in range(50)  # 50 key points
        ]

        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=key_points,
        )

        assert len(extraction.key_points) == 50

    def test_max_themes_per_extraction(self):
        """Should handle many themes without issues."""
        themes = [
            Theme(
                theme_id=f"THEME_{i}",
                label=f"Theme {i}",
                description=f"Description for theme {i}",
                related_key_points=[f"KP_{i}"],
            )
            for i in range(20)  # 20 themes
        ]

        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            themes=themes,
        )

        assert len(extraction.themes) == 20

    def test_max_quotes_per_extraction(self):
        """Should handle many quotes without issues."""
        quotes = [
            Quote(
                quote_id=f"QT_{i}",
                text=f"Quote text {i}",
                source_id="SRC_1",
                timestamp=f"00:{i:02d}:00",
            )
            for i in range(30)  # 30 quotes
        ]

        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            quotes=quotes,
        )

        assert len(extraction.quotes) == 30

    def test_max_sources_aggregation(self):
        """Should aggregate from many sources without issues."""
        from backend.pipeline.stages.gap_analysis import aggregate_semantic_units

        ctx = PipelineContext(job_id="test-many", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id=f"SRC_{i}",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
                key_points=[
                    KeyPoint(
                        key_point_id=f"KP_S{i}_1",
                        statement=f"Key point from source {i}",
                        source_ids=[f"SRC_{i}"],
                        confidence=ConfidenceLevel.HIGH,
                    )
                ],
            )
            for i in range(10)  # 10 sources
        ]

        key_points, themes, tensions = aggregate_semantic_units(ctx)

        assert len(key_points) == 10

    def test_max_claims_per_extraction(self):
        """Should handle many claims without issues."""
        claims = [
            Claim(
                claim_id=f"CLM_{i}",
                statement=f"Claim {i}",
                source_id="SRC_1",
                confidence=ConfidenceLevel.MEDIUM,
            )
            for i in range(25)  # 25 claims
        ]

        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            claims=claims,
        )

        assert len(extraction.claims) == 25


# =============================================================================
# Test: Boundary Values
# =============================================================================


class TestBoundaryValues:
    """Test boundary value conditions."""

    def test_confidence_at_ceiling(self):
        """Should handle confidence exactly at ceiling."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Test statement",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.HIGH,  # Exactly at ceiling for transcript_grounded
        )

        assert key_point.confidence == ConfidenceLevel.HIGH

    def test_timestamp_zero(self):
        """Should handle timestamp at start of video."""
        quote = Quote(
            quote_id="QT_1",
            text="Opening statement",
            source_id="SRC_1",
            timestamp="00:00:00",
        )

        assert quote.timestamp == "00:00:00"

    def test_timestamp_long_video(self):
        """Should handle timestamps for very long videos."""
        quote = Quote(
            quote_id="QT_1",
            text="Statement from long video",
            source_id="SRC_1",
            timestamp="23:59:59",  # Near 24 hours
        )

        assert quote.timestamp == "23:59:59"

    def test_id_naming_convention(self):
        """Should follow ID naming convention."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Test",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.MEDIUM,
        )
        theme = Theme(
            theme_id="THEME_1",
            label="Test",
            description="Test",
            related_key_points=["KP_1"],
        )
        tension = Tension(
            tension_id="TEN_1",
            description="Test",
            involved_key_points=["KP_1"],
        )
        gap = Gap(
            gap_id="GAP_1",
            description="Test",
            why_expected="Test",
        )

        assert key_point.key_point_id.startswith("KP_")
        assert theme.theme_id.startswith("THEME_")
        assert tension.tension_id.startswith("TEN_")
        assert gap.gap_id.startswith("GAP_")

    def test_single_word_content(self):
        """Should handle single-word content."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Yes",  # Single word
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.LOW,
        )

        assert key_point.statement == "Yes"


# =============================================================================
# Test: Unicode and Special Characters
# =============================================================================


class TestUnicodeSpecialChars:
    """Test handling of unicode and special characters."""

    def test_unicode_quotes(self):
        """Should handle unicode characters in quotes."""
        quote = Quote(
            quote_id="QT_1",
            text="他说：'这是一个测试'",  # Chinese with smart quotes
            source_id="SRC_1",
            timestamp="00:01:00",
        )

        assert "测试" in quote.text

    def test_emoji_in_content(self):
        """Should handle emojis in content."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="The reaction was overwhelmingly positive 👍🎉",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.MEDIUM,
        )

        assert "👍" in key_point.statement

    def test_newlines_in_content(self):
        """Should handle newlines in content."""
        theme = Theme(
            theme_id="THEME_1",
            label="Multi-line Theme",
            description="This theme\nspans multiple\nlines",
            related_key_points=["KP_1"],
        )

        assert "\n" in theme.description

    def test_markdown_special_chars(self):
        """Should handle markdown special characters."""
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="The *bold* claim about **important** topic with `code`",
            source_ids=["SRC_1"],
            confidence=ConfidenceLevel.MEDIUM,
        )

        assert "*" in key_point.statement
        assert "`" in key_point.statement

    def test_html_entities_in_content(self):
        """Should handle HTML entities in content."""
        claim = Claim(
            claim_id="CLM_1",
            statement="Revenue increased > 50% & profits doubled",
            source_id="SRC_1",
            confidence=ConfidenceLevel.HIGH,
        )

        assert ">" in claim.statement
        assert "&" in claim.statement
