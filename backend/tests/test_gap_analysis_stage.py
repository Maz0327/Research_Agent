"""Tests for gap_analysis.py stage.

Phase 9: Tests gap identification from semantic extractions.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional

from backend.models.semantic_units import (
    AnalysisMode,
    ConfidenceLevel,
    KeyPoint,
    Theme,
    Tension,
    SemanticExtractionResult,
    Gap,
)
from backend.pipeline.context import PipelineContext


# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockSourceIdentityPackage:
    """Mock source identity package for testing."""
    source_id: str
    source_type: str
    url: str
    title: str
    is_accessible: bool = True
    creator: Optional[str] = None


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_context():
    """Create a mock pipeline context with extractions."""
    ctx = PipelineContext(
        job_id="test-job-gap",
        topic="Test Gap Analysis Topic",
    )

    # Add semantic extractions
    ctx.semantic_extractions = [
        SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            key_points=[
                KeyPoint(
                    key_point_id="KP_1",
                    statement="Test key point 1",
                    source_ids=["SRC_1"],
                    confidence=ConfidenceLevel.HIGH,
                ),
            ],
            themes=[
                Theme(
                    theme_id="THEME_1",
                    label="Test Theme",
                    description="Theme description",
                    related_key_points=["KP_1"],
                ),
            ],
            tensions=[
                Tension(
                    tension_id="TEN_1",
                    description="Test tension",
                    involved_key_points=["KP_1"],
                ),
            ],
        ),
    ]

    # Add source identity packages
    ctx.source_identity_packages = [
        MockSourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test1",
            title="Test Video 1",
            is_accessible=True,
        ),
        MockSourceIdentityPackage(
            source_id="SRC_2",
            source_type="article",
            url="https://example.com/article",
            title="Test Article",
            is_accessible=False,
        ),
    ]

    ctx.identified_gaps = []
    return ctx


@pytest.fixture
def mock_context_no_extractions():
    """Create a mock pipeline context without extractions."""
    ctx = PipelineContext(
        job_id="test-job-empty",
        topic="Empty Topic",
    )
    ctx.semantic_extractions = []
    ctx.identified_gaps = []
    return ctx


# =============================================================================
# Test: parse_gap_response
# =============================================================================


class TestParseGapResponse:
    """Test parse_gap_response function."""

    def test_parse_gap_response_valid(self):
        """Should parse valid gap response."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        response_data = {
            "gaps": [
                {
                    "gap_id": "GAP_1",
                    "description": "Missing expert opinion",
                    "why_expected": "Topic involves technical details",
                    "related_themes": ["THEME_1"],
                    "related_key_points": ["KP_1"],
                    "suggested_research_direction": "Interview domain experts",
                },
                {
                    "gap_id": "GAP_2",
                    "description": "No opposing viewpoint",
                    "why_expected": "Controversial topic",
                    "related_themes": [],
                    "related_key_points": ["KP_2"],
                },
            ]
        }

        gaps = parse_gap_response(response_data)

        assert len(gaps) == 2
        assert gaps[0].gap_id == "GAP_1"
        assert gaps[0].description == "Missing expert opinion"
        assert gaps[0].why_expected == "Topic involves technical details"
        assert gaps[0].related_themes == ["THEME_1"]
        assert gaps[0].suggested_research_direction == "Interview domain experts"
        assert gaps[1].gap_id == "GAP_2"
        assert gaps[1].suggested_research_direction is None

    def test_parse_gap_response_empty(self):
        """Should handle empty response."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        response_data = {"gaps": []}
        gaps = parse_gap_response(response_data)
        assert len(gaps) == 0

    def test_parse_gap_response_missing_fields(self):
        """Should handle missing optional fields with defaults."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        response_data = {
            "gaps": [
                {
                    "description": "Minimal gap",
                }
            ]
        }

        gaps = parse_gap_response(response_data)

        assert len(gaps) == 1
        assert gaps[0].gap_id == "GAP_1"  # Auto-generated
        assert gaps[0].description == "Minimal gap"
        assert gaps[0].why_expected == ""
        assert gaps[0].related_themes == []
        assert gaps[0].related_key_points == []
        assert gaps[0].suggested_research_direction is None


# =============================================================================
# Test: build_source_manifest
# =============================================================================


class TestBuildSourceManifest:
    """Test build_source_manifest function."""

    def test_build_source_manifest(self, mock_context):
        """Should build manifest from packages."""
        from backend.pipeline.stages.gap_analysis import build_source_manifest

        manifest = build_source_manifest(mock_context)

        assert len(manifest) == 2
        assert manifest[0]["source_id"] == "SRC_1"
        assert manifest[0]["type"] == "youtube"
        assert manifest[0]["title"] == "Test Video 1"
        assert manifest[0]["status"] == "ingested"
        assert manifest[1]["source_id"] == "SRC_2"
        assert manifest[1]["status"] == "failed"

    def test_build_source_manifest_empty(self):
        """Should handle missing packages."""
        from backend.pipeline.stages.gap_analysis import build_source_manifest

        ctx = PipelineContext(job_id="test", topic="Test")
        # No source_identity_packages attribute

        manifest = build_source_manifest(ctx)

        assert len(manifest) == 0


# =============================================================================
# Test: aggregate_semantic_units
# =============================================================================


class TestAggregateSemanticUnits:
    """Test aggregate_semantic_units function."""

    def test_aggregate_semantic_units(self, mock_context):
        """Should aggregate units from extractions."""
        from backend.pipeline.stages.gap_analysis import aggregate_semantic_units

        key_points, themes, tensions = aggregate_semantic_units(mock_context)

        assert len(key_points) == 1
        assert key_points[0]["key_point_id"] == "KP_1"
        assert key_points[0]["statement"] == "Test key point 1"
        assert key_points[0]["confidence"] == "high"

        assert len(themes) == 1
        assert themes[0]["theme_id"] == "THEME_1"
        assert themes[0]["label"] == "Test Theme"

        assert len(tensions) == 1
        assert tensions[0]["tension_id"] == "TEN_1"


# =============================================================================
# Test: stage_gap_analysis
# =============================================================================


class TestStageGapAnalysis:
    """Test stage_gap_analysis main function."""

    @patch("backend.pipeline.stages.gap_analysis.update_job")
    @patch("backend.pipeline.stages.gap_analysis.GeminiClient")
    def test_stage_gap_analysis_success(self, mock_gemini_class, mock_update_job, mock_context):
        """Should successfully run gap analysis stage."""
        from backend.pipeline.stages.gap_analysis import stage_gap_analysis

        # Mock Gemini response
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {
                "gaps": [
                    {
                        "gap_id": "GAP_1",
                        "description": "Missing primary source",
                        "why_expected": "Claims need verification",
                        "related_themes": ["THEME_1"],
                        "related_key_points": ["KP_1"],
                    }
                ]
            },
            "cost": 0.01,
        }

        stage_gap_analysis(mock_context)

        # Verify gaps were identified
        assert len(mock_context.identified_gaps) == 1
        assert mock_context.identified_gaps[0].gap_id == "GAP_1"
        assert mock_update_job.called

    @patch("backend.pipeline.stages.gap_analysis.update_job")
    def test_stage_gap_analysis_no_extractions(self, mock_update_job, mock_context_no_extractions):
        """Should skip when no extractions exist."""
        from backend.pipeline.stages.gap_analysis import stage_gap_analysis

        stage_gap_analysis(mock_context_no_extractions)

        # Should add warning
        assert any("skipped" in w.lower() for w in mock_context_no_extractions.warnings)
        assert len(mock_context_no_extractions.identified_gaps) == 0
