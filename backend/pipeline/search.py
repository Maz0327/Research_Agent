"""Unified search module with multi-API fallback."""
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.integrations.exa_client import ExaSearchClient, search_with_exa
from backend.integrations.brave_search_client import BraveSearchClient, search_with_brave
from backend.integrations.perplexity_client import _perplexity_search  # Existing


class UnifiedSearchClient:
    """
    Unified search with automatic fallback.

    This is the PRIMARY search interface. Use this, not individual clients.

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
            response = _perplexity_search(query)
            # Convert Perplexity response to standard format
            urls = response.get("urls", [])
            return {
                "results": [{"url": url} for url in urls],
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

    Use this in the pipeline. It handles API selection automatically.
    """
    client = UnifiedSearchClient()
    result = client.search(query, num_results=num_results, **kwargs)
    return result.get("results", [])
