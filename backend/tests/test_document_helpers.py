"""
Tests for backend/pipeline/document_helpers.py
"""
import pytest
from unittest.mock import MagicMock
from backend.pipeline.document_helpers import (
    generate_master_index,
    generate_transcripts_md,
    generate_web_extracts_md,
    generate_evidence_table_md,
)


class TestGenerateMasterIndex:
    """Tests for generate_master_index function."""

    def test_includes_topic(self):
        """Should include topic in output."""
        job_config = MagicMock()
        job_config.topic = "Test Topic"
        job_config.mode.value = "investigation"

        result = generate_master_index(job_config, {})

        assert "Test Topic" in result

    def test_includes_mode(self):
        """Should include mode in output."""
        job_config = MagicMock()
        job_config.topic = "Test Topic"
        job_config.mode.value = "investigation"

        result = generate_master_index(job_config, {})

        assert "investigation" in result

    def test_includes_document_links(self):
        """Should include document section links."""
        job_config = MagicMock()
        job_config.topic = "Test Topic"
        job_config.mode.value = "investigation"

        result = generate_master_index(job_config, {})

        assert "Research Map" in result
        assert "Source Shortlist" in result
        assert "Evidence Table" in result


class TestGenerateTranscriptsMd:
    """Tests for generate_transcripts_md function."""

    def test_empty_transcripts(self):
        """Should handle empty transcript list."""
        result = generate_transcripts_md([])

        assert "No transcripts available" in result

    def test_transcript_with_text(self):
        """Should include transcript text."""
        transcript = MagicMock()
        transcript.video_id = "dQw4w9WgXcQ"
        transcript.video_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"
        transcript.status.value = "success"
        transcript.text = "Sample transcript text"
        transcript.error_message = None

        result = generate_transcripts_md([transcript])

        assert "dQw4w9WgXcQ" in result
        assert "Sample transcript text" in result

    def test_transcript_with_error(self):
        """Should show error message for failed transcripts."""
        transcript = MagicMock()
        transcript.video_id = "abc123def45"
        transcript.video_url = "https://youtube.com/watch?v=abc123def45"
        transcript.status.value = "failed"
        transcript.text = None
        transcript.error_message = "Transcript unavailable"

        result = generate_transcripts_md([transcript])

        assert "Transcript unavailable" in result


class TestGenerateWebExtractsMd:
    """Tests for generate_web_extracts_md function."""

    def test_empty_sources(self):
        """Should handle empty source list."""
        result = generate_web_extracts_md([])

        assert "No web sources available" in result

    def test_source_with_content(self):
        """Should include source content."""
        source = MagicMock()
        source.title = "Test Article"
        source.url = "https://example.com/article"
        source.source_type.value = "article"
        source.published_at = "2025-01-01"
        source.text = "Article content here"
        source.notes = None

        result = generate_web_extracts_md([source])

        assert "Test Article" in result
        assert "example.com" in result


class TestGenerateEvidenceTableMd:
    """Tests for generate_evidence_table_md function."""

    def test_empty_evidence(self):
        """Should handle empty evidence list."""
        result = generate_evidence_table_md([])

        assert "No evidence records available" in result

    def test_evidence_table_format(self):
        """Should generate markdown table format."""
        result = generate_evidence_table_md([])

        # Even empty should have header structure
        assert "Evidence Table" in result
