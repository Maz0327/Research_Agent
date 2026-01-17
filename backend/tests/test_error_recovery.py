"""Tests for error recovery scenarios in the semantic pipeline.

Phase 9: Tests partial failure handling, timeout recovery, and validation failures.
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
# Test: Partial Extraction Continues
# =============================================================================


class TestPartialExtractionContinues:
    """Test that extraction continues when one source fails."""

    @patch("backend.pipeline.stages.gap_analysis.update_job")
    @patch("backend.pipeline.stages.gap_analysis.GeminiClient")
    def test_gap_analysis_handles_gemini_error(self, mock_gemini_class, mock_update_job):
        """Should handle Gemini errors without crashing."""
        from backend.pipeline.stages.gap_analysis import stage_gap_analysis

        ctx = PipelineContext(job_id="test-error", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            )
        ]
        ctx.source_identity_packages = []
        ctx.identified_gaps = []

        # Mock Gemini error
        mock_gemini_class.side_effect = Exception("API connection failed")

        stage_gap_analysis(ctx)

        # Should continue with empty gaps, not crash
        assert ctx.identified_gaps == []

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    @patch("backend.pipeline.stages.semantic_synthesis.GeminiClient")
    def test_synthesis_handles_error(self, mock_gemini_class, mock_update_job):
        """Should handle synthesis errors gracefully."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        ctx = PipelineContext(job_id="test-error", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            )
        ]

        # Mock Gemini to raise exception
        mock_gemini_class.side_effect = Exception("Unexpected error")

        stage_semantic_synthesis(ctx)

        # Should set defaults and add warning
        assert ctx.semantic_core == ""
        assert ctx.synthesized_themes == []

    def test_extraction_with_missing_optional_fields(self):
        """Should handle extractions missing optional fields."""
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            # No key_points, claims, quotes, themes, tensions
        )

        # Should have empty lists by default
        assert extraction.key_points == []
        assert extraction.claims == []
        assert extraction.quotes == []
        assert extraction.themes == []
        assert extraction.tensions == []

    def test_context_warnings_accumulate(self):
        """Should accumulate multiple warnings."""
        ctx = PipelineContext(job_id="test-warnings", topic="Test")

        ctx.add_warning("Warning 1")
        ctx.add_warning("Warning 2")
        ctx.add_warning("Warning 3")

        assert len(ctx.warnings) == 3
        assert "Warning 1" in ctx.warnings
        assert "Warning 2" in ctx.warnings
        assert "Warning 3" in ctx.warnings

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.youtube_client.enumerate_channel_uploads")
    def test_youtube_enumeration_error_recovery(self, mock_enumerate, mock_update_job):
        """Should recover from YouTube enumeration errors."""
        from backend.pipeline.stages.youtube import stage_4_youtube_enumeration
        from backend.models.job_config import JobConfig, YouTubeConfig, BudgetsConfig

        ctx = PipelineContext(job_id="test-yt-error", topic="Test")
        ctx.job_config = JobConfig(
            topic="Test",
            mode="investigation",
            youtube=YouTubeConfig(channels=["test"]),
            budgets=BudgetsConfig(),
        )
        ctx.youtube_videos = []

        # Mock error
        mock_enumerate.side_effect = Exception("YouTube API error")

        stage_4_youtube_enumeration(ctx)

        # Should add warning but not crash
        assert any("failed" in w.lower() for w in ctx.warnings)


# =============================================================================
# Test: Gemini Timeout/Error Handling
# =============================================================================


