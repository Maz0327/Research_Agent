"""
Run storage manager - Store and retrieve run outputs.

Storage path convention:
    jobs/{job_id}/runs/{run_id}/doc_0.json          # Full Doc 0 (baseline)
    jobs/{job_id}/runs/{run_id}/doc_0_delta.json     # New sources only (expand runs)
    jobs/{job_id}/runs/{run_id}/doc_1.json           # Full Doc 1 or append section
    jobs/{job_id}/runs/{run_id}/doc_2.json           # Full Doc 2 or append section
    jobs/{job_id}/runs/{run_id}/producer_packet.json
    jobs/{job_id}/runs/{run_id}/booster_output.json

Merge logic:
    - Doc 0: get_merged_doc_0() — merges parent + delta for expand runs
    - Doc 1: get_merged_doc_1() — walks run chain, appends sections or replaces
    - Doc 2: get_merged_doc_2() — walks run chain, appends sections or replaces
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


def _load_run_doc(run: Run, doc_key: str, load_fn: Optional[callable] = None) -> Optional[dict[str, Any]]:
    """
    Load a specific doc (doc_1 or doc_2) from a run's outputs.

    Tries path first, falls back to inline.

    Args:
        run: Run object with outputs
        doc_key: 'doc_1' or 'doc_2'
        load_fn: Optional loader (defaults to load_run_document)

    Returns:
        Document dict or None
    """
    if not run.outputs:
        return None

    loader = load_fn or load_run_document
    path = getattr(run.outputs, f"{doc_key}_path", None)
    inline = getattr(run.outputs, f"{doc_key}_inline", None)

    if path:
        doc = loader(path)
        if doc:
            return doc

    return inline


def _build_run_chain(target_run: Run, all_runs: list[Run]) -> list[Run]:
    """
    Build ordered run chain from baseline to target_run.

    Walks parent_run_id links to build the chain, then returns
    them in chronological order (baseline first, target last).

    Args:
        target_run: The run to build the chain for
        all_runs: All runs for the job

    Returns:
        List of runs from baseline to target, in order
    """
    runs_by_id = {r.run_id: r for r in all_runs}

    chain = []
    current = target_run
    while current:
        chain.append(current)
        if current.parent_run_id and current.parent_run_id in runs_by_id:
            current = runs_by_id[current.parent_run_id]
        else:
            break

    chain.reverse()  # Baseline first, target last
    return chain


def get_merged_doc_1(
    target_run: Run,
    all_runs: list[Run],
    load_fn: Optional[callable] = None,
) -> dict[str, Any]:
    """
    Build complete Doc 1 (Jump-Start Directions) by walking the run chain.

    Merge rules:
    - Baseline: Use as foundation
    - EXPAND/REFINE (doc_1_is_append=True): Append section to Doc 1
    - REGENERATE (doc_1_is_append=False): Replace Doc 1 entirely

    Append sections are stored in a top-level "appended_sections" array.
    Key points, themes, tensions, and gaps from append sections are also
    merged into the main arrays for unified access.

    Args:
        target_run: The run whose Doc 1 to compute
        all_runs: All runs for this job (for chain walking)
        load_fn: Optional document loader function

    Returns:
        Complete merged Doc 1 dict (empty dict if not available)
    """
    chain = _build_run_chain(target_run, all_runs)
    if not chain:
        return {}

    merged: dict[str, Any] = {}

    for run in chain:
        if not run.outputs:
            continue
        if not run.outputs.has_doc_1():
            continue

        doc = _load_run_doc(run, "doc_1", load_fn)
        if not doc:
            continue

        is_append = run.outputs.doc_1_is_append

        if not is_append:
            # Full replacement (baseline or regenerate) — reset merged doc
            merged = doc.copy()
            # Ensure appended_sections array exists
            if "appended_sections" not in merged:
                merged["appended_sections"] = []
        else:
            # Append section — merge into existing doc
            if not merged:
                # No base doc yet, just store the section as-is
                merged = {
                    "appended_sections": [doc],
                    "is_merged": True,
                }
                continue

            # Add to appended_sections list
            sections = merged.get("appended_sections", [])
            sections.append(doc)
            merged["appended_sections"] = sections

            # Merge key data into main arrays for unified access
            section_type = doc.get("section_type", "")

            if section_type == "expansion":
                # Expand sections have new_key_points, new_themes, etc.
                _merge_list(merged, "key_points", doc.get("new_key_points", []))
                _merge_list(merged, "themes", doc.get("new_themes", []))
                _merge_list(merged, "tensions", doc.get("new_tensions", []))
                _merge_list(merged, "contradictions", doc.get("contradictions", []))

                # Gap updates replace matching gaps or add new ones
                for gap_update in doc.get("gap_updates", []):
                    _merge_gap_update(merged, gap_update)

                # Track reinforced themes
                _merge_list(merged, "reinforced_themes", doc.get("reinforced_themes", []))

            elif section_type == "refinement":
                # Refine sections have new_insights, new_themes, etc.
                _merge_list(merged, "key_points", doc.get("new_insights", []))
                _merge_list(merged, "themes", doc.get("new_themes", []))
                _merge_list(merged, "tensions", doc.get("new_tensions", []))
                _merge_list(merged, "gaps", doc.get("new_gaps", []))
                _merge_list(merged, "reframed_findings", doc.get("reframed_findings", []))

    # Mark as merged if we have append sections
    if merged.get("appended_sections"):
        merged["is_merged"] = True
        merged["merged_run_count"] = len(merged["appended_sections"]) + 1

    return merged


def get_merged_doc_2(
    target_run: Run,
    all_runs: list[Run],
    load_fn: Optional[callable] = None,
) -> dict[str, Any]:
    """
    Build complete Doc 2 (Semantic Brief) by walking the run chain.

    Merge rules:
    - Baseline: Use as foundation
    - EXPAND/REFINE (doc_2_is_append=True): Append section to Doc 2
    - REGENERATE (doc_2_is_append=False): Replace Doc 2 entirely

    Append sections are stored in a top-level "appended_sections" array.
    The narrative is built by concatenating section narratives.

    Args:
        target_run: The run whose Doc 2 to compute
        all_runs: All runs for this job (for chain walking)
        load_fn: Optional document loader function

    Returns:
        Complete merged Doc 2 dict (empty dict if not available)
    """
    chain = _build_run_chain(target_run, all_runs)
    if not chain:
        return {}

    merged: dict[str, Any] = {}

    for run in chain:
        if not run.outputs:
            continue
        if not run.outputs.has_doc_2():
            continue

        doc = _load_run_doc(run, "doc_2", load_fn)
        if not doc:
            continue

        is_append = run.outputs.doc_2_is_append

        if not is_append:
            # Full replacement (baseline or regenerate)
            merged = doc.copy()
            if "appended_sections" not in merged:
                merged["appended_sections"] = []
        else:
            # Append section
            if not merged:
                merged = {
                    "appended_sections": [doc],
                    "is_merged": True,
                }
                continue

            # Add to appended_sections list
            sections = merged.get("appended_sections", [])
            sections.append(doc)
            merged["appended_sections"] = sections

            # Append narrative to main narrative if present
            if doc.get("narrative"):
                heading = doc.get("heading", "## Additional Analysis")
                section_text = f"\n\n{heading}\n\n{doc['narrative']}"

                if "narrative" in merged:
                    merged["narrative"] = merged["narrative"] + section_text
                elif "brief" in merged:
                    merged["brief"] = merged["brief"] + section_text
                else:
                    merged["narrative"] = section_text

    # Mark as merged if we have append sections
    if merged.get("appended_sections"):
        merged["is_merged"] = True
        merged["merged_run_count"] = len(merged["appended_sections"]) + 1

    return merged


def _merge_list(target: dict, key: str, new_items: list) -> None:
    """Append new items to a list in the target dict."""
    if not new_items:
        return
    existing = target.get(key, [])
    existing.extend(new_items)
    target[key] = existing


def _merge_gap_update(target: dict, gap_update: dict) -> None:
    """
    Merge a gap update into the target's gaps list.

    If the gap_update references an existing gap_id, update it.
    Otherwise, add it as a new gap.
    """
    gaps = target.get("gaps", target.get("research_gaps", []))
    gap_id = gap_update.get("gap_id")

    if gap_id:
        # Try to find and update existing gap
        for i, gap in enumerate(gaps):
            if gap.get("gap_id") == gap_id:
                # Update status (e.g., "addressed", "partially_addressed")
                if gap_update.get("status"):
                    gaps[i]["status"] = gap_update["status"]
                if gap_update.get("resolution"):
                    gaps[i]["resolution"] = gap_update["resolution"]
                if gap_update.get("addressing_sources"):
                    existing_sources = gaps[i].get("addressing_sources", [])
                    existing_sources.extend(gap_update["addressing_sources"])
                    gaps[i]["addressing_sources"] = existing_sources
                return

    # Not found or no gap_id — add as new gap entry
    gaps.append(gap_update)
    if "gaps" in target:
        target["gaps"] = gaps
    else:
        target["research_gaps"] = gaps


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
