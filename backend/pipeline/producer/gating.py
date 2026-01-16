"""Producer Packet gating validation (V10).

Based on: docs/authoritative/spec/RASS.md Stage G
Phase: 8

Gating Requirements (ALL must be met):
- 4+ sources in job
- At least 1 source with confidence_ceiling: high
- Job status: completed
- User explicitly requests (handled by endpoint, not here)
"""

from typing import Any


def can_generate_producer_packet(job: dict[str, Any]) -> tuple[bool, str]:
    """Check if job meets gating requirements for Doc 3.

    Requirements (ALL must be met):
    - 4+ sources in job
    - At least 1 source with confidence_ceiling: high
    - Job status: completed
    - User explicitly requests (handled by endpoint, not here)

    Args:
        job: Job record dict

    Returns:
        Tuple of (can_generate, reason)
    """
    # Check source count
    sources = job.get("sources", [])
    if len(sources) < 4:
        return False, f"Need 4+ sources, have {len(sources)}"

    # Check for high-confidence source
    high_confidence = 0
    for source in sources:
        # Check confidence_ceiling in source or source_identity_package
        confidence = source.get("confidence_ceiling", "")
        if not confidence:
            identity = source.get("source_identity_package", {})
            confidence = identity.get("confidence_ceiling", "")
        if confidence.lower() == "high":
            high_confidence += 1

    if high_confidence < 1:
        return False, "Need at least 1 high-confidence source"

    # Check job status
    status = job.get("status", "")
    if status != "completed":
        return False, f"Job must be completed, currently {status}"

    return True, "OK"


def get_source_summaries(job: dict[str, Any]) -> list[dict]:
    """Extract source summaries for producer context.

    Args:
        job: Job record dict

    Returns:
        List of source summary dicts
    """
    summaries = []
    for source in job.get("sources", []):
        summary = {
            "source_id": source.get("source_id", ""),
            "title": source.get("title", ""),
            "source_type": source.get("source_type", ""),
            "confidence_ceiling": source.get("confidence_ceiling", "medium"),
        }
        summaries.append(summary)
    return summaries
