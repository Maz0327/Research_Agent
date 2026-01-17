"""Tests for ocr_extraction.py stage.

Phase 9: Tests OCR extraction from screenshots.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from backend.pipeline.context import PipelineContext


# =============================================================================
# Test: OCRResult dataclass
# =============================================================================


class TestOCRResult:
    """Test OCRResult dataclass."""

    def test_result_creation(self):
        """Should create result with required fields."""
        from backend.pipeline.stages.ocr_extraction import OCRResult

        result = OCRResult(
            text="Extracted text",
            word_count=2,
            confidence="high",
        )

        assert result.text == "Extracted text"
        assert result.word_count == 2
        assert result.confidence == "high"
        assert result.platform_detected is None
        assert result.missing_context_warning is False
        assert result.error_message is None

    def test_result_with_error(self):
        """Should handle error state."""
        from backend.pipeline.stages.ocr_extraction import OCRResult

        result = OCRResult(
            text="",
            word_count=0,
            confidence="low",
            error_message="File not found",
        )

        assert result.error_message == "File not found"


# =============================================================================
# Test: extract_text_from_screenshot
# =============================================================================


class TestExtractTextFromScreenshot:
    """Test extract_text_from_screenshot function."""

    def test_handles_missing_file(self):
        """Should handle missing screenshot file."""
        from backend.pipeline.stages.ocr_extraction import extract_text_from_screenshot

        result = extract_text_from_screenshot(
            image_path="/nonexistent/path/image.png",
            platform_hint="twitter",
        )

        assert result.text == ""
        assert result.word_count == 0
        assert "not found" in result.error_message

    @patch("backend.integrations.gemini_client.GeminiClient")
    def test_extracts_text_successfully(self, mock_gemini_class, tmp_path):
        """Should extract text from valid screenshot."""
        from backend.pipeline.stages.ocr_extraction import extract_text_from_screenshot

        # Create temp file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image data")

        # Mock Gemini response
        mock_client = MagicMock()
        mock_gemini_class.return_value = mock_client
        mock_client.analyze_image.return_value = {
            "text": '{"extracted_text": "Tweet content here", "platform_detected": "twitter", "content_quality": "high", "is_partial": false}'
        }

        result = extract_text_from_screenshot(
            image_path=str(test_image),
            platform_hint="twitter",
        )

        assert result.text == "Tweet content here"
        assert result.word_count == 3
        assert result.confidence == "high"
        assert result.platform_detected == "twitter"

    @patch("backend.integrations.gemini_client.GeminiClient")
    def test_handles_gemini_error(self, mock_gemini_class, tmp_path):
        """Should handle Gemini errors gracefully."""
        from backend.pipeline.stages.ocr_extraction import extract_text_from_screenshot

        # Create temp file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image data")

        # Mock Gemini error
        mock_gemini_class.side_effect = Exception("API error")

        result = extract_text_from_screenshot(
            image_path=str(test_image),
            platform_hint="other",
        )

        assert result.text == ""
        assert result.word_count == 0
        assert "API error" in result.error_message


# =============================================================================
# Test: stage_ocr_extraction
# =============================================================================


class TestStageOcrExtraction:
    """Test stage_ocr_extraction pipeline stage."""

    @patch("backend.pipeline.stages.ocr_extraction.update_job")
    def test_skips_non_screenshot_jobs(self, mock_update_job):
        """Should skip non-screenshot jobs."""
        from backend.pipeline.stages.ocr_extraction import stage_ocr_extraction

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.job_config_dict = {"job_type": "standard"}

        stage_ocr_extraction(ctx)

        # Should not update job for non-screenshot jobs
        assert not mock_update_job.called

    @patch("backend.pipeline.stages.ocr_extraction.update_job")
    @patch("backend.pipeline.stages.ocr_extraction.extract_text_from_screenshot")
    def test_processes_screenshot_job(self, mock_extract, mock_update_job, tmp_path):
        """Should process screenshot input job."""
        from backend.pipeline.stages.ocr_extraction import stage_ocr_extraction, OCRResult

        # Create temp file
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"fake image data")

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.job_config_dict = {
            "job_type": "screenshot_input",
            "screenshot_path": str(test_image),
            "platform_hint": "reddit",
        }

        # Mock OCR result
        mock_extract.return_value = OCRResult(
            text="Reddit post content",
            word_count=3,
            confidence="high",
            platform_detected="reddit",
        )

        stage_ocr_extraction(ctx)

        # Verify extraction was called
        mock_extract.assert_called_once_with(str(test_image), "reddit")
        assert ctx.ocr_result.word_count == 3
        assert mock_update_job.called
