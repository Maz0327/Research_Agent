"""
Unit tests for pipeline stages.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.pipeline.context import PipelineContext


@pytest.fixture
def mock_context():
    """Create mock pipeline context for testing."""
    ctx = PipelineContext(
        job_id="test-job-123",
        topic="Test research topic about AI ethics",
    )
    return ctx


class TestInitializationStage:
    """Tests for stage_0_initialize."""

    @patch("backend.pipeline.stages.initialization.update_job")
    @patch("backend.pipeline.stages.initialization.post_slack_message")
    def test_initialize_sets_job_running(self, mock_slack, mock_update, mock_context):
        """Initialize stage should set job status to running."""
        from backend.pipeline.stages.initialization import stage_0_initialize

        stage_0_initialize(mock_context)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "running"
        assert call_kwargs["stage"] == "initializing"
        assert call_kwargs["progress_percent"] == 0

    @patch("backend.pipeline.stages.initialization.update_job")
    @patch("backend.pipeline.stages.initialization.post_slack_message")
    def test_initialize_sends_slack_notification(self, mock_slack, mock_update, mock_context):
        """Initialize stage should send Slack notification."""
        from backend.pipeline.stages.initialization import stage_0_initialize

        stage_0_initialize(mock_context)

        mock_slack.assert_called_once()
        call_args = mock_slack.call_args[0]
        assert mock_context.job_id in call_args[1]


class TestCompletionStage:
    """Tests for stage_10_completion."""

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    @patch("backend.pipeline.stages.initialization.post_slack_message")
    def test_completion_sets_job_completed(self, mock_slack, mock_update, mock_storage, mock_context):
        """Completion stage should set job status to completed."""
        from backend.pipeline.stages.initialization import stage_10_completion

        mock_context.folder_url = "https://drive.google.com/folder/123"
        mock_context.doc_urls = {"test": "url"}
        mock_context.claims = [{"id": "1"}]
        mock_context.web_sources = [{"url": "http://example.com"}]
        mock_context.youtube_videos = []

        result = stage_10_completion(mock_context)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["status"] == "completed"
        assert call_kwargs["progress_percent"] == 100

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    @patch("backend.pipeline.stages.initialization.post_slack_message")
    def test_completion_returns_result_dict(self, mock_slack, mock_update, mock_storage, mock_context):
        """Completion stage should return result dictionary."""
        from backend.pipeline.stages.initialization import stage_10_completion

        mock_context.folder_url = "https://drive.google.com/folder/123"
        mock_context.claims = [{"id": "1"}, {"id": "2"}]
        mock_context.web_sources = [{"url": "http://example.com"}]
        mock_context.youtube_videos = [{"id": "vid1"}]

        result = stage_10_completion(mock_context)

        assert result["job_id"] == mock_context.job_id
        assert result["status"] == "completed"
        assert result["claims_count"] == 2
        assert result["sources_count"] == 1
        assert result["youtube_videos_count"] == 1

    @patch("backend.pipeline.stages.initialization.get_storage_client", return_value=None)
    @patch("backend.pipeline.stages.initialization.update_job")
    @patch("backend.pipeline.stages.initialization.post_slack_message")
    def test_completion_handles_missing_drive_folder(self, mock_slack, mock_update, mock_storage, mock_context):
        """Completion stage should handle missing Drive folder."""
        from backend.pipeline.stages.initialization import stage_10_completion

        mock_context.folder_url = None
        mock_context.claims = []
        mock_context.web_sources = []
        mock_context.youtube_videos = []

        result = stage_10_completion(mock_context)

        assert result["folder_url"] is None
        # Should still complete without error
        assert result["status"] == "completed"


class TestPipelineContext:
    """Tests for PipelineContext dataclass."""

    def test_context_initialization(self):
        """Context should initialize with defaults."""
        ctx = PipelineContext(
            job_id="test-123",
            topic="Test topic"
        )

        assert ctx.job_id == "test-123"
        assert ctx.topic == "Test topic"
        assert ctx.claims == []
        assert ctx.warnings == []
        assert ctx.outputs == {}

    def test_add_warning(self):
        """add_warning should append to warnings list."""
        ctx = PipelineContext(job_id="test", topic="test")

        ctx.add_warning("First warning")
        ctx.add_warning("Second warning")

        assert len(ctx.warnings) == 2
        assert "First warning" in ctx.warnings

    def test_set_output(self):
        """set_output should store markdown output."""
        ctx = PipelineContext(job_id="test", topic="test")

        ctx.set_output("research_map_md", "# Research Map\nContent here")

        assert "research_map_md" in ctx.outputs
        assert "Research Map" in ctx.outputs["research_map_md"]

    def test_add_cost_without_tracker(self):
        """add_cost should not fail without cost tracker."""
        ctx = PipelineContext(job_id="test", topic="test")

        # Should not raise
        ctx.add_cost("openai", 0.01)

    def test_get_cost_summary_without_tracker(self):
        """get_cost_summary should return empty dict without tracker."""
        ctx = PipelineContext(job_id="test", topic="test")

        summary = ctx.get_cost_summary()

        assert summary == {}


class TestDiscoveryStages:
    """Tests for discovery/quality gate stages."""

    @patch("backend.pipeline.stages.discovery.update_job")
    def test_quality_gate_updates_job(self, mock_update, mock_context):
        """Quality gate should update job progress."""
        from backend.pipeline.stages.discovery import stage_3_5_quality_gate

        # Add empty sources
        mock_context.web_sources = []

        stage_3_5_quality_gate(mock_context)

        # Quality gate should update job
        mock_update.assert_called()


class TestExtractionStages:
    """Tests for extraction stages."""

    @patch("backend.pipeline.stages.extraction_stages.update_job")
    @patch("backend.pipeline.stages.extraction_stages.post_slack_message")
    def test_extraction_handles_no_content(self, mock_slack, mock_update, mock_context):
        """Extraction should handle empty transcripts and sources."""
        from backend.pipeline.stages.extraction_stages import stage_7_extraction

        mock_context.transcripts = []
        mock_context.web_sources = []

        stage_7_extraction(mock_context)

        # Should set placeholder outputs
        assert "quote_bank_md" in mock_context.outputs
        assert "No content" in mock_context.outputs["quote_bank_md"]

    @patch("backend.pipeline.stages.extraction_stages.update_job")
    def test_timeline_handles_no_events(self, mock_update, mock_context):
        """Timeline extraction should handle no events."""
        from backend.pipeline.stages.extraction_stages import stage_7_5_timeline

        mock_context.transcripts = []
        mock_context.web_sources = []
        mock_context.claims = []

        stage_7_5_timeline(mock_context)

        # Should set placeholder output
        assert "timeline_md" in mock_context.outputs

    @patch("backend.pipeline.stages.extraction_stages.update_job")
    def test_entities_handles_no_content(self, mock_update, mock_context):
        """Entity extraction should handle no content."""
        from backend.pipeline.stages.extraction_stages import stage_7_6_entities

        mock_context.transcripts = []
        mock_context.web_sources = []
        mock_context.claims = []

        stage_7_6_entities(mock_context)

        # Should set placeholder output
        assert "entities_md" in mock_context.outputs
