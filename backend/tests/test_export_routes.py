"""
Tests for backend/app/routes/export_routes.py

Tests document export endpoints for JSON, BibTeX, RIS, markdown, etc.

Phase 9 - Critical Gap Fix
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone


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
def sample_completed_job():
    """Create a sample completed job record for export testing."""
    from backend.models.job_record import JobRecord, Artifacts

    artifacts = Artifacts(
        clips=[
            {
                "clip_id": "CLIP_1",
                "title": "Test Clip",
                "start_time": "00:00:00",
                "end_time": "00:01:00",
            }
        ],
        quotes=[
            {
                "quote_id": "QT_1",
                "text": "This is a test quote",
                "timestamp": "00:30",
                "source_id": "SRC_1",
            }
        ],
        source_ledger={"topic": "Test", "sources": []},
        semantic_brief={"summary": "Test brief"},
        jump_start={"directions": []},
    )

    return JobRecord(
        job_id="550e8400-e29b-41d4-a716-446655440000",
        status="completed",
        stage="completed",
        progress_percent=100,
        config_json={
            "topic": "Test Research Topic",
            "prompt": "Test prompt",
            "title": "Test Video Analysis",
            "research_topic": "Testing exports",
        },
        user_id="test-user-123",
        created_at=datetime.now(timezone.utc),
        warnings=[],
        outputs={},
        artifacts=artifacts,
        reddit_posts=[],
        entities={},
        timeline_events=[],
        discovered_angles=[],
    )


@pytest.fixture
def sample_running_job():
    """Create a sample running job (not ready for export)."""
    from backend.models.job_record import JobRecord

    return JobRecord(
        job_id="660e8400-e29b-41d4-a716-446655440001",
        status="running",
        stage="extraction",
        progress_percent=50,
        config_json={"topic": "Running job"},
        user_id="test-user-123",
        created_at=datetime.now(timezone.utc),
        warnings=[],
        outputs={},
        artifacts=None,
    )


@pytest.fixture
def other_user_job():
    """Create a job owned by another user."""
    from backend.models.job_record import JobRecord

    return JobRecord(
        job_id="770e8400-e29b-41d4-a716-446655440002",
        status="completed",
        stage="completed",
        progress_percent=100,
        config_json={"topic": "Other user job"},
        user_id="other-user-456",  # Different user
        created_at=datetime.now(timezone.utc),
        warnings=[],
        outputs={},
        artifacts=None,
    )


@pytest.fixture
def export_client(mock_auth_user):
    """Create test client for export endpoints with mocked auth."""
    from backend.app.main import app
    from backend.auth.ban_check import get_active_user

    async def mock_get_active_user(user=None):
        return mock_auth_user

    app.dependency_overrides[get_active_user] = mock_get_active_user

    yield TestClient(app)

    app.dependency_overrides.clear()


# =============================================================================
# TestExportJobEndpoint
# =============================================================================


class TestExportJobEndpoint:
    """Tests for GET /jobs/{job_id}/export endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_job_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.get(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export?format=json"
        )
        assert response.status_code == 404

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_unauthorized_job(self, mock_get_job, export_client, other_user_job):
        """Should return 403 for job owned by another user."""
        mock_get_job.return_value = other_user_job

        response = export_client.get(
            f"/jobs/{other_user_job.job_id}/export?format=json"
        )
        assert response.status_code == 403

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_running_job_rejected(self, mock_get_job, export_client, sample_running_job):
        """Should reject export for non-completed jobs."""
        mock_get_job.return_value = sample_running_job

        response = export_client.get(
            f"/jobs/{sample_running_job.job_id}/export?format=json"
        )
        assert response.status_code == 400
        assert "not ready" in response.json()["detail"].lower()

    @patch("backend.app.routes.export_routes.ExportManager")
    @patch("backend.app.routes.export_routes.get_job")
    def test_export_json_format(self, mock_get_job, mock_export_manager, export_client, sample_completed_job):
        """Should export job in JSON format."""
        mock_get_job.return_value = sample_completed_job

        mock_manager = MagicMock()
        mock_manager.to_json.return_value = '{"test": "data"}'
        mock_export_manager.return_value = mock_manager

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export?format=json"
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    @patch("backend.app.routes.export_routes.ExportManager")
    @patch("backend.app.routes.export_routes.get_job")
    def test_export_bibtex_format(self, mock_get_job, mock_export_manager, export_client, sample_completed_job):
        """Should export job in BibTeX format."""
        mock_get_job.return_value = sample_completed_job

        mock_manager = MagicMock()
        mock_manager.to_bibtex.return_value = "@article{test, title={Test}}"
        mock_export_manager.return_value = mock_manager

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export?format=bibtex"
        )

        assert response.status_code == 200
        assert "bibtex" in response.headers["content-type"]

    @patch("backend.app.routes.export_routes.ExportManager")
    @patch("backend.app.routes.export_routes.get_job")
    def test_export_with_download_flag(self, mock_get_job, mock_export_manager, export_client, sample_completed_job):
        """Should set Content-Disposition for download."""
        mock_get_job.return_value = sample_completed_job

        mock_manager = MagicMock()
        mock_manager.to_json.return_value = '{"test": "data"}'
        mock_export_manager.return_value = mock_manager

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export?format=json&download=true"
        )

        assert response.status_code == 200
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]

    @patch("backend.app.routes.export_routes.ExportManager")
    @patch("backend.app.routes.export_routes.get_job")
    def test_export_brief_format(self, mock_get_job, mock_export_manager, export_client, sample_completed_job):
        """Should export job as markdown brief."""
        mock_get_job.return_value = sample_completed_job

        mock_manager = MagicMock()
        mock_manager.to_brief.return_value = "# Research Brief\n\nTest content"
        mock_export_manager.return_value = mock_manager

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export?format=brief"
        )

        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]


