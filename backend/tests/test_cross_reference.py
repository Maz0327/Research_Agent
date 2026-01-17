"""
Unit tests for cross-reference pipeline stage.

Tests for: extract_themes_from_extractions, extract_key_points_from_extractions,
extract_tensions_from_extractions, parse_cross_reference_response,
stage_cross_reference, run_cross_reference_analysis

Phase 9 Task 9.2.4
"""
import pytest
from unittest.mock import MagicMock, patch

from backend.pipeline.stages.cross_reference import (
    extract_themes_from_extractions,
    extract_key_points_from_extractions,
    extract_tensions_from_extractions,
    parse_cross_reference_response,
    stage_cross_reference,
    run_cross_reference_analysis,
)
from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    Gap,
    KeyPoint,
    SemanticExtractionResult,
    Tension,
    Theme,
)
from backend.models.document_outputs import CrossReferenceNotes
from backend.pipeline.context import PipelineContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_extraction():
    """Sample extraction result."""
    return SemanticExtractionResult(
        source_id="SRC_1",
        analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        themes=[
            Theme(
                theme_id="THEME_1",
                label="Financial Risk",
                description="Concerns about financial exposure",
                related_key_points=["KP_1", "KP_2"],
            ),
            Theme(
                theme_id="THEME_2",
                label="Market Volatility",
                description="Market uncertainty impacts",
                related_key_points=["KP_3"],
            ),
        ],
        key_points=[
            KeyPoint(
                key_point_id="KP_1",
                statement="Revenue declined 20% in Q4",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.HIGH,
            ),
            KeyPoint(
                key_point_id="KP_2",
                statement="Cost cuts planned for 2024",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.MEDIUM,
            ),
            KeyPoint(
                key_point_id="KP_3",
                statement="Market share stable despite pressure",
                source_ids=["SRC_1"],
                confidence=ConfidenceLevel.LOW,
            ),
        ],
        tensions=[
            Tension(
                tension_id="TEN_1",
                description="Revenue down but market share stable",
                involved_key_points=["KP_1", "KP_3"],
                is_cross_source=False,
            ),
        ],
    )


@pytest.fixture
def sample_extraction_2():
    """Second extraction for multi-source tests."""
    return SemanticExtractionResult(
        source_id="SRC_2",
        analysis_mode=AnalysisMode.ARTICLE_FETCHED,
        themes=[
            Theme(
                theme_id="THEME_3",
                label="Regulatory Pressure",
                description="Government scrutiny increasing",
                related_key_points=["KP_4"],
            ),
        ],
        key_points=[
            KeyPoint(
                key_point_id="KP_4",
                statement="New regulations expected in 2024",
                source_ids=["SRC_2"],
                confidence=ConfidenceLevel.HIGH,
            ),
        ],
    )


