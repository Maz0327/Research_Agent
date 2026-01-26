"""
Run storage manager - Store and retrieve run outputs.

Storage path convention:
    jobs/{job_id}/runs/{run_id}/doc_0.json
    jobs/{job_id}/runs/{run_id}/doc_1.json
    jobs/{job_id}/runs/{run_id}/doc_2.json
    jobs/{job_id}/runs/{run_id}/doc_0_delta.json  (for add_sources runs)
    jobs/{job_id}/runs/{run_id}/producer_packet.json
    jobs/{job_id}/runs/{run_id}/booster_output.json
"""

import json
from typing import Any, Optional

from loguru import logger

from backend.integrations.supabase_storage import get_storage_client
from backend.models.run_models import (
    Run,
    RunOutputs,
    RunType,
)


def store_run_outputs(
    job_id: str,
    run: Run,
    doc_0: Optional[dict[str, Any]] = None,
    doc_1: Optional[dict[str, Any]] = None,
    doc_2: Optional[dict[str, Any]] = None,
    is_doc_0_delta: bool = False,
    parent_doc_0_path: Optional[str] = None,
    new_source_ids: Optional[list[str]] = None,
) -> RunOutputs:
    """
    Store run outputs to GCS.

    Args:
        job_id: Parent job ID
        run: Run object
        doc_0: Source Ledger document (None to skip)
        doc_1: Jump-Start document (None to skip)
        doc_2: Semantic Brief document (None to skip)
        is_doc_0_delta: True if doc_0 only contains new sources (add_sources runs)
        parent_doc_0_path: Path to parent Doc 0 for merging (if delta)
        new_source_ids: Source IDs added in this run

    Returns:
        RunOutputs with storage paths
    """
    logger.info(f"[{job_id}] Storing run {run.run_id} outputs")

    storage = get_storage_client()
    base_path = f"jobs/{job_id}/runs/{run.run_id}"

    outputs = RunOutputs(
        doc_0_is_delta=is_doc_0_delta,
        doc_0_parent_path=parent_doc_0_path,
        new_source_ids=new_source_ids,
    )

    # Store Doc 0
    if doc_0 is not None:
        doc_0_filename = "doc_0_delta.json" if is_doc_0_delta else "doc_0.json"
        path = f"{base_path}/{doc_0_filename}"
        try:
            content = json.dumps(doc_0, indent=2, ensure_ascii=False)
            storage.upload_file(path, content.encode("utf-8"), "application/json")
            outputs.doc_0_path = path
            logger.debug(f"[{job_id}] Stored Doc 0 at {path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store Doc 0: {e}")
            outputs.doc_0_inline = doc_0

    # Store Doc 1
    if doc_1 is not None:
        path = f"{base_path}/doc_1.json"
        try:
            content = json.dumps(doc_1, indent=2, ensure_ascii=False)
            storage.upload_file(path, content.encode("utf-8"), "application/json")
            outputs.doc_1_path = path
            logger.debug(f"[{job_id}] Stored Doc 1 at {path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store Doc 1: {e}")
            outputs.doc_1_inline = doc_1

    # Store Doc 2
    if doc_2 is not None:
        path = f"{base_path}/doc_2.json"
        try:
            content = json.dumps(doc_2, indent=2, ensure_ascii=False)
            storage.upload_file(path, content.encode("utf-8"), "application/json")
            outputs.doc_2_path = path
            logger.debug(f"[{job_id}] Stored Doc 2 at {path}")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store Doc 2: {e}")
            outputs.doc_2_inline = doc_2

    stored_count = sum([
        1 if outputs.doc_0_path else 0,
        1 if outputs.doc_1_path else 0,
        1 if outputs.doc_2_path else 0,
    ])
    logger.info(f"[{job_id}] Run {run.run_id} stored: {stored_count}/3 docs uploaded")

    return outputs


