# Technical Execution Plan (TEP) v2.0
## Research Agent - Multi-API Implementation Guide for Claude Sonnet

### Document Purpose
This TEP provides step-by-step technical implementation for the **v2 multi-API architecture**. It supersedes TEP_v1.md and must be followed EXACTLY.

**CRITICAL FOR SONNET:** This document contains explicit code examples. Use them as-is. Do NOT "improve" or "simplify" them.

---

## Pre-Implementation Checklist

**SONNET: Before writing ANY code, confirm these:**
- [ ] Read PRD_v2.md completely (NOT PRD_v1)
- [ ] Read this TEP completely
- [ ] Verify all API keys are in .env
- [ ] Create git branch: `feature/multi-api-v2`
- [ ] Verify Redis is running
- [ ] Run existing tests to confirm baseline works

---

## Phase 1: New API Client Implementations [Days 1-3]

### Step 1.1: Exa.ai Client (PRIMARY SEARCH)

**File: `backend/integrations/exa_client.py`** (CREATE NEW FILE)

```python
"""Exa.ai neural search client - PRIMARY search API."""
import os
from typing import List, Dict, Optional, Any
from loguru import logger

# SONNET: Install with: pip install exa-py
from exa_py import Exa

from backend.config import get_settings


class ExaSearchClient:
    """
    Exa.ai client for neural semantic search.

    SONNET WARNING: This is the PRIMARY search API. Use it FIRST before Brave/Perplexity.
    Exa has 94.9% accuracy vs ~80% for traditional search.
    """

    def __init__(self):
        """Initialize Exa client."""
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY environment variable is required")
        self.client = Exa(api_key=api_key)
        self.cost_per_search = 0.001  # Approximate cost tracking

    def search(
        self,
        query: str,
        num_results: int = 20,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        use_autoprompt: bool = True,
    ) -> Dict[str, Any]:
        """
        Search using Exa's neural search.

        Args:
            query: Search query
            num_results: Number of results (max 100)
            include_domains: Only include these domains
            exclude_domains: Exclude these domains (e.g., ["reddit.com"])
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            use_autoprompt: Let Exa enhance the query automatically

        Returns:
            Dict with results and metadata
        """
        try:
            logger.info(f"Exa search: '{query[:50]}...' (num_results={num_results})")

            # Build search parameters
            search_params = {
                "query": query,
                "num_results": min(num_results, 100),
                "use_autoprompt": use_autoprompt,
            }

            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            if start_date:
                search_params["start_crawl_date"] = start_date
            if end_date:
                search_params["end_crawl_date"] = end_date

            # Execute search
            results = self.client.search(**search_params)

            # Format results
            formatted_results = []
            for result in results.results:
                formatted_results.append({
                    "url": result.url,
                    "title": result.title,
                    "score": getattr(result, "score", None),
                    "published_date": getattr(result, "published_date", None),
                    "author": getattr(result, "author", None),
                })

            logger.info(f"Exa returned {len(formatted_results)} results")

            return {
                "results": formatted_results,
                "query": query,
                "api": "exa",
                "cost": self.cost_per_search,
            }

        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            raise

    def search_and_contents(
        self,
        query: str,
        num_results: int = 10,
        text_length: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search AND get content in one call (more efficient).

        SONNET: Use this when you need content immediately.
        This is cheaper than search + separate extraction.
        """
        try:
            logger.info(f"Exa search_and_contents: '{query[:50]}...'")

            results = self.client.search_and_contents(
                query,
                num_results=min(num_results, 100),
                text={"max_characters": text_length},
                **kwargs
            )

            formatted_results = []
            for result in results.results:
                formatted_results.append({
                    "url": result.url,
                    "title": result.title,
                    "text": getattr(result, "text", ""),
                    "score": getattr(result, "score", None),
                    "published_date": getattr(result, "published_date", None),
                })

            return {
                "results": formatted_results,
                "query": query,
                "api": "exa",
                "cost": self.cost_per_search * 1.5,  # Contents costs more
            }

        except Exception as e:
            logger.error(f"Exa search_and_contents failed: {e}")
            raise


def search_with_exa(
    query: str,
    num_results: int = 20,
    **kwargs
) -> List[Dict]:
    """
    Convenience function for Exa search.

    SONNET: Use this in the pipeline. Returns list of results.
    """
    client = ExaSearchClient()
    response = client.search(query, num_results=num_results, **kwargs)
    return response["results"]
```

### Step 1.2: Brave Search Client (BACKUP SEARCH)

**File: `backend/integrations/brave_search_client.py`** (CREATE NEW FILE)

```python
"""Brave Search API client - BACKUP search when Exa fails."""
import os
from typing import List, Dict, Optional, Any
import httpx
from loguru import logger


class BraveSearchClient:
    """
    Brave Search client - use as FALLBACK when Exa fails.

    SONNET WARNING: This is the BACKUP search. Use Exa first.
    Brave has 2000 free requests/month.
    """

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self):
        """Initialize Brave client."""
        self.api_key = os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            logger.warning("BRAVE_API_KEY not set - Brave search unavailable")
        self.cost_per_search = 0.0  # Free tier, then $0.003

    def search(
        self,
        query: str,
        count: int = 20,
        freshness: Optional[str] = None,
        safesearch: str = "off",
    ) -> Dict[str, Any]:
        """
        Search using Brave Search API.

        Args:
            query: Search query
            count: Number of results (max 100)
            freshness: Time filter - pd (day), pw (week), pm (month), py (year)
            safesearch: off, moderate, strict

        Returns:
            Dict with results and metadata
        """
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY not configured")

        try:
            logger.info(f"Brave search: '{query[:50]}...'")

            headers = {
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            }

            params = {
                "q": query,
                "count": min(count, 100),
                "safesearch": safesearch,
            }

            if freshness:
                params["freshness"] = freshness

            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.BASE_URL, headers=headers, params=params)
                response.raise_for_status()

            data = response.json()

            # Extract web results
            formatted_results = []
            web_results = data.get("web", {}).get("results", [])

            for result in web_results:
                formatted_results.append({
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "published_date": result.get("age"),  # Brave uses "age"
                })

            logger.info(f"Brave returned {len(formatted_results)} results")

            return {
                "results": formatted_results,
                "query": query,
                "api": "brave",
                "cost": self.cost_per_search,
            }

        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            raise


def search_with_brave(query: str, count: int = 20, **kwargs) -> List[Dict]:
    """Convenience function for Brave search."""
    client = BraveSearchClient()
    response = client.search(query, count=count, **kwargs)
    return response["results"]
```

### Step 1.3: Jina AI Reader Client (CONTENT EXTRACTION)

**File: `backend/integrations/jina_reader_client.py`** (CREATE NEW FILE)

