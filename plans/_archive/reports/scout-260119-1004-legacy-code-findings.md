# Legacy Code Findings - Quick Reference

**Audit Date:** 2026-01-19  
**Report:** `scout-260119-1004-legacy-pipeline-audit.md` (full details)

---

## What's Legacy (Should Be Removed)

### 1. Commented-out Stage Imports in `backend/worker.py` (Lines 119-125)
```python
# LEGACY DISABLED (D5) - These stages replaced by semantic pipeline
# stage_7_extraction,
# stage_7_5_timeline,
# stage_7_6_entities,
# stage_8_validation,
# stage_8_5_angle_discovery,
# stage_8_6_documentary_intelligence,
```
**Action:** ✂️ DELETE - These are dead imports that can never execute

### 2. Commented-out Stage Execution in `backend/worker.py` (Lines 227-240)
```python
# =====================================================================
# LEGACY STAGES DISABLED (D5 - Decision: 2026-01-17)
# run_stage_with_recovery(stage_7_extraction, ctx, "claim_extraction")
# extraction_group = StageGroup("extraction")
# [... more commented code ...]
# =====================================================================
```
**Action:** ✂️ DELETE CODE (but keep the comment block explaining D5 decision)

### 3. Empty `/backend/legacy/` Directory
**Action:** ✂️ DELETE - Contains only `__pycache__`

---

## What's NOT Legacy (Keep As-Is)

### ✅ Document Names: 00_MASTER_INDEX through 11_DOCUMENTARY_BLUEPRINT
**Location:** `backend/pipeline/stages/output.py`, `backend/integrations/google_drive_docs.py`

These are **actively used and user-facing**. System generates:
- Old format (00_-11_): For backward compatibility
- New format (20_-22_): From semantic pipeline

**Why keep:** Part of API contract, users expect these names

### ✅ Legacy Prompt Fallback Mechanism
**Location:** `backend/pipeline/prompts/semantic_extraction_prompt.py`

```python
def build_semantic_extraction_prompt(..., use_legacy_prompt: bool = False):
    if not use_legacy_prompt:
        try:
            return get_prompt_for_mode(...)  # NEW approach
        except (ImportError, ValueError):
            pass  # Fall back gracefully
```

**Why keep:** Defensive programming - graceful degradation if modern prompts unavailable

### ✅ Archive Docs Directory
**Location:** `/Archive Docs/` (54 historical files)

**Why keep:** Good historical reference, properly segregated from active code

### ✅ Legacy Test References
**Location:** `backend/tests/test_prompt_templates.py`

Pytest.skip() calls documenting legacy prompts without guardrails

**Why keep:** Technical debt tracking in tests, not in production code

---

## Dead Files (Already Removed)

These legacy stage files are **completely removed** ✅:
- ❌ `stage_7_extraction.py` - Not found (good)
- ❌ `stage_7_5_timeline.py` - Not found (good)
- ❌ `stage_7_6_entities.py` - Not found (good)
- ❌ `stage_8_validation.py` - Not found (good)
- ❌ `stage_8_5_angle_discovery.py` - Not found (good)
- ❌ `stage_8_6_documentary_intelligence.py` - Not found (good)

---

## Summary by Priority

### P1: Remove Immediately
- Delete commented imports in `worker.py` (lines 119-125) - 6 lines
- Delete commented stage execution in `worker.py` (lines 231-240) - 10 lines  
- Delete `/backend/legacy/` directory - empty, just clutter

**Impact:** Cleaner code, better readability, zero functional change

### P2: Keep (No Action)
- Document naming (00_-11_) - User-facing API
- Prompt fallback mechanism - Defensive programming
- Archive documentation - Historical reference
- Test references - Technical debt tracking

---

## Key Decision Referenced

**D5 (2026-01-17):** Legacy pipeline stages 7-8.6 completely disabled, replaced by semantic pipeline (stages A-E).

This is **properly documented** but commented code should be **removed** since:
1. Code can be found in git history
2. Comments in code clutter active logic
3. Dead code discourages maintenance

---

**See full report:** `scout-260119-1004-legacy-pipeline-audit.md`
