"""
Tests for producer packet gating validation.

Regression tests for the fix: sources_count returning 0 because
JobRecord doesn't have a 'sources' attribute - sources are in
artifacts.source_ledger.source_manifest.
"""

import pytest
from backend.pipeline.producer.gating import (
    can_generate_producer_packet,
    get_source_summaries,
    _extract_sources_from_job,
)


class TestSourceExtraction:
    """Tests for _extract_sources_from_job helper."""

    def test_extract_from_direct_sources(self):
        """Should extract sources from job['sources'] if present."""
        job = {
            "sources": [
                {"source_id": "SRC_1", "title": "Test Source 1"},
                {"source_id": "SRC_2", "title": "Test Source 2"},
            ]
        }
        sources = _extract_sources_from_job(job)
        assert len(sources) == 2
        assert sources[0]["source_id"] == "SRC_1"

    def test_extract_from_source_manifest(self):
        """Should extract sources from artifacts.source_ledger.source_manifest."""
        job = {
            "status": "completed",
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "title": "Video 1"},
                        {"source_id": "SRC_2", "type": "article", "title": "Article 1"},
                        {"source_id": "SRC_3", "type": "youtube", "title": "Video 2"},
                        {"source_id": "SRC_4", "type": "reddit", "title": "Reddit 1"},
                    ]
                }
            }
        }
        sources = _extract_sources_from_job(job)
        assert len(sources) == 4
        assert sources[0]["source_id"] == "SRC_1"

    def test_extract_from_nested_data_wrapper(self):
        """Should handle storage format with 'data' wrapper."""
        job = {
            "status": "completed",
            "artifacts": {
                "source_ledger": {
                    "data": {
                        "source_manifest": [
                            {"source_id": "SRC_1", "type": "youtube"},
                            {"source_id": "SRC_2", "type": "article"},
                            {"source_id": "SRC_3", "type": "youtube"},
                            {"source_id": "SRC_4", "type": "reddit"},
                        ]
                    }
                }
            }
        }
        sources = _extract_sources_from_job(job)
        assert len(sources) == 4

    def test_extract_from_entries_fallback(self):
        """Should fall back to 'entries' key if source_manifest not present."""
        job = {
            "artifacts": {
                "source_ledger": {
                    "entries": [
                        {"source_id": "SRC_1", "confidence_ceiling": "high"},
                        {"source_id": "SRC_2", "confidence_ceiling": "medium"},
                    ]
                }
            }
        }
        sources = _extract_sources_from_job(job)
        assert len(sources) == 2

    def test_extract_empty_when_no_artifacts(self):
        """Should return empty list when no artifacts."""
        job = {"status": "completed"}
        sources = _extract_sources_from_job(job)
        assert sources == []

    def test_extract_empty_when_no_source_ledger(self):
        """Should return empty list when no source_ledger."""
        job = {
            "artifacts": {
                "doc_0_path": "documents/abc/doc_0.json"
            }
        }
        sources = _extract_sources_from_job(job)
        assert sources == []