@pytest.fixture
def mock_context():
    """Mock pipeline context."""
    ctx = MagicMock(spec=PipelineContext)
    ctx.job_id = "JOB_1"
    ctx.warnings = []

    def add_warning(msg):
        ctx.warnings.append(msg)

    ctx.add_warning = add_warning
    return ctx


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini response for cross-reference."""
    return {
        "data": {
            "supports": [
                {
                    "existing_id": "KP_1",
                    "new_id": "KP_4",
                    "description": "New data supports revenue decline",
                }
            ],
            "contradicts": [
                {
                    "existing_id": "KP_3",
                    "new_id": "KP_5",
                    "description": "New data contradicts stability claim",
                }
            ],
            "new_tensions": [
                {
                    "tension_id": "TEN_NEW_1",
                    "description": "Cross-source conflict on outlook",
                    "involved_ids": ["KP_1", "KP_4"],
                    "is_cross_source": True,
                }
            ],
            "new_gaps": [
                {
                    "gap_id": "GAP_NEW_1",
                    "description": "Missing employee perspective",
                    "why_expected": "Employees would know internal situation",
                    "related_new_ids": ["KP_4"],
                }
            ],
            "summary": {
                "supports_count": 1,
                "contradicts_count": 1,
                "new_tensions_count": 1,
                "new_gaps_count": 1,
                "overall_alignment": "mixed",
            },
        },
        "cost": 0.02,
    }


# =============================================================================
# TestExtractThemesFromExtractions
# =============================================================================


class TestExtractThemesFromExtractions:
    """Tests for extract_themes_from_extractions function."""

    def test_extracts_themes_correctly(self, sample_extraction):
        """Should extract themes with source_id."""
        themes = extract_themes_from_extractions([sample_extraction])

        assert len(themes) == 2
        assert themes[0]["theme_id"] == "THEME_1"
        assert themes[0]["label"] == "Financial Risk"
        assert themes[0]["description"] == "Concerns about financial exposure"
        assert themes[0]["related_key_points"] == ["KP_1", "KP_2"]
        assert themes[0]["source_id"] == "SRC_1"

    def test_handles_multiple_extractions(self, sample_extraction, sample_extraction_2):
        """Should combine themes from multiple extractions."""
        themes = extract_themes_from_extractions([sample_extraction, sample_extraction_2])

        assert len(themes) == 3
        source_ids = [t["source_id"] for t in themes]
        assert "SRC_1" in source_ids
        assert "SRC_2" in source_ids

    def test_handles_empty_extractions(self):
        """Should return empty list for empty input."""
        themes = extract_themes_from_extractions([])
        assert themes == []

    def test_handles_extraction_with_no_themes(self, sample_extraction):
        """Should handle extraction with no themes."""
        sample_extraction.themes = []
        themes = extract_themes_from_extractions([sample_extraction])
        assert themes == []


# =============================================================================
# TestExtractKeyPointsFromExtractions
# =============================================================================


class TestExtractKeyPointsFromExtractions:
    """Tests for extract_key_points_from_extractions function."""

    def test_extracts_key_points_correctly(self, sample_extraction):
        """Should extract key points with confidence as string."""
        key_points = extract_key_points_from_extractions([sample_extraction])

        assert len(key_points) == 3
        assert key_points[0]["key_point_id"] == "KP_1"
        assert key_points[0]["statement"] == "Revenue declined 20% in Q4"
        assert key_points[0]["source_ids"] == ["SRC_1"]
        assert key_points[0]["confidence"] == "high"  # String value from enum

    def test_handles_multiple_extractions(self, sample_extraction, sample_extraction_2):
        """Should combine key points from multiple extractions."""
        key_points = extract_key_points_from_extractions([sample_extraction, sample_extraction_2])

        assert len(key_points) == 4

    def test_handles_empty_extractions(self):
        """Should return empty list for empty input."""
        key_points = extract_key_points_from_extractions([])
        assert key_points == []

    def test_preserves_confidence_levels(self, sample_extraction):
        """Should preserve all confidence levels correctly."""
        key_points = extract_key_points_from_extractions([sample_extraction])

        confidence_values = {kp["confidence"] for kp in key_points}
        assert "high" in confidence_values
        assert "medium" in confidence_values
        assert "low" in confidence_values


# =============================================================================
# TestExtractTensionsFromExtractions
# =============================================================================


class TestExtractTensionsFromExtractions:
    """Tests for extract_tensions_from_extractions function."""

    def test_extracts_tensions_correctly(self, sample_extraction):
        """Should extract tensions with involved key points."""
        tensions = extract_tensions_from_extractions([sample_extraction])

        assert len(tensions) == 1
        assert tensions[0]["tension_id"] == "TEN_1"
        assert tensions[0]["description"] == "Revenue down but market share stable"
        assert tensions[0]["involved_key_points"] == ["KP_1", "KP_3"]

    def test_handles_no_tensions(self, sample_extraction_2):
        """Should handle extraction with no tensions."""
        tensions = extract_tensions_from_extractions([sample_extraction_2])
        assert tensions == []

    def test_handles_empty_extractions(self):
        """Should return empty list for empty input."""
        tensions = extract_tensions_from_extractions([])
        assert tensions == []


# =============================================================================
# TestParseCrossReferenceResponse
# =============================================================================


class TestParseCrossReferenceResponse:
    """Tests for parse_cross_reference_response function."""

    def test_parses_complete_response(self, mock_gemini_response):
        """Should parse all fields correctly."""
        result = parse_cross_reference_response(mock_gemini_response["data"])

        assert isinstance(result, CrossReferenceNotes)
        assert len(result.supports) == 1
        assert len(result.contradicts) == 1
        assert len(result.new_tensions) == 1
        assert len(result.new_gaps) == 1

    def test_parses_supports(self, mock_gemini_response):
        """Should preserve supports as-is."""
        result = parse_cross_reference_response(mock_gemini_response["data"])

        assert result.supports[0]["existing_id"] == "KP_1"
        assert result.supports[0]["new_id"] == "KP_4"

    def test_parses_contradicts(self, mock_gemini_response):
        """Should preserve contradicts as-is."""
        result = parse_cross_reference_response(mock_gemini_response["data"])

        assert result.contradicts[0]["existing_id"] == "KP_3"

    def test_parses_new_tensions_as_tension_objects(self, mock_gemini_response):
        """Should convert new_tensions to Tension objects."""
        result = parse_cross_reference_response(mock_gemini_response["data"])

        tension = result.new_tensions[0]
        assert isinstance(tension, Tension)
        assert tension.tension_id == "TEN_NEW_1"
        assert tension.description == "Cross-source conflict on outlook"
        assert tension.involved_key_points == ["KP_1", "KP_4"]
        assert tension.is_cross_source is True

    def test_parses_new_gaps_as_gap_objects(self, mock_gemini_response):
        """Should convert new_gaps to Gap objects."""
        result = parse_cross_reference_response(mock_gemini_response["data"])

        gap = result.new_gaps[0]
        assert isinstance(gap, Gap)
        assert gap.gap_id == "GAP_NEW_1"
        assert gap.description == "Missing employee perspective"
        assert gap.why_expected == "Employees would know internal situation"
        assert gap.related_key_points == ["KP_4"]

    def test_handles_empty_response(self):
        """Should handle empty response gracefully."""
        result = parse_cross_reference_response({})

        assert result.supports == []
        assert result.contradicts == []
        assert result.new_tensions == []
        assert result.new_gaps == []

    def test_auto_generates_tension_ids(self):
        """Should auto-generate tension IDs if missing."""
        data = {
            "new_tensions": [
                {"description": "Tension 1", "involved_ids": ["KP_1"]},
                {"description": "Tension 2", "involved_ids": ["KP_2"]},
            ]
        }
        result = parse_cross_reference_response(data)

        assert result.new_tensions[0].tension_id == "TEN_1"
        assert result.new_tensions[1].tension_id == "TEN_2"

    def test_auto_generates_gap_ids(self):
        """Should auto-generate gap IDs if missing."""
        data = {
            "new_gaps": [
                {"description": "Gap 1", "why_expected": "Reason 1"},
                {"description": "Gap 2", "why_expected": "Reason 2"},
            ]
        }
        result = parse_cross_reference_response(data)

        assert result.new_gaps[0].gap_id == "GAP_1"
        assert result.new_gaps[1].gap_id == "GAP_2"

    def test_defaults_is_cross_source_to_true(self):
        """Should default is_cross_source to True for new tensions."""
        data = {
            "new_tensions": [
                {
                    "tension_id": "TEN_1",
                    "description": "Tension without is_cross_source",
                    "involved_ids": [],
                }
            ]
        }
        result = parse_cross_reference_response(data)

        assert result.new_tensions[0].is_cross_source is True


# =============================================================================
# TestStageCrossReference
# =============================================================================


class TestStageCrossReference:
    """Tests for stage_cross_reference pipeline stage."""

    @patch("backend.pipeline.stages.cross_reference.update_job")
    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_calls_update_job(self, mock_client_class, mock_update_job, mock_context, sample_extraction, sample_extraction_2):
        """Should call update_job at start."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = [sample_extraction_2]

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {"data": {}, "cost": 0.01}

        stage_cross_reference(mock_context)

        mock_update_job.assert_called()
        first_call = mock_update_job.call_args_list[0]
        assert first_call.kwargs["stage"] == "cross_reference"

    @patch("backend.pipeline.stages.cross_reference.update_job")
    def test_skips_when_no_original_extractions(self, mock_update_job, mock_context):
        """Should skip and warn when no original extractions."""
        mock_context.original_extractions = []
        mock_context.semantic_extractions = []

        stage_cross_reference(mock_context)

        assert any("no original extractions" in w for w in mock_context.warnings)

    @patch("backend.pipeline.stages.cross_reference.update_job")
    def test_skips_when_no_new_extractions(self, mock_update_job, mock_context, sample_extraction):
        """Should skip and warn when no new extractions."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = []

        stage_cross_reference(mock_context)

        assert any("no new extractions" in w for w in mock_context.warnings)

    @patch("backend.pipeline.stages.cross_reference.update_job")
    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_stores_cross_reference_notes(self, mock_client_class, mock_update_job, mock_context, sample_extraction, sample_extraction_2, mock_gemini_response):
        """Should store CrossReferenceNotes in context."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = [sample_extraction_2]

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = mock_gemini_response

        stage_cross_reference(mock_context)

        assert hasattr(mock_context, "cross_reference_notes")
        assert isinstance(mock_context.cross_reference_notes, CrossReferenceNotes)

    @patch("backend.pipeline.stages.cross_reference.update_job")
    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_handles_gemini_error(self, mock_client_class, mock_update_job, mock_context, sample_extraction, sample_extraction_2):
        """Should add warning on Gemini error."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = [sample_extraction_2]

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {"error": "API error"}

        stage_cross_reference(mock_context)

        assert any("Cross-reference error" in w for w in mock_context.warnings)

    @patch("backend.pipeline.stages.cross_reference.update_job")
    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_handles_exception(self, mock_client_class, mock_update_job, mock_context, sample_extraction, sample_extraction_2):
        """Should add warning and set default notes on exception."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = [sample_extraction_2]

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.side_effect = Exception("Connection failed")

        stage_cross_reference(mock_context)

        assert any("Cross-reference error" in w for w in mock_context.warnings)
        assert hasattr(mock_context, "cross_reference_notes")
        assert mock_context.cross_reference_notes.supports == []

    @patch("backend.pipeline.stages.cross_reference.update_job")
    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_tracks_cost(self, mock_client_class, mock_update_job, mock_context, sample_extraction, sample_extraction_2, mock_gemini_response):
        """Should track cost if add_cost available."""
        mock_context.original_extractions = [sample_extraction]
        mock_context.semantic_extractions = [sample_extraction_2]
        mock_context.add_cost = MagicMock()

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = mock_gemini_response

        stage_cross_reference(mock_context)

        mock_context.add_cost.assert_called_once_with("gemini_cross_reference", 0.02)