```python
"""Jina AI Reader - fast content extraction to LLM-ready markdown."""
import os
from typing import Dict, Optional, List
import httpx
from loguru import logger


class JinaReaderClient:
    """
    Jina AI Reader for URL content extraction.

    SONNET WARNING: This REPLACES Playwright scraping.
    - 2-3 seconds per page (vs 10-30s for Playwright)
    - Returns clean markdown
    - Handles JavaScript rendering
    - FREE with rate limits
    """

    BASE_URL = "https://r.jina.ai/"

    def __init__(self):
        """Initialize Jina client."""
        # API key is optional - improves rate limits
        self.api_key = os.getenv("JINA_API_KEY")
        self.timeout = 30.0
        self.cost_per_extraction = 0.0  # Free tier

    def extract(self, url: str) -> Dict[str, str]:
        """
        Extract content from URL as markdown.

        Args:
            url: Target URL to extract content from

        Returns:
            Dict with markdown content and metadata
        """
        try:
            logger.info(f"Jina extracting: {url[:50]}...")

            # Construct Jina Reader URL
            jina_url = f"{self.BASE_URL}{url}"

            headers = {
                "Accept": "text/markdown",
                "X-Return-Format": "markdown",
            }

            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(jina_url, headers=headers)
                response.raise_for_status()

            markdown_content = response.text

            logger.info(f"Jina extracted {len(markdown_content)} chars from {url[:30]}...")

            return {
                "url": url,
                "content": markdown_content,
                "content_type": "markdown",
                "char_count": len(markdown_content),
                "api": "jina",
                "cost": self.cost_per_extraction,
            }

        except httpx.TimeoutException:
            logger.warning(f"Jina timeout for {url}")
            return {"url": url, "content": "", "error": "timeout"}
        except Exception as e:
            logger.error(f"Jina extraction failed for {url}: {e}")
            return {"url": url, "content": "", "error": str(e)}

    def extract_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> List[Dict[str, str]]:
        """
        Extract content from multiple URLs.

        SONNET: Use this for batch extraction. More efficient than individual calls.
        """
        import asyncio

        async def extract_async(url: str) -> Dict:
            """Async extraction helper."""
            try:
                jina_url = f"{self.BASE_URL}{url}"
                headers = {"Accept": "text/markdown"}

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(jina_url, headers=headers)
                    response.raise_for_status()

                return {
                    "url": url,
                    "content": response.text,
                    "content_type": "markdown",
                }
            except Exception as e:
                return {"url": url, "content": "", "error": str(e)}

        async def extract_all():
            """Extract all URLs with concurrency limit."""
            semaphore = asyncio.Semaphore(max_concurrent)

            async def limited_extract(url):
                async with semaphore:
                    return await extract_async(url)

            tasks = [limited_extract(url) for url in urls]
            return await asyncio.gather(*tasks)

        logger.info(f"Jina batch extracting {len(urls)} URLs...")
        results = asyncio.run(extract_all())
        logger.info(f"Jina batch complete: {len([r for r in results if r.get('content')])} successful")

        return results


def extract_with_jina(url: str) -> str:
    """
    Convenience function - extract URL content as markdown.

    SONNET: Use this in the pipeline. Returns markdown string.
    """
    client = JinaReaderClient()
    result = client.extract(url)
    return result.get("content", "")


def extract_batch_with_jina(urls: List[str]) -> List[Dict]:
    """Convenience function for batch extraction."""
    client = JinaReaderClient()
    return client.extract_batch(urls)
```

### Step 1.4: GDELT News Client (NEWS DISCOVERY)

**File: `backend/integrations/gdelt_client.py`** (CREATE NEW FILE)

```python
"""GDELT Project API client - FREE news discovery at scale."""
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import httpx
from loguru import logger


class GDELTClient:
    """
    GDELT Project API for global news discovery.

    SONNET WARNING: This is FREE and has massive scale.
    - 100,000+ articles/day
    - 65 languages
    - Real-time updates (15-minute lag)

    Use this for NEWS discovery, not general search.
    """

    DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    GKG_API_URL = "https://api.gdeltproject.org/api/v2/gkg/gkg"

    def __init__(self):
        """Initialize GDELT client."""
        self.timeout = 30.0
        self.cost_per_query = 0.0  # Always free!

    def search_articles(
        self,
        query: str,
        mode: str = "ArtList",
        max_records: int = 50,
        timespan: str = "24h",
        source_country: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search GDELT for news articles.

        Args:
            query: Search query
            mode: ArtList (list), TimelineVol (volume), etc.
            max_records: Max results (up to 250)
            timespan: 15min, 1h, 24h, 7d, 30d
            source_country: Filter by source country
            domain: Filter by domain

        Returns:
            Dict with articles and metadata
        """
        try:
            logger.info(f"GDELT search: '{query[:50]}...' (timespan={timespan})")

            params = {
                "query": query,
                "mode": mode,
                "format": "json",
                "maxrecords": min(max_records, 250),
                "timespan": timespan,
            }

            if source_country:
                params["sourcecountry"] = source_country
            if domain:
                params["domain"] = domain

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.DOC_API_URL, params=params)
                response.raise_for_status()

            data = response.json()

            # Extract articles
            articles = data.get("articles", [])
            formatted_articles = []

            for article in articles:
                formatted_articles.append({
                    "url": article.get("url"),
                    "title": article.get("title"),
                    "source": article.get("domain"),
                    "source_country": article.get("sourcecountry"),
                    "language": article.get("language"),
                    "published_date": article.get("seendate"),
                    "tone": article.get("tone"),  # Sentiment score
                })

            logger.info(f"GDELT returned {len(formatted_articles)} articles")

            return {
                "results": formatted_articles,
                "query": query,
                "timespan": timespan,
                "api": "gdelt",
                "cost": self.cost_per_query,
            }

        except Exception as e:
            logger.error(f"GDELT search failed: {e}")
            raise

    def search_entities(
        self,
        query: str,
        entity_type: str = "PERSON",
        timespan: str = "24h",
    ) -> Dict[str, Any]:
        """
        Search GDELT Global Knowledge Graph for entities.

        Args:
            query: Search query
            entity_type: PERSON, ORGANIZATION, LOCATION
            timespan: Time window

        Returns:
            Dict with entities and their mentions
        """
        try:
            logger.info(f"GDELT GKG search: '{query}' type={entity_type}")

            params = {
                "query": f"{query} {entity_type.lower()}",
                "mode": "PointData",
                "format": "json",
                "timespan": timespan,
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.GKG_API_URL, params=params)
                response.raise_for_status()

            data = response.json()

            return {
                "entities": data,
                "query": query,
                "entity_type": entity_type,
                "api": "gdelt_gkg",
                "cost": self.cost_per_query,
            }

        except Exception as e:
            logger.error(f"GDELT GKG search failed: {e}")
            raise

    def get_trending(
        self,
        timespan: str = "24h",
        max_records: int = 20
    ) -> List[Dict]:
        """
        Get trending topics from GDELT.

        SONNET: Use for breaking_news mode to find hot topics.
        """
        try:
            params = {
                "mode": "TimelineVolInfo",
                "format": "json",
                "timespan": timespan,
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.DOC_API_URL, params=params)
                response.raise_for_status()

            data = response.json()
            return data.get("timeline", [])[:max_records]

        except Exception as e:
            logger.error(f"GDELT trending failed: {e}")
            return []


def search_news_gdelt(
    query: str,
    timespan: str = "24h",
    max_records: int = 50
) -> List[Dict]:
    """
    Convenience function for GDELT news search.

    SONNET: Use this for news discovery. Returns list of articles.
    """
    client = GDELTClient()
    response = client.search_articles(query, timespan=timespan, max_records=max_records)
    return response["results"]
```

### Step 1.5: ClaimBuster Client (CLAIM DETECTION)

**File: `backend/integrations/claimbuster_client.py`** (CREATE NEW FILE)

