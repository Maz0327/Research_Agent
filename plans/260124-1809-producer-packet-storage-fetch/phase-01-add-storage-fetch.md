# Phase 1: Add Storage Fetch Logic

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: `plans/reports/brainstorm-260124-1809-producer-packet-empty-output.md`

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-01-24 |
| Priority | P1 |
| Status | Done |
| Effort | 20m |

## Problem

In `run_producer_task`, worker fetches `source_ledger` (Doc 0) for gating but never fetches `semantic_brief` (Doc 2) which producer pipeline needs.

## Related Files

- `backend/worker.py` - lines 1540-1576 (run_producer_task)

## Implementation Steps

### Step 1: Add semantic_brief fetch after gating check

Location: `backend/worker.py` after line 1556 (`job_dict["artifacts"] = artifacts_dict`)

```python
# Fetch semantic_brief (Doc 2) from storage if needed
doc_2_path = artifacts_dict.get("doc_2_path")
semantic_brief = artifacts_dict.get("semantic_brief")

# Check if semantic_brief has content
def _has_semantic_content(sb: dict | None) -> bool:
    if not sb or not isinstance(sb, dict):
        return False
    # Check for themes or key_points
    if sb.get("themes") or sb.get("key_points"):
        return True
    # Check nested data format
    data = sb.get("data")
    if isinstance(data, dict):
        if data.get("themes") or data.get("key_points"):
            return True
    return False

needs_doc2_fetch = doc_2_path and not _has_semantic_content(semantic_brief)

if needs_doc2_fetch:
    try:
        storage = get_storage_client()
        if storage:
            doc_2_data = storage.download_document(doc_2_path)
            artifacts_dict["semantic_brief"] = doc_2_data
            job_dict["artifacts"] = artifacts_dict
            logger.info(f"[{job_id}] Fetched semantic_brief from storage for producer")
        else:
            logger.warning(f"[{job_id}] Storage client unavailable - cannot fetch semantic_brief")
    except Exception as e:
        logger.warning(f"[{job_id}] Failed to fetch semantic_brief: {e}")
```

### Step 2: Verify import exists

Ensure `get_storage_client` is already imported (should be - used for source_ledger fetch).

## Todo

- [ ] Add semantic_brief fetch logic after line 1556
- [ ] Add helper function `_has_semantic_content`
- [ ] Test locally with mock data
- [ ] Verify no syntax errors

## Success Criteria

1. `semantic_brief` fetched from storage when `doc_2_path` exists
2. Existing inline artifact handling still works
3. No changes to gating logic
4. Graceful failure if storage unavailable

## Risks

- **Low:** Storage fetch adds network latency (~100-200ms)
- **Mitigation:** Already acceptable - same pattern used for source_ledger

## Unresolved Questions

None.
