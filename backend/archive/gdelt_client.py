"""GDELT Project API client - FREE news discovery at scale."""
from typing import List, Dict, Optional, Any
import httpx
from loguru import logger


class GDELTClient:
    """
    GDELT Project API for global news discovery.

    This is FREE and has massive scale.
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

        Use for breaking_news mode to find hot topics.
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

    Use this for news discovery. Returns list of articles.
    """
    client = GDELTClient()
    response = client.search_articles(query, timespan=timespan, max_records=max_records)
    return response["results"]
