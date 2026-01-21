"""
Tests for backend/state/ module

Tests job store operations including in-memory and Supabase implementations.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from backend.models.job_record import JobRecord
from backend.utils.validators import ValidationError


@pytest.fixture
def sample_config():
    """Sample job configuration."""
    return {
        "topic": "Test research topic",
        "prompt": "Test prompt",
        "pipeline": "full",
    }


class TestInMemoryJobStore:
    """Tests for in-memory job store."""

    def test_create_job(self, sample_config):
        """Creating a job should return a JobRecord."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        job = store.create_job(config_json=sample_config)

        assert job is not None
        assert job.job_id is not None
        assert job.status == "queued"
        assert job.config_json == sample_config

    def test_get_job(self, sample_config):
        """Getting an existing job should return the job."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        created_job = store.create_job(config_json=sample_config)

        retrieved_job = store.get_job(created_job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id

    def test_get_nonexistent_job(self):
        """Getting a non-existent job should return None."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        job = store.get_job("550e8400-e29b-41d4-a716-446655440000")

        assert job is None

    def test_update_job(self, sample_config):
        """Updating a job should modify its fields."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        created_job = store.create_job(config_json=sample_config)

        updated_job = store.update_job(
            created_job.job_id,
            status="running",
            progress_percent=50,
        )

        assert updated_job.status == "running"
        assert updated_job.progress_percent == 50

    def test_list_jobs(self, sample_config):
        """Listing jobs should return all jobs."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        store.create_job(config_json=sample_config)
        store.create_job(config_json=sample_config)

        jobs = store.list_jobs()

        assert len(jobs) == 2

    def test_list_jobs_with_user_filter(self, sample_config):
        """Listing jobs with user filter should return only user's jobs."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        store.create_job(config_json=sample_config, user_id="user-1")
        store.create_job(config_json=sample_config, user_id="user-2")

        user_jobs = store.list_jobs(user_id="user-1")

        assert len(user_jobs) == 1
        assert user_jobs[0].user_id == "user-1"

    def test_list_jobs_pagination(self, sample_config):
        """Listing jobs should support pagination."""
        from backend.state.impl.in_memory import InMemoryJobStore

        store = InMemoryJobStore()
        for _ in range(5):
            store.create_job(config_json=sample_config)

        page1 = store.list_jobs(limit=2, offset=0)
        page2 = store.list_jobs(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2


class TestJobStoreFactory:
    """Tests for job store factory."""

    @patch("backend.state.factory.get_settings")
    def test_in_memory_store_selected(self, mock_get_settings):
        """In-memory store should be selected when Supabase is disabled."""
        from backend.state.factory import get_job_store
        from backend.state.impl.in_memory import InMemoryJobStore

        # Clear cached store to test fresh
        get_job_store.cache_clear()

        # Mock settings with no Supabase credentials
        mock_settings = MagicMock()
        mock_settings.supabase_url = None
        mock_settings.supabase_service_role_key = None
        mock_get_settings.return_value = mock_settings

        store = get_job_store()
        # Check store type
        assert isinstance(store, InMemoryJobStore)

        # Clear cache after test
        get_job_store.cache_clear()


class TestValidationInJobStore:
    """Tests for validation in job store operations."""

    def test_invalid_uuid_raises_validation_error(self):
        """Invalid UUID should raise ValidationError."""
        from backend.state.impl.supabase_store import SupabaseJobStore
        from backend.utils.validators import validate_uuid, ValidationError

        # Test the validate_uuid function directly
        with pytest.raises(ValidationError):
            validate_uuid("not-a-uuid", "job_id")

    def test_empty_uuid_raises_validation_error(self):
        """Empty UUID should raise ValidationError."""
        from backend.utils.validators import validate_uuid, ValidationError

        with pytest.raises(ValidationError) as exc_info:
            validate_uuid("", "job_id")

        assert "empty" in str(exc_info.value).lower()


class TestJobRecordModel:
    """Tests for JobRecord model."""

    def test_job_record_creation(self):
        """JobRecord should be created with valid data."""
        job = JobRecord(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            status="queued",
            stage="initialization",
            progress_percent=0,
            config_json={"topic": "Test"},
            created_at=datetime.now(timezone.utc),
            warnings=[],
            outputs={},
        )

        assert job.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert job.status == "queued"

    def test_job_record_with_artifacts(self):
        """JobRecord can have artifacts."""
        from backend.models.job_record import Artifacts

        artifacts = Artifacts(
            doc_0_path="documents/abc/doc_0.json",
            doc_1_path="documents/abc/doc_1.json",
            doc_2_path="documents/abc/doc_2.json",
        )

        job = JobRecord(
            job_id="550e8400-e29b-41d4-a716-446655440000",
            status="completed",
            stage="done",
            progress_percent=100,
            config_json={"topic": "Test"},
            created_at=datetime.now(timezone.utc),
            warnings=[],
            artifacts=artifacts,
        )

        assert job.artifacts is not None
        assert job.artifacts.doc_0_path == "documents/abc/doc_0.json"