# =============================================================================
# TestRunCrossReferenceAnalysis
# =============================================================================


class TestRunCrossReferenceAnalysis:
    """Tests for run_cross_reference_analysis standalone function."""

    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_returns_tuple(self, mock_client_class, sample_extraction, sample_extraction_2, mock_gemini_response):
        """Should return (CrossReferenceNotes, cost) tuple."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = mock_gemini_response

        result = run_cross_reference_analysis([sample_extraction], [sample_extraction_2])

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], CrossReferenceNotes)
        assert isinstance(result[1], float)

    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_returns_cost(self, mock_client_class, sample_extraction, sample_extraction_2, mock_gemini_response):
        """Should return correct cost."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = mock_gemini_response

        _, cost = run_cross_reference_analysis([sample_extraction], [sample_extraction_2])

        assert cost == 0.02

    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    def test_raises_on_error(self, mock_client_class, sample_extraction, sample_extraction_2):
        """Should raise RuntimeError on Gemini error."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = {"error": "API error"}

        with pytest.raises(RuntimeError, match="Cross-reference failed"):
            run_cross_reference_analysis([sample_extraction], [sample_extraction_2])

    @patch("backend.pipeline.stages.cross_reference.GeminiClient")
    @patch("backend.pipeline.stages.cross_reference.build_cross_reference_prompt")
    def test_calls_build_prompt(self, mock_build_prompt, mock_client_class, sample_extraction, sample_extraction_2, mock_gemini_response):
        """Should call build_cross_reference_prompt with correct args."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.generate_json.return_value = mock_gemini_response
        mock_build_prompt.return_value = "test prompt"

        run_cross_reference_analysis([sample_extraction], [sample_extraction_2])

        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args.kwargs

        assert call_kwargs["original_source_count"] == 1
        assert call_kwargs["new_source_count"] == 1
        assert len(call_kwargs["existing_themes"]) == 2
        assert len(call_kwargs["new_themes"]) == 1


