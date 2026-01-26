"""Tests for Supadata metadata retrieval functionality.

Tests the fetch_metadata method and pipeline integration.
"""

import pytest
from unittest.mock import MagicMock, patch
import httpx


class TestSupadataFetchMetadata:
    """Test SupadataClient.fetch_metadata method."""

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_fetch_metadata_success(self):
        """Should fetch metadata successfully."""
        from backend.integrations.supadata_client import SupadataClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "platform": "youtube",
            "title": "Test Video Title",
            "author": {"name": "Test Channel"},
            "stats": {"views": 1000, "likes": 100},
            "media": {"thumbnailUrl": "https://example.com/thumb.jpg", "duration": 600},
            "createdAt": "2024-01-01T00:00:00Z",
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = SupadataClient()
            result = client.fetch_metadata("https://youtube.com/watch?v=test123")

        assert result["platform"] == "youtube"
        assert result["title"] == "Test Video Title"
        assert result["media"]["duration"] == 600

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_fetch_metadata_correct_endpoint(self):
        """Should call correct endpoint with URL param."""
        from backend.integrations.supadata_client import SupadataClient

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"platform": "youtube"}

        with patch.object(httpx.Client, "get", return_value=mock_response) as mock_get:
            client = SupadataClient()
            client.fetch_metadata("https://youtube.com/watch?v=test123")

            # Verify correct endpoint and params
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == "/metadata"
            assert call_args[1]["params"]["url"] == "https://youtube.com/watch?v=test123"

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_fetch_metadata_api_error(self):
        """Should raise SupadataError on API error."""
        from backend.integrations.supadata_client import SupadataClient, SupadataError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = SupadataClient()

            with pytest.raises(SupadataError) as exc_info:
                client.fetch_metadata("invalid-url")

            assert "400" in str(exc_info.value)

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_fetch_metadata_http_error(self):
        """Should handle HTTP errors gracefully."""
        from backend.integrations.supadata_client import SupadataClient, SupadataError

        with patch.object(httpx.Client, "get", side_effect=httpx.HTTPError("Connection failed")):
            client = SupadataClient()

            with pytest.raises(SupadataError) as exc_info:
                client.fetch_metadata("https://youtube.com/watch?v=test123")

            assert "HTTP error" in str(exc_info.value)


class TestFetchVideoMetadataConvenience:
    """Test fetch_video_metadata convenience function."""

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_returns_metadata_on_success(self):
        """Should return metadata dict on success."""
        from backend.integrations.supadata_client import fetch_video_metadata

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"platform": "youtube", "title": "Test"}

        with patch.object(httpx.Client, "get", return_value=mock_response):
            result = fetch_video_metadata("https://youtube.com/watch?v=test123")

        assert result is not None
        assert result["platform"] == "youtube"

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_none_when_not_configured(self):
        """Should return None when SUPADATA_API_KEY not set."""
        from backend.integrations.supadata_client import fetch_video_metadata

        # Clear any cached availability check
        result = fetch_video_metadata("https://youtube.com/watch?v=test123")
        assert result is None

    @patch.dict("os.environ", {"SUPADATA_API_KEY": "test-api-key"})
    def test_returns_none_on_error(self):
        """Should return None (not raise) on error - non-blocking."""
        from backend.integrations.supadata_client import fetch_video_metadata

        with patch.object(httpx.Client, "get", side_effect=Exception("Network error")):
            result = fetch_video_metadata("https://youtube.com/watch?v=test123")

        # Should not raise, should return None
        assert result is None


