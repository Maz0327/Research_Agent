"""Unit tests for Quality Gate source filtering."""
import pytest

from backend.pipeline.quality_gate import (
    quality_gate,
    run_quality_gate,
    Source,
    QualityGateOutput,
    QualityGateStats,
    QUALITY_GATE_CONFIG,
    HIGH_AUTHORITY_WHITELIST,
    HIGH_AUTHORITY_DOMAINS,
    _deduplicate,
    _calculate_quality_score,
    _check_hard_rejection,
)


def test_source_creation():
    """Test Source dataclass initialization."""
    source = Source(
        url="https://www.example.com/article?utm_source=test",
        title="Test Article",
        snippet="This is a test snippet for relevance scoring.",
    )

    assert source.domain == "example.com"
    assert source.canonical_url == "https://example.com/article"
    assert source.source_type == "web"


def test_source_canonicalization():
    """Test URL canonicalization removes tracking params."""
    source = Source(
        url="https://example.com/path?utm_source=twitter&utm_medium=social&id=123"
    )

    # Should remove utm params but keep id
    assert "utm_source" not in source.canonical_url
    assert "utm_medium" not in source.canonical_url
    assert "id=123" in source.canonical_url


def test_deduplicate():
    """Test source deduplication by canonical URL."""
    sources = [
        Source(url="https://example.com/article"),
        Source(url="https://example.com/article?utm_source=twitter"),  # Same canonical
        Source(url="https://other.com/article"),
    ]

    unique = _deduplicate(sources)

    assert len(unique) == 2
    assert unique[0].domain == "example.com"
    assert unique[1].domain == "other.com"


def test_quality_score_whitelist():
    """Test whitelist domains get maximum score."""
    source = Source(url="https://nytimes.com/article")
    score = _calculate_quality_score(source)
    assert score == 1.0


def test_quality_score_gov_tld():
    """Test .gov TLD gets maximum score."""
    source = Source(url="https://cdc.gov/health")
    score = _calculate_quality_score(source)
    assert score == 1.0


def test_quality_score_edu_tld():
    """Test .edu TLD gets maximum score."""
    source = Source(url="https://stanford.edu/research")
    score = _calculate_quality_score(source)
    assert score == 1.0


def test_quality_score_high_authority():
    """Test high authority domains get score bonus."""
    source = Source(url="https://wired.com/article")
    score = _calculate_quality_score(source)
    assert score > 0.5  # Base + bonus


def test_quality_score_syndicator_penalty():
    """Test syndicator domains get penalty."""
    source = Source(url="https://yahoo.com/news/article")
    score = _calculate_quality_score(source)
    # Should be penalized for being syndicator
    assert source.is_syndicator


def test_hard_rejection_invalid_url():
    """Test invalid URLs are hard rejected."""
    source = Source(url="not-a-url")
    reason = _check_hard_rejection(source)
    assert reason == "invalid_url"


def test_hard_rejection_junk_patterns():
    """Test junk patterns are hard rejected."""
    junk_sources = [
        Source(url="https://example.com/page/2"),
        Source(url="https://example.com/feed/"),
        Source(url="https://example.com/search?q=test"),
        Source(url="https://example.com/login"),
        Source(url="https://example.com/cart"),
    ]

    for source in junk_sources:
        reason = _check_hard_rejection(source)
        assert reason == "junk_pattern", f"Expected rejection for {source.url}"


def test_hard_rejection_valid_url():
    """Test valid URLs are not rejected."""
    source = Source(url="https://example.com/article/important-news")
    reason = _check_hard_rejection(source)
    assert reason is None


def test_quality_gate_basic():
    """Test basic quality gate operation."""
    sources = [
        {"url": "https://example.com/article1", "title": "Article 1", "snippet": "Content 1"},
        {"url": "https://example.com/article2", "title": "Article 2", "snippet": "Content 2"},
        {"url": "https://nytimes.com/important", "title": "NYT", "snippet": "Content 3"},
    ]

    output = quality_gate(sources, mode="full")

    assert isinstance(output, QualityGateOutput)
    assert len(output.approved) > 0
    assert output.stats.total_discovered == 3


def test_quality_gate_removes_duplicates():
    """Test quality gate removes duplicate URLs."""
    sources = [
        {"url": "https://example.com/article"},
        {"url": "https://example.com/article?utm_source=twitter"},  # Same canonical
        {"url": "https://example.com/article?ref=home"},  # Same canonical
    ]

    output = quality_gate(sources, mode="full")

    assert output.stats.after_dedup == 1


def test_quality_gate_respects_mode_floors():
    """Test quality gate respects mode-specific floors."""
    sources = [
        {"url": f"https://example{i}.com/article", "source_type": "web"}
        for i in range(20)
    ]

    # Quick mode has lower floors
    output_quick = quality_gate(sources, mode="quick")
    # Investigation mode has higher floors
    output_investigation = quality_gate(sources, mode="investigation")

    assert output_quick.stats.approved_count <= output_investigation.stats.approved_count


def test_run_quality_gate_returns_dict():
    """Test run_quality_gate convenience function returns dict."""
    sources = [
        {"url": "https://example.com/article", "title": "Test", "snippet": "Content"},
    ]

    result = run_quality_gate(sources, mode="full")

    assert isinstance(result, dict)
    assert "approved" in result
    assert "soft_rejected" in result
    assert "hard_rejected" in result
    assert "stats" in result


def test_quality_gate_whitelist_bypass_limit():
    """Test whitelist domains bypass domain limit."""
    # Create many sources from same whitelist domain
    sources = [
        {"url": f"https://nytimes.com/article{i}", "title": f"Article {i}"}
        for i in range(10)
    ]

    output = quality_gate(sources, mode="quick")

    # All should be approved (whitelist bypasses domain limit)
    approved_nyt = [s for s in output.approved if "nytimes.com" in s.domain]
    assert len(approved_nyt) > QUALITY_GATE_CONFIG["max_per_domain"]


def test_quality_gate_domain_limit():
    """Test non-whitelist domains are subject to domain limit."""
    # Create many sources from same non-whitelist domain
    sources = [
        {"url": f"https://random-blog.com/article{i}", "title": f"Article {i}"}
        for i in range(10)
    ]

    output = quality_gate(sources, mode="full")

    # Should be limited
    approved_domain = [s for s in output.approved if "random-blog.com" in s.domain]
    assert len(approved_domain) <= QUALITY_GATE_CONFIG["max_per_domain"]


def test_quality_gate_stats():
    """Test quality gate returns comprehensive stats."""
    sources = [
        {"url": "https://example.com/valid"},
        {"url": "not-a-url"},  # Will be hard rejected
        {"url": "https://example.com/valid2"},
    ]

    output = quality_gate(sources, mode="full")

    assert output.stats.total_discovered == 3
    assert output.stats.rejected_count >= 1
    assert "invalid_url" in output.stats.rejection_breakdown
