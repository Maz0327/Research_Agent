"""Tests for youtube.py stage.

Phase 9: Tests YouTube enumeration and transcript fetching stages.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


# =============================================================================
# Mock Classes
# =============================================================================


@dataclass
class MockVideo:
    """Mock video object."""
    video_id: str
    title: str
    url: str
    duration_seconds: int = 600  # 10 minutes default


@dataclass
class MockTranscript:
    """Mock transcript object."""
    video_id: str
    text: str
    source: str
    status: str = "available"


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    from backend.pipeline.context import PipelineContext
    from backend.models.job_config import (
        JobConfig,
        YouTubeConfig,
        BudgetsConfig,
    )

    ctx = PipelineContext(
        job_id="test-job-youtube",
        topic="Test YouTube Topic",
    )

    # Set up job config
    ctx.job_config = JobConfig(
        topic="Test YouTube Topic",
        mode="investigation",
        youtube=YouTubeConfig(
            channels=["test_channel"],
            max_videos=5,
            fetch_transcripts=True,
            exclude_shorts=True,
        ),
        budgets=BudgetsConfig(
            max_transcription_minutes=60,
        ),
    )

    ctx.youtube_videos = []
    ctx.transcripts = []
    return ctx


@pytest.fixture
def mock_context_no_channels():
    """Create a mock pipeline context without channels (for topic search)."""
    from backend.pipeline.context import PipelineContext
    from backend.models.job_config import (
        JobConfig,
        YouTubeConfig,
        BudgetsConfig,
    )

    ctx = PipelineContext(
        job_id="test-job-youtube-search",
        topic="Test Topic Search",
    )

    # Set up job config without channels
    ctx.job_config = JobConfig(
        topic="Test Topic Search",
        mode="investigation",
        youtube=YouTubeConfig(
            channels=[],  # No channels = topic search mode
            max_videos=5,
            fetch_transcripts=True,
            exclude_shorts=True,
        ),
        budgets=BudgetsConfig(
            max_transcription_minutes=60,
        ),
    )

    ctx.youtube_videos = []
    ctx.transcripts = []
    return ctx


# =============================================================================
# Test: stage_4_youtube_enumeration
# =============================================================================


class TestYouTubeEnumeration:
    """Test stage_4_youtube_enumeration function."""

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.youtube_client.enumerate_channel_uploads")
    def test_enumeration_with_channels(self, mock_enumerate, mock_update_job, mock_context):
        """Should enumerate videos from specified channels."""
        from backend.pipeline.stages.youtube import stage_4_youtube_enumeration

        # Mock response
        mock_enumerate.return_value = {
            "videos": [
                MockVideo("vid1", "Test Video 1", "https://youtube.com/watch?v=vid1"),
                MockVideo("vid2", "Test Video 2", "https://youtube.com/watch?v=vid2"),
            ],
            "youtube_index_md": "# YouTube Index\n- Video 1\n- Video 2",
        }

        stage_4_youtube_enumeration(mock_context)

        # Verify enumeration was called
        mock_enumerate.assert_called_once_with(mock_context.job_config)
        assert len(mock_context.youtube_videos) == 2

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.youtube_client.search_youtube_videos")
    def test_enumeration_topic_search(self, mock_search, mock_update_job, mock_context_no_channels):
        """Should search YouTube by topic when no channels specified."""
        from backend.pipeline.stages.youtube import stage_4_youtube_enumeration

        # Mock response
        mock_search.return_value = {
            "videos": [
                MockVideo("vid1", "Topic Result 1", "https://youtube.com/watch?v=vid1"),
            ],
            "youtube_index_md": "# YouTube Index\n- Topic Result 1",
        }

        stage_4_youtube_enumeration(mock_context_no_channels)

        # Verify search was called with topic
        mock_search.assert_called_once()
        assert len(mock_context_no_channels.youtube_videos) == 1

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.youtube_client.enumerate_channel_uploads")
    def test_enumeration_handles_error(self, mock_enumerate, mock_update_job, mock_context):
        """Should handle enumeration errors gracefully."""
        from backend.pipeline.stages.youtube import stage_4_youtube_enumeration

        # Mock error
        mock_enumerate.side_effect = Exception("API error")

        stage_4_youtube_enumeration(mock_context)

        # Should add warning
        assert any("failed" in w.lower() for w in mock_context.warnings)


# =============================================================================
# Test: stage_5_transcripts
# =============================================================================


class TestTranscriptFetching:
    """Test stage_5_transcripts function."""

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.transcripts.fetch_transcript_v2")
    def test_fetch_transcripts_success(self, mock_fetch, mock_update_job, mock_context):
        """Should fetch transcripts for videos."""
        from backend.pipeline.stages.youtube import stage_5_transcripts
        from backend.integrations.transcripts import TranscriptStatus

        # Setup videos
        mock_context.youtube_videos = [
            MockVideo("vid1", "Test Video 1", "https://youtube.com/watch?v=vid1", 600),
        ]

        # Mock transcript response
        mock_transcript = MagicMock()
        mock_transcript.status = TranscriptStatus.AVAILABLE
        mock_transcript.source = "supadata"
        mock_fetch.return_value = mock_transcript

        stage_5_transcripts(mock_context)

        # Verify transcript was fetched
        mock_fetch.assert_called_once()
        assert len(mock_context.transcripts) == 1

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.transcripts.fetch_transcript_v2")
    def test_fetch_transcripts_budget_limit(self, mock_fetch, mock_update_job, mock_context):
        """Should respect transcription budget limits."""
        from backend.pipeline.stages.youtube import stage_5_transcripts
        from backend.integrations.transcripts import TranscriptStatus

        # Set low budget (5 minutes)
        mock_context.job_config.budgets.max_transcription_minutes = 5

        # Setup videos that exceed budget
        mock_context.youtube_videos = [
            MockVideo("vid1", "Long Video", "https://youtube.com/watch?v=vid1", 3600),  # 60 min
            MockVideo("vid2", "Another Video", "https://youtube.com/watch?v=vid2", 600),
        ]

        # Mock transcript response
        mock_transcript = MagicMock()
        mock_transcript.status = TranscriptStatus.AVAILABLE
        mock_fetch.return_value = mock_transcript

        stage_5_transcripts(mock_context)

        # Should add budget warning
        assert any("budget" in w.lower() for w in mock_context.warnings)

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.transcripts.fetch_transcript_v2")
    def test_fetch_transcripts_unavailable(self, mock_fetch, mock_update_job, mock_context):
        """Should handle unavailable transcripts."""
        from backend.pipeline.stages.youtube import stage_5_transcripts
        from backend.integrations.transcripts import TranscriptStatus

        # Setup video
        mock_context.youtube_videos = [
            MockVideo("vid1", "No Transcript Video", "https://youtube.com/watch?v=vid1"),
        ]

        # Mock missing transcript (TranscriptStatus.MISSING, not UNAVAILABLE)
        mock_transcript = MagicMock()
        mock_transcript.status = TranscriptStatus.MISSING
        mock_fetch.return_value = mock_transcript

        stage_5_transcripts(mock_context)

        # Should add warning about missing transcript
        assert any("missing" in w.lower() for w in mock_context.warnings)

    @patch("backend.pipeline.stages.youtube.update_job")
    @patch("backend.integrations.transcripts.fetch_transcript_v2")
    def test_fetch_transcripts_handles_error(self, mock_fetch, mock_update_job, mock_context):
        """Should handle fetch errors gracefully."""
        from backend.pipeline.stages.youtube import stage_5_transcripts

        # Setup video
        mock_context.youtube_videos = [
            MockVideo("vid1", "Error Video", "https://youtube.com/watch?v=vid1"),
        ]

        # Mock error
        mock_fetch.side_effect = Exception("API error")

        stage_5_transcripts(mock_context)

        # Should add warning but not crash
        assert any("failed" in w.lower() for w in mock_context.warnings)

    @patch("backend.pipeline.stages.youtube.update_job")
    def test_fetch_transcripts_disabled(self, mock_update_job, mock_context):
        """Should skip when fetch_transcripts is disabled."""
        from backend.pipeline.stages.youtube import stage_5_transcripts

        # Disable transcript fetching
        mock_context.job_config.youtube.fetch_transcripts = False
        mock_context.youtube_videos = [
            MockVideo("vid1", "Test Video", "https://youtube.com/watch?v=vid1"),
        ]

        stage_5_transcripts(mock_context)

        # Should not fetch any transcripts
        assert len(mock_context.transcripts) == 0
