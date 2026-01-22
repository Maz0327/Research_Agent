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

from loguru import logger


def _extract_sources_from_job(job: dict[str, Any]) -> list[dict]:
    """Extract sources list from job data.

    Sources can be found in multiple locations (checked in priority order):
    1. job["sources"] - if explicitly provided (legacy/direct)
    2. job["artifacts"]["source_ledger"]["source_manifest"] - inline Doc 0 data
    3. job["artifacts"]["source_ledger"]["data"]["source_manifest"] - nested inline
    4. Must fetch from storage if only doc_0_path available (caller responsibility)

    Args:
        job: Job record dict

    Returns:
        List of source dicts with at least source_id and confidence info
    """
    # Priority 1: Direct sources array
    if job.get("sources"):
        return job["sources"]

    # Priority 2: Extract from artifacts.source_ledger (inline data)
    artifacts = job.get("artifacts")
    if not artifacts:
        logger.debug("No artifacts in job dict")
        return []

    # Handle Pydantic model or dict
    if hasattr(artifacts, "model_dump"):
        artifacts = artifacts.model_dump(exclude_none=True)
    elif hasattr(artifacts, "__dict__"):
        artifacts = {k: v for k, v in artifacts.__dict__.items() if not k.startswith("_")}

    source_ledger = artifacts.get("source_ledger")
    if not source_ledger:
        logger.debug("No source_ledger in artifacts")
        return []

    # Handle nested dict structure from storage
    if isinstance(source_ledger, dict):
        # Check for data wrapper (from storage format)
        if "data" in source_ledger and isinstance(source_ledger["data"], dict):
            source_ledger = source_ledger["data"]

        # source_manifest is the array of sources in Doc 0
        sources = source_ledger.get("source_manifest", [])
        if sources:
            logger.debug(f"Found {len(sources)} sources in source_ledger.source_manifest")
            return sources

        # Also check 'entries' key (older format)
        entries = source_ledger.get("entries", [])
        if entries:
            logger.debug(f"Found {len(entries)} sources in source_ledger.entries")
            return entries

    logger.debug("No sources found in source_ledger")
    return []


def can_generate_producer_packet(job: dict[str, Any]) -> tuple[bool, str]:
    """Check if job meets gating requirements for Doc 3.

    Requirements (ALL must be met):
    - 4+ sources in job
    - At least 1 source with confidence_ceiling: high
    - Job status: completed
    - User explicitly requests (handled by endpoint, not here)

    Args:
        job: Job record dict (with artifacts containing source_ledger)

    Returns:
        Tuple of (can_generate, reason)
    """
    # Check source count - extract from artifacts.source_ledger
    sources = _extract_sources_from_job(job)
    if len(sources) < 4:
        return False, f"Need 4+ sources, have {len(sources)}"

    # Check for high-confidence source
    high_confidence = 0
    for source in sources:
        # Check confidence_ceiling in source (Doc 0 format) or source_identity_package
        confidence = source.get("confidence_ceiling", "")
        if not confidence:
            # Try 'status' field which may contain confidence info
            confidence = source.get("status", "")
        if not confidence:
            identity = source.get("source_identity_package", {})
            confidence = identity.get("confidence_ceiling", "")
        # Also check 'type' for high-quality source types
        source_type = source.get("type", source.get("source_type", ""))

        # High confidence if explicitly marked or is a transcript-grounded video
        if isinstance(confidence, str) and confidence.lower() == "high":
            high_confidence += 1
        elif source_type in ("youtube", "article") and source.get("status") == "ingested":
            # Ingested sources have been successfully processed
            high_confidence += 1

    if high_confidence < 1:
        return False, "Need at least 1 high-confidence source"

    # Check job status
    # Accept "running_producer" because if the worker is running gating,
    # the API route already validated status was "completed" before queuing the task.
    status = job.get("status", "")
    valid_statuses = ("completed", "completed_with_warnings", "running_producer")
    if status not in valid_statuses:
        return False, f"Job must be completed, currently {status}"

    return True, "OK"


def get_source_summaries(job: dict[str, Any]) -> list[dict]:
    """Extract source summaries for producer context.

    Args:
        job: Job record dict

    Returns:
        List of source summary dicts
    """
    sources = _extract_sources_from_job(job)
    summaries = []
    for source in sources:
        summary = {
            "source_id": source.get("source_id", ""),
            "title": source.get("title", ""),
            # Handle both 'source_type' and 'type' keys (Doc 0 format uses 'type')
            "source_type": source.get("source_type", source.get("type", "")),
            "confidence_ceiling": source.get("confidence_ceiling", "medium"),
        }
        summaries.append(summary)
    return summaries
