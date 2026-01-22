"""
Tests for backend/app/routes/jobs_routes.py

Tests the job creation, listing, status, and cancellation endpoints.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.models.job_record import JobRecord, Artifacts


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    from backend.auth import AuthUser
    return AuthUser(
        user_id="test-user-123",
        email="test@example.com",
        role="authenticated"
    )


@pytest.fixture
def sample_job_record():
    """Create a sample job record for testing."""
    return JobRecord(
        job_id="550e8400-e29b-41d4-a716-446655440000",
        status="queued",
        stage="initialization",
        progress_percent=0,
        config_json={
            "topic": "Test topic",
            "prompt": "Test prompt",
            "pipeline": "full",
        },
        user_id="test-user-123",
        created_at=datetime.now(timezone.utc),
        warnings=[],
        outputs={},
        artifacts=None,
    )


@pytest.fixture
def app_client(mock_auth_user):
    """Create test client for the FastAPI app with mocked auth."""
    from backend.app.main import app
    from backend.auth.dependencies import get_current_user, get_optional_user
    from backend.auth.ban_check import get_active_user

    # Override auth dependencies for testing
    async def mock_get_current_user():
        return mock_auth_user

    async def mock_get_optional_user():
        return mock_auth_user

    async def mock_get_active_user(user=None):
        return mock_auth_user

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_optional_user] = mock_get_optional_user
    app.dependency_overrides[get_active_user] = mock_get_active_user

    yield TestClient(app)

    # Clean up overrides
    app.dependency_overrides.clear()


class TestCreateJobEndpoint:
    """Tests for POST /jobs endpoint (DEPRECATED since 2026-01-19).

    This endpoint now returns 410 Gone. Use the new source-first endpoints:
    - POST /jobs/video-analysis
    - POST /jobs/text-input
    - POST /jobs/screenshot-input
    - POST /jobs/mixed-input
    """

    def test_deprecated_endpoint_returns_410(self, app_client):
        """Deprecated POST /jobs endpoint should return 410 Gone."""
        response = app_client.post(
            "/jobs",
            json={"prompt": "Test prompt", "pipeline": "full"}
        )
        assert response.status_code == 410
        data = response.json()
        assert "detail" in data
        assert data["detail"]["message"] == "Legacy topic-based job creation is deprecated"
        assert "alternatives" in data["detail"]


class TestGetJobEndpoint:
    """Tests for GET /jobs/{job_id} endpoint."""

    def test_get_job_invalid_uuid(self, app_client):
        """Invalid job ID format should return 400."""
        response = app_client.get("/jobs/not-a-valid-uuid")
        assert response.status_code == 400
        assert "Invalid job ID" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_get_job_not_found(self, mock_get_job, app_client):
        """Non-existent job should return 404."""
        mock_get_job.return_value = None

        response = app_client.get("/jobs/550e8400-e29b-41d4-a716-446655440000")
        assert response.status_code == 404

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_get_job_success(self, mock_get_job, app_client, sample_job_record):
        """Valid job ID should return job status."""
        # Create job without user_id for anonymous access
        sample_job_record.user_id = None
        mock_get_job.return_value = sample_job_record

        response = app_client.get(f"/jobs/{sample_job_record.job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == sample_job_record.job_id
        assert data["status"] == "queued"


class TestListJobsEndpoint:
    """Tests for GET /jobs endpoint."""

    @patch("backend.app.routes.jobs_routes.list_jobs")
    def test_list_jobs_empty(self, mock_list_jobs, app_client):
        """List jobs should return empty list when no jobs exist."""
        mock_list_jobs.return_value = []

        response = app_client.get("/jobs")
        assert response.status_code == 200
        assert response.json()["jobs"] == []

    @patch("backend.app.routes.jobs_routes.list_jobs")
    def test_list_jobs_with_pagination(self, mock_list_jobs, app_client, sample_job_record):
        """List jobs should support pagination."""
        mock_list_jobs.return_value = [sample_job_record]

        response = app_client.get("/jobs?limit=10&offset=0")
        assert response.status_code == 200
        assert len(response.json()["jobs"]) == 1


class TestCancelJobEndpoint:
    """Tests for POST /jobs/{job_id}/cancel endpoint."""

    def test_cancel_job_invalid_uuid(self, app_client):
        """Invalid job ID format should return 400."""
        # app_client fixture already has auth mocked
        response = app_client.post("/jobs/not-a-valid-uuid/cancel")
        assert response.status_code == 400

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_cancel_job_not_found(self, mock_get_job, app_client):
        """Non-existent job should return 404."""
        mock_get_job.return_value = None

        # app_client fixture already has auth mocked
        response = app_client.post("/jobs/550e8400-e29b-41d4-a716-446655440000/cancel")
        assert response.status_code == 404