```python
"""ClaimBuster API - FREE claim detection and scoring."""
import os
from typing import List, Dict, Any
import httpx
from loguru import logger


class ClaimBusterClient:
    """
    ClaimBuster API for detecting check-worthy claims.

    SONNET WARNING: Use this BEFORE Perplexity validation.
    - FREE for academic use
    - Scores claims 0-1 for check-worthiness
    - Only send high-scoring claims to Perplexity

    This saves significant Perplexity costs!
    """

    API_URL = "https://idir.uta.edu/claimbuster/api/v2/score/text/"

    def __init__(self):
        """Initialize ClaimBuster client."""
        self.api_key = os.getenv("CLAIMBUSTER_API_KEY", "")
        self.threshold = 0.5  # Only claims above this get validated
        self.timeout = 30.0
        self.cost_per_request = 0.0  # Always free!

    def score_text(self, text: str) -> Dict[str, Any]:
        """
        Score text for check-worthy claims.

        Args:
            text: Text to analyze (can be multiple sentences)

        Returns:
            Dict with scored claims
        """
        try:
            logger.info(f"ClaimBuster scoring text ({len(text)} chars)...")

            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            payload = {"input_text": text}

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.API_URL, headers=headers, json=payload)
                response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Format results
            scored_claims = []
            for result in results:
                scored_claims.append({
                    "text": result.get("text"),
                    "score": result.get("score", 0),
                    "check_worthy": result.get("score", 0) >= self.threshold,
                })

            logger.info(f"ClaimBuster found {len([c for c in scored_claims if c['check_worthy']])} check-worthy claims")

            return {
                "claims": scored_claims,
                "total_claims": len(scored_claims),
                "check_worthy_count": len([c for c in scored_claims if c["check_worthy"]]),
                "api": "claimbuster",
                "cost": self.cost_per_request,
            }

        except Exception as e:
            logger.error(f"ClaimBuster scoring failed: {e}")
            return {"claims": [], "error": str(e)}

    def score_claims(self, claims: List[str]) -> List[Dict]:
        """
        Score a list of claim strings.

        SONNET: Use this to filter claims before Perplexity.
        """
        scored = []
        for claim in claims:
            result = self.score_text(claim)
            if result.get("claims"):
                scored.append({
                    "claim": claim,
                    "score": result["claims"][0].get("score", 0),
                    "check_worthy": result["claims"][0].get("check_worthy", False),
                })
            else:
                scored.append({
                    "claim": claim,
                    "score": 0,
                    "check_worthy": False,
                })
        return scored

    def filter_check_worthy(
        self,
        claims: List[str],
        threshold: float = None
    ) -> List[str]:
        """
        Filter claims to only check-worthy ones.

        SONNET: This is the KEY function. Use it to reduce Perplexity costs.

        Example:
            all_claims = ["claim1", "claim2", "claim3"]  # 3 claims
            worthy_claims = filter_check_worthy(all_claims)  # Maybe 1-2 claims
            # Only validate worthy_claims with Perplexity
        """
        threshold = threshold or self.threshold
        scored = self.score_claims(claims)
        return [
            item["claim"] for item in scored
            if item.get("score", 0) >= threshold
        ]


def score_claims_claimbuster(claims: List[str]) -> List[Dict]:
    """Convenience function for claim scoring."""
    client = ClaimBusterClient()
    return client.score_claims(claims)


def filter_check_worthy_claims(claims: List[str], threshold: float = 0.5) -> List[str]:
    """
    Filter to check-worthy claims only.

    SONNET: ALWAYS call this before Perplexity validation!
    """
    client = ClaimBusterClient()
    return client.filter_check_worthy(claims, threshold)
```

### Step 1.6: Google Fact Check Client (EXISTING FACT-CHECKS)

**File: `backend/integrations/google_factcheck_client.py`** (CREATE NEW FILE)

```python
"""Google Fact Check Tools API - Find existing fact-checks."""
import os
from typing import List, Dict, Any, Optional
import httpx
from loguru import logger


class GoogleFactCheckClient:
    """
    Google Fact Check Tools API.

    SONNET WARNING: Use this BEFORE creating new validations.
    - FREE (part of Google Cloud)
    - Finds existing fact-checks from reputable sources
    - If a claim is already checked, use that instead of Perplexity

    This saves both time and money!
    """

    API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    def __init__(self):
        """Initialize Google Fact Check client."""
        self.api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY")
        if not self.api_key:
            # Try fallback to general Google API key
            self.api_key = os.getenv("GOOGLE_API_KEY")
        self.timeout = 15.0
        self.cost_per_request = 0.0  # Always free!

    def search(
        self,
        query: str,
        language_code: str = "en",
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for existing fact-checks.

        Args:
            query: Claim or topic to search
            language_code: Language filter (en, es, fr, etc.)
            page_size: Max results

        Returns:
            Dict with existing fact-checks
        """
        if not self.api_key:
            logger.warning("Google Fact Check API key not configured")
            return {"fact_checks": [], "error": "API key not configured"}

        try:
            logger.info(f"Google Fact Check: '{query[:50]}...'")

            params = {
                "key": self.api_key,
                "query": query,
                "languageCode": language_code,
                "pageSize": page_size,
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.API_URL, params=params)
                response.raise_for_status()

            data = response.json()
            claims = data.get("claims", [])

            # Format results
            fact_checks = []
            for claim in claims:
                for review in claim.get("claimReview", []):
                    fact_checks.append({
                        "claim_text": claim.get("text"),
                        "claimant": claim.get("claimant"),
                        "claim_date": claim.get("claimDate"),
                        "publisher": review.get("publisher", {}).get("name"),
                        "url": review.get("url"),
                        "title": review.get("title"),
                        "rating": review.get("textualRating"),
                        "language": review.get("languageCode"),
                    })

            logger.info(f"Google Fact Check found {len(fact_checks)} existing checks")

            return {
                "fact_checks": fact_checks,
                "query": query,
                "api": "google_factcheck",
                "cost": self.cost_per_request,
            }

        except Exception as e:
            logger.error(f"Google Fact Check failed: {e}")
            return {"fact_checks": [], "error": str(e)}

    def check_claim(self, claim: str) -> Optional[Dict]:
        """
        Check if a specific claim has been fact-checked.

        Returns the first matching fact-check or None.
        """
        result = self.search(claim, page_size=1)
        fact_checks = result.get("fact_checks", [])
        return fact_checks[0] if fact_checks else None


def find_existing_factchecks(query: str) -> List[Dict]:
    """
    Find existing fact-checks for a claim.

    SONNET: Call this before Perplexity validation. If fact-check exists, use it!
    """
    client = GoogleFactCheckClient()
    result = client.search(query)
    return result.get("fact_checks", [])


def claim_already_checked(claim: str) -> Optional[Dict]:
    """
    Check if claim already has a fact-check.

    Returns fact-check dict or None.
    """
    client = GoogleFactCheckClient()
    return client.check_claim(claim)
```

### Step 1.7: Semantic Scholar Client (ACADEMIC SOURCES)

**File: `backend/integrations/semantic_scholar_client.py`** (CREATE NEW FILE)

```python
"""Semantic Scholar API - FREE access to 200M+ academic papers."""
import os
from typing import List, Dict, Any, Optional
import httpx
from loguru import logger


class SemanticScholarClient:
    """
    Semantic Scholar API for academic paper search.

    SONNET WARNING: Use this for INVESTIGATION mode.
    - FREE (100 req/sec limit)
    - 200M+ papers
    - Includes citations, abstracts, open access PDFs

    Academic sources add credibility to documentary research.
    """

    API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self):
        """Initialize Semantic Scholar client."""
        # API key is optional but increases rate limits
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.timeout = 30.0
        self.cost_per_request = 0.0  # Always free!

    def search(
        self,
        query: str,
        limit: int = 20,
        fields: Optional[List[str]] = None,
        year_range: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        """
        Search for academic papers.

        Args:
            query: Search query
            limit: Max results (up to 100)
            fields: Fields to return
            year_range: (start_year, end_year) filter

        Returns:
            Dict with papers and metadata
        """
        try:
            logger.info(f"Semantic Scholar search: '{query[:50]}...'")

            if fields is None:
                fields = [
                    "title",
                    "abstract",
                    "year",
                    "authors",
                    "citationCount",
                    "url",
                    "openAccessPdf",
                    "venue",
                ]

            params = {
                "query": query,
                "limit": min(limit, 100),
                "fields": ",".join(fields),
            }

            if year_range:
                params["year"] = f"{year_range[0]}-{year_range[1]}"

            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.API_URL, headers=headers, params=params)
                response.raise_for_status()

            data = response.json()
            papers = data.get("data", [])

            # Format results
            formatted_papers = []
            for paper in papers:
                authors = paper.get("authors", [])
                author_names = [a.get("name", "") for a in authors[:5]]  # First 5 authors

                formatted_papers.append({
                    "title": paper.get("title"),
                    "abstract": paper.get("abstract"),
                    "year": paper.get("year"),
                    "authors": author_names,
                    "citation_count": paper.get("citationCount", 0),
                    "url": paper.get("url"),
                    "pdf_url": paper.get("openAccessPdf", {}).get("url") if paper.get("openAccessPdf") else None,
                    "venue": paper.get("venue"),
                })

            logger.info(f"Semantic Scholar found {len(formatted_papers)} papers")

            return {
                "papers": formatted_papers,
                "query": query,
                "total": data.get("total", len(formatted_papers)),
                "api": "semantic_scholar",
                "cost": self.cost_per_request,
            }

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return {"papers": [], "error": str(e)}

    def get_paper(self, paper_id: str) -> Optional[Dict]:
        """Get details for a specific paper by ID."""
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
            params = {
                "fields": "title,abstract,year,authors,citationCount,url,openAccessPdf,references,citations"
            }

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Semantic Scholar get_paper failed: {e}")
            return None


def search_academic_papers(query: str, limit: int = 20) -> List[Dict]:
    """
    Search for academic papers.

    SONNET: Use in investigation mode for scientific claims.
    """
    client = SemanticScholarClient()
    result = client.search(query, limit=limit)
    return result.get("papers", [])
```

