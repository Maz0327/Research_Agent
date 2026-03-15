"""Document Version Manager — Phase 3.

Implements the 4-version rolling window for all pipeline documents (Doc 0-4).

Storage layout (per architecture Rule 13b):
  research-jobs/{job_id}/doc_{N}/v{version}.json      — document content
  research-jobs/{job_id}/doc_{N}/v{version}_meta.json — version metadata
  research-jobs/{job_id}/doc_{N}/latest.json           — pointer to latest version number

Rolling window:
  - Maximum 4 versions stored: latest + 3 previous
  - When 5th version is created, oldest is dropped automatically
  - Versions are per-document and independent (Doc 0 may be v5 while Doc 3 is v2)

Diff summary format:
  "+N sources, +N claims" for additions
  "-N sources, -N claims" for removals
  "Regenerated from new angle" for different_angle mode
  etc.
"""

import json
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from loguru import logger

from backend.integrations.supabase_storage import get_storage_client
from backend.models.creator_brief import DocumentVersionMetadata

# Maximum number of versions to keep per document
MAX_VERSIONS = 4

# Doc numbers that support versioning
DOC_TYPES = ("doc_0", "doc_1", "doc_2", "doc_3", "doc_4", "doc_5", "doc_6", "doc_7")

# Trigger type
TriggerType = Literal[
    "initial_run",
    "deep_dive",
    "expand_sources",
    "deeper",
    "different_angle",
    "custom",
    "inline_edit",
]


def store_document_version(
    job_id: str,
    doc_type: str,
    content: dict[str, Any],
    trigger: TriggerType = "initial_run",
    markdown: Optional[str] = None,
) -> tuple[int, Optional[str]]:
    """Store a new version of a document and apply rolling window cleanup.

    Creates the new version, updates the latest pointer, and drops the oldest
    version if the window exceeds MAX_VERSIONS.

    Args:
        job_id: Job identifier.
        doc_type: Document type ("doc_0", "doc_1", "doc_2", "doc_3", "doc_4").
        content: Document content as dict.
        trigger: What triggered this new version.
        markdown: Optional markdown representation of the document.

    Returns:
        Tuple of (version_number, storage_path_or_None).
        version_number is the new version's integer number (1-based).
        storage_path is None if storage is unavailable.
    """
    storage = get_storage_client()
    if not storage:
        logger.info(f"[{job_id}] Storage not configured, skipping version storage for {doc_type}")
        return 1, None

    try:
        # Determine the next version number
        current_latest = _get_latest_version(storage, job_id, doc_type)
        new_version = current_latest + 1

        # Build version metadata
        meta = _build_version_metadata(
            version=new_version,
            trigger=trigger,
            content=content,
            previous_content=_load_version_content(storage, job_id, doc_type, current_latest),
        )

        # Prepare full document payload
        versioned_content = {
            "data": content,
            "markdown": markdown,
            "version_metadata": meta.model_dump(mode="json"),
        }

        # Upload version document
        version_path = _version_path(job_id, doc_type, new_version)
        json_bytes = json.dumps(versioned_content, indent=2, default=str).encode("utf-8")
        storage.upload_file(version_path, json_bytes, "application/json")
        logger.info(f"[{job_id}] Stored {doc_type} v{new_version} at {version_path}")

        # Update latest pointer
        _update_latest_pointer(storage, job_id, doc_type, new_version)

        # Apply rolling window — drop oldest if over limit
        _apply_rolling_window(storage, job_id, doc_type, new_version)

        return new_version, version_path

    except Exception as e:
        logger.warning(f"[{job_id}] Version storage failed for {doc_type}: {e}")
        return 1, None