# =============================================================================
# TestCrossReferenceIntegration
# =============================================================================


class TestCrossReferenceIntegration:
    """Integration tests for cross-reference flow."""

    def test_extraction_helpers_work_together(self, sample_extraction, sample_extraction_2):
        """All extraction helpers should produce consistent output."""
        extractions = [sample_extraction, sample_extraction_2]

        themes = extract_themes_from_extractions(extractions)
        key_points = extract_key_points_from_extractions(extractions)
        tensions = extract_tensions_from_extractions(extractions)

        # Verify all theme source_ids exist
        for theme in themes:
            assert theme["source_id"] in ["SRC_1", "SRC_2"]

        # Verify all key point source_ids exist
        for kp in key_points:
            for src_id in kp["source_ids"]:
                assert src_id in ["SRC_1", "SRC_2"]

    def test_parse_handles_realistic_response(self):
        """Should handle realistic Gemini response."""
        response = {
            "supports": [
                {"existing_id": "KP_1", "new_id": "KP_NEW_1", "description": "Confirms trend"},
                {"existing_id": "KP_2", "new_id": "KP_NEW_2", "description": "Supports claim"},
            ],
            "contradicts": [
                {"existing_id": "KP_3", "new_id": "KP_NEW_3", "description": "Direct contradiction"},
            ],
            "new_tensions": [
                {
                    "tension_id": "TEN_NEW_1",
                    "description": "Timeline discrepancy between sources",
                    "involved_ids": ["KP_1", "KP_NEW_1"],
                    "is_cross_source": True,
                },
                {
                    "tension_id": "TEN_NEW_2",
                    "description": "Conflicting expert opinions",
                    "involved_ids": ["KP_2", "KP_NEW_2"],
                    "is_cross_source": True,
                },
            ],
            "new_gaps": [
                {
                    "gap_id": "GAP_NEW_1",
                    "description": "Missing financial data for Q3",
                    "why_expected": "Quarterly reports should exist",
                    "related_new_ids": ["KP_NEW_1"],
                },
            ],
        }

        result = parse_cross_reference_response(response)

        assert len(result.supports) == 2
        assert len(result.contradicts) == 1
        assert len(result.new_tensions) == 2
        assert len(result.new_gaps) == 1

        # Verify tension structure
        for tension in result.new_tensions:
            assert tension.is_cross_source is True
            assert len(tension.involved_key_points) >= 1

        # Verify gap structure
        for gap in result.new_gaps:
            assert gap.why_expected != ""
