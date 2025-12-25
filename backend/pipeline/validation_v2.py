"""Multi-stage claim validation with cost optimization."""
from typing import List, Dict, Any, Tuple
from loguru import logger

from backend.integrations.claimbuster_client import (
    ClaimBusterClient
)
from backend.integrations.google_factcheck_client import (
    GoogleFactCheckClient,
    claim_already_checked
)
from backend.integrations.perplexity_client import _perplexity_search
from backend.models.claim import Claim, EvidenceRecord, EvidenceStatus, Citation


class MultiStageValidator:
    """
    Multi-stage claim validation pipeline.

    This pipeline MUST be followed in order:
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
                    evidence_for=[Citation(url=existing_check.get("url"))] if status == EvidenceStatus.VERIFIED else [],
                    evidence_against=[Citation(url=existing_check.get("url"))] if status == EvidenceStatus.DEBUNKED else [],
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

    Use this instead of the old validate_claims function.
    """
    validator = MultiStageValidator()
    return validator.validate_claims(claims, topic, max_perplexity_calls)