def get_document_version(
    job_id: str,
    doc_type: str,
    version: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Retrieve a specific document version.

    Args:
        job_id: Job identifier.
        doc_type: Document type ("doc_0", "doc_1", etc.).
        version: Version number to retrieve. None = latest.

    Returns:
        Versioned document dict with keys: data, markdown, version_metadata.
        None if not found or storage unavailable.
    """
    storage = get_storage_client()
    if not storage:
        return None

    try:
        if version is None:
            version = _get_latest_version(storage, job_id, doc_type)
            if version == 0:
                return None

        path = _version_path(job_id, doc_type, version)
        content_bytes = storage.download(path, bucket=storage._documents_bucket)
        return json.loads(content_bytes.decode("utf-8"))

    except Exception as e:
        logger.warning(f"[{job_id}] Failed to get {doc_type} v{version}: {e}")
        return None


def list_document_versions(
    job_id: str,
    doc_type: str,
) -> list[dict[str, Any]]:
    """List all available versions for a document with their metadata.

    Args:
        job_id: Job identifier.
        doc_type: Document type ("doc_0", "doc_1", etc.).

    Returns:
        List of version metadata dicts, newest first.
        Empty list if no versions or storage unavailable.
    """
    storage = get_storage_client()
    if not storage:
        return []

    try:
        latest = _get_latest_version(storage, job_id, doc_type)
        if latest == 0:
            return []

        versions = []
        # Iterate from latest down to oldest in window
        for v in range(latest, max(0, latest - MAX_VERSIONS), -1):
            version_doc = get_document_version(job_id, doc_type, v)
            if version_doc:
                meta = version_doc.get("version_metadata", {})
                versions.append({
                    "version": v,
                    "is_latest": v == latest,
                    **meta,
                })

        return versions

    except Exception as e:
        logger.warning(f"[{job_id}] Failed to list versions for {doc_type}: {e}")
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _version_path(job_id: str, doc_type: str, version: int) -> str:
    """Build storage path for a versioned document.

    Args:
        job_id: Job identifier.
        doc_type: Document type (e.g., "doc_3").
        version: Version number.

    Returns:
        Storage path string.
    """
    return f"research-jobs/{job_id}/{doc_type}/v{version}.json"


def _latest_pointer_path(job_id: str, doc_type: str) -> str:
    """Build storage path for the latest version pointer file.

    Args:
        job_id: Job identifier.
        doc_type: Document type.

    Returns:
        Storage path string.
    """
    return f"research-jobs/{job_id}/{doc_type}/latest.json"


def _get_latest_version(storage: Any, job_id: str, doc_type: str) -> int:
    """Get the current latest version number from the pointer file.

    Args:
        storage: Storage client.
        job_id: Job identifier.
        doc_type: Document type.

    Returns:
        Latest version number, or 0 if no versions exist yet.
    """
    try:
        path = _latest_pointer_path(job_id, doc_type)
        content = storage.download(path, bucket=storage._documents_bucket)
        pointer = json.loads(content.decode("utf-8"))
        return pointer.get("latest_version", 0)
    except Exception:
        return 0  # No versions exist yet


def _update_latest_pointer(
    storage: Any,
    job_id: str,
    doc_type: str,
    version: int,
) -> None:
    """Update the latest version pointer file.

    Args:
        storage: Storage client.
        job_id: Job identifier.
        doc_type: Document type.
        version: New latest version number.
    """
    path = _latest_pointer_path(job_id, doc_type)
    pointer = {
        "latest_version": version,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    content = json.dumps(pointer, indent=2).encode("utf-8")
    storage.upload_file(path, content, "application/json")


def _apply_rolling_window(
    storage: Any,
    job_id: str,
    doc_type: str,
    latest_version: int,
) -> None:
    """Drop the oldest version if we exceed MAX_VERSIONS.

    Args:
        storage: Storage client.
        job_id: Job identifier.
        doc_type: Document type.
        latest_version: Newly created version number.
    """
    oldest_to_keep = latest_version - MAX_VERSIONS + 1
    if oldest_to_keep <= 1:
        return  # Under the limit, nothing to drop

    version_to_drop = oldest_to_keep - 1
    if version_to_drop < 1:
        return

    drop_path = _version_path(job_id, doc_type, version_to_drop)
    try:
        storage.delete_file(drop_path, bucket=storage._documents_bucket)
        logger.info(f"[{job_id}] Dropped old version {doc_type} v{version_to_drop} (rolling window)")
    except Exception as e:
        # Non-fatal — old version already gone or delete failed
        logger.debug(f"[{job_id}] Could not drop old version {drop_path}: {e}")


def _load_version_content(
    storage: Any,
    job_id: str,
    doc_type: str,
    version: int,
) -> Optional[dict[str, Any]]:
    """Load the raw content dict for a given version (for diff computation).

    Args:
        storage: Storage client.
        job_id: Job identifier.
        doc_type: Document type.
        version: Version number to load.

    Returns:
        Content dict or None if version doesn't exist.
    """
    if version <= 0:
        return None
    try:
        path = _version_path(job_id, doc_type, version)
        content = storage.download(path, bucket=storage._documents_bucket)
        doc = json.loads(content.decode("utf-8"))
        return doc.get("data")
    except Exception:
        return None


def _build_version_metadata(
    version: int,
    trigger: TriggerType,
    content: dict[str, Any],
    previous_content: Optional[dict[str, Any]],
) -> DocumentVersionMetadata:
    """Build DocumentVersionMetadata for a new version.

    Computes source_count, claim_count, and diff_summary by comparing
    the new content to the previous version.

    Args:
        version: New version number.
        trigger: What triggered this version.
        content: New document content dict.
        previous_content: Previous version content (for diff), or None.

    Returns:
        DocumentVersionMetadata instance.
    """
    # Extract counts from new content
    source_count = _count_sources(content)
    claim_count = _count_claims(content)

    # Compute diff summary
    diff_summary = _compute_diff_summary(
        trigger=trigger,
        new_source_count=source_count,
        new_claim_count=claim_count,
        previous_content=previous_content,
    )

    return DocumentVersionMetadata(
        version=version,
        trigger=trigger,
        source_count=source_count,
        claim_count=claim_count,
        diff_summary=diff_summary,
    )


def _count_sources(content: dict[str, Any]) -> int:
    """Count sources in document content.

    Works for Source Ledger (has 'sources') and other docs (has 'source_count').

    Args:
        content: Document content dict.

    Returns:
        Source count.
    """
    if "sources" in content:
        return len(content["sources"])
    return content.get("source_count", 0)


def _count_claims(content: dict[str, Any]) -> int:
    """Count claims in document content.

    Works for Semantic Brief (has 'key_points') and Creator Brief (has 'core_facts').

    Args:
        content: Document content dict.

    Returns:
        Claim/key_point count.
    """
    # Semantic Brief uses key_points
    if "key_points" in content:
        return len(content["key_points"])
    # Creator Brief uses core_facts
    if "core_facts" in content:
        return len(content["core_facts"])
    # Source Ledger doesn't have claims directly
    return 0


def _compute_diff_summary(
    trigger: TriggerType,
    new_source_count: int,
    new_claim_count: int,
    previous_content: Optional[dict[str, Any]],
) -> str:
    """Generate a human-readable diff summary.

    Args:
        trigger: What triggered this version.
        new_source_count: Sources in new version.
        new_claim_count: Claims in new version.
        previous_content: Previous version content, or None.

    Returns:
        Human-readable diff summary string.
    """
    if previous_content is None:
        # Initial version
        parts = []
        if new_source_count:
            parts.append(f"{new_source_count} sources")
        if new_claim_count:
            parts.append(f"{new_claim_count} claims")
        return "Initial: " + ", ".join(parts) if parts else "Initial version"

    prev_sources = _count_sources(previous_content)
    prev_claims = _count_claims(previous_content)

    delta_sources = new_source_count - prev_sources
    delta_claims = new_claim_count - prev_claims

    parts = []
    if delta_sources != 0:
        sign = "+" if delta_sources > 0 else ""
        parts.append(f"{sign}{delta_sources} sources")
    if delta_claims != 0:
        sign = "+" if delta_claims > 0 else ""
        parts.append(f"{sign}{delta_claims} claims")

    if not parts:
        # No numerical change — describe by trigger mode
        mode_descriptions = {
            "deep_dive": "Deeper research directions added",
            "expand_sources": "Sources expanded",
            "deeper": "Deeper extraction applied",
            "different_angle": "New perspective applied",
            "custom": "Custom iteration applied",
            "initial_run": "No change",
        }
        return mode_descriptions.get(trigger, "Updated")

    return ", ".join(parts)


# =============================================================================
# Iteration Record Storage (Task 3.2.6)
# =============================================================================

def store_iteration_record(
    job_id: str,
    iterate_id: str,
    mode: str,
    versions_created: list[str],
    elapsed_seconds: float = 0.0,
) -> None:
    """Store a lightweight iteration record for the iteration history.

    Stored at: research-jobs/{job_id}/iterations/{iterate_id}.json

    Args:
        job_id: Job identifier.
        iterate_id: Unique iterate ID (iter_<timestamp>).
        mode: Iteration mode (deep_dive, expand_sources, etc.)
        versions_created: List of "doc_N vX" strings.
        elapsed_seconds: How long the iteration took.
    """
    storage = get_storage_client()
    if not storage:
        logger.debug(f"[{job_id}] No storage client; skipping iteration record for {iterate_id}")
        return

    path = f"research-jobs/{job_id}/iterations/{iterate_id}.json"
    record = {
        "iterate_id": iterate_id,
        "mode": mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "versions_created": versions_created,
        "elapsed_seconds": elapsed_seconds,
    }
    try:
        content = json.dumps(record, indent=2).encode("utf-8")
        storage.upload_file(path, content, "application/json")
        logger.debug(f"[{job_id}] Iteration record stored: {iterate_id}")
    except Exception as e:
        logger.warning(f"[{job_id}] Could not store iteration record {iterate_id}: {e}")
