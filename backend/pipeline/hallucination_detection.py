"""Semantic entropy-based hallucination detection.

Hallucination Prevention Rule SE-001: High semantic entropy indicates hallucination.

Research shows that when LLMs hallucinate, they produce inconsistent outputs
across multiple samples. This module detects such inconsistency.

Reference: plans/reports/researcher-260114-1657-gemini-hallucination-prevention.md

Usage:
    For high-stakes claims (synthesis assertions, critical quotes), run
    multi-sample generation and check semantic entropy. High entropy (>0.75)
    suggests the claim may be hallucinated.
"""

from collections import Counter
from math import log2
from typing import Any, Callable, Optional

from loguru import logger


def compute_semantic_entropy(responses: list[str]) -> float:
    """
    Compute normalized semantic entropy from a list of responses.

    Lower entropy = more consistent = likely factual
    Higher entropy = inconsistent = possibly hallucinated

    Args:
        responses: List of LLM responses to the same prompt

    Returns:
        Normalized entropy (0.0 = perfectly consistent, 1.0 = maximally inconsistent)
    """
    if not responses:
        return 1.0  # No responses = maximum uncertainty

    # Cluster by exact match (simplified semantic clustering)
    # In production, could use embedding similarity clustering
    clusters = Counter(responses)
    total = len(responses)

    if total == 1:
        return 0.0  # Single sample = no entropy measurable

    # Compute Shannon entropy
    entropy = 0.0
    for count in clusters.values():
        if count > 0:
            prob = count / total
            entropy -= prob * log2(prob)

    # Normalize by maximum possible entropy
    max_entropy = log2(len(responses))
    if max_entropy == 0:
        return 0.0

    return entropy / max_entropy


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for semantic comparison.

    Removes minor variations that don't affect meaning:
    - Whitespace differences
    - Punctuation at end
    - Case differences
    """
    text = text.strip().lower()
    # Remove trailing punctuation
    while text and text[-1] in ".!?":
        text = text[:-1]
    # Normalize whitespace
    text = " ".join(text.split())
    return text


def cluster_by_similarity(
    responses: list[str],
    similarity_threshold: float = 0.85,
) -> list[list[str]]:
    """
    Cluster responses by semantic similarity.

    Simple approach: normalize and group exact matches.
    For production, consider using embeddings.

    Args:
        responses: List of text responses
        similarity_threshold: Threshold for considering responses similar

    Returns:
        List of clusters (each cluster is a list of similar responses)
    """
    normalized = [normalize_for_comparison(r) for r in responses]

    # Group by normalized form
    groups: dict[str, list[str]] = {}
    for original, norm in zip(responses, normalized):
        if norm not in groups:
            groups[norm] = []
        groups[norm].append(original)

    return list(groups.values())


async def detect_hallucination_via_entropy(
    claim: str,
    generate_fn: Callable[[str, float], Any],
    samples: int = 5,
    temperature: float = 0.3,
    entropy_threshold: float = 0.75,
) -> dict:
    """
    Detect potential hallucination using semantic entropy.

    Generates multiple paraphrases of a claim and checks consistency.
    High entropy suggests the model is uncertain = possible hallucination.

    Args:
        claim: The claim to verify
        generate_fn: Async function(prompt, temperature) -> response text
        samples: Number of samples to generate (default 5)
        temperature: Temperature for generation (default 0.3)
        entropy_threshold: Above this = likely hallucination (default 0.75)

    Returns:
        dict with:
            - is_likely_hallucination: bool
            - entropy: float (0-1)
            - consistency: float (1 - entropy)
            - dominant_response: most common response
            - sample_count: number of samples generated
            - cluster_count: number of distinct response clusters
    """
    prompt = f"Rephrase this claim concisely in one sentence: {claim}"

    responses = []
    for i in range(samples):
        try:
            response = await generate_fn(prompt, temperature)
            if response:
                responses.append(str(response))
        except Exception as e:
            logger.warning(f"Sample {i+1} generation failed: {e}")

    if len(responses) < 2:
        logger.warning("Insufficient samples for entropy calculation")
        return {
            "is_likely_hallucination": False,  # Can't determine
            "entropy": 0.0,
            "consistency": 1.0,
            "dominant_response": responses[0] if responses else None,
            "sample_count": len(responses),
            "cluster_count": len(responses),
            "error": "insufficient_samples",
        }

    # Cluster responses
    clusters = cluster_by_similarity(responses)

    # Compute entropy from cluster sizes
    cluster_sizes = [len(c) for c in clusters]
    total = sum(cluster_sizes)

    entropy = 0.0
    for size in cluster_sizes:
        if size > 0:
            prob = size / total
            entropy -= prob * log2(prob)

    # Normalize
    max_entropy = log2(len(responses))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    # Find dominant response (most common cluster)
    dominant_cluster = max(clusters, key=len)
    dominant_response = dominant_cluster[0] if dominant_cluster else None

    is_hallucination = normalized_entropy > entropy_threshold

    if is_hallucination:
        logger.warning(
            f"Claim gave inconsistent results ({normalized_entropy:.2f}): "
            f"'{claim[:50]}...'"
        )

    return {
        "is_likely_hallucination": is_hallucination,
        "entropy": normalized_entropy,
        "consistency": 1 - normalized_entropy,
        "dominant_response": dominant_response,
        "sample_count": len(responses),
        "cluster_count": len(clusters),
    }


def detect_hallucination_sync(
    claim: str,
    generate_fn: Callable[[str, float], str],
    samples: int = 5,
    temperature: float = 0.3,
    entropy_threshold: float = 0.75,
) -> dict:
    """
    Synchronous version of hallucination detection.

    For use in non-async contexts.

    Args:
        claim: The claim to verify
        generate_fn: Sync function(prompt, temperature) -> response text
        samples: Number of samples to generate
        temperature: Temperature for generation
        entropy_threshold: Above this = likely hallucination

    Returns:
        dict with hallucination detection results
    """
    prompt = f"Rephrase this claim concisely in one sentence: {claim}"

    responses = []
    for i in range(samples):
        try:
            response = generate_fn(prompt, temperature)
            if response:
                responses.append(str(response))
        except Exception as e:
            logger.warning(f"Sample {i+1} generation failed: {e}")

    if len(responses) < 2:
        return {
            "is_likely_hallucination": False,
            "entropy": 0.0,
            "consistency": 1.0,
            "dominant_response": responses[0] if responses else None,
            "sample_count": len(responses),
            "cluster_count": len(responses),
            "error": "insufficient_samples",
        }

    clusters = cluster_by_similarity(responses)
    cluster_sizes = [len(c) for c in clusters]
    total = sum(cluster_sizes)

    entropy = 0.0
    for size in cluster_sizes:
        if size > 0:
            prob = size / total
            entropy -= prob * log2(prob)

    max_entropy = log2(len(responses))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    dominant_cluster = max(clusters, key=len)
    dominant_response = dominant_cluster[0] if dominant_cluster else None

    is_hallucination = normalized_entropy > entropy_threshold

    if is_hallucination:
        logger.warning(
            f"Claim gave inconsistent results ({normalized_entropy:.2f}): "
            f"'{claim[:50]}...'"
        )

    return {
        "is_likely_hallucination": is_hallucination,
        "entropy": normalized_entropy,
        "consistency": 1 - normalized_entropy,
        "dominant_response": dominant_response,
        "sample_count": len(responses),
        "cluster_count": len(clusters),
    }


def batch_check_claims(
    claims: list[dict],
    generate_fn: Callable[[str, float], str],
    samples: int = 3,
    entropy_threshold: float = 0.75,
) -> tuple[list[dict], list[str]]:
    """
    Check a batch of claims for potential hallucination.

    Only runs entropy check on high-confidence claims that could benefit
    from verification. Low-confidence claims are already appropriately uncertain.

    Args:
        claims: List of claim dicts with "statement" and "confidence" fields
        generate_fn: Function to generate responses
        samples: Number of samples per claim
        entropy_threshold: Threshold for hallucination detection

    Returns:
        Tuple of (updated_claims, warnings)
    """
    warnings = []

    for claim in claims:
        confidence = claim.get("confidence", "medium")

        # Only check high-confidence claims (they're the risky ones)
        if confidence not in ("high",):
            continue

        statement = claim.get("statement", "")
        if not statement:
            continue

        result = detect_hallucination_sync(
            statement,
            generate_fn,
            samples=samples,
            entropy_threshold=entropy_threshold,
        )

        claim["_entropy_score"] = result["entropy"]
        claim["_consistency"] = result["consistency"]

        if result["is_likely_hallucination"]:
            claim_id = claim.get("claim_id", "UNKNOWN")
            # Downgrade confidence
            claim["confidence"] = "low"
            claim["_hallucination_flag"] = True
            warning = (
                f"{claim_id}: inconsistent when checked multiple times - "
                "marked as needing review"
            )
            warnings.append(warning)
            logger.warning(f"Claim {claim_id} flagged as inconsistent (score: {result['entropy']:.2f})")

    return claims, warnings
