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


class TestIterateJobEndpoint:
    """Tests for POST /jobs/{job_id}/iterate endpoint.

    Iteration is APPEND-ONLY: never modifies baseline artifacts,
    never changes job.status from completed.
    """

    def test_iterate_job_invalid_uuid(self, app_client):
        """Invalid job ID format should return 400."""
        response = app_client.post(
            "/jobs/not-a-valid-uuid/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 400
        assert "Invalid job ID" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_not_found(self, mock_get_job, app_client):
        """Non-existent job should return 404."""
        mock_get_job.return_value = None

        response = app_client.post(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_wrong_owner(self, mock_get_job, app_client, sample_job_record):
        """Iterating someone else's job should return 403."""
        sample_job_record.user_id = "different-user-456"
        mock_get_job.return_value = sample_job_record

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_not_completed(self, mock_get_job, app_client, sample_job_record):
        """Iterating a non-completed job should return 400."""
        sample_job_record.status = "running"
        mock_get_job.return_value = sample_job_record

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 400
        assert "must be completed" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_already_running(self, mock_get_job, app_client, sample_job_record):
        """Iterating when another iteration is running should return 409."""
        sample_job_record.status = "completed"
        sample_job_record.iteration_status = "running"
        mock_get_job.return_value = sample_job_record

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 409
        assert "already running" in response.json()["detail"]

    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_missing_baseline_docs(self, mock_get_job, app_client, sample_job_record):
        """Iterating without baseline docs should return 400."""
        sample_job_record.status = "completed"
        sample_job_record.artifacts = Artifacts()  # Empty artifacts
        mock_get_job.return_value = sample_job_record

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "more_sources"}
        )
        assert response.status_code == 400
        assert "Baseline documents required" in response.json()["detail"]

    @patch("backend.worker.run_iteration_task")
    @patch("backend.app.routes.jobs_routes.update_job")
    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_success(
        self, mock_get_job, mock_update_job, mock_iteration_task, app_client, sample_job_record
    ):
        """Successful iteration should queue task and return iteration_id."""
        # Setup completed job with baseline docs
        sample_job_record.status = "completed"
        sample_job_record.iteration_status = None
        sample_job_record.artifacts = Artifacts(
            doc_0_path="jobs/test/doc_0.json",
            doc_1_path="jobs/test/doc_1.json",
            doc_2_path="jobs/test/doc_2.json",
            iterations=[],  # No prior iterations
        )
        mock_get_job.return_value = sample_job_record
        mock_update_job.return_value = sample_job_record

        # Mock the Celery task
        mock_iteration_task.apply_async = MagicMock()

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={
                "mode": "more_sources",
                "user_prompt": "Find more diverse perspectives",
                "max_new_sources": 4,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == sample_job_record.job_id
        assert data["iteration_id"] == "it_0001"  # First iteration
        assert data["iteration_index"] == 1
        assert data["status"] == "queued"

        # Verify task was queued
        mock_iteration_task.apply_async.assert_called_once()

    @patch("backend.worker.run_iteration_task")
    @patch("backend.app.routes.jobs_routes.update_job")
    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_increments_index(
        self, mock_get_job, mock_update_job, mock_iteration_task, app_client, sample_job_record
    ):
        """Second iteration should have index 2 and id it_0002."""
        sample_job_record.status = "completed"
        sample_job_record.iteration_status = None
        sample_job_record.artifacts = Artifacts(
            doc_0_path="jobs/test/doc_0.json",
            doc_1_path="jobs/test/doc_1.json",
            doc_2_path="jobs/test/doc_2.json",
            iterations=[
                {
                    "iteration_id": "it_0001",
                    "index": 1,
                    "status": "completed",
                    "created_at": "2026-01-20T00:00:00Z",
                    "request": {"mode": "more_sources"},
                }
            ],
        )
        mock_get_job.return_value = sample_job_record
        mock_update_job.return_value = sample_job_record
        mock_iteration_task.apply_async = MagicMock()

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "deeper"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["iteration_id"] == "it_0002"
        assert data["iteration_index"] == 2

    def test_iterate_job_validates_mode(self, app_client):
        """Invalid mode should return 422."""
        response = app_client.post(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/iterate",
            json={"mode": "invalid_mode"}
        )
        assert response.status_code == 422  # Validation error

    def test_iterate_job_validates_max_new_sources(self, app_client):
        """max_new_sources > 10 should return 422."""
        response = app_client.post(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/iterate",
            json={"mode": "more_sources", "max_new_sources": 15}
        )
        assert response.status_code == 422

    @patch("backend.worker.run_iteration_task")
    @patch("backend.app.routes.jobs_routes.update_job")
    @patch("backend.app.routes.jobs_routes.get_job")
    def test_iterate_job_concurrent_race_condition(
        self, mock_get_job, mock_update_job, mock_iteration_task, app_client, sample_job_record
    ):
        """Concurrent iteration attempts should return 409 via unique constraint.

        TOCTOU Fix: The unique partial index on (id) WHERE iteration_status IN
        ('queued', 'running') ensures only one active iteration per job.
        If update_job raises a unique constraint violation, we return 409.
        """
        sample_job_record.status = "completed"
        sample_job_record.iteration_status = None  # Passes application check
        sample_job_record.artifacts = Artifacts(
            doc_0_path="jobs/test/doc_0.json",
            doc_1_path="jobs/test/doc_1.json",
            doc_2_path="jobs/test/doc_2.json",
            iterations=[],
        )
        mock_get_job.return_value = sample_job_record

        # Simulate unique constraint violation from database
        mock_update_job.side_effect = Exception(
            "duplicate key value violates unique constraint \"idx_one_active_iteration_per_job\""
        )
        mock_iteration_task.apply_async = MagicMock()

        response = app_client.post(
            f"/jobs/{sample_job_record.job_id}/iterate",
            json={"mode": "more_sources"}
        )

        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"]

        # Task should NOT be queued when constraint violation occurs
        mock_iteration_task.apply_async.assert_not_called()