### Step 1.8: Whisper Transcription Client (TIER 2 TRANSCRIPTS)

**File: `backend/integrations/whisper_client.py`** (CREATE NEW FILE)

```python
"""OpenAI Whisper API client for YouTube audio transcription."""
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional
import subprocess
from loguru import logger
import openai


class WhisperTranscriptionClient:
    """
    OpenAI Whisper API for transcribing YouTube videos without captions.

    SONNET WARNING: This is TIER 2 of the transcript system.
    - Cost: $0.006/minute
    - Only use when youtube-transcript-api fails (Tier 1)
    - Downloads audio with yt-dlp, then transcribes

    DO NOT skip Tier 1. Always try native captions first!
    """

    def __init__(self):
        """Initialize Whisper client."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY required for Whisper transcription")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.cost_per_minute = 0.006

    def download_audio(self, video_id: str, output_dir: Optional[str] = None) -> str:
        """
        Download audio from YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID
            output_dir: Directory to save audio (uses temp if not specified)

        Returns:
            Path to downloaded audio file
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        output_path = Path(output_dir) / f"{video_id}.mp3"

        try:
            logger.info(f"Downloading audio for {video_id}...")

            # Use yt-dlp to download audio only
            cmd = [
                "yt-dlp",
                "-x",  # Extract audio
                "--audio-format", "mp3",
                "--audio-quality", "128K",
                "-o", str(output_path),
                f"https://www.youtube.com/watch?v={video_id}",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp failed: {result.stderr}")
                raise RuntimeError(f"yt-dlp failed: {result.stderr}")

            logger.info(f"Audio downloaded: {output_path}")
            return str(output_path)

        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio download timed out")
        except Exception as e:
            raise RuntimeError(f"Failed to download audio: {e}")

    def transcribe(
        self,
        audio_path: str,
        language: str = "en",
    ) -> Dict:
        """
        Transcribe audio file using Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (en, es, fr, etc.)

        Returns:
            Dict with transcript and metadata
        """
        try:
            logger.info(f"Transcribing with Whisper: {audio_path}")

            # Get audio duration for cost estimation
            duration_minutes = self._get_audio_duration(audio_path)

            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",  # Includes timestamps
                )

            # Extract segments with timestamps
            segments = []
            if hasattr(response, 'segments'):
                for seg in response.segments:
                    segments.append({
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", ""),
                    })

            cost = duration_minutes * self.cost_per_minute

            logger.info(f"Whisper transcription complete: {len(segments)} segments, ${cost:.4f}")

            return {
                "text": response.text,
                "segments": segments,
                "language": language,
                "duration_minutes": duration_minutes,
                "method": "whisper",
                "cost": cost,
            }

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in minutes."""
        try:
            import mutagen
            from mutagen.mp3 import MP3

            audio = MP3(audio_path)
            return audio.info.length / 60.0
        except:
            # Fallback: estimate from file size (~128kbps)
            file_size = os.path.getsize(audio_path)
            return (file_size / 16000) / 60.0  # Rough estimate

    def transcribe_youtube(
        self,
        video_id: str,
        max_duration_minutes: float = 60.0,
    ) -> Dict:
        """
        Full pipeline: download audio and transcribe.

        SONNET: This is the main function. Use it for Tier 2 transcription.

        Args:
            video_id: YouTube video ID
            max_duration_minutes: Maximum video length to transcribe

        Returns:
            Dict with transcript and cost
        """
        try:
            # Download audio
            audio_path = self.download_audio(video_id)

            # Check duration
            duration = self._get_audio_duration(audio_path)
            if duration > max_duration_minutes:
                raise ValueError(f"Video too long: {duration:.1f}m > {max_duration_minutes}m limit")

            # Transcribe
            result = self.transcribe(audio_path)
            result["video_id"] = video_id

            # Cleanup
            try:
                os.remove(audio_path)
            except:
                pass

            return result

        except Exception as e:
            logger.error(f"YouTube transcription failed for {video_id}: {e}")
            raise


def transcribe_with_whisper(video_id: str, max_duration: float = 60.0) -> Dict:
    """
    Transcribe YouTube video with Whisper API.

    SONNET: Use this as Tier 2 fallback when youtube-transcript-api fails.
    """
    client = WhisperTranscriptionClient()
    return client.transcribe_youtube(video_id, max_duration)
```

---

## Phase 2: Update Search Pipeline [Days 4-5]

### Step 2.1: Create Unified Search Module

**File: `backend/pipeline/search.py`** (CREATE NEW FILE)

```python
"""Unified search module with multi-API fallback."""
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.integrations.exa_client import ExaSearchClient, search_with_exa
from backend.integrations.brave_search_client import BraveSearchClient, search_with_brave
from backend.integrations.perplexity_client import perplexity_search  # Existing


class UnifiedSearchClient:
    """
    Unified search with automatic fallback.

    SONNET: This is the PRIMARY search interface. Use this, not individual clients.

    Search priority:
    1. Exa.ai (94.9% accuracy, paid)
    2. Brave Search (backup, free tier)
    3. Perplexity (last resort, expensive)
    """

    def __init__(self):
        """Initialize with fallback chain."""
        self.exa = None
        self.brave = None

        try:
            self.exa = ExaSearchClient()
        except Exception as e:
            logger.warning(f"Exa client init failed: {e}")

        try:
            self.brave = BraveSearchClient()
        except Exception as e:
            logger.warning(f"Brave client init failed: {e}")

    def search(
        self,
        query: str,
        num_results: int = 20,
        mode: str = "general",  # general, news, academic
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search with automatic fallback.

        Args:
            query: Search query
            num_results: Number of results
            mode: Search mode for API selection
            **kwargs: Additional parameters

        Returns:
            Dict with results, api used, and cost
        """
        errors = []

        # Tier 1: Try Exa
        if self.exa:
            try:
                logger.info(f"Searching with Exa: '{query[:30]}...'")
                result = self.exa.search(query, num_results=num_results, **kwargs)
                if result.get("results"):
                    return result
            except Exception as e:
                logger.warning(f"Exa search failed: {e}")
                errors.append(f"Exa: {str(e)}")

        # Tier 2: Try Brave
        if self.brave:
            try:
                logger.info(f"Falling back to Brave: '{query[:30]}...'")
                result = self.brave.search(query, count=num_results)
                if result.get("results"):
                    return result
            except Exception as e:
                logger.warning(f"Brave search failed: {e}")
                errors.append(f"Brave: {str(e)}")

        # Tier 3: Perplexity (expensive fallback)
        try:
            logger.info(f"Falling back to Perplexity: '{query[:30]}...'")
            response = perplexity_search(query)
            # Convert Perplexity response to standard format
            return {
                "results": response.get("urls", []),
                "query": query,
                "api": "perplexity",
                "cost": 0.20,  # Approximate
            }
        except Exception as e:
            logger.error(f"All search methods failed: {errors}, Perplexity: {e}")
            raise RuntimeError(f"All search methods failed: {errors}")


def unified_search(query: str, num_results: int = 20, **kwargs) -> List[Dict]:
    """
    Perform search with automatic fallback.

    SONNET: Use this in the pipeline. It handles API selection automatically.
    """
    client = UnifiedSearchClient()
    result = client.search(query, num_results=num_results, **kwargs)
    return result.get("results", [])
```

