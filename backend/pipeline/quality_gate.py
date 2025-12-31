"""Quality Gate: Deterministic source filtering between Discovery and Extraction.

PRD v4.3 Core Innovation: The Quality Gate is a deterministic algorithm
(no LLM, no API calls) that filters discovered sources before extraction.

CONSERVATIVE MODE: Prioritizes recall over precision to avoid losing valuable data.

Key features:
- Deduplication and URL canonicalization
- Quality scoring based on domain authority and content signals
- Discovery-informed weighting (topic determines priorities)
- Source type diversity with configurable floors and caps
- Whitelist for trusted domains (no limits)
- Soft-reject category (keeps sources as references)
- BM25 relevance scoring (Dec 2025 optimization)

Execution time target: <5 seconds
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from collections import defaultdict
from loguru import logger

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 not installed. BM25 scoring disabled. Install with: pip install rank-bm25")


# =============================================================================
# CONSERVATIVE MODE CONFIGURATION
# User preference: Less filtering to avoid losing valuable data
# =============================================================================

QUALITY_GATE_CONFIG = {
    "max_per_domain": 4,          # Was 2 in PRD - increased to avoid missing corroborating sources
    "type_cap_percent": 75,       # Was 60% in PRD - increased for topic-appropriate distribution
    "thin_snippet_threshold": 30, # Characters - very lenient
    "enable_soft_reject": True,   # Keep rejected sources as "reference links" instead of discarding
    "relevance_weight": 0.6,      # Weight for relevance score in combined scoring
    "quality_weight": 0.4,        # Weight for quality score in combined scoring
}

# Junk patterns - ONLY clear spam, not content pages
# Removed: /category/, /tag/, /author/ (these sometimes contain real content)
JUNK_PATTERNS = [
    r'/page/\d+$',        # Pagination only (not /page/article-name)
    r'/feed/?$',          # RSS feeds
    r'/search\?',         # Search result pages
    r'/login',            # Auth pages
    r'/cart',             # E-commerce
    r'/checkout',         # E-commerce
    r'/#[^/]*$',          # Anchor-only URLs
    r'/wp-admin/',        # WordPress admin
    r'/xmlrpc\.php',      # WordPress API
]

# Compiled patterns for efficiency
JUNK_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in JUNK_PATTERNS]

# WHITELIST - unlimited extraction from these domains
# These are trusted sources - no domain limit applies
HIGH_AUTHORITY_WHITELIST = {
    'nytimes.com', 'washingtonpost.com', 'wsj.com', 'bbc.com', 'bbc.co.uk',
    'theguardian.com', 'reuters.com', 'apnews.com', 'npr.org',
    'nature.com', 'science.org', 'sciencemag.org', 'arxiv.org',
    'pnas.org', 'cell.com', 'thelancet.com', 'nejm.org',
}

# TLDs that get whitelist treatment
WHITELIST_TLDS = {'.gov', '.edu'}

# Standard high authority (still subject to domain limit, but get score bonus)
HIGH_AUTHORITY_DOMAINS = {
    'theatlantic.com', 'newyorker.com', 'wired.com', 'arstechnica.com',
    'techcrunch.com', 'theverge.com', 'economist.com', 'ft.com',
    'bloomberg.com', 'forbes.com', 'businessinsider.com',
    'cnbc.com', 'cnn.com', 'msnbc.com', 'foxnews.com', 'abcnews.go.com',
    'nbcnews.com', 'cbsnews.com', 'politico.com', 'thehill.com',
    'vox.com', 'slate.com', 'salon.com', 'huffpost.com',
    'medium.com', 'substack.com',
}

# Wire services / syndicators - for independence detection
WIRE_SERVICES = {'reuters', 'ap', 'afp', 'upi', 'bloomberg'}
SYNDICATORS = {'yahoo.com', 'msn.com', 'news.google.com', 'smartnews.com', 'flipboard.com'}

# Source type mapping
SOURCE_TYPES = {'web', 'news', 'video', 'academic', 'discussion'}

# Source floors by mode (CONSERVATIVE - increased limits)
SOURCE_FLOORS = {
    'quick': {'web': 3, 'news': 1, 'video': 1, 'academic': 0, 'discussion': 0, 'max_slots': 8},
    'breaking_news': {'web': 3, 'news': 4, 'video': 1, 'academic': 0, 'discussion': 1, 'max_slots': 15},
    'full': {'web': 4, 'news': 3, 'video': 3, 'academic': 2, 'discussion': 1, 'max_slots': 25},
    'investigation': {'web': 5, 'news': 3, 'video': 4, 'academic': 3, 'discussion': 3, 'max_slots': 40},
    'profile': {'web': 3, 'news': 3, 'video': 4, 'academic': 1, 'discussion': 1, 'max_slots': 25},
    'controversy': {'web': 3, 'news': 3, 'video': 3, 'academic': 2, 'discussion': 4, 'max_slots': 25},
}

# Default floors for unknown modes
DEFAULT_FLOORS = {'web': 3, 'news': 2, 'video': 2, 'academic': 1, 'discussion': 1, 'max_slots': 20}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Source:
    """Represents a discovered source."""
    url: str
    title: str = ""
    snippet: str = ""
    source_type: str = "web"  # web, news, video, academic, discussion
    relevance_score: float = 0.5
    domain: str = ""
    canonical_url: str = ""
    quality_score: float = 0.0
    final_score: float = 0.0
    is_wire_service: bool = False
    is_syndicator: bool = False

    def __post_init__(self):
        if not self.domain:
            self.domain = self._extract_domain(self.url)
        if not self.canonical_url:
            self.canonical_url = self._canonicalize_url(self.url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        """Canonicalize URL for deduplication."""
        try:
            parsed = urlparse(url)

            # Remove tracking parameters
            tracking_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term',
                               'utm_content', 'ref', 'source', 'fbclid', 'gclid'}
            query_params = parse_qs(parsed.query)
            filtered_params = {k: v for k, v in query_params.items()
                               if k.lower() not in tracking_params}

            # Rebuild URL
            new_query = urlencode(filtered_params, doseq=True)
            canonical = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip('/'),
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))
            return canonical
        except Exception:
            return url.lower()


@dataclass
class QualityGateStats:
    """Statistics from Quality Gate execution."""
    total_discovered: int = 0
    after_dedup: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    soft_rejected_count: int = 0
    type_weights: Dict[str, float] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    rejection_breakdown: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage."""
        return {
            "total_discovered": self.total_discovered,
            "after_dedup": self.after_dedup,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "soft_rejected_count": self.soft_rejected_count,
            "type_weights": self.type_weights,
            "by_type": self.by_type,
            "rejection_breakdown": self.rejection_breakdown,
        }