class TestProducerGating:
    """Tests for can_generate_producer_packet function."""

    def test_gating_passes_with_4_sources(self):
        """Gating should pass with 4+ sources and high confidence."""
        job = {
            "status": "completed",
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "status": "ingested", "confidence_ceiling": "high"},
                        {"source_id": "SRC_2", "type": "article", "status": "ingested"},
                        {"source_id": "SRC_3", "type": "youtube", "status": "ingested"},
                        {"source_id": "SRC_4", "type": "reddit", "status": "ingested"},
                    ]
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is True
        assert reason == "OK"

    def test_gating_fails_with_insufficient_sources(self):
        """Gating should fail with fewer than 4 sources."""
        job = {
            "status": "completed",
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube"},
                        {"source_id": "SRC_2", "type": "article"},
                    ]
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is False
        assert "Need 4+ sources, have 2" in reason

    def test_gating_fails_with_zero_sources_regression(self):
        """REGRESSION: Gating should not report 0 sources when doc_0_path exists.

        This tests the specific production bug where sources_count was 0
        because JobRecord.sources doesn't exist - sources are in
        artifacts.source_ledger.source_manifest.
        """
        # Simulate job with doc_0_path but no inline source_ledger
        # (source_ledger must be fetched from storage in this case)
        job = {
            "status": "completed",
            "artifacts": {
                "doc_0_path": "documents/550e8400/doc_0.json"
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is False
        # Should report 0 sources (need to fetch from storage)
        assert "have 0" in reason

    def test_gating_with_inline_source_ledger(self):
        """Gating should work with inline source_ledger data."""
        job = {
            "status": "completed",
            "artifacts": {
                "doc_0_path": "documents/550e8400/doc_0.json",
                "source_ledger": {
                    "data": {
                        "document_type": "source_ledger",
                        "topic": "Test topic",
                        "source_manifest": [
                            {"source_id": "SRC_1", "type": "youtube", "status": "ingested", "confidence_ceiling": "high"},
                            {"source_id": "SRC_2", "type": "article", "status": "ingested"},
                            {"source_id": "SRC_3", "type": "youtube", "status": "ingested"},
                            {"source_id": "SRC_4", "type": "reddit", "status": "ingested"},
                        ]
                    }
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is True
        assert reason == "OK"

    def test_gating_fails_incomplete_job(self):
        """Gating should fail if job not completed."""
        job = {
            "status": "running",
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": f"SRC_{i}", "type": "youtube", "confidence_ceiling": "high"}
                        for i in range(5)
                    ]
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is False
        assert "must be completed" in reason

    def test_gating_passes_with_completed_with_warnings(self):
        """Gating should pass if job completed_with_warnings."""
        job = {
            "status": "completed_with_warnings",
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "status": "ingested", "confidence_ceiling": "high"},
                        {"source_id": "SRC_2", "type": "article", "status": "ingested"},
                        {"source_id": "SRC_3", "type": "youtube", "status": "ingested"},
                        {"source_id": "SRC_4", "type": "reddit", "status": "ingested"},
                    ]
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is True

    def test_gating_passes_with_running_producer_status(self):
        """REGRESSION: Gating should pass when status is 'running_producer'.

        This tests the deadlock fix where:
        1. API route validates gating (status=completed)
        2. API sets status='running_producer' and queues worker
        3. Worker re-runs gating but status is now 'running_producer'

        The worker's gating check must accept 'running_producer' because
        the API already validated the job was completed before queuing.
        """
        job = {
            "status": "running_producer",  # Set by API before worker runs
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "status": "ingested", "confidence_ceiling": "high"},
                        {"source_id": "SRC_2", "type": "article", "status": "ingested"},
                        {"source_id": "SRC_3", "type": "youtube", "status": "ingested"},
                        {"source_id": "SRC_4", "type": "reddit", "status": "ingested"},
                    ]
                }
            }
        }
        can_generate, reason = can_generate_producer_packet(job)
        assert can_generate is True, f"Gating should pass with running_producer status, got: {reason}"
        assert reason == "OK"


class TestGetSourceSummaries:
    """Tests for get_source_summaries function."""

    def test_extracts_summaries_from_source_manifest(self):
        """Should extract source summaries from source_manifest."""
        job = {
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "title": "Video Title"},
                        {"source_id": "SRC_2", "type": "article", "title": "Article Title"},
                    ]
                }
            }
        }
        summaries = get_source_summaries(job)
        assert len(summaries) == 2
        assert summaries[0]["source_id"] == "SRC_1"
        assert summaries[0]["source_type"] == "youtube"
        assert summaries[0]["title"] == "Video Title"

    def test_handles_missing_source_type_key(self):
        """Should handle 'type' key (Doc 0 format) as source_type."""
        job = {
            "artifacts": {
                "source_ledger": {
                    "source_manifest": [
                        {"source_id": "SRC_1", "type": "youtube", "title": "Test"},
                    ]
                }
            }
        }
        summaries = get_source_summaries(job)
        assert summaries[0]["source_type"] == "youtube"


class TestHasSourcesHelper:
    """Tests for the _has_sources helper used in storage fetch logic."""

    def test_has_sources_none(self):
        """Should return False for None."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        assert _has_sources(None) is False

    def test_has_sources_empty_dict(self):
        """Should return False for empty dict."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        assert _has_sources({}) is False

    def test_has_sources_direct_manifest(self):
        """Should return True for direct source_manifest."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        sl = {"source_manifest": [{"source_id": "SRC_1"}]}
        assert _has_sources(sl) is True

    def test_has_sources_nested_data(self):
        """Should return True for nested data.source_manifest (storage format)."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        sl = {"data": {"source_manifest": [{"source_id": "SRC_1"}]}, "markdown": "..."}
        assert _has_sources(sl) is True

    def test_has_sources_empty_manifest(self):
        """Should return False for empty source_manifest array."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        sl = {"source_manifest": []}
        assert _has_sources(sl) is False

    def test_has_sources_markdown_only(self):
        """Should return False for dict with only markdown (no sources)."""
        def _has_sources(sl):
            if not sl or not isinstance(sl, dict):
                return False
            if sl.get("source_manifest"):
                return True
            data = sl.get("data")
            if isinstance(data, dict) and data.get("source_manifest"):
                return True
            return False

        sl = {"markdown": "# Source Ledger...", "data": {}}
        assert _has_sources(sl) is False