### Step 2.2: Create Unified Content Extraction

**File: `backend/pipeline/extraction.py`** (CREATE NEW FILE)

```python
"""Unified content extraction with Jina Reader."""
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.integrations.jina_reader_client import (
    JinaReaderClient,
    extract_with_jina,
    extract_batch_with_jina
)

# Keep Trafilatura as fallback
try:
    from trafilatura import fetch_url, extract as trafilatura_extract
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("Trafilatura not available for fallback")


class UnifiedExtractor:
    """
    Unified content extraction with Jina + Trafilatura fallback.

    SONNET: Use Jina Reader FIRST. It's faster and returns clean markdown.
    Only fall back to Trafilatura if Jina fails.

    DO NOT use Playwright unless both fail.
    """

    def __init__(self):
        """Initialize extractor."""
        self.jina = JinaReaderClient()

    def extract(self, url: str) -> Dict[str, Any]:
        """
        Extract content from URL.

        Args:
            url: Target URL

        Returns:
            Dict with content and metadata
        """
        # Tier 1: Try Jina Reader
        try:
            result = self.jina.extract(url)
            if result.get("content") and len(result["content"]) > 100:
                return result
        except Exception as e:
            logger.warning(f"Jina extraction failed for {url}: {e}")

        # Tier 2: Try Trafilatura (local, no API)
        if TRAFILATURA_AVAILABLE:
            try:
                logger.info(f"Falling back to Trafilatura for {url}")
                downloaded = fetch_url(url)
                if downloaded:
                    text = trafilatura_extract(downloaded)
                    if text:
                        return {
                            "url": url,
                            "content": text,
                            "content_type": "text",
                            "api": "trafilatura",
                            "cost": 0,
                        }
            except Exception as e:
                logger.warning(f"Trafilatura failed for {url}: {e}")

        # Return empty if all fail
        logger.error(f"All extraction methods failed for {url}")
        return {
            "url": url,
            "content": "",
            "error": "All extraction methods failed",
        }

    def extract_batch(self, urls: List[str]) -> List[Dict]:
        """
        Extract content from multiple URLs.

        Uses Jina batch extraction for efficiency.
        """
        results = []

        # Try batch with Jina first
        try:
            jina_results = self.jina.extract_batch(urls)
            for result in jina_results:
                if result.get("content") and len(result.get("content", "")) > 100:
                    results.append(result)
                else:
                    # Try Trafilatura for failed ones
                    fallback = self.extract(result["url"])
                    results.append(fallback)
            return results
        except Exception as e:
            logger.warning(f"Batch extraction failed: {e}")

        # Fallback: Extract one by one
        for url in urls:
            results.append(self.extract(url))

        return results


def extract_content(url: str) -> str:
    """
    Extract content from URL.

    SONNET: Use this in the pipeline. Returns markdown/text string.
    """
    extractor = UnifiedExtractor()
    result = extractor.extract(url)
    return result.get("content", "")


def extract_content_batch(urls: List[str]) -> List[Dict]:
    """Extract content from multiple URLs."""
    extractor = UnifiedExtractor()
    return extractor.extract_batch(urls)
```

---

## Phase 3: Update Validation Pipeline [Days 6-7]

### Step 3.1: Create Multi-Stage Validation

**File: `backend/pipeline/validation_v2.py`** (CREATE NEW FILE)

```python
"""Multi-stage claim validation with cost optimization."""
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger

from backend.integrations.claimbuster_client import (
    ClaimBusterClient,
    filter_check_worthy_claims
)
from backend.integrations.google_factcheck_client import (
    GoogleFactCheckClient,
    find_existing_factchecks,
    claim_already_checked
)
from backend.integrations.perplexity_client import _perplexity_search
from backend.models.claim import Claim, EvidenceRecord, EvidenceStatus


class MultiStageValidator:
    """
    Multi-stage claim validation pipeline.

    SONNET: This pipeline MUST be followed in order:
    1. ClaimBuster - Filter to check-worthy claims (FREE)
    2. Google Fact Check - Find existing fact-checks (FREE)
    3. Perplexity - Validate remaining uncertain claims (PAID)

    DO NOT skip steps 1 and 2. They save significant costs.
    """

    def __init__(self):
        """Initialize validation clients."""
        self.claimbuster = ClaimBusterClient()
        self.google_fc = GoogleFactCheckClient()

    def validate_claims(
        self,
        claims: List[Claim],
        topic: str,
        max_perplexity_calls: int = 10,
    ) -> Tuple[List[EvidenceRecord], Dict[str, Any]]:
        """
        Validate claims using multi-stage pipeline.

        Args:
            claims: List of Claim objects to validate
            topic: Research topic for context
            max_perplexity_calls: Max Perplexity API calls (cost control)

        Returns:
            Tuple of (evidence_records, cost_breakdown)
        """
        logger.info(f"Starting multi-stage validation for {len(claims)} claims")

        evidence_records = []
        cost_breakdown = {
            "claimbuster": 0,
            "google_factcheck": 0,
            "perplexity": 0,
            "total": 0,
        }

        # Stage 1: ClaimBuster scoring (FREE)
        logger.info("Stage 1: ClaimBuster scoring")
        claim_texts = [c.canonical_claim for c in claims]
        scored_claims = self.claimbuster.score_claims(claim_texts)

        check_worthy_claims = []
        for claim, score_data in zip(claims, scored_claims):
            if score_data.get("check_worthy", False):
                check_worthy_claims.append(claim)
            else:
                # Low-priority claims get UNPROVEN status
                evidence_records.append(EvidenceRecord(
                    claim_id=claim.claim_id,
                    status=EvidenceStatus.UNPROVEN,
                    evidence_for=[],
                    evidence_against=[],
                    notes=f"ClaimBuster score: {score_data.get('score', 0):.2f} (below threshold)",
                ))

        logger.info(f"Stage 1 complete: {len(check_worthy_claims)} check-worthy claims")

        # Stage 2: Google Fact Check (FREE)
        logger.info("Stage 2: Google Fact Check lookup")
        needs_perplexity = []

        for claim in check_worthy_claims:
            existing_check = claim_already_checked(claim.canonical_claim)

            if existing_check:
                # Use existing fact-check
                rating = existing_check.get("rating", "").lower()

                if any(word in rating for word in ["true", "correct", "accurate"]):
                    status = EvidenceStatus.VERIFIED
                elif any(word in rating for word in ["false", "incorrect", "wrong", "pants on fire"]):
                    status = EvidenceStatus.DEBUNKED
                else:
                    status = EvidenceStatus.UNPROVEN

                evidence_records.append(EvidenceRecord(
                    claim_id=claim.claim_id,
                    status=status,
                    evidence_for=[{"url": existing_check.get("url")}] if status == EvidenceStatus.VERIFIED else [],
                    evidence_against=[{"url": existing_check.get("url")}] if status == EvidenceStatus.DEBUNKED else [],
                    notes=f"Existing fact-check by {existing_check.get('publisher')}: {rating}",
                ))
            else:
                # No existing check - need Perplexity
                needs_perplexity.append(claim)

        logger.info(f"Stage 2 complete: {len(needs_perplexity)} claims need Perplexity validation")

        # Stage 3: Perplexity validation (PAID - limited)
        logger.info(f"Stage 3: Perplexity validation (max {max_perplexity_calls} calls)")

        # Limit to budget
        claims_to_validate = needs_perplexity[:max_perplexity_calls]
        skipped_claims = needs_perplexity[max_perplexity_calls:]

        for claim in claims_to_validate:
            evidence = self._validate_with_perplexity(claim, topic)
            evidence_records.append(evidence)
            cost_breakdown["perplexity"] += 0.20  # Approximate cost per call

        # Mark skipped claims
        for claim in skipped_claims:
            evidence_records.append(EvidenceRecord(
                claim_id=claim.claim_id,
                status=EvidenceStatus.UNPROVEN,
                evidence_for=[],
                evidence_against=[],
                notes="Skipped due to budget limit - requires manual verification",
            ))

        cost_breakdown["total"] = sum(cost_breakdown.values())

        logger.info(f"Validation complete. Total cost: ${cost_breakdown['total']:.2f}")

        return evidence_records, cost_breakdown

    def _validate_with_perplexity(self, claim: Claim, topic: str) -> EvidenceRecord:
        """Validate single claim with Perplexity."""
        try:
            query = f"""Validate this claim about "{topic}":

Claim: {claim.canonical_claim}

Task:
1. Is this claim Verified, Debunked, or Unproven?
2. Provide evidence URLs that support or contradict the claim
3. Brief assessment notes
"""
            response = _perplexity_search(query, model="sonar")
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse response (same logic as existing validation.py)
            content_lower = content.lower()
            status = EvidenceStatus.UNPROVEN

            if "verified" in content_lower or "confirmed" in content_lower:
                status = EvidenceStatus.VERIFIED
            elif "debunked" in content_lower or "false" in content_lower:
                status = EvidenceStatus.DEBUNKED

            return EvidenceRecord(
                claim_id=claim.claim_id,
                status=status,
                evidence_for=[],
                evidence_against=[],
                notes=content[:500] if content else "Perplexity validation complete",
            )

        except Exception as e:
            logger.error(f"Perplexity validation failed for {claim.claim_id}: {e}")
            return EvidenceRecord(
                claim_id=claim.claim_id,
                status=EvidenceStatus.UNPROVEN,
                evidence_for=[],
                evidence_against=[],
                notes=f"Validation error: {str(e)}",
            )


def validate_claims_v2(
    claims: List[Claim],
    topic: str,
    max_perplexity_calls: int = 10
) -> Tuple[List[EvidenceRecord], Dict]:
    """
    Validate claims with multi-stage pipeline.

    SONNET: Use this instead of the old validate_claims function.
    """
    validator = MultiStageValidator()
    return validator.validate_claims(claims, topic, max_perplexity_calls)
```

