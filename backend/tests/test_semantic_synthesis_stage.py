"""Tests for semantic_synthesis.py stage.

Phase 9: Tests synthesis of unified semantic understanding from extractions.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    KeyPoint,
    Claim,
    Quote,
    Theme,
    Tension,
    SemanticExtractionResult,
    Gap,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_extraction():
    """Create a mock semantic extraction result."""
    return SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        key_points=[
            KeyPoint(
                key_point_id="KP_1",
                statement="Test key point 1",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
            KeyPoint(
                key_point_id="KP_2",
                statement="Test key point 2",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ],
        claims=[
            Claim(
                claim_id="CLM_1",
                statement="Test claim 1",
                source_id="SRC_1",
                supporting_quotes=["QT_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
        quotes=[
            Quote(
                quote_id="QT_1",
                text="Test quote text",
                source_id="SRC_1",
                timestamp="00:01:00",
            ),
        ],
        themes=[
            Theme(
                theme_id="THEME_1",
                label="Test Theme",
                description="A test theme description",
                related_key_points=["KP_1", "KP_2"],
            ),
        ],
        tensions=[
            Tension(
                tension_id="TEN_1",
                description="Test tension",
                involved_key_points=["KP_1"],
            ),
        ],
    )


@pytest.fixture
def mock_context(mock_extraction):
    """Create a mock pipeline context with extractions."""
    ctx = PipelineContext(
        job_id="test-job-123",
        topic="Test research topic",
    )
    ctx.semantic_extractions = [mock_extraction]
    ctx.identified_gaps = [
        Gap(
            gap_id="GAP_1",
            description="Test gap",
            why_expected="Expected because...",
            related_themes=["THEME_1"],
            related_key_points=["KP_1"],
        ),
    ]
    return ctx


@pytest.fixture
def multi_source_context():
    """Create a context with extractions from multiple sources."""
    ctx = PipelineContext(
        job_id="test-job-multi",
        topic="Multi-source test",
    )

    # Source 1 extraction
    extraction_1 = SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        key_points=[
            KeyPoint(
                key_point_id="KP_1",
                statement="Source 1 key point",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
    )

    # Source 2 extraction
    extraction_2 = SemanticExtractionResult(
        source_id="SRC_2",
        analysis_mode=AnalysisMode.CAPTION_GROUNDED,
        key_points=[
            KeyPoint(
                key_point_id="KP_2",
                statement="Source 2 key point",
                source_ids=["SRC_2"],
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ],
    )

    ctx.semantic_extractions = [extraction_1, extraction_2]
    ctx.identified_gaps = []
    return ctx


# =============================================================================
# Test: aggregate_for_synthesis
# =============================================================================


class TestAggregateForSynthesis:
    """Test aggregate_for_synthesis function."""

    def test_aggregates_key_points(self, mock_context):
        """Should aggregate all key points from extractions."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        key_points, themes, tensions, gaps = aggregate_for_synthesis(mock_context)

        assert len(key_points) == 2
        assert key_points[0]["key_point_id"] == "KP_1"
        assert key_points[1]["key_point_id"] == "KP_2"

    def test_aggregates_themes(self, mock_context):
        """Should aggregate all themes from extractions."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        key_points, themes, tensions, gaps = aggregate_for_synthesis(mock_context)

        assert len(themes) == 1
        assert themes[0]["theme_id"] == "THEME_1"

    def test_aggregates_tensions(self, mock_context):
        """Should aggregate all tensions from extractions."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        key_points, themes, tensions, gaps = aggregate_for_synthesis(mock_context)

        assert len(tensions) == 1
        assert tensions[0]["tension_id"] == "TEN_1"

    def test_aggregates_gaps(self, mock_context):
        """Should aggregate gaps from gap analysis."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        key_points, themes, tensions, gaps = aggregate_for_synthesis(mock_context)

        assert len(gaps) == 1
        assert gaps[0]["gap_id"] == "GAP_1"

    def test_handles_empty_extractions(self):
        """Should handle context with no extractions."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        ctx = PipelineContext(job_id="empty-job", topic="Empty")
        ctx.semantic_extractions = []
        ctx.identified_gaps = []

        key_points, themes, tensions, gaps = aggregate_for_synthesis(ctx)

        assert len(key_points) == 0
        assert len(themes) == 0
        assert len(tensions) == 0
        assert len(gaps) == 0


# =============================================================================
# Test: calculate_verification_rate
# =============================================================================


class TestCalculateVerificationRate:
    """Test calculate_verification_rate function."""

    def test_calculates_rate_with_verified_claims(self, mock_context):
        """Should calculate rate when claims have quotes."""
        from backend.pipeline.stages.semantic_synthesis import calculate_verification_rate

        rate = calculate_verification_rate(mock_context)

        # 1 claim with supporting quote out of 1 = 100%
        assert rate == 1.0

    def test_handles_no_claims(self):
        """Should return 0 when no claims exist."""
        from backend.pipeline.stages.semantic_synthesis import calculate_verification_rate

        ctx = PipelineContext(job_id="no-claims", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.VIDEO_ONLY,
            ),
        ]

        rate = calculate_verification_rate(ctx)

        assert rate == 0.0


# =============================================================================
# Test: parse_synthesis_response
# =============================================================================