def load_run_document(path: str) -> Optional[dict[str, Any]]:
    """
    Load a document from GCS.

    Args:
        path: Storage path

    Returns:
        Document dict or None if not found
    """
    if not path:
        return None

    try:
        storage = get_storage_client()
        content = storage.download_file(path)
        if content:
            return json.loads(content.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Failed to load document from {path}: {e}")

    return None


def get_merged_doc_0(run: Run, load_fn: Optional[callable] = None) -> dict[str, Any]:
    """
    Get the complete Doc 0 for a run, merging parent + delta if needed.

    For add_sources runs where doc_0_is_delta=True, this merges the parent
    Doc 0 with the delta to produce a complete Source Ledger.

    Args:
        run: Run object with outputs
        load_fn: Optional document loader function (defaults to load_run_document)

    Returns:
        Complete Doc 0 dict (empty dict if not available)
    """
    if not run.outputs:
        return {}

    outputs = run.outputs
    loader = load_fn or load_run_document

    # If not a delta, just return the doc directly
    if not outputs.doc_0_is_delta:
        if outputs.doc_0_path:
            doc = loader(outputs.doc_0_path)
            return doc if doc else (outputs.doc_0_inline or {})
        return outputs.doc_0_inline or {}

    # Delta run: need to merge parent + delta
    parent_doc_0: dict[str, Any] = {}
    if outputs.doc_0_parent_path:
        parent_doc_0 = loader(outputs.doc_0_parent_path) or {}

    delta_doc_0: dict[str, Any] = {}
    if outputs.doc_0_path:
        delta_doc_0 = loader(outputs.doc_0_path) or {}
    elif outputs.doc_0_inline:
        delta_doc_0 = outputs.doc_0_inline

    # Merge: parent sources + new sources
    parent_sources = parent_doc_0.get("sources", [])
    new_sources = delta_doc_0.get("sources", [])

    parent_manifest = parent_doc_0.get("source_manifest", [])
    new_manifest = delta_doc_0.get("source_manifest", [])

    merged = {
        **parent_doc_0,  # Start with parent
        "sources": parent_sources + new_sources,
        "source_manifest": parent_manifest + new_manifest,
    }

    # Update counts
    merged["source_count"] = len(merged["sources"])
    merged["ingested_count"] = sum(
        1 for s in merged["sources"]
        if s.get("status") == "ingested"
    )
    merged["failed_count"] = sum(
        1 for s in merged["sources"]
        if s.get("status") == "failed"
    )

    # Mark as merged
    merged["is_merged"] = True
    merged["merged_from_runs"] = [
        outputs.doc_0_parent_path,
        outputs.doc_0_path,
    ]

    return merged


def store_run_producer(
    job_id: str,
    run_id: str,
    producer_packet: dict[str, Any],
    markdown: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Store producer packet for a run.

    Args:
        job_id: Parent job ID
        run_id: Run ID
        producer_packet: Producer packet data
        markdown: Rendered markdown

    Returns:
        Tuple of (packet_path, md_path) or (None, None) if failed
    """
    storage = get_storage_client()
    base_path = f"jobs/{job_id}/runs/{run_id}"

    packet_path = None
    md_path = None

    # Store JSON
    try:
        path = f"{base_path}/producer_packet.json"
        content = json.dumps(producer_packet, indent=2, ensure_ascii=False)
        storage.upload_file(path, content.encode("utf-8"), "application/json")
        packet_path = path
    except Exception as e:
        logger.warning(f"[{job_id}] Failed to store producer packet: {e}")

    # Store markdown
    if markdown:
        try:
            path = f"{base_path}/producer_packet.md"
            storage.upload_file(path, markdown.encode("utf-8"), "text/markdown")
            md_path = path
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store producer markdown: {e}")

    return packet_path, md_path


def store_run_booster(
    job_id: str,
    run_id: str,
    booster_output: dict[str, Any],
    markdown: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Store booster output for a run.

    Args:
        job_id: Parent job ID
        run_id: Run ID
        booster_output: Booster output data
        markdown: Rendered markdown expansion

    Returns:
        Tuple of (output_path, md_path) or (None, None) if failed
    """
    storage = get_storage_client()
    base_path = f"jobs/{job_id}/runs/{run_id}"

    output_path = None
    md_path = None

    # Store JSON
    try:
        path = f"{base_path}/booster_output.json"
        content = json.dumps(booster_output, indent=2, ensure_ascii=False)
        storage.upload_file(path, content.encode("utf-8"), "application/json")
        output_path = path
    except Exception as e:
        logger.warning(f"[{job_id}] Failed to store booster output: {e}")

    # Store markdown
    if markdown:
        try:
            path = f"{base_path}/booster_expansion.md"
            storage.upload_file(path, markdown.encode("utf-8"), "text/markdown")
            md_path = path
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to store booster markdown: {e}")

    return output_path, md_path
