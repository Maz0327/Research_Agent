"""ClaimBuster API - FREE claim detection and scoring."""
import os
from typing import List, Dict, Any
import httpx
from loguru import logger


class ClaimBusterClient:
    """
    ClaimBuster API for detecting check-worthy claims.

    Use this BEFORE Perplexity validation.
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

        Use this to filter claims before Perplexity.
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

        This is the KEY function. Use it to reduce Perplexity costs.

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

    ALWAYS call this before Perplexity validation!
    """
    client = ClaimBusterClient()
    return client.filter_check_worthy(claims, threshold)