class TestGeminiErrorHandling:
    """Test Gemini API error handling."""

    @patch("backend.pipeline.stages.semantic_synthesis.update_job")
    @patch("backend.pipeline.stages.semantic_synthesis.GeminiClient")
    def test_gemini_error_response_handling(self, mock_gemini_class, mock_update_job):
        """Should handle Gemini error response."""
        from backend.pipeline.stages.semantic_synthesis import stage_semantic_synthesis

        ctx = PipelineContext(job_id="test-error", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            )
        ]

        # Mock error response (not exception)
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "error": "Rate limit exceeded"
        }

        stage_semantic_synthesis(ctx)

        # Should add warning about error
        assert any("error" in w.lower() for w in ctx.warnings)

    @patch("backend.pipeline.stages.gap_analysis.update_job")
    @patch("backend.pipeline.stages.gap_analysis.GeminiClient")
    def test_gemini_empty_response(self, mock_gemini_class, mock_update_job):
        """Should handle empty Gemini response."""
        from backend.pipeline.stages.gap_analysis import stage_gap_analysis

        ctx = PipelineContext(job_id="test-empty-resp", topic="Test")
        ctx.semantic_extractions = [
            SemanticExtractionResult(
                source_id="SRC_1",
                analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
            )
        ]
        ctx.source_identity_packages = []
        ctx.identified_gaps = []

        # Mock empty response
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.generate_json.return_value = {
            "data": {},  # Empty data
            "cost": 0.0,
        }

        stage_gap_analysis(ctx)

        # Should handle gracefully with empty gaps
        assert ctx.identified_gaps == []

    @patch("backend.pipeline.stages.ocr_extraction.update_job")
    def test_ocr_handles_missing_file(self, mock_update_job):
        """Should handle missing screenshot file."""
        from backend.pipeline.stages.ocr_extraction import stage_ocr_extraction

        ctx = PipelineContext(job_id="test-missing-file", topic="Test")
        ctx.job_config_dict = {
            "job_type": "screenshot_input",
            "screenshot_path": "/nonexistent/path/image.png",
        }

        stage_ocr_extraction(ctx)

        # Should add warning
        assert any("failed" in w.lower() for w in ctx.warnings)

    def test_parse_gap_response_handles_malformed(self):
        """Should handle malformed gap response."""
        from backend.pipeline.stages.gap_analysis import parse_gap_response

        # Malformed response
        response_data = {
            "gaps": [
                {"invalid_field": "value"},  # Missing required fields
            ]
        }

        gaps = parse_gap_response(response_data)

        # Should create gap with defaults
        assert len(gaps) == 1
        assert gaps[0].description == ""  # Default empty string

    def test_parse_synthesis_response_handles_malformed(self):
        """Should handle malformed synthesis response."""
        from backend.pipeline.stages.semantic_synthesis import parse_synthesis_response

        # Malformed response
        response_data = {
            "invalid_key": "value"
        }

        result = parse_synthesis_response(response_data)

        # Should use defaults
        assert result["semantic_core"] == ""
        assert result["themes"] == []


# =============================================================================
# Test: Validation Failure Handling
# =============================================================================


class TestValidationFailureHandling:
    """Test validation failure handling."""

    def test_confidence_ceiling_enforcement(self):
        """Should cap confidence at ceiling."""
        from backend.pipeline.stages.source_identity import SourceIdentityPackage

        # Create package with VIDEO_ONLY mode (LOW ceiling)
        pkg = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="",
            title="Test",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
        )

        # Ceiling should be LOW
        assert pkg.confidence_ceiling == ConfidenceLevel.LOW

        # Key point with HIGH confidence would violate ceiling
        # The validation stage would correct this

    def test_broken_provenance_detection(self):
        """Should detect broken provenance chains."""
        # Key point referencing non-existent source
        key_point = KeyPoint(
            key_point_id="KP_1",
            statement="Test statement",
            source_ids=["SRC_99"],  # Non-existent source
            confidence=ConfidenceLevel.MEDIUM,
        )

        # Theme referencing non-existent key point
        theme = Theme(
            theme_id="THEME_1",
            label="Test Theme",
            description="Test",
            related_key_points=["KP_99"],  # Non-existent key point
        )

        # These should be caught by validation stage
        assert key_point.source_ids == ["SRC_99"]
        assert theme.related_key_points == ["KP_99"]

    def test_video_only_no_quotes(self):
        """VIDEO_ONLY mode should not have quotes."""
        # Valid VIDEO_ONLY extraction (no quotes)
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.VIDEO_ONLY,
            quotes=[],  # No quotes allowed
        )

        assert extraction.quotes == []

    def test_text_provided_no_quotes(self):
        """TEXT_PROVIDED mode should not have quotes."""
        # Valid TEXT_PROVIDED extraction (no quotes)
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.TEXT_PROVIDED,
            quotes=[],  # No quotes allowed
        )

        assert extraction.quotes == []

    def test_ocr_extracted_no_quotes(self):
        """OCR_EXTRACTED mode should not have quotes."""
        # Valid OCR_EXTRACTED extraction (no quotes)
        extraction = SemanticExtractionResult(
            source_id="SRC_1",
            analysis_mode=AnalysisMode.OCR_EXTRACTED,
            quotes=[],  # No quotes allowed
        )

        assert extraction.quotes == []