@dataclass
class QualityGateOutput:
    """Output from Quality Gate processing."""
    approved: List[Source] = field(default_factory=list)        # Extract content from these
    soft_rejected: List[Source] = field(default_factory=list)   # Keep as reference links
    hard_rejected: List[Source] = field(default_factory=list)   # Clear spam/duplicates
    stats: QualityGateStats = field(default_factory=QualityGateStats)


# =============================================================================
# QUALITY GATE IMPLEMENTATION
# =============================================================================

def quality_gate(
    sources: List[Dict],
    mode: str = "full",
    niche: Optional[str] = None,
    query_terms: Optional[List[str]] = None,
) -> QualityGateOutput:
    """
    Main Quality Gate function.

    CONSERVATIVE MODE: Prioritizes keeping valuable sources.
    - Whitelist domains bypass limits
    - Soft reject preserves sources as references
    - Higher thresholds = fewer rejections

    Deterministic, no LLM, <5 seconds.

    Args:
        sources: List of discovered sources (dicts with url, title, snippet, etc.)
        mode: Pipeline mode (quick, full, investigation, etc.)
        niche: Optional niche overlay (downfalls, mysteries, etc.)
        query_terms: Optional list of query terms for BM25 relevance scoring

    Returns:
        QualityGateOutput with approved, soft_rejected, hard_rejected sources and stats
    """
    logger.info(f"Quality Gate: Processing {len(sources)} sources (mode={mode}, niche={niche})")

    output = QualityGateOutput()
    output.stats.total_discovered = len(sources)

    # Get floor configuration for this mode
    floors = SOURCE_FLOORS.get(mode, DEFAULT_FLOORS).copy()
    max_slots = floors.pop('max_slots')

    # Override with niche-specific source floors if niche is specified
    if niche:
        try:
            from backend.pipeline.niche_loader import get_niche
            niche_config = get_niche(niche)
            if niche_config and niche_config.source_floors:
                # Merge niche floors (niche takes precedence)
                for source_type, floor_value in niche_config.source_floors.items():
                    if source_type in floors:
                        floors[source_type] = floor_value
                logger.info(f"Quality Gate: Applied niche '{niche}' source floors: {floors}")
        except Exception as e:
            logger.warning(f"Quality Gate: Failed to load niche '{niche}': {e}")

    # Step 1: Convert to Source objects
    source_objects = [_dict_to_source(s) for s in sources]

    # Step 2: Deduplicate
    unique_sources = _deduplicate(source_objects)
    output.stats.after_dedup = len(unique_sources)

    # Step 2.5: Calculate BM25 scores if query terms provided (Dec 2025 optimization)
    bm25_scores: Dict[str, float] = {}
    if query_terms and BM25_AVAILABLE:
        bm25_scores = _calculate_bm25_scores(unique_sources, query_terms)
        logger.info(f"BM25 scoring applied with {len(query_terms)} query terms")

    # Step 3: Calculate quality scores
    for source in unique_sources:
        source.quality_score = _calculate_quality_score(source)

        # Add BM25 relevance bonus (up to 0.2)
        bm25_bonus = 0.0
        if source.canonical_url in bm25_scores:
            bm25_bonus = min(0.2, bm25_scores[source.canonical_url] * 0.2)

        source.final_score = (
            QUALITY_GATE_CONFIG["relevance_weight"] * source.relevance_score +
            QUALITY_GATE_CONFIG["quality_weight"] * source.quality_score +
            bm25_bonus
        )

    # Step 4: Hard reject clear spam (junk patterns, invalid URLs)
    valid_sources = []
    for source in unique_sources:
        rejection_reason = _check_hard_rejection(source)
        if rejection_reason:
            output.hard_rejected.append(source)
            output.stats.rejection_breakdown[rejection_reason] = \
                output.stats.rejection_breakdown.get(rejection_reason, 0) + 1
        else:
            valid_sources.append(source)

    # Step 5: Calculate discovery-informed type weights
    type_weights = _calculate_type_weights(valid_sources)
    output.stats.type_weights = type_weights

    # Step 6: Allocate slots
    approved, soft_rejected = _allocate_slots(
        valid_sources,
        floors,
        max_slots,
        type_weights,
    )

    output.approved = approved
    output.soft_rejected = soft_rejected
    output.stats.approved_count = len(approved)
    output.stats.soft_rejected_count = len(soft_rejected)
    output.stats.rejected_count = len(output.hard_rejected)

    # Calculate by_type
    for source in approved:
        output.stats.by_type[source.source_type] = \
            output.stats.by_type.get(source.source_type, 0) + 1

    logger.info(
        f"Quality Gate complete: {output.stats.approved_count} approved, "
        f"{output.stats.soft_rejected_count} soft-rejected, "
        f"{output.stats.rejected_count} hard-rejected"
    )

    return output


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _dict_to_source(d: Dict) -> Source:
    """Convert dictionary to Source object."""
    return Source(
        url=d.get('url', ''),
        title=d.get('title', ''),
        snippet=d.get('snippet', d.get('content', '')),
        source_type=d.get('source_type', d.get('type', 'web')),
        relevance_score=d.get('relevance_score', d.get('score', 0.5)),
    )