# =============================================================================
# TestExportAllFormatsEndpoint
# =============================================================================


class TestExportAllFormatsEndpoint:
    """Tests for GET /jobs/{job_id}/export/all endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_all_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.get(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export/all"
        )
        assert response.status_code == 404

    @patch("backend.app.routes.export_routes.ExportManager")
    @patch("backend.app.routes.export_routes.get_job")
    def test_export_all_formats(self, mock_get_job, mock_export_manager, export_client, sample_completed_job):
        """Should export job in all formats."""
        mock_get_job.return_value = sample_completed_job

        mock_manager = MagicMock()
        mock_manager.generate_all_from_data.return_value = {
            "json": "{}",
            "bibtex": "@article{}",
            "ris": "TY  - ",
        }
        mock_export_manager.return_value = mock_manager

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export/all"
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "exports" in data


# =============================================================================
# TestMarkdownExportEndpoint
# =============================================================================


class TestMarkdownExportEndpoint:
    """Tests for GET /jobs/{job_id}/export/markdown endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_markdown_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.get(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export/markdown"
        )
        assert response.status_code == 404

    @patch("backend.app.routes.export_routes.get_job")
    def test_markdown_no_artifacts(self, mock_get_job, export_client, sample_completed_job):
        """Should return 400 if no artifacts."""
        sample_completed_job.artifacts = None
        mock_get_job.return_value = sample_completed_job

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export/markdown"
        )
        assert response.status_code == 400

    @patch("backend.pipeline.video_export_formatter.format_video_analysis_for_export")
    @patch("backend.app.routes.export_routes.get_job")
    def test_markdown_export_success(
        self, mock_get_job, mock_format, export_client, sample_completed_job
    ):
        """Should export video analysis as markdown."""
        mock_get_job.return_value = sample_completed_job
        mock_format.return_value = "# Video Analysis\n\nTest content"

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export/markdown"
        )

        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]


# =============================================================================
# TestClipsOnlyEndpoint
# =============================================================================


class TestClipsOnlyEndpoint:
    """Tests for GET /jobs/{job_id}/export/clips-only endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_clips_only_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.get(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export/clips-only"
        )
        assert response.status_code == 404

    @patch("backend.pipeline.video_export_formatter.format_clips_only")
    @patch("backend.app.routes.export_routes.get_job")
    def test_clips_only_success(self, mock_get_job, mock_format, export_client, sample_completed_job):
        """Should export clips only."""
        mock_get_job.return_value = sample_completed_job
        mock_format.return_value = "# Clips\n\n1. Test clip"

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export/clips-only"
        )

        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]


# =============================================================================
# TestQuotesOnlyEndpoint
# =============================================================================


class TestQuotesOnlyEndpoint:
    """Tests for GET /jobs/{job_id}/export/quotes-only endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_quotes_only_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.get(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export/quotes-only"
        )
        assert response.status_code == 404

    @patch("backend.pipeline.video_export_formatter.format_quotes_only")
    @patch("backend.app.routes.export_routes.get_job")
    def test_quotes_only_success(self, mock_get_job, mock_format, export_client, sample_completed_job):
        """Should export quotes only."""
        mock_get_job.return_value = sample_completed_job
        mock_format.return_value = "# Quotes\n\n> Test quote"

        response = export_client.get(
            f"/jobs/{sample_completed_job.job_id}/export/quotes-only"
        )

        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]


