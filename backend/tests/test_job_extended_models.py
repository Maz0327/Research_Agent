"""
Unit tests for extended job models (evolving jobs).

Tests for: SourceStateEnum, JobSource, AddSourcesRequest, AddSourcesResponse,
ProcessPendingResponse

Phase 9 Task 9.1.5
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.models.job import (
    SourceStateEnum,
    JobSource,
    AddSourcesRequest,
    AddSourcesResponse,
    ProcessPendingResponse,
    MixedTextInput,
)


# =============================================================================
# TestSourceStateEnum
# =============================================================================


class TestSourceStateEnum:
    """Tests for SourceStateEnum."""

    def test_state_values(self):
        """SourceStateEnum should have correct string values."""
        assert SourceStateEnum.PENDING.value == "pending"
        assert SourceStateEnum.PROCESSING.value == "processing"
        assert SourceStateEnum.PROCESSED.value == "processed"
        assert SourceStateEnum.FAILED.value == "failed"
        assert SourceStateEnum.EXCLUDED.value == "excluded"

    def test_all_states_exist(self):
        """All expected states should be defined."""
        states = [
            SourceStateEnum.PENDING,
            SourceStateEnum.PROCESSING,
            SourceStateEnum.PROCESSED,
            SourceStateEnum.FAILED,
            SourceStateEnum.EXCLUDED,
        ]
        assert len(states) == 5
        assert len(SourceStateEnum) == 5

    def test_state_from_string(self):
        """Should be able to create from string value."""
        assert SourceStateEnum("pending") == SourceStateEnum.PENDING
        assert SourceStateEnum("processing") == SourceStateEnum.PROCESSING
        assert SourceStateEnum("processed") == SourceStateEnum.PROCESSED

    def test_invalid_state_raises(self):
        """Invalid state string should raise ValueError."""
        with pytest.raises(ValueError):
            SourceStateEnum("invalid_state")


# =============================================================================
# TestJobSource
# =============================================================================


class TestJobSource:
    """Tests for JobSource model."""

    def test_job_source_creation_minimal(self):
        """Should create with minimal fields."""
        source = JobSource(
            source_id="SRC_1",
            source_type="youtube",
            added_at=datetime.now(timezone.utc),
        )
        assert source.source_id == "SRC_1"
        assert source.source_type == "youtube"
        assert source.status == SourceStateEnum.PENDING  # Default
        assert source.is_original is True  # Default

    def test_job_source_creation_full(self):
        """Should create with all fields."""
        now = datetime.now(timezone.utc)
        source = JobSource(
            source_id="SRC_2",
            source_type="article",
            url="https://example.com/article",
            title="Test Article",
            status=SourceStateEnum.PROCESSED,
            added_at=now,
            processed_at=now,
            error=None,
            is_original=False,
        )
        assert source.source_id == "SRC_2"
        assert source.url == "https://example.com/article"
        assert source.title == "Test Article"
        assert source.status == SourceStateEnum.PROCESSED
        assert source.is_original is False

    def test_job_source_status_tracking(self):
        """Should track status changes."""
        source = JobSource(
            source_id="SRC_1",
            source_type="youtube",
            added_at=datetime.now(timezone.utc),
        )
        assert source.status == SourceStateEnum.PENDING

        # Simulate status update
        source.status = SourceStateEnum.PROCESSING
        assert source.status == SourceStateEnum.PROCESSING

        source.status = SourceStateEnum.PROCESSED
        assert source.status == SourceStateEnum.PROCESSED

    def test_job_source_with_error(self):
        """Should store error for failed sources."""
        source = JobSource(
            source_id="SRC_1",
            source_type="youtube",
            added_at=datetime.now(timezone.utc),
            status=SourceStateEnum.FAILED,
            error="Transcript not available",
        )
        assert source.status == SourceStateEnum.FAILED
        assert source.error == "Transcript not available"

    def test_job_source_required_fields(self):
        """Should require source_id, source_type, added_at."""
        with pytest.raises(ValidationError):
            JobSource()  # Missing all required fields

        with pytest.raises(ValidationError):
            JobSource(source_id="SRC_1")  # Missing source_type, added_at

        with pytest.raises(ValidationError):
            JobSource(source_id="SRC_1", source_type="youtube")  # Missing added_at


# =============================================================================
# TestAddSourcesRequest
# =============================================================================


class TestAddSourcesRequest:
    """Tests for AddSourcesRequest model."""

    def test_request_with_video_urls(self):
        """Should accept video URLs."""
        request = AddSourcesRequest(
            video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
        )
        assert len(request.video_urls) == 1
        assert len(request.article_urls) == 0
        assert len(request.text_inputs) == 0

    def test_request_with_article_urls(self):
        """Should accept article URLs."""
        request = AddSourcesRequest(
            article_urls=["https://example.com/article"],
        )
        assert len(request.article_urls) == 1

    def test_request_with_text_inputs(self):
        """Should accept text inputs."""
        # MixedTextInput requires title and content >= 50 chars
        text_input = MixedTextInput(
            title="Test Input",
            content="This is test content that needs to be at least fifty characters long for validation.",
        )
        request = AddSourcesRequest(
            text_inputs=[text_input],
        )
        assert len(request.text_inputs) == 1

    def test_request_validation_at_least_one_source(self):
        """Should require at least one source."""
        with pytest.raises(ValueError, match="At least one source required"):
            AddSourcesRequest(
                video_urls=[],
                article_urls=[],
                text_inputs=[],
            )

    def test_max_sources_limit(self):
        """Should enforce maximum 10 sources per addition via max_length on each field."""
        text_inputs = [
            MixedTextInput(
                title=f"Input {i}",
                content=f"This is content number {i} and it needs to be at least fifty characters for validation.",
            )
            for i in range(11)
        ]
        # Pydantic max_length validation raises ValidationError (too_long)
        with pytest.raises(ValidationError):
            AddSourcesRequest(text_inputs=text_inputs)

    def test_max_sources_combined(self):
        """Should enforce max across all source types."""
        text_inputs = [
            MixedTextInput(
                title=f"Input {i}",
                content=f"This is content number {i} and it needs to be at least fifty characters for validation.",
            )
            for i in range(6)
        ]
        # 6 text + 5 articles = 11 > 10
        with pytest.raises(ValueError, match="Maximum 10 sources"):
            AddSourcesRequest(
                article_urls=[f"https://example.com/{i}" for i in range(5)],
                text_inputs=text_inputs,
            )

    def test_process_immediately_flag(self):
        """Should accept process_immediately flag."""
        request = AddSourcesRequest(
            article_urls=["https://example.com/article"],
            process_immediately=True,
        )
        assert request.process_immediately is True

    def test_process_immediately_default_false(self):
        """process_immediately should default to False."""
        request = AddSourcesRequest(
            article_urls=["https://example.com/article"],
        )
        assert request.process_immediately is False

    def test_multiple_source_types(self):
        """Should accept multiple source types together."""
        request = AddSourcesRequest(
            video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            article_urls=["https://example.com/article"],
            text_inputs=[MixedTextInput(
                title="Test Input",
                content="This is test content that needs to be at least fifty characters long for validation.",
            )],
        )
        assert len(request.video_urls) == 1
        assert len(request.article_urls) == 1
        assert len(request.text_inputs) == 1

    def test_exactly_10_sources_allowed(self):
        """Should allow exactly 10 sources."""
        text_inputs = [
            MixedTextInput(
                title=f"Input {i}",
                content=f"This is content number {i} and it needs to be at least fifty characters for validation.",
            )
            for i in range(10)
        ]
        request = AddSourcesRequest(text_inputs=text_inputs)
        assert len(request.text_inputs) == 10


# =============================================================================
# TestAddSourcesResponse
# =============================================================================


class TestAddSourcesResponse:
    """Tests for AddSourcesResponse model."""

    def test_response_creation(self):
        """Should create response with all fields."""
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=3,
            pending_count=5,
            status="sources_pending",
        )
        assert response.job_id == "JOB_123"
        assert response.sources_added == 3
        assert response.pending_count == 5
        assert response.status == "sources_pending"

    def test_response_with_warnings(self):
        """Should accept optional warnings."""
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=2,
            pending_count=2,
            status="sources_pending",
            warnings=["Duplicate URL ignored", "Article may be paywalled"],
        )
        assert len(response.warnings) == 2

    def test_response_batch_timeout_default(self):
        """batch_timeout_seconds should default to 60."""
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=1,
            pending_count=1,
            status="sources_pending",
        )
        assert response.batch_timeout_seconds == 60

    def test_response_custom_batch_timeout(self):
        """Should accept custom batch timeout."""
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=1,
            pending_count=1,
            status="sources_pending",
            batch_timeout_seconds=120,
        )
        assert response.batch_timeout_seconds == 120

    def test_response_processing_status(self):
        """Should accept processing status."""
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=1,
            pending_count=0,
            status="processing",
        )
        assert response.status == "processing"


# =============================================================================
# TestProcessPendingResponse
# =============================================================================


class TestProcessPendingResponse:
    """Tests for ProcessPendingResponse model."""

    def test_process_pending_response_creation(self):
        """Should create response correctly."""
        response = ProcessPendingResponse(
            job_id="JOB_123",
            status="processing",
            pending_count=3,
        )
        assert response.job_id == "JOB_123"
        assert response.status == "processing"
        assert response.pending_count == 3

    def test_process_pending_required_fields(self):
        """Should require all fields."""
        with pytest.raises(ValidationError):
            ProcessPendingResponse(job_id="JOB_123")

        with pytest.raises(ValidationError):
            ProcessPendingResponse(job_id="JOB_123", status="processing")


# =============================================================================
# TestEvolvingJobsIntegration
# =============================================================================


class TestEvolvingJobsIntegration:
    """Integration tests for evolving jobs models."""

    def test_job_source_state_progression(self):
        """Should track typical state progression."""
        source = JobSource(
            source_id="SRC_1",
            source_type="youtube",
            url="https://www.youtube.com/watch?v=abc123",
            added_at=datetime.now(timezone.utc),
            is_original=False,  # Added to existing job
        )

        # Initial state
        assert source.status == SourceStateEnum.PENDING
        assert source.processed_at is None

        # Processing starts
        source.status = SourceStateEnum.PROCESSING
        assert source.status == SourceStateEnum.PROCESSING

        # Processing completes
        source.status = SourceStateEnum.PROCESSED
        source.processed_at = datetime.now(timezone.utc)
        assert source.status == SourceStateEnum.PROCESSED
        assert source.processed_at is not None

    def test_job_source_failure_flow(self):
        """Should track failed source correctly."""
        source = JobSource(
            source_id="SRC_2",
            source_type="youtube",
            added_at=datetime.now(timezone.utc),
        )

        # Processing starts
        source.status = SourceStateEnum.PROCESSING

        # Processing fails
        source.status = SourceStateEnum.FAILED
        source.error = "Video is private"

        assert source.status == SourceStateEnum.FAILED
        assert source.error == "Video is private"

    def test_request_response_flow(self):
        """Should model typical add sources flow."""
        # 1. Create request
        request = AddSourcesRequest(
            video_urls=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
            article_urls=["https://example.com/article"],
        )
        assert len(request.video_urls) + len(request.article_urls) == 2

        # 2. Create response
        response = AddSourcesResponse(
            job_id="JOB_123",
            sources_added=2,
            pending_count=2,
            status="sources_pending",
            batch_timeout_seconds=60,
        )
        assert response.sources_added == 2

        # 3. Process pending
        process_response = ProcessPendingResponse(
            job_id="JOB_123",
            status="processing",
            pending_count=2,
        )
        assert process_response.pending_count == 2

    def test_original_vs_added_sources(self):
        """Should distinguish original and added sources."""
        # Original source from job creation
        original = JobSource(
            source_id="SRC_1",
            source_type="youtube",
            added_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            is_original=True,
        )

        # Source added later
        added = JobSource(
            source_id="SRC_2",
            source_type="article",
            added_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
            is_original=False,
        )

        assert original.is_original is True
        assert added.is_original is False
        assert added.added_at > original.added_at