def _deduplicate(sources: List[Source]) -> List[Source]:
    """Deduplicate sources by canonical URL."""
    seen_urls: Set[str] = set()
    unique: List[Source] = []

    for source in sources:
        if source.canonical_url not in seen_urls:
            seen_urls.add(source.canonical_url)
            unique.append(source)

    logger.debug(f"Deduplication: {len(sources)} -> {len(unique)} sources")
    return unique


def _calculate_quality_score(source: Source) -> float:
    """
    Calculate quality score for a source.

    Factors:
    - Domain authority (whitelist/high authority bonuses)
    - TLD bonuses (.gov, .edu)
    - Snippet length (thin content penalty)
    - Wire service detection
    """
    score = 0.5  # Base score

    domain = source.domain

    # Whitelist domains get max score
    if domain in HIGH_AUTHORITY_WHITELIST:
        return 1.0

    # Check TLD whitelist
    for tld in WHITELIST_TLDS:
        if domain.endswith(tld):
            return 1.0

    # High authority bonus
    if domain in HIGH_AUTHORITY_DOMAINS:
        score += 0.3

    # TLD bonuses
    if domain.endswith('.org'):
        score += 0.1
    elif domain.endswith('.net'):
        score += 0.05

    # Snippet length check (thin content penalty)
    snippet_len = len(source.snippet) if source.snippet else 0
    if snippet_len < QUALITY_GATE_CONFIG["thin_snippet_threshold"]:
        score -= 0.1

    # Wire service / syndicator detection
    source.is_wire_service = any(ws in domain for ws in WIRE_SERVICES)
    source.is_syndicator = domain in SYNDICATORS

    # Syndicators get slight penalty (want original sources)
    if source.is_syndicator:
        score -= 0.1

    return max(0.0, min(1.0, score))