class TestParseSynthesisResponse:
    """Test parse_synthesis_response function."""

    def test_parses_valid_response(self):
        """Should parse a valid synthesis response."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {
            "semantic_core": {
                "text": "This is the semantic core.",
                "based_on": ["KP_1", "KP_2"],
            },
            "themes": [
                {
                    "theme_id": "THEME_1",
                    "label": "Main Theme",
                    "description": "Theme description",
                    "supporting_key_points": ["KP_1"],
                }
            ],
            "speculative_observations": [
                {
                    "text": "Speculative observation",
                    "based_on": ["KP_2"],
                    "label": "speculative",
                }
            ],
            "confidence_assessment": {
                "level": "high",
                "reasoning": ["Good source diversity"],
            },
        }

        result = parse_synthesis_response(response_data)

        assert result["semantic_core"] == "This is the semantic core."
        assert result["semantic_core_based_on"] == ["KP_1", "KP_2"]
        assert len(result["themes"]) == 1
        assert len(result["speculative_observations"]) == 1
        assert result["confidence_level"] == ConfidenceLevel.HIGH

    def test_parses_string_semantic_core(self):
        """Should handle semantic_core as plain string."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {
            "semantic_core": "Plain text core",
            "themes": [],
            "speculative_observations": [],
            "confidence_assessment": {"level": "medium"},
        }

        result = parse_synthesis_response(response_data)

        assert result["semantic_core"] == "Plain text core"

    def test_handles_missing_fields(self):
        """Should handle missing optional fields with defaults."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {}

        result = parse_synthesis_response(response_data)

        assert result["semantic_core"] == ""
        assert result["themes"] == []
        assert result["confidence_level"] == ConfidenceLevel.MEDIUM

    def test_handles_invalid_confidence_level(self):
        """Should default to MEDIUM for invalid confidence."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        response_data = {
            "confidence_assessment": {"level": "invalid"},
        }

        result = parse_synthesis_response(response_data)

        assert result["confidence_level"] == ConfidenceLevel.MEDIUM


# =============================================================================
# Test: stage_semantic_synthesis
# =============================================================================


class TestStageSemanticSynthesis:
    """Test stage_semantic_synthesis main function."""

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    @patch("backend.pipeline.stages.semantic_synthesis.GeminiClient")
    def test_stage_success(self, mock_gemini_class, mock_update_job, mock_context):
        """Should successfully run synthesis stage."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        # Mock Gemini response
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {
                "semantic_core": {"text": "Synthesized core", "based_on": ["KP_1"]},
                "themes": [],
                "speculative_observations": [],
                "confidence_assessment": {"level": "medium", "reasoning": []},
            },
            "cost": 0.01,
        }

        stage_semantic_synthesis(mock_context)

        # Verify context was updated
        assert mock_context.semantic_core == "Synthesized core"
        assert mock_context.synthesized_themes == []
        assert mock_update_job.called

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    def test_stage_skips_without_extractions(self, mock_update_job):
        """Should skip synthesis when no extractions exist."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        ctx = PipelineContext(job_id="empty-job", topic="Test")
        ctx.semantic_extractions = []

        stage_semantic_synthesis(ctx)

        # Should add warning
        assert any("skipped" in w.lower() for w in ctx.warnings)

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    @patch("backend.pipeline.stages.semantic_synthesis.GeminiClient")
    def test_stage_handles_gemini_error(self, mock_gemini_class, mock_update_job, mock_context):
        """Should handle Gemini errors gracefully."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        # Mock Gemini error response
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "error": "API error",
        }

        stage_semantic_synthesis(mock_context)

        # Should add warning but not crash
        assert any("error" in w.lower() for w in mock_context.warnings)

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    @patch("backend.pipeline.stages.semantic_synthesis.GeminiClient")
    def test_stage_handles_exception(self, mock_gemini_class, mock_update_job, mock_context):
        """Should handle unexpected exceptions gracefully."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        # Mock Gemini to raise exception
        mock_gemini_class.side_effect = Exception("Unexpected error")

        stage_semantic_synthesis(mock_context)

        # Should set defaults and add warning
        assert mock_context.semantic_core == ""
        assert mock_context.synthesized_themes == []


# =============================================================================
# Test: Multi-source synthesis
# =============================================================================


class TestMultiSourceSynthesis:
    """Test synthesis with multiple sources."""

    def test_aggregates_from_multiple_sources(self, multi_source_context):
        """Should aggregate key points from all sources."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis

        key_points, themes, tensions, gaps = aggregate_for_synthesis(multi_source_context)

        assert len(key_points) == 2
        source_ids = {kp["source_ids"][0] for kp in key_points}
        assert "SRC_1" in source_ids
        assert "SRC_2" in source_ids

    def test_tracks_source_coverage(self, multi_source_context):
        """Should track which sources support each key point."""
        from backend.pipeline.stages.semantic_synthesis import aggregate_for_synthesis_with_attribution

        key_points, themes, tensions, gaps, coverage, conflicts = aggregate_for_synthesis_with_attribution(
            multi_source_context
        )

        assert "KP_1" in coverage
        assert "KP_2" in coverage
        assert coverage["KP_1"] == ["SRC_1"]
        assert coverage["KP_2"] == ["SRC_2"]
