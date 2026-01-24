# Brainstorm: Producer Packet Empty Output

**Date:** 2026-01-24
**Job ID:** 0085a89e-7987-4ffc-93d7-2a52ae37db5a
**Status:** Root cause identified

---

## Problem Statement

Producer Packet (Doc 3) returns empty/None values despite having 4 sources and valid Doc 0/1/2.

### Symptoms
- Story Core: All fields `None`
- Narrative Angles: Missing
- Opening Hooks: Missing
- Titles/Thumbnails: Missing
- Risk Assessment: Generic "cannot assess without context"

---

## Root Cause

**BUG: `semantic_brief` (Doc 2) not fetched from storage before producer pipeline.**

### Code Flow
1. Worker fetches job from database
2. Job has `artifacts.doc_2_path` (storage path) but `artifacts.semantic_brief` is `None`
3. Worker fetches `source_ledger` (Doc 0) for gating check ✅
4. Worker **does NOT** fetch `semantic_brief` (Doc 2) ❌
5. `run_producer_pipeline()` receives empty `semantic_brief`
6. LLM context shows `"(No themes)"`, `"(No key points)"`, `"(No tensions)"`
7. LLM produces empty/minimal output

### Location
- `backend/worker.py` lines 1540-1576
- Missing fetch between gating check (1559) and pipeline run (1576)

---

## Solution

Add `semantic_brief` fetch logic after gating passes:

```python
# After line 1555 in worker.py:
doc_2_path = artifacts_dict.get("doc_2_path")
semantic_brief = artifacts_dict.get("semantic_brief")
needs_doc2_fetch = doc_2_path and not semantic_brief

if needs_doc2_fetch:
    try:
        storage = get_storage_client()
        if storage:
            doc_2_data = storage.download_document(doc_2_path)
            artifacts_dict["semantic_brief"] = doc_2_data
            logger.info(f"[{job_id}] Fetched semantic_brief from storage for producer")
    except Exception as e:
        logger.warning(f"[{job_id}] Failed to fetch semantic_brief: {e}")

job_dict["artifacts"] = artifacts_dict
```

---

## Impact

- **Severity:** HIGH (Producer Packet completely broken for storage-based jobs)
- **Affected:** All jobs where docs stored externally (production)
- **Not Affected:** Jobs with inline artifacts (local testing)

---

## Validation

After fix:
1. Trigger producer on job 0085a89e-7987-4ffc-93d7-2a52ae37db5a
2. Verify Story Core populated
3. Verify narrative angles, hooks, titles generated
4. Check cardinality meets spec minimums (2+ angles, 2+ hooks, 2+ structures)

---

## Unresolved Questions

None - root cause is clear.
