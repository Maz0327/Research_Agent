"""
RAG Grounding - Optional fact-checking for high-confidence claims.

Purpose: Verify that claims extracted by the LLM are grounded in source text.
This is an additional layer of hallucination prevention beyond quote verification.

Feature-Flagged: Controlled by HallucinationConfig.enable_rag_grounding

Grounding Verification Process:
1. For each claim with confidence >= threshold
2. Find best matching text span in source
3. Assess grounding strength: STRONG, PARTIAL, WEAK, NONE
4. Optionally suggest confidence adjustment

Uses fuzzy matching from quote_verification.py to avoid duplication.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger

from backend.pipeline.stages.quote_verification import (
    find_best_match,
    normalize_text,
    EXACT_MATCH_THRESHOLD,
    FUZZY_MATCH_THRESHOLD,
)


class GroundingStrength(str, Enum):
    """Grounding assessment result."""
    STRONG = "strong"      # 90%+ match, direct textual evidence
    PARTIAL = "partial"    # 70-89% match, related text found
    WEAK = "weak"          # 50-69% match, tangentially related
    NONE = "none"          # <50% match, no supporting text


# Thresholds for grounding assessment
STRONG_GROUNDING_THRESHOLD = 0.90
PARTIAL_GROUNDING_THRESHOLD = 0.70
WEAK_GROUNDING_THRESHOLD = 0.50


@dataclass
class GroundingResult:
    """Result of verifying claim grounding in source text."""
    claim_id: str
    claim_text: str
    original_confidence: str
    grounding_strength: GroundingStrength
    match_score: float
    matched_span: Optional[str] = None
    suggested_confidence: Optional[str] = None
    grounding_note: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text[:100] + "..." if len(self.claim_text) > 100 else self.claim_text,
            "original_confidence": self.original_confidence,
            "grounding_strength": self.grounding_strength.value,
            "match_score": round(self.match_score, 3),
            "matched_span": self.matched_span,
            "suggested_confidence": self.suggested_confidence,
            "grounding_note": self.grounding_note,
        }


def assess_grounding_strength(match_score: float) -> GroundingStrength:
    """Convert match score to grounding strength level."""
    if match_score >= STRONG_GROUNDING_THRESHOLD:
        return GroundingStrength.STRONG
    elif match_score >= PARTIAL_GROUNDING_THRESHOLD:
        return GroundingStrength.PARTIAL
    elif match_score >= WEAK_GROUNDING_THRESHOLD:
        return GroundingStrength.WEAK
    else:
        return GroundingStrength.NONE


def suggest_confidence_for_grounding(
    original_confidence: str,
    grounding_strength: GroundingStrength,
) -> tuple[Optional[str], Optional[str]]:
    """Suggest confidence adjustment based on grounding strength.

    Args:
        original_confidence: The LLM's assigned confidence (high/medium/low)
        grounding_strength: Assessed grounding strength

    Returns:
        Tuple of (suggested_confidence, note)
        - suggested_confidence: None if no change needed
        - note: Explanation for the suggestion
    """
    if grounding_strength == GroundingStrength.STRONG:
        return None, None  # Strong grounding supports any confidence

    if grounding_strength == GroundingStrength.PARTIAL:
        if original_confidence == "high":
            return "medium", "Partial grounding; suggest medium confidence"
        return None, None

    if grounding_strength == GroundingStrength.WEAK:
        if original_confidence in ("high", "medium"):
            return "low", "Weak grounding; suggest low confidence"
        return None, None

    # GroundingStrength.NONE
    if original_confidence != "low":
        return "low", "No grounding found; suggest low confidence or removal"
    return None, "No grounding found; consider removing claim"


def verify_claim_grounding(
    claim_id: str,
    claim_text: str,
    source_text: str,
    original_confidence: str = "medium",
) -> GroundingResult:
    """Verify that a claim has supporting evidence in source text.

    Args:
        claim_id: Identifier for the claim
        claim_text: The claim statement to verify
        source_text: The raw source content to search in
        original_confidence: The LLM's assigned confidence

    Returns:
        GroundingResult with assessment
    """
    if not claim_text or not source_text:
        return GroundingResult(
            claim_id=claim_id,
            claim_text=claim_text or "",
            original_confidence=original_confidence,
            grounding_strength=GroundingStrength.NONE,
            match_score=0.0,
            grounding_note="Empty claim or source text",
        )

    # Find best matching span in source
    match_score, matched_span = find_best_match(claim_text, source_text)

    # Assess grounding strength
    strength = assess_grounding_strength(match_score)

    # Get confidence suggestion
    suggested_conf, note = suggest_confidence_for_grounding(original_confidence, strength)

    return GroundingResult(
        claim_id=claim_id,
        claim_text=claim_text,
        original_confidence=original_confidence,
        grounding_strength=strength,
        match_score=match_score,
        matched_span=matched_span if strength != GroundingStrength.NONE else None,
        suggested_confidence=suggested_conf,
        grounding_note=note,
    )


def verify_claims_grounding(
    claims: list,
    source_text: str,
    source_id: str,
    confidence_threshold: str = "high",
    max_claims: int = 10,
) -> tuple[list[GroundingResult], list[str]]:
    """Verify grounding for multiple claims.

    Works with both Claim objects and dicts.

    Args:
        claims: List of Claim objects or dicts with claim_id, statement, confidence
        source_text: The raw source content
        source_id: Source identifier for logging
        confidence_threshold: Minimum confidence to verify (high, medium, low)
        max_claims: Maximum claims to verify (cost control)

    Returns:
        Tuple of (grounding_results, warnings)
    """
    if not claims:
        return [], []

    warnings = []

    # Filter claims by confidence threshold
    confidence_order = {"low": 0, "medium": 1, "high": 2}
    threshold_value = confidence_order.get(confidence_threshold.lower(), 2)

    claims_to_verify = []
    for claim in claims:
        # Handle both Claim objects and dicts
        if hasattr(claim, "confidence"):
            # Claim object
            claim_conf = claim.confidence.value if hasattr(claim.confidence, "value") else str(claim.confidence)
        else:
            # Dict
            claim_conf = claim.get("confidence", "medium")
        claim_conf = claim_conf.lower()

        if confidence_order.get(claim_conf, 1) >= threshold_value:
            claims_to_verify.append(claim)

    # Limit to max_claims
    claims_to_verify = claims_to_verify[:max_claims]

    if not claims_to_verify:
        logger.debug(f"[{source_id}] No claims meet threshold for grounding verification")
        return [], []

    logger.info(
        f"[{source_id}] Verifying grounding for {len(claims_to_verify)} claims "
        f"(threshold={confidence_threshold})"
    )

    results = []
    strongly_grounded = 0
    partially_grounded = 0
    weakly_grounded = 0
    not_grounded = 0

    for claim in claims_to_verify:
        # Extract claim data - handle both Claim objects and dicts
        if hasattr(claim, "claim_id"):
            # Claim object
            claim_id = claim.claim_id
            claim_text = claim.statement
            claim_conf = claim.confidence.value if hasattr(claim.confidence, "value") else str(claim.confidence)
        else:
            # Dict
            claim_id = claim.get("claim_id", "UNKNOWN")
            claim_text = claim.get("statement", "")
            claim_conf = claim.get("confidence", "medium")

        result = verify_claim_grounding(
            claim_id=claim_id,
            claim_text=claim_text,
            source_text=source_text,
            original_confidence=claim_conf,
        )
        results.append(result)

        if result.grounding_strength == GroundingStrength.STRONG:
            strongly_grounded += 1
        elif result.grounding_strength == GroundingStrength.PARTIAL:
            partially_grounded += 1
        elif result.grounding_strength == GroundingStrength.WEAK:
            weakly_grounded += 1
        else:
            not_grounded += 1

        # Log warnings for problematic claims
        if result.suggested_confidence:
            warnings.append(
                f"Claim {result.claim_id}: {result.grounding_note} (score={result.match_score:.2f})"
            )

    # Calculate grounding rate (strong + partial / total)
    total_verified = len(results)
    grounded_count = strongly_grounded + partially_grounded
    grounding_rate = grounded_count / total_verified if total_verified > 0 else 1.0

    logger.info(
        f"[{source_id}] Grounding verification: {grounded_count}/{total_verified} grounded "
        f"({grounding_rate:.1%}) - strong={strongly_grounded}, partial={partially_grounded}, "
        f"weak={weakly_grounded}, none={not_grounded}"
    )

    return results, warnings


def apply_grounding_adjustments(
    claims: list,
    grounding_results: list[GroundingResult],
) -> tuple[list, list[str]]:
    """Apply suggested confidence adjustments from grounding verification.

    Works with both Claim objects and dicts.

    Args:
        claims: Original claims list (Claim objects or dicts)
        grounding_results: Grounding verification results

    Returns:
        Tuple of (adjusted_claims, warnings)
    """
    from backend.models.semantic_units import ConfidenceLevel

    # Build lookup by claim_id
    adjustments = {
        r.claim_id: r for r in grounding_results
        if r.suggested_confidence is not None
    }

    if not adjustments:
        return claims, []

    warnings = []

    for claim in claims:
        # Handle both Claim objects and dicts
        if hasattr(claim, "claim_id"):
            # Claim object
            claim_id = claim.claim_id
            old_conf = claim.confidence.value if hasattr(claim.confidence, "value") else str(claim.confidence)

            if claim_id in adjustments:
                result = adjustments[claim_id]
                new_conf = result.suggested_confidence

                # Apply adjustment to object
                try:
                    claim.confidence = ConfidenceLevel(new_conf.lower())
                except ValueError:
                    claim.confidence = ConfidenceLevel.LOW

                warnings.append(
                    f"Claim {claim_id}: confidence {old_conf} -> {new_conf} "
                    f"({result.grounding_note})"
                )
        else:
            # Dict
            claim_id = claim.get("claim_id", "")
            if claim_id in adjustments:
                result = adjustments[claim_id]
                old_conf = claim.get("confidence", "medium")
                new_conf = result.suggested_confidence

                # Apply adjustment to dict
                claim["confidence"] = new_conf
                claim["_grounding_adjusted"] = True
                claim["_grounding_note"] = result.grounding_note
                claim["_grounding_score"] = result.match_score

                warnings.append(
                    f"Claim {claim_id}: confidence {old_conf} -> {new_conf} "
                    f"({result.grounding_note})"
                )

    # Return the modified claims list (modifications made in-place)
    return claims, warnings