class TestMetadataPipelineIntegration:
    """Test metadata integration in source_identity stage."""

    @patch("backend.pipeline.stages.source_identity.update_job")
    @patch("backend.pipeline.stages.source_identity.acquire_transcript")
    @patch("backend.pipeline.stages.source_identity.fetch_video_metadata")
    def test_stage_fetches_metadata(self, mock_fetch_metadata, mock_acquire, mock_update_job):
        """Should fetch metadata for videos during source identity stage."""
        from backend.pipeline.stages.source_identity import stage_source_identity
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.transcript_acquisition import TranscriptResult
        from backend.models.semantic_units import AnalysisMode

        # Mock context with a video
        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = [
            {"url": "https://youtube.com/watch?v=test123", "title": "Test Video"},
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

        # Mock metadata fetch
        mock_fetch_metadata.return_value = {
            "platform": "youtube",
            "title": "Test Video",
            "media": {"duration": 300},
        }

        with patch("backend.pipeline.stages.source_identity.is_transcript_available", return_value=True):
            stage_source_identity(ctx)

        # Verify metadata was fetched
        mock_fetch_metadata.assert_called_once_with("https://youtube.com/watch?v=test123")

        # Verify update_job was called with partial_artifacts containing video_metadata
        update_calls = mock_update_job.call_args_list
        # Find the call with partial_artifacts
        artifact_call = None
        for call in update_calls:
            if call[1].get("partial_artifacts"):
                artifact_call = call
                break

        assert artifact_call is not None, "update_job should be called with partial_artifacts"
        assert "video_metadata" in artifact_call[1]["partial_artifacts"]
        assert "https://youtube.com/watch?v=test123" in artifact_call[1]["partial_artifacts"]["video_metadata"]

    @patch("backend.pipeline.stages.source_identity.update_job")
    @patch("backend.pipeline.stages.source_identity.acquire_transcript")
    @patch("backend.pipeline.stages.source_identity.fetch_video_metadata")
    def test_stage_continues_on_metadata_failure(self, mock_fetch_metadata, mock_acquire, mock_update_job):
        """Should continue pipeline even if metadata fetch fails (non-blocking)."""
        from backend.pipeline.stages.source_identity import stage_source_identity
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.transcript_acquisition import TranscriptResult
        from backend.models.semantic_units import AnalysisMode

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = [
            {"url": "https://youtube.com/watch?v=test123", "title": "Test Video"},
        ]
        ctx.web_sources = []
        ctx.reddit_posts = []

        # Mock transcript acquisition (success)
        mock_result = MagicMock(spec=TranscriptResult)
        mock_result.text = "Transcript text"
        mock_result.transcript_source = MagicMock()
        mock_result.transcript_source.value = "supadata"
        mock_result.analysis_mode = AnalysisMode.TRANSCRIPT_GROUNDED
        mock_result.to_provenance.return_value = MagicMock()
        mock_acquire.return_value = mock_result

        # Mock metadata fetch failure
        mock_fetch_metadata.return_value = None  # Simulates failure

        with patch("backend.pipeline.stages.source_identity.is_transcript_available", return_value=True):
            # Should NOT raise exception
            stage_source_identity(ctx)

        # Pipeline should continue - packages should be created
        assert len(ctx.source_identity_packages) == 1
        assert ctx.source_identity_packages[0].source_id == "SRC_1"

    @patch("backend.pipeline.stages.source_identity.update_job")
    @patch("backend.pipeline.stages.source_identity.acquire_transcript")
    @patch("backend.pipeline.stages.source_identity.fetch_video_metadata")
    def test_metadata_stored_under_correct_key(self, mock_fetch_metadata, mock_acquire, mock_update_job):
        """Should store metadata under artifacts.video_metadata keyed by URL."""
        from backend.pipeline.stages.source_identity import stage_source_identity
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.transcript_acquisition import TranscriptResult
        from backend.models.semantic_units import AnalysisMode

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = [
            {"url": "https://youtube.com/watch?v=vid1", "title": "Video 1"},
            {"url": "https://youtube.com/watch?v=vid2", "title": "Video 2"},
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

        # Mock metadata fetch - returns different data for each URL
        def metadata_side_effect(url):
            if "vid1" in url:
                return {"platform": "youtube", "title": "Video 1", "media": {"duration": 100}}
            elif "vid2" in url:
                return {"platform": "youtube", "title": "Video 2", "media": {"duration": 200}}
            return None

        mock_fetch_metadata.side_effect = metadata_side_effect

        with patch("backend.pipeline.stages.source_identity.is_transcript_available", return_value=True):
            stage_source_identity(ctx)

        # Find the update_job call with partial_artifacts
        artifact_call = None
        for call in mock_update_job.call_args_list:
            if call[1].get("partial_artifacts"):
                artifact_call = call
                break

        assert artifact_call is not None
        video_metadata = artifact_call[1]["partial_artifacts"]["video_metadata"]

        # Both URLs should be keyed
        assert "https://youtube.com/watch?v=vid1" in video_metadata
        assert "https://youtube.com/watch?v=vid2" in video_metadata
        assert video_metadata["https://youtube.com/watch?v=vid1"]["media"]["duration"] == 100
        assert video_metadata["https://youtube.com/watch?v=vid2"]["media"]["duration"] == 200


class TestMergeSupadataMetadata:
    """Test _merge_supadata_metadata helper function."""

    def test_merge_updates_empty_fields(self):
        """Should merge metadata into package with empty fields."""
        from backend.pipeline.stages.source_identity import (
            _merge_supadata_metadata,
            SourceIdentityPackage,
        )
        from backend.models.semantic_units import AnalysisMode

        # Package with empty metadata fields
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test123",
            title="Untitled Video",  # Will be updated
            creator=None,            # Will be updated
            published=None,          # Will be updated
            duration_seconds=None,   # Will be updated
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        metadata = {
            "title": "Rich Supadata Title",
            "author": {"name": "Test Channel", "url": "https://youtube.com/@test"},
            "createdAt": "2024-06-15T10:00:00Z",
            "media": {"duration": 600, "thumbnailUrl": "https://example.com/thumb.jpg"},
        }

        _merge_supadata_metadata(package, metadata)

        assert package.title == "Rich Supadata Title"
        assert package.creator == "Test Channel"
        assert package.published == "2024-06-15T10:00:00Z"
        assert package.duration_seconds == 600
        assert package.duration_minutes == 10.0

    def test_merge_does_not_overwrite_existing_fields(self):
        """Should NOT overwrite fields that already have values."""
        from backend.pipeline.stages.source_identity import (
            _merge_supadata_metadata,
            SourceIdentityPackage,
        )
        from backend.models.semantic_units import AnalysisMode

        # Package with existing metadata
        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test123",
            title="Existing Title",           # Should NOT be overwritten
            creator="Existing Creator",       # Should NOT be overwritten
            published="2024-01-01",           # Should NOT be overwritten
            duration_seconds=300,             # Should NOT be overwritten
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        metadata = {
            "title": "New Supadata Title",
            "author": {"name": "New Channel"},
            "createdAt": "2024-06-15T10:00:00Z",
            "media": {"duration": 600},
        }

        _merge_supadata_metadata(package, metadata)

        # All fields should remain unchanged
        assert package.title == "Existing Title"
        assert package.creator == "Existing Creator"
        assert package.published == "2024-01-01"
        assert package.duration_seconds == 300

    def test_merge_handles_missing_metadata_fields(self):
        """Should handle metadata with missing fields gracefully."""
        from backend.pipeline.stages.source_identity import (
            _merge_supadata_metadata,
            SourceIdentityPackage,
        )
        from backend.models.semantic_units import AnalysisMode

        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test123",
            title="Untitled Video",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        # Partial metadata - only title
        metadata = {"title": "Just a Title"}

        _merge_supadata_metadata(package, metadata)

        assert package.title == "Just a Title"
        assert package.creator is None  # Not in metadata
        assert package.published is None  # Not in metadata

    def test_merge_handles_none_metadata(self):
        """Should handle None metadata gracefully."""
        from backend.pipeline.stages.source_identity import (
            _merge_supadata_metadata,
            SourceIdentityPackage,
        )
        from backend.models.semantic_units import AnalysisMode

        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test123",
            title="Original Title",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        _merge_supadata_metadata(package, None)

        # Package unchanged
        assert package.title == "Original Title"

    def test_merge_handles_empty_metadata(self):
        """Should handle empty dict metadata gracefully."""
        from backend.pipeline.stages.source_identity import (
            _merge_supadata_metadata,
            SourceIdentityPackage,
        )
        from backend.models.semantic_units import AnalysisMode

        package = SourceIdentityPackage(
            source_id="SRC_1",
            source_type="youtube",
            url="https://youtube.com/watch?v=test123",
            title="Original Title",
            analysis_mode=AnalysisMode.TRANSCRIPT_GROUNDED,
        )

        _merge_supadata_metadata(package, {})

        # Package unchanged
        assert package.title == "Original Title"


class TestMetadataMergedIntoPackage:
    """Test that metadata is merged into package during stage execution."""

    @patch("backend.pipeline.stages.source_identity.update_job")
    @patch("backend.pipeline.stages.source_identity.acquire_transcript")
    @patch("backend.pipeline.stages.source_identity.fetch_video_metadata")
    def test_metadata_merged_into_package(self, mock_fetch_metadata, mock_acquire, mock_update_job):
        """Should merge Supadata metadata into source_identity_packages for Doc 0."""
        from backend.pipeline.stages.source_identity import stage_source_identity
        from backend.pipeline.context import PipelineContext
        from backend.pipeline.transcript_acquisition import TranscriptResult
        from backend.models.semantic_units import AnalysisMode

        ctx = PipelineContext(job_id="test-job", topic="Test")
        ctx.youtube_videos = [
            {"url": "https://youtube.com/watch?v=test123", "title": "Untitled Video"},
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

        # Mock metadata fetch with rich data
        mock_fetch_metadata.return_value = {
            "title": "Rich Video Title from Supadata",
            "author": {"name": "Supadata Channel Name"},
            "createdAt": "2024-06-15T10:00:00Z",
            "media": {"duration": 1200},  # 20 minutes
        }

        with patch("backend.pipeline.stages.source_identity.is_transcript_available", return_value=True):
            stage_source_identity(ctx)

        # Verify the package was enriched with Supadata metadata
        assert len(ctx.source_identity_packages) == 1
        package = ctx.source_identity_packages[0]

        assert package.title == "Rich Video Title from Supadata"
        assert package.creator == "Supadata Channel Name"
        assert package.published == "2024-06-15T10:00:00Z"
        assert package.duration_seconds == 1200
        assert package.duration_minutes == 20.0
