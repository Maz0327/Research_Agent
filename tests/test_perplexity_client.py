"""Unit tests for Perplexity client."""
import pytest

from backend.integrations.perplexity_client import (
    research_map,
    source_shortlist,
    _classify_source_type,
    _extract_title_from_url,
    _is_valid_source_url,
)
from backend.models.job_config import JobConfig, ResearchMode, SourcesConfig, BudgetsConfig
from backend.models.source import SourceType


def test_classify_source_type():
    """Test source type classification."""
    assert _classify_source_type("https://www.reddit.com/r/politics") == SourceType.REDDIT
    assert _classify_source_type("https://www.archives.gov/research") == SourceType.GOV
    assert _classify_source_type("https://www.gov.uk/example") == SourceType.GOV
    assert _classify_source_type("https://arxiv.org/abs/1234") == SourceType.ACADEMIC
    assert _classify_source_type("https://www.harvard.edu/example") == SourceType.ACADEMIC
    assert _classify_source_type("https://www.bbc.com/news") == SourceType.NEWS
    assert _classify_source_type("https://www.example.com/page") == SourceType.WEB


def test_is_valid_source_url():
    """Test URL validation."""
    assert _is_valid_source_url("https://example.com/article") is True
    assert _is_valid_source_url("https://www.bbc.com/news/article") is True
    assert _is_valid_source_url("https://www.google.com/search?q=test") is False
    assert _is_valid_source_url("https://twitter.com/user/status/123") is False


def test_extract_title_from_url():
    """Test title extraction from URL."""
    title = _extract_title_from_url("https://example.com/some-article-title-here")
    assert "Some Article Title Here" in title
    assert len(title) > 0


def test_research_map_basic():
    """Test research_map with a basic job config."""
    job = JobConfig(
        topic="Candace Owens claims about Charlie Kirk",
        mode=ResearchMode.CLAIMS_EVIDENCE,
    )
    
    # This will return safe defaults if Perplexity API key is not set
    result = research_map(job)
    
    assert "research_map_md" in result
    assert "angles" in result
    assert "key_terms" in result
    assert isinstance(result["angles"], list)
    assert isinstance(result["key_terms"], list)
    assert job.topic in result["research_map_md"] or "Research Map" in result["research_map_md"]


def test_source_shortlist_basic():
    """Test source_shortlist with a basic job config."""
    job = JobConfig(
        topic="Candace Owens claims about Charlie Kirk",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        sources=SourcesConfig(
            web=True,
            include_news=True,
            include_reddit_public=False,
            include_academic=False,
            include_gov=False,
        ),
        budgets=BudgetsConfig(
            max_web_urls=10,
            max_claims_to_validate=10,
            max_validation_links_per_claim=5,
        ),
    )
    
    angles = ["fact-checking", "timeline"]
    key_terms = ["Candace", "Owens", "Charlie", "Kirk", "claims"]
    
    # This will return empty shortlist if Perplexity API key is not set
    result = source_shortlist(job, angles, key_terms)
    
    assert "urls" in result
    assert "shortlist_md" in result
    assert isinstance(result["urls"], list)
    assert isinstance(result["shortlist_md"], str)
    assert "# Source Shortlist" in result["shortlist_md"]
    assert job.topic in result["shortlist_md"]


def test_source_shortlist_respects_budget():
    """Test that source_shortlist respects max_web_urls budget."""
    job = JobConfig(
        topic="Test topic",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        sources=SourcesConfig(web=True),
        budgets=BudgetsConfig(max_web_urls=5),
    )
    
    angles = ["angle1", "angle2", "angle3"]
    key_terms = ["test", "topic"]
    
    result = source_shortlist(job, angles, key_terms)
    
    # Even if API is not configured, the structure should be correct
    assert len(result["urls"]) <= job.budgets.max_web_urls


def test_source_shortlist_with_all_source_types():
    """Test source_shortlist with all source types enabled."""
    job = JobConfig(
        topic="Comprehensive research topic",
        mode=ResearchMode.INVESTIGATION,
        sources=SourcesConfig(
            web=True,
            include_news=True,
            include_reddit_public=True,
            include_academic=True,
            include_gov=True,
        ),
        budgets=BudgetsConfig(max_web_urls=50),
    )
    
    angles = ["investigation", "fact-checking"]
    key_terms = ["research", "topic"]
    
    result = source_shortlist(job, angles, key_terms)
    
    assert "urls" in result
    assert "shortlist_md" in result
    # Should mention different source types in markdown
    assert any(keyword in result["shortlist_md"].lower() for keyword in ["source", "shortlist"])


def test_source_shortlist_markdown_structure():
    """Test that shortlist markdown has proper structure."""
    job = JobConfig(
        topic="Test topic for markdown",
        mode=ResearchMode.CLAIMS_EVIDENCE,
        sources=SourcesConfig(web=True, include_news=True),
        budgets=BudgetsConfig(max_web_urls=10),
    )
    
    angles = ["angle1", "angle2"]
    key_terms = ["test", "markdown"]
    
    result = source_shortlist(job, angles, key_terms)
    markdown = result["shortlist_md"]
    
    # Should have headers
    assert "#" in markdown
    # Should mention topic
    assert job.topic in markdown
    # Should mention budget
    assert str(job.budgets.max_web_urls) in markdown or "Budget" in markdown.lower()

