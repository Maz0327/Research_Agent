"""Tavily API client for web search and content extraction.

Tavily is the PRIMARY search API for PRD v4.3, replacing Exa.
Provides both search and extraction in a single API.

Pricing (validated Dec 2024):
- Basic search: 1 credit
- Advanced search: 2 credits
- Extract: 1-2 credits per URL
- Free tier: 1,000 credits/month

Rate limits:
- Dev tier: 100 RPM
- Prod tier: 1,000 RPM
"""
import os
from typing import List, Dict, Optional, Any
from loguru import logger

try:
    from tavily import TavilyClient as TavilySDK
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("tavily-python not installed. Install with: pip install tavily-python")


class TavilyClient:
    """
    Tavily API client for web search and content extraction.

    This is the PRIMARY search API for PRD v4.3.
    Use it FIRST before falling back to Exa or Brave.
    """

    def __init__(self):
        """Initialize Tavily client."""
        if not TAVILY_AVAILABLE:
            raise ImportError("tavily-python library not installed. Install with: pip install tavily-python")

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")

        self.client = TavilySDK(api_key=api_key)
        self.cost_per_basic_search = 1  # credits
        self.cost_per_advanced_search = 2  # credits
        self.cost_per_extract = 1  # credits per URL (approx)

    def search(
        self,
        query: str,
        num_results: int = 20,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search the web using Tavily.

        Args:
            query: Search query
            num_results: Number of results (max 20 for basic, 100 for advanced)
            search_depth: "basic" (1 credit) or "advanced" (2 credits)
            include_domains: Only include these domains
            exclude_domains: Exclude these domains
            include_answer: Include AI-generated answer
            include_raw_content: Include full page content (expensive)
            max_tokens: Limit tokens per result

        Returns:
            Dict with results and metadata
        """
        try:
            logger.info(f"Tavily search: '{query[:50]}...' (depth={search_depth}, num={num_results})")

            # Build search parameters
            params = {
                "query": query,
                "max_results": min(num_results, 20 if search_depth == "basic" else 100),
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
            }

            if include_domains:
                params["include_domains"] = include_domains
            if exclude_domains:
                params["exclude_domains"] = exclude_domains
            if max_tokens:
                params["max_tokens"] = max_tokens

            # Execute search
            response = self.client.search(**params)

            # Format results
            results = []
            for result in response.get("results", []):
                results.append({
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "content": result.get("content"),  # Snippet
                    "raw_content": result.get("raw_content"),  # Full content if requested
                    "score": result.get("score"),
                    "published_date": result.get("published_date"),
                })

            cost = self.cost_per_advanced_search if search_depth == "advanced" else self.cost_per_basic_search

            logger.info(f"Tavily returned {len(results)} results (cost: {cost} credits)")

            return {
                "results": results,
                "query": query,
                "answer": response.get("answer"),  # AI answer if requested
                "api": "tavily",
                "cost_credits": cost,
            }

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            raise

    def extract(
        self,
        urls: List[str],
    ) -> Dict[str, Any]:
        """
        Extract content from URLs using Tavily Extract API.

        Args:
            urls: List of URLs to extract content from

        Returns:
            Dict with extracted content for each URL
        """
        try:
            logger.info(f"Tavily extract: {len(urls)} URLs")

            # Tavily extract can handle multiple URLs
            response = self.client.extract(urls=urls)

            # Format results
            results = []
            for result in response.get("results", []):
                results.append({
                    "url": result.get("url"),
                    "raw_content": result.get("raw_content"),
                })

            failed = response.get("failed_results", [])
            if failed:
                logger.warning(f"Tavily extract failed for {len(failed)} URLs")

            cost = len(urls) * self.cost_per_extract

            logger.info(f"Tavily extracted {len(results)} URLs (cost: ~{cost} credits)")

            return {
                "results": results,
                "failed": failed,
                "api": "tavily",
                "cost_credits": cost,
            }

        except Exception as e:
            logger.error(f"Tavily extract failed: {e}")
            raise

    def extract_batch(
        self,
        urls: List[str],
        batch_size: int = 5,
    ) -> List[Dict]:
        """
        Extract content from URLs in batches.

        Per PRD v4.3: Process 5 URLs at a time for cost efficiency.

        Args:
            urls: List of URLs to extract
            batch_size: Number of URLs per batch (default 5)

        Returns:
            List of extraction results
        """
        all_results = []
        failed_urls = []

        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            try:
                response = self.extract(batch)
                all_results.extend(response["results"])
                failed_urls.extend(response.get("failed", []))
            except Exception as e:
                logger.error(f"Batch {i // batch_size} failed: {e}")
                failed_urls.extend(batch)

        return {
            "results": all_results,
            "failed": failed_urls,
            "api": "tavily",
        }

    def search_and_extract(
        self,
        query: str,
        num_results: int = 10,
        search_depth: str = "advanced",
    ) -> Dict[str, Any]:
        """
        Search and extract content in one workflow.

        This is the most efficient method when you need both
        search results and full content.

        Args:
            query: Search query
            num_results: Number of results
            search_depth: Search depth (basic or advanced)

        Returns:
            Dict with search results including extracted content
        """
        try:
            # Use include_raw_content to get full content in search
            response = self.search(
                query=query,
                num_results=num_results,
                search_depth=search_depth,
                include_raw_content=True,
            )

            return response

        except Exception as e:
            logger.error(f"Tavily search_and_extract failed: {e}")
            raise


# Convenience functions for use in pipeline

def search_with_tavily(
    query: str,
    num_results: int = 20,
    search_depth: str = "basic",
    **kwargs
) -> List[Dict]:
    """
    Convenience function for Tavily search.

    Use this in the pipeline. Returns list of results.
    Falls back gracefully if Tavily is unavailable.
    """
    try:
        client = TavilyClient()
        response = client.search(
            query,
            num_results=num_results,
            search_depth=search_depth,
            **kwargs
        )
        return response["results"]
    except Exception as e:
        logger.error(f"Tavily search failed, returning empty: {e}")
        return []


def extract_with_tavily(urls: List[str]) -> List[Dict]:
    """
    Convenience function for Tavily extract.

    Use this in the pipeline. Returns list of extraction results.
    """
    try:
        client = TavilyClient()
        response = client.extract_batch(urls)
        return response["results"]
    except Exception as e:
        logger.error(f"Tavily extract failed, returning empty: {e}")
        return []


def is_tavily_available() -> bool:
    """Check if Tavily is available and configured."""
    if not TAVILY_AVAILABLE:
        return False
    return bool(os.getenv("TAVILY_API_KEY"))
