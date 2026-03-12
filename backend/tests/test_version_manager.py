"""Tests for document version manager (Phase 3).

Validates:
- Storage method calls (upload_file, delete_file, download)
- Path prefix consistency (research-jobs/)
- Rolling window logic
- Latest pointer management
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.pipeline.version_manager import (
    MAX_VERSIONS,
    _apply_rolling_window,
    _build_version_metadata,
    _compute_diff_summary,
    _count_claims,
    _count_sources,
    _latest_pointer_path,
    _version_path,
    get_document_version,
    list_document_versions,
    store_document_version,
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

class TestPathHelpers:
    """Verify storage paths include the research-jobs/ prefix."""

    def test_version_path_has_prefix(self) -> None:
        path = _version_path("job-123", "doc_3", 2)
        assert path == "research-jobs/job-123/doc_3/v2.json"

    def test_latest_pointer_path_has_prefix(self) -> None:
        path = _latest_pointer_path("job-123", "doc_0")
        assert path == "research-jobs/job-123/doc_0/latest.json"

    def test_version_path_v1(self) -> None:
        path = _version_path("abc", "doc_1", 1)
        assert path == "research-jobs/abc/doc_1/v1.json"


# ---------------------------------------------------------------------------
# store_document_version
# ---------------------------------------------------------------------------

class TestStoreDocumentVersion:
    """Verify store_document_version calls the correct storage methods."""

    @patch("backend.pipeline.version_manager.get_storage_client")
    def test_first_version_uploads_correctly(self, mock_get_client: MagicMock) -> None:
        """First version: upload v1.json + latest.json, no rolling window drop."""
        storage = MagicMock()
        storage._documents_bucket = "documents"
        # No existing versions
        storage.download.side_effect = Exception("not found")
        mock_get_client.return_value = storage

        version, path = store_document_version(
            job_id="job-1",
            doc_type="doc_3",
            content={"core_facts": [{"id": "f1"}]},
            trigger="initial_run",
            markdown="# Brief",
        )

        assert version == 1
        assert path == "research-jobs/job-1/doc_3/v1.json"

        # Should have called upload_file for v1.json and latest.json
        upload_calls = storage.upload_file.call_args_list
        assert len(upload_calls) == 2  # v1.json + latest.json
        assert upload_calls[0][0][0] == "research-jobs/job-1/doc_3/v1.json"
        assert upload_calls[1][0][0] == "research-jobs/job-1/doc_3/latest.json"

        # Should NOT have called delete_file (only 1 version, under MAX_VERSIONS)
        storage.delete_file.assert_not_called()

    @patch("backend.pipeline.version_manager.get_storage_client")
    def test_no_storage_returns_fallback(self, mock_get_client: MagicMock) -> None:
        """When storage is unavailable, return (1, None)."""
        mock_get_client.return_value = None
        version, path = store_document_version("job-1", "doc_0", {"sources": []})
        assert version == 1
        assert path is None

    @patch("backend.pipeline.version_manager.get_storage_client")
    def test_rolling_window_drops_oldest(self, mock_get_client: MagicMock) -> None:
        """When 5th version is created, v1 should be dropped."""
        storage = MagicMock()
        storage._documents_bucket = "documents"
        # Simulate latest pointer returning v4
        latest_pointer = json.dumps({"latest_version": 4}).encode("utf-8")
        storage.download.return_value = latest_pointer
        mock_get_client.return_value = storage

        version, path = store_document_version(
            job_id="job-1",
            doc_type="doc_2",
            content={"key_points": [{"id": "kp1"}, {"id": "kp2"}]},
            trigger="deeper",
        )

        assert version == 5
        assert path == "research-jobs/job-1/doc_2/v5.json"

        # Should drop v1 (oldest outside window)
        storage.delete_file.assert_called_once_with(
            "research-jobs/job-1/doc_2/v1.json",
            bucket="documents",
        )


# ---------------------------------------------------------------------------
# get_document_version
# ---------------------------------------------------------------------------

class TestGetDocumentVersion:

    @patch("backend.pipeline.version_manager.get_storage_client")
    def test_get_specific_version(self, mock_get_client: MagicMock) -> None:
        storage = MagicMock()
        storage._documents_bucket = "documents"
        doc = {"data": {"sources": []}, "markdown": "# Doc", "version_metadata": {"version": 2}}
        storage.download.return_value = json.dumps(doc).encode("utf-8")
        mock_get_client.return_value = storage

        result = get_document_version("job-1", "doc_0", version=2)
        assert result is not None
        assert result["data"] == {"sources": []}
        storage.download.assert_called_once_with(
            "research-jobs/job-1/doc_0/v2.json",
            bucket="documents",
        )

    @patch("backend.pipeline.version_manager.get_storage_client")
    def test_no_storage_returns_none(self, mock_get_client: MagicMock) -> None:
        mock_get_client.return_value = None
        assert get_document_version("job-1", "doc_0") is None


# ---------------------------------------------------------------------------
# Rolling window logic
# ---------------------------------------------------------------------------

class TestRollingWindow:

    def test_apply_rolling_window_under_limit(self) -> None:
        """No deletion when under MAX_VERSIONS."""
        storage = MagicMock()
        storage._documents_bucket = "documents"
        _apply_rolling_window(storage, "job-1", "doc_3", latest_version=3)
        storage.delete_file.assert_not_called()

    def test_apply_rolling_window_at_limit(self) -> None:
        """No deletion when exactly at MAX_VERSIONS."""
        storage = MagicMock()
        storage._documents_bucket = "documents"
        _apply_rolling_window(storage, "job-1", "doc_3", latest_version=MAX_VERSIONS)
        storage.delete_file.assert_not_called()

    def test_apply_rolling_window_over_limit(self) -> None:
        """Drop v1 when creating v5 (MAX_VERSIONS=4)."""
        storage = MagicMock()
        storage._documents_bucket = "documents"
        _apply_rolling_window(storage, "job-1", "doc_3", latest_version=MAX_VERSIONS + 1)
        storage.delete_file.assert_called_once_with(
            "research-jobs/job-1/doc_3/v1.json",
            bucket="documents",
        )


# ---------------------------------------------------------------------------
# Count & diff helpers
# ---------------------------------------------------------------------------

class TestCountHelpers:

    def test_count_sources_from_list(self) -> None:
        assert _count_sources({"sources": [1, 2, 3]}) == 3

    def test_count_sources_from_field(self) -> None:
        assert _count_sources({"source_count": 7}) == 7

    def test_count_sources_empty(self) -> None:
        assert _count_sources({}) == 0

    def test_count_claims_key_points(self) -> None:
        assert _count_claims({"key_points": [1, 2]}) == 2

    def test_count_claims_core_facts(self) -> None:
        assert _count_claims({"core_facts": [1]}) == 1

    def test_count_claims_empty(self) -> None:
        assert _count_claims({}) == 0


class TestDiffSummary:

    def test_initial_version(self) -> None:
        summary = _compute_diff_summary("initial_run", 5, 3, None)
        assert "Initial" in summary
        assert "5 sources" in summary
        assert "3 claims" in summary

    def test_sources_added(self) -> None:
        prev = {"sources": [1, 2]}
        summary = _compute_diff_summary("expand_sources", 4, 2, prev)
        assert "+2 sources" in summary

    def test_no_change_uses_mode(self) -> None:
        prev = {"sources": [1], "key_points": [1]}
        summary = _compute_diff_summary("different_angle", 1, 1, prev)
        assert summary == "New perspective applied"
