"""
Relevance Validator — Score and filter search candidates.

Scoring dimensions:
1. Topic relevance (keyword/semantic match)
2. Authority (domain quality, known good sources)
3. Freshness (publication date proximity)
4. Accessibility (no paywalls, login walls, junk)

The validator is intentionally simple and CPU-only for speed.
No LLM calls — those happen in the grounded search pipeline's Layer 3.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from loguru import logger


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class SearchCandidate:
    """A search result candidate with scoring metadata."""
    url: str
    title: str
    snippet: str
    relevance_score: float = 0.5
    provider: str = "unknown"
    source_type: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "relevance_score": round(self.relevance_score, 3),
            "provider": self.provider,
            "source_type": self.source_type,
        }


# ---------------------------------------------------------------------------
# Junk / paywall patterns
# ---------------------------------------------------------------------------

JUNK_DOMAINS = {
    "pinterest.com", "pinterest.co.uk",
    "facebook.com", "instagram.com",
    "tiktok.com",
    "amazon.com", "ebay.com", "etsy.com",
    "quora.com",  # Low-quality for research
    "scribd.com",  # Paywalled
    "slideshare.net",
    "researchgate.net",  # Login wall
}

JUNK_URL_PATTERNS = [
    r"/login",
    r"/signin",
    r"/subscribe",
    r"/pricing",
    r"/cart",
    r"/checkout",
    r"\.pdf$",  # Often inaccessible without special handling
]

# Domains known for high-quality content
AUTHORITY_DOMAINS = {
    "reuters.com": 0.9,
    "apnews.com": 0.9,
    "bbc.com": 0.85,
    "bbc.co.uk": 0.85,
    "nytimes.com": 0.85,
    "washingtonpost.com": 0.85,
    "theguardian.com": 0.8,
    "nature.com": 0.9,
    "science.org": 0.9,
    "arxiv.org": 0.85,
    "wikipedia.org": 0.7,
    "gov": 0.8,
    "edu": 0.8,
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_topic_relevance(candidate: SearchCandidate, topic: str) -> float:
    """Score topic relevance based on keyword overlap."""
    topic_words = set(topic.lower().split())
    # Remove stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "but", "not", "with", "from", "by", "as", "this", "that", "it", "be", "do", "does", "did", "have", "has", "had"}
    topic_words -= stop_words

    if not topic_words:
        return 0.5

    text = f"{candidate.title} {candidate.snippet}".lower()
    matches = sum(1 for w in topic_words if w in text)
    return min(matches / len(topic_words), 1.0)


def _score_authority(candidate: SearchCandidate) -> float:
    """Score source authority based on domain reputation."""
    try:
        parsed = urlparse(candidate.url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Check exact domain match
        if domain in AUTHORITY_DOMAINS:
            return AUTHORITY_DOMAINS[domain]

        # Check TLD-based authority (.gov, .edu)
        tld = domain.split(".")[-1]
        if tld in AUTHORITY_DOMAINS:
            return AUTHORITY_DOMAINS[tld]

        # Default authority
        return 0.5

    except Exception:
        return 0.3


def _is_junk(candidate: SearchCandidate) -> bool:
    """Check if a candidate is junk (paywall, login wall, etc.)."""
    try:
        parsed = urlparse(candidate.url)
        domain = parsed.netloc.lower().replace("www.", "")

        # Check junk domains
        if domain in JUNK_DOMAINS:
            return True
        if any(domain.endswith(f".{jd}") for jd in JUNK_DOMAINS):
            return True

        # Check URL patterns
        path = parsed.path.lower()
        for pattern in JUNK_URL_PATTERNS:
            if re.search(pattern, path):
                return True

        return False

    except Exception:
        return False


def _classify_source_type(candidate: SearchCandidate) -> str:
    """Classify the source type from URL."""
    url = candidate.url.lower()
    domain = urlparse(url).netloc.lower()

    if "youtube.com" in domain or "youtu.be" in domain:
        return "video"
    if "reddit.com" in domain:
        return "reddit"
    if "twitter.com" in domain or "x.com" in domain:
        return "social"
    if any(d in domain for d in ["arxiv.org", "nature.com", "science.org", "pubmed"]):
        return "academic"
    if any(d in domain for d in ["reuters.com", "apnews.com", "bbc.com", "cnn.com"]):
        return "news"

    return "web"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_and_filter_candidates(
    candidates: list[SearchCandidate],
    topic: str,
    min_score: float = 0.3,
) -> list[SearchCandidate]:
    """
    Score and filter search candidates.

    Args:
        candidates: Raw candidates from search providers
        topic: Research topic for relevance scoring
        min_score: Minimum combined score to keep (0-1)

    Returns:
        Filtered and scored candidates, sorted by relevance (descending)
    """
    scored: list[SearchCandidate] = []

    for candidate in candidates:
        # Skip junk
        if _is_junk(candidate):
            logger.debug(f"Filtered junk: {candidate.url}")
            continue

        # Score dimensions
        topic_score = _score_topic_relevance(candidate, topic)
        authority_score = _score_authority(candidate)

        # Combined score (weighted average)
        combined = (topic_score * 0.6) + (authority_score * 0.3) + (candidate.relevance_score * 0.1)

        if combined >= min_score:
            candidate.relevance_score = round(combined, 3)
            candidate.source_type = _classify_source_type(candidate)
            scored.append(candidate)

    # Sort by relevance (descending)
    scored.sort(key=lambda c: c.relevance_score, reverse=True)

    logger.info(f"Scored {len(scored)}/{len(candidates)} candidates above threshold {min_score}")
    return scored
