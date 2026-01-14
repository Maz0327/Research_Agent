"""Semantic Scholar API - FREE access to 200M+ academic papers."""
import os
from typing import List, Dict, Any, Optional
import httpx
from loguru import logger


class SemanticScholarClient:
    """
    Semantic Scholar API for academic paper search.

    Use this for INVESTIGATION mode.
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

    Use in investigation mode for scientific claims.
    """
    client = SemanticScholarClient()
    result = client.search(query, limit=limit)
    return result.get("papers", [])
