"""Inline Edit Stage — Surgical section editing.

Temperature: 0.3 (controlled, surgical)

Edits a single section of any document without regenerating the entire thing.
1. Load current document version from version_manager
2. Extract target section by section_id
3. Prompt LLM to rewrite ONLY that section
4. Parse returned section, splice back into full document
5. Store as new version with trigger="inline_edit"
"""

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from backend.integrations.gemini_client import GeminiClient
from backend.pipeline.version_manager import (
    get_document_version,
    store_document_version,
)

INLINE_EDIT_TEMPERATURE = 0.3

INLINE_EDIT_ROLE = """You are a precise document editor. Your task is to rewrite ONLY the specified
section of the document according to the edit instruction.

CRITICAL RULES:
1. Return ONLY the rewritten section as a JSON object matching the section schema
2. Do NOT modify any other sections
3. Preserve all provenance IDs (claim_ids, source_ids) unless the edit changes which claims are referenced
4. Keep the same section_id
5. Follow the edit instruction exactly
"""


def run_inline_edit(
    job_id: str,
    doc_type: str,
    section_id: str,
    edit_instruction: str,
) -> tuple[dict[str, Any], float, list[str]]:
    """Edit a single section of a document.

    Args:
        job_id: Job identifier.
        doc_type: Document type (e.g. 'doc_5', 'doc_7').
        section_id: Section ID to edit (e.g. 'SECT_3', 'SCRIPT_SEC_4').
        edit_instruction: What to change (e.g. 'make more casual', 'expand').

    Returns:
        Tuple of (updated_document_dict, cost, warnings).

    Raises:
        ValueError: If document or section not found.
    """
    logger.info(f"[{job_id}] Inline edit: {doc_type}/{section_id} — {edit_instruction}")
    warnings: list[str] = []

    # Load current document version
    doc_data = get_document_version(job_id, doc_type)
    if not doc_data:
        raise ValueError(f"Document {doc_type} not found for job {job_id}")

    document = doc_data.get("data", doc_data)
    if isinstance(document, dict) and "data" in document:
        document = document["data"]

    # Find the sections array
    sections_key = _find_sections_key(document)
    if not sections_key:
        raise ValueError(f"No sections array found in {doc_type}")

    sections = document.get(sections_key, [])
    section_idx = None
    target_section = None

    for i, section in enumerate(sections):
        sid = section.get("section_id", "")
        if sid == section_id:
            section_idx = i
            target_section = section
            break

    if target_section is None:
        raise ValueError(f"Section {section_id} not found in {doc_type}")

    # Build prompt for surgical edit
    prompt = _build_inline_edit_prompt(
        document=document,
        section=target_section,
        section_id=section_id,
        edit_instruction=edit_instruction,
    )

    # LLM call
    client = GeminiClient()
    response = client.generate_json(
        prompt=prompt,
        system_message=INLINE_EDIT_ROLE,
        temperature=INLINE_EDIT_TEMPERATURE,
    )

    if response.get("error"):
        raise ValueError(f"LLM error: {response['error']}")

    raw_section = response.get("data", {})
    if not raw_section:
        raise ValueError("LLM returned empty section")

    # Ensure section_id is preserved
    raw_section["section_id"] = section_id

    cost = response.get("cost", 0.0)

    # Splice the edited section back into the document
    updated_document = dict(document)
    updated_sections = list(sections)
    updated_sections[section_idx] = raw_section
    updated_document[sections_key] = updated_sections

    # Store as new version
    version_num, storage_path = store_document_version(
        job_id=job_id,
        doc_type=doc_type,
        content=updated_document,
        trigger="inline_edit",
    )

    logger.info(
        f"[{job_id}] Inline edit complete: {doc_type}/{section_id} → v{version_num}"
    )

    return updated_document, cost, warnings


def _find_sections_key(document: dict) -> str | None:
    """Find the sections array key in a document.

    Different document types use different key names for their sections array.

    Args:
        document: Document dict.

    Returns:
        Key name for sections array, or None.
    """
    # Ordered by likelihood
    for key in ("sections", "platforms", "hook_options", "core_facts"):
        if key in document and isinstance(document[key], list):
            return key
    return None


def _build_inline_edit_prompt(
    document: dict,
    section: dict,
    section_id: str,
    edit_instruction: str,
) -> str:
    """Build the inline edit prompt.

    Args:
        document: Full document dict (for context).
        section: The section to edit.
        section_id: Section ID.
        edit_instruction: Edit instruction.

    Returns:
        Complete prompt string.
    """
    doc_type = document.get("document_type", "unknown")
    topic = document.get("topic", "")

    # Truncate full doc context to avoid token bloat
    context_keys = ["title", "topic", "tone", "target_length", "story_arc"]
    context = {k: document[k] for k in context_keys if k in document}

    return f"""
DOCUMENT TYPE: {doc_type}
TOPIC: {topic}
CONTEXT: {json.dumps(context)}

SECTION TO EDIT (section_id: {section_id}):
{json.dumps(section, indent=2)}

EDIT INSTRUCTION: {edit_instruction}

Rewrite this section according to the instruction.
Return the complete rewritten section as a JSON object with the same keys.
Preserve the section_id as "{section_id}".
Preserve all claim_ids and source_ids unless the edit instruction requires changing them.
"""