def _calculate_bm25_scores(
    sources: List["Source"],
    query_terms: List[str],
) -> Dict[str, float]:
    """
    Calculate BM25 relevance scores for sources.

    Research-validated optimization (Dec 2025):
    - Uses BM25Okapi for topic relevance scoring
    - Adds up to 0.2 bonus to quality score for highly relevant sources

    Args:
        sources: List of Source objects
        query_terms: List of query terms to match against

    Returns:
        Dict mapping canonical_url to normalized BM25 score (0.0-1.0)
    """
    if not BM25_AVAILABLE or not query_terms or not sources:
        return {}

    try:
        # Tokenize source content (title + snippet)
        corpus = []
        for source in sources:
            text = f"{source.title or ''} {source.snippet or ''}".lower()
            corpus.append(text.split())

        # Guard against empty corpus (all sources have empty title/snippet)
        if not any(tokens for tokens in corpus):
            logger.debug("BM25 skipped: empty corpus (no text content)")
            return {}

        # Build BM25 index
        bm25 = BM25Okapi(corpus)

        # Score against query terms
        scores = bm25.get_scores(query_terms)

        # Normalize scores to 0.0-1.0
        max_score = max(scores) if scores.max() > 0 else 1.0
        normalized_scores = scores / max_score if max_score > 0 else scores

        # Map to URLs
        result = {}
        for i, source in enumerate(sources):
            result[source.canonical_url] = float(normalized_scores[i])

        logger.debug(f"BM25 scoring: {len(sources)} sources, query={query_terms[:3]}")
        return result

    except Exception as e:
        logger.warning(f"BM25 scoring failed: {e}")
        return {}


def _check_hard_rejection(source: Source) -> Optional[str]:
    """
    Check if source should be hard rejected.

    Returns rejection reason or None if valid.
    """
    # Invalid URL
    if not source.url or not source.url.startswith(('http://', 'https://')):
        return "invalid_url"

    # Check junk patterns
    for pattern in JUNK_PATTERNS_COMPILED:
        if pattern.search(source.url):
            return "junk_pattern"

    return None


def _calculate_type_weights(sources: List[Source]) -> Dict[str, float]:
    """
    Calculate discovery-informed type weights.

    Topics determine where good information lives.
    Weight = (avg_relevance * 0.7) + (quantity_bonus * 0.3)
    """
    type_scores: Dict[str, List[float]] = defaultdict(list)
    type_counts: Dict[str, int] = defaultdict(int)

    for source in sources:
        type_scores[source.source_type].append(source.relevance_score)
        type_counts[source.source_type] += 1

    total_sources = len(sources) if sources else 1
    weights: Dict[str, float] = {}

    for source_type in SOURCE_TYPES:
        scores = type_scores.get(source_type, [])
        count = type_counts.get(source_type, 0)

        avg_relevance = sum(scores) / len(scores) if scores else 0.0
        quantity_bonus = min(count / total_sources, 0.5)  # Cap at 50%

        weights[source_type] = avg_relevance * 0.7 + quantity_bonus * 0.3

    # Normalize weights
    total_weight = sum(weights.values()) or 1
    weights = {k: v / total_weight for k, v in weights.items()}

    return weights


