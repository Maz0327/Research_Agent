"""Fixture for testing Google Drive and Docs integration."""
# This is a fixture script that can be run to test Google Drive integration
# Usage: python -m pytest tests/fixtures/google_drive_test.py

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.integrations.google_drive_docs import create_research_packet, DOC_NAMES


def test_google_drive_integration():
    """Test fixture for Google Drive integration."""
    folder_name = "Test Research Packet - Fixture"
    
    # Create sample content for all documents
    doc_contents = {
        "00_MASTER_INDEX": "# Master Index\n\nThis is a test research packet.\n\n## Documents\n\n- 01_RESEARCH_MAP\n- 02_SOURCE_SHORTLIST\n- etc.",
        "01_RESEARCH_MAP": "# Research Map\n\n## Topic\nTest topic\n\n## Angles\n1. Angle 1\n2. Angle 2",
        "02_SOURCE_SHORTLIST": "# Source Shortlist\n\n## Sources\n\n1. https://example.com/article",
        "03_YOUTUBE_INDEX": "# YouTube Index\n\n| Video | Channel | Date |\n|-------|---------|------|",
        "04_TRANSCRIPTS": "# Transcripts\n\n## Video 1\n\nTranscript content here...",
        "05_WEB_EXTRACTS": "# Web Extracts\n\n## Article 1\n\nExtracted content...",
        "06_QUOTE_BANK": "# Quote Bank\n\n> Quote 1\n\n*Citation: [Source](url)*",
        "07_CLAIMS_LEDGER": "# Claims Ledger\n\n| Claim ID | Claim | Type |\n|----------|-------|------|",
        "08_EVIDENCE_TABLE": "# Evidence Table\n\n| Claim | Status | Evidence |\n|-------|--------|----------|",
        "09_MISSING_ANGLES": "# Missing Angles\n\n## Missing Perspectives\n\n1. Perspective 1\n2. Perspective 2",
    }
    
    try:
        result = create_research_packet(folder_name, doc_contents)
        
        print(f"\n✅ Successfully created research packet!")
        print(f"Folder URL: {result['folder_url']}")
        print(f"\nDocument URLs:")
        for doc_name, doc_url in result["doc_urls"].items():
            print(f"  {doc_name}: {doc_url}")
        print(f"\nManifest URL: {result['manifest_url']}")
        
        return result
    
    except Exception as e:
        print(f"\n❌ Failed to create research packet: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    test_google_drive_integration()

