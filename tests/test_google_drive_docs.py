"""Unit tests for Google Drive and Docs integration."""
import pytest

from backend.integrations.google_drive_docs import (
    create_research_packet,
    DOC_NAMES,
)


def test_doc_names_defined():
    """Test that DOC_NAMES contains all expected documents."""
    expected_docs = [
        "00_MASTER_INDEX",
        "01_RESEARCH_MAP",
        "02_SOURCE_SHORTLIST",
        "03_YOUTUBE_INDEX",
        "04_TRANSCRIPTS",
        "05_WEB_EXTRACTS",
        "06_QUOTE_BANK",
        "07_CLAIMS_LEDGER",
        "08_EVIDENCE_TABLE",
        "09_MISSING_ANGLES",
    ]
    
    assert len(DOC_NAMES) == 10
    assert all(doc in DOC_NAMES for doc in expected_docs)


def test_create_research_packet_structure():
    """Test that create_research_packet has correct structure."""
    folder_name = "Test Research Packet"
    doc_contents = {
        "00_MASTER_INDEX": "# Master Index\n\nTest content",
        "01_RESEARCH_MAP": "# Research Map\n\nMap content",
    }
    
    # This will fail without Google OAuth credentials, but tests structure
    try:
        result = create_research_packet(folder_name, doc_contents)
        
        # Should return dict with required keys
        assert "folder_url" in result
        assert "doc_urls" in result
        assert "manifest_url" in result
        assert isinstance(result["doc_urls"], dict)
        
        # Should have URLs for all created docs
        assert len(result["doc_urls"]) == len(DOC_NAMES)
        
    except (MissingRequiredSettingError, RuntimeError):
        # Expected if OAuth not configured
        pytest.skip("Google OAuth not configured for testing")


def test_create_research_packet_with_all_docs():
    """Test creating packet with all document contents."""
    folder_name = "Full Research Packet"
    doc_contents = {
        doc_name: f"# {doc_name}\n\nContent for {doc_name}"
        for doc_name in DOC_NAMES
    }
    
    try:
        result = create_research_packet(folder_name, doc_contents)
        
        assert result["folder_url"] is not None
        assert len(result["doc_urls"]) == len(DOC_NAMES)
        
        # Check all doc URLs are present
        for doc_name in DOC_NAMES:
            assert doc_name in result["doc_urls"]
            assert result["doc_urls"][doc_name].startswith("http")
        
        assert result["manifest_url"] is not None
        
    except (MissingRequiredSettingError, RuntimeError):
        pytest.skip("Google OAuth not configured for testing")


def test_create_research_packet_with_partial_contents():
    """Test creating packet with only some document contents."""
    folder_name = "Partial Research Packet"
    doc_contents = {
        "01_RESEARCH_MAP": "# Research Map\n\nMap here",
        "06_QUOTE_BANK": "# Quote Bank\n\nQuotes here",
    }
    
    try:
        result = create_research_packet(folder_name, doc_contents)
        
        # Should still create all docs, but only some have content
        assert len(result["doc_urls"]) == len(DOC_NAMES)
        
    except (MissingRequiredSettingError, RuntimeError):
        pytest.skip("Google OAuth not configured for testing")