---

## Phase 4: Update Transcript Pipeline [Days 8-9]

### Step 4.1: Create 3-Tier Transcript System

**File: `backend/pipeline/transcripts_v2.py`** (CREATE NEW FILE)

```python
"""3-tier YouTube transcript extraction system."""
from typing import Dict, List, Optional, Any
from loguru import logger

# Tier 1: Native captions
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable
)

# Tier 2: Whisper
from backend.integrations.whisper_client import WhisperTranscriptionClient

# Tier 3: AssemblyAI (optional)
try:
    import assemblyai as aai
    ASSEMBLYAI_AVAILABLE = True
except ImportError:
    ASSEMBLYAI_AVAILABLE = False


class ThreeTierTranscriptExtractor:
    """
    3-tier YouTube transcript extraction.

    SONNET: This is the CORRECT transcript system. Implement all 3 tiers.

    Tier 1: youtube-transcript-api (FREE, native captions)
    Tier 2: yt-dlp + Whisper API ($0.006/min)
    Tier 3: AssemblyAI ($0.015/min, includes speaker diarization)

    DO NOT skip tiers. Always try cheaper options first.
    """

    def __init__(self):
        """Initialize transcript extractors."""
        self.whisper = None
        try:
            self.whisper = WhisperTranscriptionClient()
        except Exception as e:
            logger.warning(f"Whisper client not available: {e}")

    def get_transcript(
        self,
        video_id: str,
        max_cost: float = 0.50,
        languages: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Get transcript using 3-tier fallback system.

        Args:
            video_id: YouTube video ID
            max_cost: Maximum allowed cost for transcription
            languages: Preferred languages for captions

        Returns:
            Dict with transcript, method used, and cost
        """
        if languages is None:
            languages = ["en", "en-GB", "en-US", "en-AU"]

        logger.info(f"Getting transcript for {video_id} (max_cost=${max_cost})")

        # Tier 1: Try native captions (FREE)
        result = self._try_native_captions(video_id, languages)
        if result.get("success"):
            return result

        # Get video duration for cost calculation
        duration_minutes = self._estimate_duration(video_id)
        logger.info(f"Video duration: ~{duration_minutes:.1f} minutes")

        # Tier 2: Whisper API ($0.006/min)
        whisper_cost = duration_minutes * 0.006
        if self.whisper and whisper_cost <= max_cost:
            result = self._try_whisper(video_id, duration_minutes)
            if result.get("success"):
                return result

        # Tier 3: AssemblyAI ($0.015/min)
        assemblyai_cost = duration_minutes * 0.015
        if ASSEMBLYAI_AVAILABLE and assemblyai_cost <= max_cost:
            result = self._try_assemblyai(video_id)
            if result.get("success"):
                return result

        # All tiers failed
        return {
            "success": False,
            "video_id": video_id,
            "transcript": None,
            "error": "All transcript methods failed",
            "method": "none",
            "cost": 0,
        }

    def _try_native_captions(
        self,
        video_id: str,
        languages: List[str]
    ) -> Dict:
        """Tier 1: Try to get native captions."""
        try:
            logger.info(f"Tier 1: Trying native captions for {video_id}")

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try manual transcripts first (higher quality)
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
                data = transcript.fetch()
                return {
                    "success": True,
                    "video_id": video_id,
                    "transcript": data,
                    "text": " ".join([item["text"] for item in data]),
                    "method": "native_manual",
                    "cost": 0,
                }
            except:
                pass

            # Fall back to auto-generated
            try:
                transcript = transcript_list.find_generated_transcript(languages)
                data = transcript.fetch()
                return {
                    "success": True,
                    "video_id": video_id,
                    "transcript": data,
                    "text": " ".join([item["text"] for item in data]),
                    "method": "native_auto",
                    "cost": 0,
                }
            except:
                pass

            # Try any available transcript
            for transcript in transcript_list:
                try:
                    data = transcript.fetch()
                    return {
                        "success": True,
                        "video_id": video_id,
                        "transcript": data,
                        "text": " ".join([item["text"] for item in data]),
                        "method": f"native_{transcript.language_code}",
                        "cost": 0,
                    }
                except:
                    continue

            return {"success": False, "error": "No usable transcript found"}

        except NoTranscriptFound:
            logger.info(f"No native transcript for {video_id}")
            return {"success": False, "error": "No transcript found"}
        except TranscriptsDisabled:
            logger.info(f"Transcripts disabled for {video_id}")
            return {"success": False, "error": "Transcripts disabled"}
        except VideoUnavailable:
            logger.info(f"Video unavailable: {video_id}")
            return {"success": False, "error": "Video unavailable"}
        except Exception as e:
            logger.warning(f"Tier 1 failed for {video_id}: {e}")
            return {"success": False, "error": str(e)}

    def _try_whisper(self, video_id: str, duration_minutes: float) -> Dict:
        """Tier 2: Try Whisper transcription."""
        try:
            logger.info(f"Tier 2: Trying Whisper for {video_id}")

            result = self.whisper.transcribe_youtube(
                video_id,
                max_duration_minutes=duration_minutes + 5  # Small buffer
            )

            # Convert to standard format
            transcript_data = []
            for seg in result.get("segments", []):
                transcript_data.append({
                    "text": seg.get("text", ""),
                    "start": seg.get("start", 0),
                    "duration": seg.get("end", 0) - seg.get("start", 0),
                })

            return {
                "success": True,
                "video_id": video_id,
                "transcript": transcript_data,
                "text": result.get("text", ""),
                "method": "whisper",
                "cost": result.get("cost", 0),
            }

        except Exception as e:
            logger.warning(f"Tier 2 (Whisper) failed for {video_id}: {e}")
            return {"success": False, "error": str(e)}

    def _try_assemblyai(self, video_id: str) -> Dict:
        """Tier 3: Try AssemblyAI transcription."""
        if not ASSEMBLYAI_AVAILABLE:
            return {"success": False, "error": "AssemblyAI not available"}

        try:
            logger.info(f"Tier 3: Trying AssemblyAI for {video_id}")

            import os
            aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

            # Download audio first
            from backend.integrations.whisper_client import WhisperTranscriptionClient
            whisper = WhisperTranscriptionClient()
            audio_path = whisper.download_audio(video_id)

            # Transcribe with AssemblyAI
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path)

            if transcript.status == aai.TranscriptStatus.error:
                raise RuntimeError(f"AssemblyAI error: {transcript.error}")

            # Convert to standard format
            transcript_data = []
            if transcript.words:
                for word in transcript.words:
                    transcript_data.append({
                        "text": word.text,
                        "start": word.start / 1000,  # Convert to seconds
                        "duration": (word.end - word.start) / 1000,
                    })

            # Calculate cost
            duration_minutes = (transcript.audio_duration or 0) / 60
            cost = duration_minutes * 0.015

            # Cleanup
            try:
                os.remove(audio_path)
            except:
                pass

            return {
                "success": True,
                "video_id": video_id,
                "transcript": transcript_data,
                "text": transcript.text,
                "method": "assemblyai",
                "cost": cost,
            }

        except Exception as e:
            logger.warning(f"Tier 3 (AssemblyAI) failed for {video_id}: {e}")
            return {"success": False, "error": str(e)}

    def _estimate_duration(self, video_id: str) -> float:
        """Estimate video duration in minutes."""
        # Try to get from YouTube API if available
        try:
            import os
            from googleapiclient.discovery import build

            api_key = os.getenv("YOUTUBE_API_KEY")
            if api_key:
                youtube = build("youtube", "v3", developerKey=api_key)
                response = youtube.videos().list(
                    part="contentDetails",
                    id=video_id
                ).execute()

                if response.get("items"):
                    duration_str = response["items"][0]["contentDetails"]["duration"]
                    # Parse ISO 8601 duration (PT1H2M3S)
                    import re
                    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
                    if match:
                        hours = int(match.group(1) or 0)
                        minutes = int(match.group(2) or 0)
                        seconds = int(match.group(3) or 0)
                        return hours * 60 + minutes + seconds / 60
        except:
            pass

        # Default estimate
        return 10.0  # Assume 10 minutes


def get_transcript_v2(video_id: str, max_cost: float = 0.50) -> Dict:
    """
    Get transcript using 3-tier system.

    SONNET: Use this instead of the old transcript fetching.
    """
    extractor = ThreeTierTranscriptExtractor()
    return extractor.get_transcript(video_id, max_cost=max_cost)
```

