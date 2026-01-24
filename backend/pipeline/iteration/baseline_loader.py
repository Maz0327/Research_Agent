"""
Load baseline documents and extractions for iteration.

Handles loading from GCS storage or inline artifacts fallback.
"""

import json
from typing import Any, TypedDict
from loguru import logger

from backend.integrations.supabase_storage import get_storage_client
from backend.models.semantic_units import SemanticExtractionResult


class BaselineData(TypedDict):
    """Baseline data loaded from completed job."""

    doc_0: dict[str, Any]  # Source Ledger
    doc_1: dict[str, Any]  # Jump-Start
    doc_2: dict[str, Any]  # Semantic Brief
    extractions: list[dict[str, Any]]  # Semantic extraction results
    topic: str  # Original research topic
    source_urls: list[str]  # All URLs from baseline


def load_baseline(job_id: str, artifacts: dict[str, Any], config: dict[str, Any] | None = None) -> BaselineData:
    """
    Load baseline documents from storage or inline artifacts.

    Priority: Storage paths > Inline data

    Args:
        job_id: Job ID for logging
        artifacts: Job artifacts dict
        config: Job config dict (for topic)

    Returns:
        BaselineData with all documents and extractions

    Raises:
        ValueError: If required baseline data missing
    """
    logger.info(f"[{job_id}] Loading baseline data for iteration")

    # Load documents
    doc_0 = _load_document(job_id, artifacts, "doc_0", "source_ledger")
    doc_1 = _load_document(job_id, artifacts, "doc_1", "jump_start")
    doc_2 = _load_document(job_id, artifacts, "doc_2", "semantic_brief")

    if not doc_0:
        raise ValueError(f"[{job_id}] Baseline Doc 0 (Source Ledger) not found")
    if not doc_1:
        raise ValueError(f"[{job_id}] Baseline Doc 1 (Jump-Start) not found")
    if not doc_2:
        raise ValueError(f"[{job_id}] Baseline Doc 2 (Semantic Brief) not found")

    # Load extractions
    extractions = artifacts.get("semantic_extractions", [])
    if not extractions:
        logger.warning(f"[{job_id}] No semantic extractions found in baseline")

    # Get topic from config or doc_0
    topic = ""
    if config:
        topic = config.get("topic", "") or config.get("prompt", "")
    if not topic and doc_0:
        # Try to get from doc_0 metadata
        topic = doc_0.get("topic", "") or doc_0.get("research_topic", "")

    # Extract source URLs from Doc 0
    source_urls = extract_source_urls(doc_0)

    logger.info(
        f"[{job_id}] Baseline loaded: {len(extractions)} extractions, "
        f"{len(source_urls)} sources, topic='{topic[:50]}...'"
    )

    return BaselineData(
        doc_0=doc_0,
        doc_1=doc_1,
        doc_2=doc_2,
        extractions=extractions,
        topic=topic,
        source_urls=source_urls,
    )


def _load_document(
    job_id: str,
    artifacts: dict[str, Any],
    path_key: str,
    inline_key: str,
) -> dict[str, Any] | None:
    """
    Load a document from storage path or inline data.

    Args:
        job_id: Job ID for logging
        artifacts: Artifacts dict
        path_key: Key for storage path (e.g., "doc_0_path")
        inline_key: Key for inline data (e.g., "source_ledger")

    Returns:
        Document dict or None if not found
    """
    # Try storage path first
    storage_path = artifacts.get(f"{path_key}_path")
    if storage_path:
        try:
            storage = get_storage_client()
            content = storage.download_file(storage_path)
            if content:
                doc = json.loads(content)
                logger.debug(f"[{job_id}] Loaded {path_key} from storage: {storage_path}")
                return doc
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to load {path_key} from storage: {e}")

    # Fallback to inline data
    inline_data = artifacts.get(inline_key)
    if inline_data:
        logger.debug(f"[{job_id}] Using inline {inline_key}")
        return inline_data if isinstance(inline_data, dict) else {}

    return None


def extract_source_urls(doc_0: dict[str, Any]) -> list[str]:
    """
    Extract all source URLs from Source Ledger (Doc 0).

    Args:
        doc_0: Source Ledger document

    Returns:
        List of source URLs
    """
    urls: list[str] = []

    # Try different possible structures
    sources = doc_0.get("sources", [])
    if not sources:
        sources = doc_0.get("source_entries", [])

    for source in sources:
        url = source.get("url") or source.get("source_url")
        if url:
            urls.append(url)

    return urls


def reconstruct_source_packages(doc_0: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Reconstruct minimal source info from Doc 0 for re-extraction.

    This extracts enough metadata to re-run extraction on sources.

    Args:
        doc_0: Source Ledger document

    Returns:
        List of source package-like dicts with source_id, url, title, analysis_mode
    """
    packages: list[dict[str, Any]] = []

    sources = doc_0.get("sources", []) or doc_0.get("source_entries", [])

    for source in sources:
        source_id = source.get("source_id") or source.get("id")
        url = source.get("url") or source.get("source_url")
        title = source.get("title", "Unknown")
        source_type = source.get("source_type", "article")

        # Map source_type to analysis_mode
        if source_type == "youtube":
            analysis_mode = "transcript_grounded"
        elif source_type == "text_provided":
            analysis_mode = "text_provided"
        elif source_type == "screenshot":
            analysis_mode = "ocr_extracted"
        else:
            analysis_mode = "article_fetched"

        packages.append({
            "source_id": source_id,
            "url": url,
            "title": title,
            "source_type": source_type,
            "analysis_mode": analysis_mode,
        })

    return packages
