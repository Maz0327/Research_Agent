"""Serper search API client - BACKUP keyword search.

Research-validated stack (Dec 2025):
- Cost: $1/1k searches (cheapest reliable option)
- Success rate: 93.5%
- Use case: Fallback when Exa/Perplexity fail
"""
from typing import Optional, Any

import httpx
from loguru import logger


class SerperClient:
    """Client for Serper Google Search API.

    Use this as BACKUP search when Exa (semantic) or Perplexity (speed) fail.
    Serper is reliable and cheap ($1/1k) but returns raw Google results.
    """

    BASE_URL = "https://google.serper.dev"
    COST_PER_SEARCH = 0.001  # $1/1k searches

    def __init__(self):
        """Initialize Serper client."""
        from backend.config import get_settings
        settings = get_settings()

        if not settings.serper_api_key:
            raise ValueError("SERPER_API_KEY environment variable is required")

        self.api_key = settings.serper_api_key

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        country: str = "us",
        language: str = "en",
    ) -> dict[str, Any]:
        """Perform Google search via Serper.

        Args:
            query: Search query
            num_results: Number of results (max 100)
            search_type: Type of search (search, news, images, videos)
            country: Country code for localization
            language: Language code

        Returns:
            Dict with results and metadata
        """
        try:
            logger.info(f"Serper {search_type}: '{query[:50]}...' (num={num_results})")

            endpoint = f"{self.BASE_URL}/{search_type}"

            payload = {
                "q": query,
                "num": min(num_results, 100),
                "gl": country,
                "hl": language,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            # Format organic results
            results = []
            for item in data.get("organic", []):
                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet", ""),
                    "position": item.get("position"),
                    "date": item.get("date"),
                })

            # Include knowledge graph if present
            knowledge_graph = data.get("knowledgeGraph")

            logger.info(f"Serper returned {len(results)} results")

            return {
                "results": results,
                "knowledge_graph": knowledge_graph,
                "query": query,
                "api": "serper",
                "cost": self.COST_PER_SEARCH,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Serper HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Serper search failed: {e}")
            raise

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        time_period: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search news articles via Serper.

        Args:
            query: Search query
            num_results: Number of results
            time_period: Time filter (d=day, w=week, m=month, y=year)

        Returns:
            Dict with news results
        """
        try:
            logger.info(f"Serper news: '{query[:50]}...'")

            payload = {
                "q": query,
                "num": min(num_results, 100),
            }

            if time_period:
                payload["tbs"] = f"qdr:{time_period}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/news",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("news", []):
                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "image_url": item.get("imageUrl"),
                })

            logger.info(f"Serper news returned {len(results)} results")

            return {
                "results": results,
                "query": query,
                "api": "serper_news",
                "cost": self.COST_PER_SEARCH,
            }

        except Exception as e:
            logger.error(f"Serper news search failed: {e}")
            raise

    def search_sync(
        self,
        query: str,
        num_results: int = 10,
        **kwargs
    ) -> dict[str, Any]:
        """Synchronous version of search for non-async contexts."""
        try:
            logger.info(f"Serper sync: '{query[:50]}...'")

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/search",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "num": min(num_results, 100),
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet", ""),
                })

            return {
                "results": results,
                "query": query,
                "api": "serper",
                "cost": self.COST_PER_SEARCH,
            }

        except Exception as e:
            logger.error(f"Serper sync search failed: {e}")
            raise


# Convenience functions for pipeline use

async def search_with_serper(
    query: str,
    num_results: int = 10,
    **kwargs
) -> list[dict]:
    """Search with Serper. Returns list of results."""
    client = SerperClient()
    response = await client.search(query, num_results=num_results, **kwargs)
    return response["results"]


async def search_news_with_serper(
    query: str,
    num_results: int = 10,
    time_period: Optional[str] = None,
) -> list[dict]:
    """Search news with Serper. Returns list of results."""
    client = SerperClient()
    response = await client.search_news(query, num_results, time_period)
    return response["results"]


def search_with_serper_sync(
    query: str,
    num_results: int = 10,
) -> list[dict]:
    """Synchronous search with Serper. Returns list of results."""
    client = SerperClient()
    response = client.search_sync(query, num_results)
    return response["results"]