---

## Phase 5: Update Worker Pipeline [Days 10-11]

### Step 5.1: Update Worker to Use New APIs

**File: `backend/worker.py`** (MODIFY EXISTING)

**SONNET: Add these imports and replace the relevant pipeline stages:**

```python
# Add at top of file with other imports
from backend.pipeline.search import unified_search, UnifiedSearchClient
from backend.pipeline.extraction import extract_content, extract_content_batch
from backend.pipeline.validation_v2 import validate_claims_v2
from backend.pipeline.transcripts_v2 import get_transcript_v2
from backend.integrations.gdelt_client import search_news_gdelt
from backend.integrations.semantic_scholar_client import search_academic_papers

# In run_research_job function, replace the relevant stages:

# Stage 3: Source Discovery (UPDATED to use Exa + fallbacks)
logger.info(f"[{job_id}] Stage 3: Source discovery with multi-API")
update_job(job_id, stage="source_discovery", progress_percent=25)

try:
    # Use unified search (Exa -> Brave -> Perplexity fallback)
    search_results = unified_search(
        topic,
        num_results=job.budgets.max_web_urls,
        exclude_domains=["reddit.com"],  # Reddit has its own API
    )

    # For investigation/controversy modes, also get academic sources
    if job.config_json.get("mode") in ["investigation", "controversy"]:
        academic_results = search_academic_papers(topic, limit=10)
        # Add academic sources to results
        for paper in academic_results:
            if paper.get("url"):
                search_results.append({
                    "url": paper["url"],
                    "title": paper.get("title"),
                    "source_type": "academic",
                    "citation_count": paper.get("citation_count"),
                })

    # For breaking_news mode, prioritize GDELT
    if job.config_json.get("mode") == "breaking_news":
        news_results = search_news_gdelt(topic, timespan="24h", max_records=30)
        for article in news_results:
            if article.get("url"):
                search_results.insert(0, {  # Prioritize news
                    "url": article["url"],
                    "title": article.get("title"),
                    "source_type": "news",
                    "source": article.get("source"),
                })

    urls_to_extract = [r["url"] for r in search_results if r.get("url")]
    logger.info(f"[{job_id}] Found {len(urls_to_extract)} URLs to extract")

except Exception as e:
    logger.warning(f"[{job_id}] Source discovery failed: {e}")
    warnings.append(f"Source discovery failed: {str(e)}")
    urls_to_extract = []


# Stage 5: Content Extraction (UPDATED to use Jina Reader)
logger.info(f"[{job_id}] Stage 5: Content extraction with Jina Reader")
update_job(job_id, stage="content_extraction", progress_percent=40)

try:
    # Use batch extraction for efficiency
    extraction_results = extract_content_batch(urls_to_extract)

    web_sources = []
    for result in extraction_results:
        if result.get("content") and len(result["content"]) > 100:
            web_sources.append({
                "url": result["url"],
                "text": result["content"],
                "source_type": result.get("api", "jina"),
            })

    logger.info(f"[{job_id}] Extracted content from {len(web_sources)} sources")

except Exception as e:
    logger.warning(f"[{job_id}] Content extraction failed: {e}")
    warnings.append(f"Content extraction failed: {str(e)}")


# Stage 6: Transcript Fetching (UPDATED to use 3-tier system)
logger.info(f"[{job_id}] Stage 6: Transcript extraction (3-tier)")
update_job(job_id, stage="transcript_extraction", progress_percent=50)

transcripts = []
transcript_costs = 0

for video_id in video_ids[:job.budgets.max_transcription_minutes]:
    try:
        # Calculate remaining budget
        remaining_budget = job.config_json.get("max_cost_usd", 15) - transcript_costs
        max_cost_per_video = min(0.50, remaining_budget / max(1, len(video_ids)))

        result = get_transcript_v2(video_id, max_cost=max_cost_per_video)

        if result.get("success"):
            transcripts.append({
                "video_id": video_id,
                "text": result["text"],
                "transcript": result["transcript"],
                "method": result["method"],
                "cost": result.get("cost", 0),
            })
            transcript_costs += result.get("cost", 0)

    except Exception as e:
        logger.warning(f"[{job_id}] Transcript failed for {video_id}: {e}")
        warnings.append(f"Transcript failed for {video_id}: {str(e)}")

logger.info(f"[{job_id}] Got {len(transcripts)} transcripts (cost: ${transcript_costs:.2f})")


# Stage 8: Claim Validation (UPDATED to use multi-stage pipeline)
logger.info(f"[{job_id}] Stage 8: Multi-stage claim validation")
update_job(job_id, stage="claim_validation", progress_percent=70)

try:
    # Use new multi-stage validation
    evidence_records, validation_costs = validate_claims_v2(
        claims,
        topic,
        max_perplexity_calls=job.budgets.max_claims_to_validate,
    )

    logger.info(f"[{job_id}] Validated {len(evidence_records)} claims (cost: ${validation_costs['total']:.2f})")

except Exception as e:
    logger.warning(f"[{job_id}] Claim validation failed: {e}")
    warnings.append(f"Claim validation failed: {str(e)}")
    evidence_records = []
    validation_costs = {"total": 0}
```

---

