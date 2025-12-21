"""Google Fact Check Tools API - Find existing fact-checks."""
import os
from typing import List, Dict, Any, Optional
import httpx
from loguru import logger


class GoogleFactCheckClient:
    """
    Google Fact Check Tools API.

    Use this BEFORE creating new validations.
    - FREE (part of Google Cloud)
    - Finds existing fact-checks from reputable sources
    - If a claim is already checked, use that instead of Perplexity

    This saves both time and money!
    """

    API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

    def __init__(self):
        """Initialize Google Fact Check client."""
        self.api_key = os.getenv("GOOGLE_FACTCHECK_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("YOUTUBE_API_KEY")
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

    Call this before Perplexity validation. If fact-check exists, use it!
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
