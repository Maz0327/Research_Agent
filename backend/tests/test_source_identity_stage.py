"""Tests for source_identity.py stage.

Phase 9: Tests source identity resolution and packaging.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.semantic_units import AnalysisMode, ConfidenceLevel
from backend.pipeline.context import PipelineContext


# =============================================================================
# Test: SourceIdentityPackage
# =============================================================================


class TestSourceIdentityPackage:
    """Test SourceIdentityPackage dataclass."""

    def test_package_creation(self):
        """Should create package with required fields."""
        from backend.pipeline.stages.source_identity import SourceIdentityPackage

        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
        )

        assert package.source_id == "SRC_1"
        assert package.source_type == "youtube"
        assert package.url == "https://youtube.com/watch?v=test"
        assert package.title == "Test Video"
        assert package.is_accessible is True
        assert package.analysis_mode == AnalysisMode.VIDEO_ONLY

    def test_package_to_dict(self):
        """Should serialize to dictionary."""
        from backend.pipeline.stages.source_identity import SourceIdentityPackage

        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test",
            title="Test Video",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        result = package.to_dict()

        assert result["source_id"] == "SRC_1"
        assert result["source_type"] == "youtube"
        assert result["analysis_mode"] == "transcript_grounded"
        assert result["is_accessible"] is True

    def test_confidence_ceiling_property(self):
        """Should return correct ceiling for each mode."""
        from backend.pipeline.stages.source_identity import SourceIdentityPackage

        # Transcript grounded = HIGH
        pkg = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="",
            title="",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )
        assert pkg.confidence_ceiling == ConfidenceLevel.HIGH

        # Video only = LOW
        pkg.analysis_mode = AnalysisMode.VIDEO_ONLY
        assert pkg.confidence_ceiling == ConfidenceLevel.LOW

        # Text provided = MEDIUM
        pkg.analysis_mode = AnalysisMode.TEXT_PROVIDED
        assert pkg.confidence_ceiling == ConfidenceLevel.MEDIUM


# =============================================================================
# Test: build_source_identity_from_text
# =============================================================================


class TestBuildSourceIdentityFromText:
    """Test build_source_identity_from_text function."""

    def test_builds_text_identity(self):
        """Should build identity from user text."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_text

        package = build_source_identity_from_text(
            content="This is user-provided content.",
            source_label="WSJ Article",
            source_index=0,
            context_note="Behind paywall",
        )

        assert package.source_id == "SRC_1"
        assert package.source_type == "user_text"
        assert package.title == "WSJ Article"
        assert package.analysis_mode == AnalysisMode.TEXT_PROVIDED
        assert package.is_accessible is True
        assert package.user_provided is True
        assert package.context_note == "Behind paywall"
        assert package.content_word_count == 4

    def test_handles_empty_content(self):
        """Should handle empty content gracefully."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_text

        package = build_source_identity_from_text(
            content="",
            source_label="Empty Source",
            source_index=0,
        )

        assert package.is_accessible is False
        assert package.failure_reason == "No content provided"


# =============================================================================
# Test: build_source_identity_from_screenshot
# =============================================================================


class TestBuildSourceIdentityFromScreenshot:
    """Test build_source_identity_from_screenshot function."""

    def test_builds_screenshot_identity(self):
        """Should build identity from OCR text."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_screenshot

        package = build_source_identity_from_screenshot(
            ocr_text="Extracted text from screenshot",
            source_index=0,
            platform_hint="twitter",
            context_note="Tweet about topic",
        )

        assert package.source_id == "SRC_1"
        assert package.source_type == "screenshot"
        assert package.title == "Twitter/X Screenshot"
        assert package.analysis_mode == AnalysisMode.OCR_EXTRACTED
        assert package.is_accessible is True
        assert package.ocr_extracted is True
        assert package.platform_hint == "twitter"

    def test_handles_empty_ocr(self):
        """Should handle failed OCR gracefully."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_screenshot

        package = build_source_identity_from_screenshot(
            ocr_text="",
            source_index=0,
        )

        assert package.is_accessible is False
        assert package.failure_reason == "OCR extraction failed or empty"


# =============================================================================
# Test: build_source_identity_from_article
# =============================================================================


class TestBuildSourceIdentityFromArticle:
    """Test build_source_identity_from_article function."""

    def test_builds_article_identity(self):
        """Should build identity from article data."""
        from backend.pipeline.stages.source_identity import build_source_identity_from_article

        article_data = {
            "url": "https://example.com/article",
            "title": "Test Article",
            "author": "John Doe",
            "content": "Article content goes here.",
        }

        package = build_source_identity_from_article(article_data, source_index=0)

        assert package.source_id == "SRC_1"
        assert package.source_type == "article"
        assert package.title == "Test Article"
        assert package.creator == "John Doe"
        assert package.analysis_mode == AnalysisMode.TRANSCRIPT_GROUNDED
        assert package.is_accessible is True


# =============================================================================
# Test: stage_source_identity
# =============================================================================


class TestStageSourceIdentity:
    """Test stage_source_identity main function."""

    @patch("backend.pipeline.stages.source_identity.update_job")
    @patch("backend.pipeline.stages.source_identity.acquire_transcript")
    def test_stage_processes_videos(self, mock_acquire, mock_update_job):
        """Should process YouTube videos."""
        from backend.pipeline.stages.source_identity import stage_source_identity
        from backend.pipeline.transcript_acquisition import TranscriptResult

        # Mock context
        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = [
            {"url": "https://youtube.com/watch?v=test", "title": "Test Video"},
        ]
        ctx.web_sources = []
        ctx.reddit_posts = []

        # Mock transcript acquisition
        mock_result = MagicMock(spec=TranscriptResult)
        mock_result.text = "Transcript text"
        mock_result.transcript_source = MagicMock()
        mock_result.transcript_source.value = "supadata"
        mock_result.analysis_mode = AnalysisMode.TRANSCRIPT_GROUNDED
        mock_result.to_provenance.return_value = MagicMock()
        mock_acquire.return_value = mock_result

        with patch("backend.pipeline.stages.source_identity.is_transcript_available", return_value=True):
            stage_source_identity(ctx)

        assert len(ctx.source_identity_packages) == 1
        assert ctx.source_identity_packages[0].source_id == "SRC_1"
        assert mock_update_job.called

    @patch("backend.pipeline.stages.source_identity.update_job")
    def test_stage_processes_articles(self, mock_update_job):
        """Should process web articles."""
        from backend.pipeline.stages.source_identity import stage_source_identity

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = []
        ctx.web_sources = [
            {"url": "https://example.com", "title": "Article", "content": "Content"},
        ]
        ctx.reddit_posts = []

        stage_source_identity(ctx)

        assert len(ctx.source_identity_packages) == 1
        assert ctx.source_identity_packages[0].source_type == "article"