## Phase 6: Update Requirements and Environment [Days 12]

### Step 6.1: Update requirements.txt

```bash
# Add to requirements.txt:

# New API clients
exa-py>=1.0.0
httpx>=0.25.0

# Transcript extraction
yt-dlp>=2024.1.0
mutagen>=1.47.0

# Optional: AssemblyAI
assemblyai>=0.20.0

# Existing (ensure these are present)
youtube-transcript-api>=0.6.0
openai>=1.0.0
praw>=7.7.0
trafilatura>=1.6.0
```

### Step 6.2: Update .env.example

```bash
# Add to .env.example:

# === NEW API KEYS FOR v2 ===

# Exa.ai (PRIMARY SEARCH - Required)
EXA_API_KEY=your_exa_api_key

# Brave Search (BACKUP SEARCH - Optional, has free tier)
BRAVE_API_KEY=your_brave_api_key

# Jina Reader (CONTENT EXTRACTION - Optional, free tier works)
JINA_API_KEY=your_jina_api_key

# GDELT (NEWS - No key required, always free)
# No API key needed

# ClaimBuster (CLAIM DETECTION - Optional, free for academic)
CLAIMBUSTER_API_KEY=your_claimbuster_key

# Google Fact Check (EXISTING CHECKS - Part of Google Cloud)
GOOGLE_FACTCHECK_API_KEY=your_google_key

# Semantic Scholar (ACADEMIC - No key required, rate limited)
# No API key needed, but optional key increases limits
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key

# AssemblyAI (TIER 3 TRANSCRIPTS - Optional)
ASSEMBLYAI_API_KEY=your_assemblyai_key
```

---

## Phase 7: Testing [Days 13-14]

### Step 7.1: Integration Tests

**File: `tests/test_multi_api.py`** (CREATE NEW FILE)

```python
"""Tests for multi-API integrations."""
import pytest
import os

# Skip if API keys not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("EXA_API_KEY"),
    reason="API keys not configured"
)


class TestExaSearch:
    """Test Exa.ai search client."""

    def test_basic_search(self):
        from backend.integrations.exa_client import ExaSearchClient

        client = ExaSearchClient()
        result = client.search("artificial intelligence news", num_results=5)

        assert result["api"] == "exa"
        assert len(result["results"]) > 0
        assert result["results"][0].get("url")

    def test_search_with_date_filter(self):
        from backend.integrations.exa_client import ExaSearchClient

        client = ExaSearchClient()
        result = client.search(
            "AI safety",
            num_results=5,
            start_date="2024-01-01",
        )

        assert len(result["results"]) >= 0


class TestJinaReader:
    """Test Jina AI Reader client."""

    def test_extract_article(self):
        from backend.integrations.jina_reader_client import JinaReaderClient

        client = JinaReaderClient()
        result = client.extract("https://example.com")

        assert result["api"] == "jina"
        assert len(result["content"]) > 0

    def test_batch_extraction(self):
        from backend.integrations.jina_reader_client import JinaReaderClient

        client = JinaReaderClient()
        urls = [
            "https://example.com",
            "https://httpbin.org/html",
        ]
        results = client.extract_batch(urls)

        assert len(results) == 2


class TestClaimBuster:
    """Test ClaimBuster client."""

    def test_score_claim(self):
        from backend.integrations.claimbuster_client import ClaimBusterClient

        client = ClaimBusterClient()
        result = client.score_text("The earth is flat and vaccines cause autism.")

        assert result["api"] == "claimbuster"
        assert len(result["claims"]) > 0
        # These claims should score high
        assert any(c["score"] > 0.5 for c in result["claims"])

    def test_filter_check_worthy(self):
        from backend.integrations.claimbuster_client import filter_check_worthy_claims

        claims = [
            "The sky is blue",  # Low check-worthiness
            "The president claimed X without evidence",  # High check-worthiness
            "Hello world",  # Very low
        ]
        worthy = filter_check_worthy_claims(claims)

        # At least one should be filtered out
        assert len(worthy) < len(claims)


class TestGDELT:
    """Test GDELT news client."""

    def test_search_news(self):
        from backend.integrations.gdelt_client import GDELTClient

        client = GDELTClient()
        result = client.search_articles("technology", timespan="24h", max_records=10)

        assert result["api"] == "gdelt"
        assert len(result["results"]) > 0


class TestUnifiedSearch:
    """Test unified search with fallbacks."""

    def test_search_returns_results(self):
        from backend.pipeline.search import unified_search

        results = unified_search("artificial intelligence", num_results=5)

        assert len(results) > 0
        assert results[0].get("url")


class TestThreeTierTranscripts:
    """Test 3-tier transcript system."""

    def test_native_captions(self):
        """Test Tier 1: Native captions."""
        from backend.pipeline.transcripts_v2 import ThreeTierTranscriptExtractor

        extractor = ThreeTierTranscriptExtractor()
        # Use a video known to have captions
        result = extractor.get_transcript("dQw4w9WgXcQ", max_cost=0)  # Free tier only

        if result["success"]:
            assert result["method"].startswith("native")
            assert result["cost"] == 0
```

---

## Deployment Checklist

**SONNET: Complete ALL items before deploying:**

### API Setup
- [ ] Exa.ai API key configured and tested
- [ ] Brave Search API key configured (optional)
- [ ] Jina Reader working (no key needed for basic)
- [ ] ClaimBuster API tested
- [ ] Google Fact Check API configured
- [ ] Semantic Scholar working (no key needed)
- [ ] AssemblyAI key configured (optional)

### Code Changes
- [ ] All new client files created in `backend/integrations/`
- [ ] Pipeline modules updated in `backend/pipeline/`
- [ ] Worker pipeline updated to use new APIs
- [ ] Requirements.txt updated
- [ ] .env.example updated

### Testing
- [ ] All integration tests passing
- [ ] Manual test of each research mode
- [ ] Cost tracking verified
- [ ] Fallback behavior tested

### Documentation
- [ ] CLAUDE.md updated with new API info
- [ ] PRD_v2.md reviewed
- [ ] This TEP_v2.md followed completely

---

## Common Sonnet Pitfalls for v2

### 1. The "Skip Exa" Trap
**SONNET WILL TRY TO:** Keep using Perplexity because "it already works"
**YOU MUST:** Use Exa.ai as primary search. It's 94.9% accurate.

### 2. The "Skip Jina" Trap
**SONNET WILL TRY TO:** Keep using Playwright because "it's thorough"
**YOU MUST:** Use Jina Reader. It's 5x faster and returns cleaner markdown.

### 3. The "Skip ClaimBuster" Trap
**SONNET WILL TRY TO:** Send all claims to Perplexity "for completeness"
**YOU MUST:** Use ClaimBuster to filter first. It's FREE and saves money.

### 4. The "One Transcript Tier" Trap
**SONNET WILL TRY TO:** Only implement youtube-transcript-api "for simplicity"
**YOU MUST:** Implement all 3 tiers. Many videos don't have native captions.

### 5. The "Ignore Free APIs" Trap
**SONNET WILL TRY TO:** Skip GDELT, Semantic Scholar, etc. as "extra complexity"
**YOU MUST:** Use free APIs. They provide valuable data at no cost.

---

## Success Validation

After implementation, verify:

1. **Exa Search Working:**
   - Search returns accurate results
   - Fallback to Brave works when Exa fails

2. **Jina Extraction Working:**
   - Content extracted as clean markdown
   - Batch extraction handles multiple URLs

3. **ClaimBuster Pre-filtering:**
   - Claims scored before Perplexity
   - Only high-score claims sent to Perplexity

4. **3-Tier Transcripts:**
   - Native captions work (Tier 1)
   - Whisper fallback works (Tier 2)
   - AssemblyAI fallback works (Tier 3)

5. **Cost Reduction:**
   - investigation mode costs <$8 (was $15)
   - breaking_news mode costs <$1 (was $2)

---

*END OF TEP v2 - Follow this plan step by step*
