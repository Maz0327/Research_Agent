"""Tests for Supabase store DB→JobRecord mapping.

Verifies that artifacts doc_path fields survive the read path.
These tests do NOT require a real Supabase connection.
"""
import pytest
from datetime import datetime, timezone

from backend.state.impl.supabase_store import _record_from_db_row, _normalize_jsonb_field


class TestRecordFromDbRow:
    """Tests for _record_from_db_row mapping function."""

    def _make_db_row(self, **overrides) -> dict:
        """Create a minimal valid DB row for testing."""
        base = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": None,
            "title": "Test Job",
            "pipeline": "investigation",
            "created_at": "2026-01-21T10:00:00Z",
            "status": "completed",
            "stage": "completed",
            "stage_started_at": None,
            "progress_percent": 100,
            "error": None,
            "config_json": {"topic": "Test topic"},
            "warnings": [],
            "artifacts": {},
            "outputs": {},
            "interpretations": None,
            "selected_interpretations": None,
        }
        base.update(overrides)
        return base

    def test_doc_paths_preserved_through_mapping(self):
        """REGRESSION: doc_0/1/2/3_path fields must survive DB→JobRecord."""
        job_id = "550e8400-e29b-41d4-a716-446655440000"
        row = self._make_db_row(
            id=job_id,
            artifacts={
                "doc_0_path": f"documents/{job_id}/doc_0.json",
                "doc_1_path": f"documents/{job_id}/doc_1.json",
                "doc_2_path": f"documents/{job_id}/doc_2.json",
                "doc_3_path": f"documents/{job_id}/doc_3.json",
            },
        )

        job = _record_from_db_row(row)

        # These assertions would FAIL before the fix
        assert job.artifacts is not None
        assert job.artifacts.doc_0_path == f"documents/{job_id}/doc_0.json"
        assert job.artifacts.doc_1_path == f"documents/{job_id}/doc_1.json"
        assert job.artifacts.doc_2_path == f"documents/{job_id}/doc_2.json"
        assert job.artifacts.doc_3_path == f"documents/{job_id}/doc_3.json"

    def test_semantic_pipeline_fields_preserved(self):
        """Semantic pipeline fields (inline data) must be preserved."""
        row = self._make_db_row(
            artifacts={
                "source_ledger": {"topic": "Test", "sources": []},
                "jump_start": {"scope_in": ["AI"], "scope_out": []},
                "semantic_brief": {"semantic_core": "test"},
            },
        )

        job = _record_from_db_row(row)

        assert job.artifacts.source_ledger == {"topic": "Test", "sources": []}
        assert job.artifacts.jump_start == {"scope_in": ["AI"], "scope_out": []}
        assert job.artifacts.semantic_brief == {"semantic_core": "test"}

    def test_empty_artifacts_handled(self):
        """Empty artifacts should produce empty Artifacts object."""
        row = self._make_db_row(artifacts={})

        job = _record_from_db_row(row)

        assert job.artifacts is not None
        assert job.artifacts.doc_0_path is None
        assert job.artifacts.source_ledger is None

    def test_null_artifacts_handled(self):
        """NULL artifacts from DB should produce empty Artifacts object."""
        row = self._make_db_row(artifacts=None)

        job = _record_from_db_row(row)

        assert job.artifacts is not None
        assert job.artifacts.doc_0_path is None

    def test_outputs_preserved(self):
        """Outputs fields should be preserved through mapping."""
        row = self._make_db_row(
            outputs={
                "research_map_md": "# Research Map\nContent here",
                "quote_bank_md": "# Quotes\n- Quote 1",
            },
        )

        job = _record_from_db_row(row)

        assert job.outputs is not None
        assert job.outputs.research_map_md == "# Research Map\nContent here"
        assert job.outputs.quote_bank_md == "# Quotes\n- Quote 1"


class TestNormalizeJsonbField:
    """Tests for _normalize_jsonb_field helper."""

    def test_dict_passthrough(self):
        """Dict input should pass through unchanged."""
        data = {"key": "value", "nested": {"a": 1}}
        result = _normalize_jsonb_field(data)
        assert result == data

    def test_none_returns_empty_dict(self):
        """None input should return empty dict."""
        result = _normalize_jsonb_field(None)
        assert result == {}

    def test_corrupted_list_merged(self):
        """Corrupted list of dicts should be merged."""
        data = [{"a": 1}, {"b": 2}]
        result = _normalize_jsonb_field(data, field_name="test", job_id="test-123")
        assert result == {"a": 1, "b": 2}

    def test_json_string_parsed(self):
        """JSON string should be parsed to dict."""
        data = '{"key": "value"}'
        result = _normalize_jsonb_field(data)
        assert result == {"key": "value"}

    def test_invalid_string_returns_empty(self):
        """Invalid string should return empty dict."""
        result = _normalize_jsonb_field("not json")
        assert result == {}

    def test_logging_signature_accepts_context_params(self):
        """Function should accept field_name and job_id parameters without error."""
        # Just verify the function signature works - loguru sink testing is complex
        # The warning IS logged (visible in pytest stderr capture), just not easily assertable
        result = _normalize_jsonb_field([{"a": 1}], field_name="artifacts", job_id="job-123")
        assert result == {"a": 1}


class TestArtifactsSerialization:
    """Tests for Artifacts model serialization round-trip."""

    def test_model_dump_preserves_doc_paths(self):
        """Artifacts.model_dump() should include doc_path fields."""
        from backend.models.job_record import Artifacts

        artifacts = Artifacts(
            doc_0_path="documents/123/doc_0.json",
            doc_1_path="documents/123/doc_1.json",
        )

        dumped = artifacts.model_dump(exclude_none=True)

        assert dumped["doc_0_path"] == "documents/123/doc_0.json"
        assert dumped["doc_1_path"] == "documents/123/doc_1.json"

    def test_artifacts_from_dict_with_doc_paths(self):
        """Artifacts can be constructed from dict with doc_path fields."""
        from backend.models.job_record import Artifacts

        data = {
            "doc_0_path": "documents/abc/doc_0.json",
            "doc_1_path": "documents/abc/doc_1.json",
            "doc_2_path": "documents/abc/doc_2.json",
            "doc_3_path": "documents/abc/doc_3.json",
        }

        artifacts = Artifacts(**data)

        assert artifacts.doc_0_path == "documents/abc/doc_0.json"
        assert artifacts.doc_1_path == "documents/abc/doc_1.json"
        assert artifacts.doc_2_path == "documents/abc/doc_2.json"
        assert artifacts.doc_3_path == "documents/abc/doc_3.json"
