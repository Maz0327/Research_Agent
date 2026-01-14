"""Brave Search API client - BACKUP search when Exa fails."""
import os
from typing import List, Dict, Optional, Any
import httpx
from loguru import logger


class BraveSearchClient:
    """
    Brave Search client - use as FALLBACK when Exa fails.

    This is the BACKUP search. Use Exa first.
    Brave has 2000 free requests/month.
    """

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self):
        """Initialize Brave client."""
        self.api_key = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            logger.warning("BRAVE_SEARCH_API_KEY not set - Brave search unavailable")
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
            raise ValueError("BRAVE_SEARCH_API_KEY not configured")

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
