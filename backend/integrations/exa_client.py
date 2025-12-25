"""Exa.ai neural search client - PRIMARY search API."""
import os
from typing import List, Dict, Optional, Any
from loguru import logger

# Install with: pip install exa-py
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False
    logger.warning("exa-py not installed. Install with: pip install exa-py")



class ExaSearchClient:
    """
    Exa.ai client for neural semantic search.

    CRITICAL: This is the PRIMARY search API. Use it FIRST before Brave/Perplexity.
    Exa has 94.9% accuracy vs ~80% for traditional search.
    """

    def __init__(self):
        """Initialize Exa client."""
        if not EXA_AVAILABLE:
            raise ImportError("exa-py library not installed")

        # Try different environment variable names (EXAAI_ prefix for Railway compatibility)
        api_key = os.getenv("EXA_API_KEY") or os.getenv("EXAAI_SECRET_KEY") or os.getenv("EXA.AI_SECRET_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY or EXAAI_SECRET_KEY environment variable is required")

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

        Use this when you need content immediately.
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

    Use this in the pipeline. Returns list of results.
    """
    client = ExaSearchClient()
    response = client.search(query, num_results=num_results, **kwargs)
    return response["results"]