def _allocate_slots(
    sources: List[Source],
    floors: Dict[str, int],
    max_slots: int,
    type_weights: Dict[str, float],
) -> Tuple[List[Source], List[Source]]:
    """
    Allocate sources to approved and soft-rejected lists.

    Algorithm:
    1. Fill source floors first (guaranteed minimums)
    2. Allocate flexible pool by quality score
    3. Respect domain limits (except whitelist)
    4. Respect type caps (75% max per type)
    """
    type_cap = int(max_slots * QUALITY_GATE_CONFIG["type_cap_percent"] / 100)
    max_per_domain = QUALITY_GATE_CONFIG["max_per_domain"]

    # Group sources by type
    by_type: Dict[str, List[Source]] = defaultdict(list)
    for source in sources:
        by_type[source.source_type].append(source)

    # Sort each type by final_score (descending)
    for source_type in by_type:
        by_type[source_type].sort(key=lambda s: s.final_score, reverse=True)

    approved: List[Source] = []
    soft_rejected: List[Source] = []
    domain_counts: Dict[str, int] = defaultdict(int)
    type_counts: Dict[str, int] = defaultdict(int)

    def can_add(source: Source) -> Tuple[bool, str]:
        """Check if source can be added to approved list."""
        # Whitelist domains bypass domain limit
        is_whitelist = (
            source.domain in HIGH_AUTHORITY_WHITELIST or
            any(source.domain.endswith(tld) for tld in WHITELIST_TLDS)
        )

        # Check domain limit (unless whitelist)
        if not is_whitelist and domain_counts[source.domain] >= max_per_domain:
            return False, "domain_limit"

        # Check type cap
        if type_counts[source.source_type] >= type_cap:
            return False, "type_cap"

        # Check total slots
        if len(approved) >= max_slots:
            return False, "slot_exhausted"

        return True, ""

    def add_source(source: Source):
        """Add source to approved list."""
        approved.append(source)
        domain_counts[source.domain] += 1
        type_counts[source.source_type] += 1

    # Phase 1: Fill floors
    for source_type, floor in floors.items():
        available = by_type.get(source_type, [])
        added = 0
        for source in available:
            if added >= floor:
                break
            can, reason = can_add(source)
            if can:
                add_source(source)
                added += 1

    # Phase 2: Fill remaining slots with best quality sources
    remaining_sources = []
    for source_type, sources_list in by_type.items():
        for source in sources_list:
            if source not in approved:
                remaining_sources.append(source)

    # Sort by final score
    remaining_sources.sort(key=lambda s: s.final_score, reverse=True)

    for source in remaining_sources:
        if len(approved) >= max_slots:
            break
        can, reason = can_add(source)
        if can:
            add_source(source)
        else:
            # Soft reject if we would have approved but for limits
            if QUALITY_GATE_CONFIG["enable_soft_reject"]:
                soft_rejected.append(source)

    # Remaining sources that didn't make it go to soft_rejected
    for source in remaining_sources:
        if source not in approved and source not in soft_rejected:
            soft_rejected.append(source)

    return approved, soft_rejected


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_quality_gate(
    sources: List[Dict],
    mode: str = "full",
    niche: Optional[str] = None,
    query_terms: Optional[List[str]] = None,
) -> Dict:
    """
    Run Quality Gate and return results as dictionary.

    Convenience wrapper for pipeline integration.

    Args:
        sources: List of discovered sources
        mode: Pipeline mode
        niche: Optional niche overlay
        query_terms: Optional list of query terms for BM25 relevance scoring
    """
    output = quality_gate(sources, mode, niche, query_terms)

    return {
        "approved": [_source_to_dict(s) for s in output.approved],
        "soft_rejected": [_source_to_dict(s) for s in output.soft_rejected],
        "hard_rejected": [_source_to_dict(s) for s in output.hard_rejected],
        "stats": output.stats.to_dict(),
    }


def _source_to_dict(source: Source) -> Dict:
    """Convert Source object back to dictionary."""
    return {
        "url": source.url,
        "canonical_url": source.canonical_url,
        "title": source.title,
        "snippet": source.snippet,
        "source_type": source.source_type,
        "domain": source.domain,
        "relevance_score": source.relevance_score,
        "quality_score": source.quality_score,
        "final_score": source.final_score,
        "is_wire_service": source.is_wire_service,
        "is_syndicator": source.is_syndicator,
    }
