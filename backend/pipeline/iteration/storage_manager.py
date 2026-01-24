"""
Store iteration outputs to GCS.

Handles uploading iteration documents to storage under iterations/{iteration_id}/.
"""

import json
from typing import Any

from loguru import logger

from backend.integrations.supabase_storage import get_storage_client
from backend.models.job_record import IterationOutputs


def store_iteration_docs(
    job_id: str,
    iteration_id: str,
    doc_0: dict[str, Any],
    doc_1: dict[str, Any],
    doc_2: dict[str, Any],
) -> IterationOutputs:
    """
    Store iteration documents to GCS under iterations/{iteration_id}/.

    Storage paths:
    - jobs/{job_id}/iterations/{iteration_id}/doc_0.json
    - jobs/{job_id}/iterations/{iteration_id}/doc_1.json
    - jobs/{job_id}/iterations/{iteration_id}/doc_2.json

    Args:
        job_id: Parent job ID
        iteration_id: Iteration identifier
        doc_0: Source Ledger document
        doc_1: Jump-Start document
        doc_2: Semantic Brief document

    Returns:
        IterationOutputs with storage paths and inline data fallback
    """
    logger.info(f"[{job_id}] Storing iteration {iteration_id} documents")

    storage = get_storage_client()
    base_path = f"jobs/{job_id}/iterations/{iteration_id}"

    paths: dict[str, str | None] = {
        "doc_0_path": None,
        "doc_1_path": None,
        "doc_2_path": None,
    }

    # Upload each document
    docs = [
        ("doc_0", doc_0),
        ("doc_1", doc_1),
        ("doc_2", doc_2),
    ]

    for doc_name, doc_data in docs:
        if doc_data:
            try:
                path = f"{base_path}/{doc_name}.json"
                content = json.dumps(doc_data, indent=2, ensure_ascii=False)
                storage.upload_file(path, content.encode("utf-8"), "application/json")
                paths[f"{doc_name}_path"] = path
                logger.debug(f"[{job_id}] Uploaded {doc_name} to {path}")
            except Exception as e:
                logger.warning(f"[{job_id}] Failed to upload {doc_name}: {e}")

    # Build outputs with paths and inline fallback
    outputs = IterationOutputs(
        doc_0_path=paths["doc_0_path"],
        doc_1_path=paths["doc_1_path"],
        doc_2_path=paths["doc_2_path"],
        # Include inline data as fallback if storage failed
        doc_0_inline=doc_0 if not paths["doc_0_path"] else None,
        doc_1_inline=doc_1 if not paths["doc_1_path"] else None,
        doc_2_inline=doc_2 if not paths["doc_2_path"] else None,
    )

    logger.info(
        f"[{job_id}] Iteration {iteration_id} stored: "
        f"{sum(1 for p in paths.values() if p)}/3 docs uploaded"
    )

    return outputs
