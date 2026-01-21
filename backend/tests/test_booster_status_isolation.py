"""Tests for booster status isolation.

These tests ensure that booster execution does NOT modify job.status,
preventing the regression where jobs became "running_booster" and broke
UI completion gating.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone


class TestBoosterStatusIsolation:
    """Tests that booster uses separate tracking fields, not job.status."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock completed job with required artifacts."""
        job = Mock()
        job.job_id = "test-job-123"
        job.status = "completed"
        job.booster_status = None
        job.config_json = {}
        job.artifacts = Mock()
        job.artifacts.model_dump.return_value = {
            "jump_start": {"scope_in": ["test"]},
            "semantic_brief": {"semantic_core": "test"},
            "semantic_extractions": [],
        }
        return job

    def test_booster_must_not_set_running_booster_status(self):
        """CRITICAL: Booster code must NEVER set status='running_booster'."""
        from backend.worker import run_booster_task

        # Search for forbidden pattern in source code
        import inspect
        source = inspect.getsource(run_booster_task)

        # These patterns should NOT appear in the booster code anymore
        assert 'status="running_booster"' not in source, \
            "Booster must not set status='running_booster' - use booster_status instead"
        assert "status='running_booster'" not in source, \
            "Booster must not set status='running_booster' - use booster_status instead"

    def test_booster_route_must_not_set_running_booster_status(self):
        """CRITICAL: Booster route must NEVER set status='running_booster'."""
        from backend.app.routes import jobs_routes
        import inspect
        source = inspect.getsource(jobs_routes)

        # Count occurrences - should be zero in actual update_job calls
        # (May appear in comments or error messages, so we check specific patterns)
        assert 'update_job(job_id, status="running_booster"' not in source, \
            "Booster route must not set status='running_booster' - use booster_status instead"
        assert "update_job(job_id, status='running_booster'" not in source, \
            "Booster route must not set status='running_booster' - use booster_status instead"

    def test_booster_task_uses_booster_status_fields(self):
        """Booster task should update booster_status, not job.status.

        This test verifies the code structure rather than mocking the full flow,
        since the booster has complex dependencies.
        """
        from backend.worker import run_booster_task
        import inspect

        # Get the source code
        source = inspect.getsource(run_booster_task)

        # Verify booster_status is used (should appear in update_job calls)
        assert 'booster_status=' in source, \
            "Booster task must use booster_status field in update_job calls"
        assert 'booster_status="running"' in source or "booster_status='running'" in source, \
            "Booster task must set booster_status='running' on start"
        assert 'booster_status="completed"' in source or "booster_status='completed'" in source, \
            "Booster task must set booster_status='completed' on success"
        assert 'booster_status="failed"' in source or "booster_status='failed'" in source, \
            "Booster task must set booster_status='failed' on error"

        # Verify status= is NOT used with running_booster value
        assert 'status="running_booster"' not in source, \
            "Booster must never set status='running_booster'"

    @patch("backend.worker.update_job")
    @patch("backend.worker.get_job")
    def test_booster_checks_booster_status_for_running(
        self,
        mock_get_job,
        mock_update_job,
    ):
        """Booster should check booster_status='running' not job.status."""
        from backend.worker import run_booster_task

        # Create job with booster already running
        job = Mock()
        job.job_id = "test-job-123"
        job.status = "completed"  # Job is completed
        job.booster_status = "running"  # But booster is running
        job.artifacts = Mock()
        job.artifacts.model_dump.return_value = {
            "jump_start": {"scope_in": ["test"]},
            "semantic_brief": {"semantic_core": "test"},
        }
        mock_get_job.return_value = job

        # Should fail because booster is already running
        result = run_booster_task("test-job-123", "test-user-123")

        assert result["status"] == "failed"
        assert "already running" in result["error"].lower()

    def test_job_record_has_booster_fields(self):
        """JobRecord model should have all booster tracking fields."""
        from backend.models.job_record import JobRecord

        # Check field names exist
        field_names = [f.alias or name for name, f in JobRecord.model_fields.items()]

        assert "booster_status" in field_names or "booster_status" in [name for name in JobRecord.model_fields.keys()]
        assert "booster_started_at" in field_names or "booster_started_at" in [name for name in JobRecord.model_fields.keys()]
        assert "booster_completed_at" in field_names or "booster_completed_at" in [name for name in JobRecord.model_fields.keys()]
        assert "booster_error" in field_names or "booster_error" in [name for name in JobRecord.model_fields.keys()]
        assert "booster_progress_percent" in field_names or "booster_progress_percent" in [name for name in JobRecord.model_fields.keys()]

    def test_update_job_supports_booster_fields(self):
        """update_job should accept booster tracking fields."""
        from backend.state.impl.supabase_store import SupabaseJobStore
        import inspect

        # Get update_job signature
        sig = inspect.signature(SupabaseJobStore.update_job)
        params = list(sig.parameters.keys())

        # Verify booster parameters are present
        assert "booster_status" in params, "update_job must support booster_status"
        assert "booster_started_at" in params, "update_job must support booster_started_at"
        assert "booster_completed_at" in params, "update_job must support booster_completed_at"
        assert "booster_error" in params, "update_job must support booster_error"
        assert "booster_progress_percent" in params, "update_job must support booster_progress_percent"


class TestBoosterUIGating:
    """Tests that UI gating works correctly with booster status."""

    def test_completed_job_with_running_booster_is_still_completed(self):
        """
        CRITICAL: A job with status='completed' and booster_status='running'
        should still be treated as completed for UI gating purposes.

        This was the original bug: setting status='running_booster' broke
        UI completion checks.
        """
        from backend.models.job_record import JobRecord

        # Create a job that's completed but has booster running
        job = JobRecord(
            job_id="test-123",
            status="completed",  # Main pipeline is DONE
            booster_status="running",  # Booster is running separately
        )

        # For UI gating, job.status is what matters
        assert job.status == "completed"

        # booster_status is tracked separately
        assert job.booster_status == "running"

        # This test documents the fix: status NEVER changes due to booster