# =============================================================================
# TestGoogleDocsExportEndpoint
# =============================================================================


class TestGoogleDocsExportEndpoint:
    """Tests for POST /jobs/{job_id}/export/google-docs endpoint."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_google_docs_not_found(self, mock_get_job, export_client):
        """Should return 404 for non-existent job."""
        mock_get_job.return_value = None

        response = export_client.post(
            "/jobs/550e8400-e29b-41d4-a716-446655440000/export/google-docs"
        )
        assert response.status_code == 404

    @patch("backend.app.routes.export_routes.get_job")
    def test_google_docs_no_artifacts(self, mock_get_job, export_client, sample_completed_job):
        """Should return 400 if no artifacts."""
        sample_completed_job.artifacts = None
        mock_get_job.return_value = sample_completed_job

        response = export_client.post(
            f"/jobs/{sample_completed_job.job_id}/export/google-docs"
        )
        assert response.status_code == 400

    @patch("backend.integrations.google_drive_docs.create_transcript_doc")
    @patch("backend.pipeline.video_export_formatter.format_video_analysis_for_export")
    @patch("backend.app.routes.export_routes.get_job")
    def test_google_docs_success(
        self, mock_get_job, mock_format, mock_create_doc, export_client, sample_completed_job
    ):
        """Should create Google Doc successfully."""
        mock_get_job.return_value = sample_completed_job
        mock_format.return_value = "# Test Content"
        mock_create_doc.return_value = {
            "folder_url": "https://drive.google.com/folder/123",
            "doc_url": "https://docs.google.com/document/d/456",
        }

        response = export_client.post(
            f"/jobs/{sample_completed_job.job_id}/export/google-docs"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "doc_url" in data

    @patch("backend.integrations.google_drive_docs.create_transcript_doc")
    @patch("backend.pipeline.video_export_formatter.format_video_analysis_for_export")
    @patch("backend.app.routes.export_routes.get_job")
    def test_google_docs_not_configured(
        self, mock_get_job, mock_format, mock_create_doc, export_client, sample_completed_job
    ):
        """Should handle missing Google config gracefully."""
        from backend.config import MissingRequiredSettingError

        mock_get_job.return_value = sample_completed_job
        mock_format.return_value = "# Test Content"
        mock_create_doc.side_effect = MissingRequiredSettingError("Google OAuth not configured")

        response = export_client.post(
            f"/jobs/{sample_completed_job.job_id}/export/google-docs"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not configured" in data["error"].lower()


# =============================================================================
# TestExportFormatEnum
# =============================================================================


class TestExportFormatEnum:
    """Tests for ExportFormat enum values."""

    def test_all_formats_defined(self):
        """All export formats should be defined."""
        from backend.app.routes.export_routes import ExportFormat

        expected_formats = [
            "json", "bibtex", "ris", "chapters",
            "youtube_chapters", "podcast_chapters",
            "clips", "social", "brief"
        ]

        for fmt in expected_formats:
            assert hasattr(ExportFormat, fmt.upper())

    def test_content_types_mapping(self):
        """All formats should have content type mappings."""
        from backend.app.routes.export_routes import ExportFormat, CONTENT_TYPES

        for fmt in ExportFormat:
            assert fmt in CONTENT_TYPES

    def test_file_extensions_mapping(self):
        """All formats should have file extension mappings."""
        from backend.app.routes.export_routes import ExportFormat, FILE_EXTENSIONS

        for fmt in ExportFormat:
            assert fmt in FILE_EXTENSIONS


# =============================================================================
# TestExportAuthorizationAndOwnership
# =============================================================================


class TestExportAuthorizationAndOwnership:
    """Tests verifying export authorization and ownership checks."""

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_requires_ownership(self, mock_get_job, export_client, other_user_job):
        """User should only export their own jobs."""
        mock_get_job.return_value = other_user_job

        response = export_client.get(
            f"/jobs/{other_user_job.job_id}/export?format=json"
        )

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @patch("backend.app.routes.export_routes.get_job")
    def test_export_all_requires_ownership(self, mock_get_job, export_client, other_user_job):
        """User should only export all formats for their own jobs."""
        mock_get_job.return_value = other_user_job

        response = export_client.get(
            f"/jobs/{other_user_job.job_id}/export/all"
        )

        assert response.status_code == 403

    @patch("backend.app.routes.export_routes.get_job")
    def test_markdown_requires_ownership(self, mock_get_job, export_client, other_user_job):
        """User should only export markdown for their own jobs."""
        mock_get_job.return_value = other_user_job

        response = export_client.get(
            f"/jobs/{other_user_job.job_id}/export/markdown"
        )

        assert response.status_code == 403
