"""Unit tests for web capture."""
import pytest

from backend.integrations.web_capture import (
    _detect_blocked_content,
    _is_pdf_url,
    capture_web_content,
)
from backend.models.source import SourceItem, SourceType


def test_is_pdf_url():
    """Test PDF URL detection."""
    assert _is_pdf_url("https://example.com/document.pdf") is True
    assert _is_pdf_url("https://example.com/doc.PDF") is True
    assert _is_pdf_url("https://example.com/doc.pdf?param=value") is True
    assert _is_pdf_url("https://example.com/article.html") is False
    assert _is_pdf_url("https://example.com/page") is False


def test_detect_blocked_content():
    """Test blocked content detection."""
    # 403 status
    assert _detect_blocked_content("any content", 403) is True
    
    # 401 status
    assert _detect_blocked_content("any content", 401) is True
    
    # Paywall indicators (content must be >500 chars to trigger pattern matching)
    padding = "<p>" + "x " * 300 + "</p>"  # Padding to exceed 500 char minimum
    html_with_paywall = f"""
    <html>
    <body>
    <h1>Subscribe to continue reading</h1>
    {padding}
    </body>
    </html>
    """
    assert _detect_blocked_content(html_with_paywall, 200) is True

    html_with_signin = f"""
    <html>
    <body>
    <h1>Please sign in to access this content</h1>
    {padding}
    </body>
    </html>
    """
    assert _detect_blocked_content(html_with_signin, 200) is True
    
    # Normal content
    html_normal = """
    <html>
    <body>
    <h1>Article Title</h1>
    <p>This is a normal article with readable content that goes on for a while...</p>
    </body>
    </html>
    """
    assert _detect_blocked_content(html_normal, 200) is False


def test_capture_web_content_pdf():
    """Test that PDFs are handled correctly."""
    sources = [
        SourceItem(
            url="https://example.com/document.pdf",
            title="PDF Document",
            source_type=SourceType.WEB,
        )
    ]
    
    result = capture_web_content(sources)
    
    assert len(result) == 1
    assert result[0].source_type == SourceType.PDF
    assert result[0].text is None  # PDFs not parsed
    assert "PDF" in (result[0].notes or "")


def test_capture_web_content_structure():
    """Test that capture_web_content returns correct structure."""
    sources = [
        SourceItem(
            url="https://example.com/article",
            title="Test Article",
            source_type=SourceType.WEB,
        )
    ]
    
    # This will attempt to fetch (may fail without network, but structure should be correct)
    result = capture_web_content(sources)
    
    assert len(result) == len(sources)
    assert isinstance(result[0], SourceItem)
    assert result[0].url == sources[0].url
    assert result[0].title == sources[0].title


def test_capture_web_content_preserves_existing_text():
    """Test that sources with existing text are not re-processed."""
    sources = [
        SourceItem(
            url="https://example.com/article",
            title="Test Article",
            source_type=SourceType.WEB,
            text="Already extracted text",
        )
    ]
    
    result = capture_web_content(sources)
    
    assert len(result) == 1
    assert result[0].text == "Already extracted text"  # Should be preserved


def test_capture_web_content_skips_youtube():
    """Test that YouTube sources are skipped."""
    sources = [
        SourceItem(
            url="https://www.youtube.com/watch?v=abc123",
            title="YouTube Video",
            source_type=SourceType.YOUTUBE,
        )
    ]
    
    result = capture_web_content(sources)
    
    assert len(result) == 1
    assert result[0].source_type == SourceType.YOUTUBE
    # Should not attempt to fetch YouTube URLs


def test_capture_web_content_handles_reddit():
    """Test that Reddit URLs can be captured."""
    sources = [
        SourceItem(
            url="https://www.reddit.com/r/politics/comments/abc123/test_thread/",
            title="Reddit Thread",
            source_type=SourceType.REDDIT,
        )
    ]
    
    # Structure test - actual fetch may fail without network
    result = capture_web_content(sources)
    
    assert len(result) == 1
    assert result[0].source_type == SourceType.REDDIT
    assert result[0].url == sources[0].url

