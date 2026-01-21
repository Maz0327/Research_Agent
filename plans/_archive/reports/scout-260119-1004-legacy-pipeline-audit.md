# Legacy Pipeline Code Audit Report

**Date:** 2026-01-19  
**Time:** 10:04 UTC  
**Audit Scope:** Complete Research_Agent codebase  
**Status:** ✅ COMPREHENSIVE AUDIT COMPLETE

---

## Executive Summary

The Research Agent codebase contains **multiple references to legacy pipeline code** that has been intentionally disabled per Decision D5 (2026-01-17). The legacy code exists in three forms:

1. **Commented-out stage imports and function calls** (actively disabled)
2. **Legacy document naming constants** (actively used for backward compatibility)
3. **Legacy prompt fallback mechanisms** (defensive backward compatibility)
4. **Legacy artifact generation functions** (defensive fallback)
5. **Archive documentation** (historical context, not in active code)

**Key Finding:** The legacy code is **not fully removed** but **intentionally disabled with clear documentation**. All disabled code is properly marked with "LEGACY DISABLED (D5)" comments.

---

## 1. NUMERIC STAGE NAMING PATTERNS

### Active (Currently Used)

The pipeline uses **numeric naming** for stages 0-10:
- `stage_0_initialize` - Initialization
- `stage_1_planning` - Planning  
- `stage_2_research_mapping` - Research mapping
- `stage_3_source_shortlist` - Source discovery
- `stage_3_5_quality_gate` - Quality filtering
- `stage_4_youtube_enumeration` - YouTube discovery
- `stage_5_transcripts` - Transcript acquisition
- `stage_6_web_capture` - Web source capture
- `stage_6_5_reddit` - Reddit collection
- `stage_9_drive_upload` - Drive output
- `stage_10_completion` - Completion

**Status:** ✅ These are CURRENT and in use. Not legacy.

### Disabled/Commented Out (Legacy)

The following stages are **intentionally disabled**:
- `stage_7_extraction` (line 120)
- `stage_7_5_timeline` (line 121)
- `stage_7_6_entities` (line 122)
- `stage_8_validation` (line 123)
- `stage_8_5_angle_discovery` (line 124)
- `stage_8_6_documentary_intelligence` (line 125)
- `run_extraction_stages_parallel` (line 142)

**Location:** `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py`  
**Lines:** 119-143  
**Reason:** Replaced by semantic pipeline (Phase 2A: stages source_identity, semantic_extraction, gap_analysis, semantic_synthesis, document_assembly)  
**Comment:** "LEGACY DISABLED (D5) - These stages replaced by semantic pipeline"  
**Status:** ⚠️ **SHOULD BE REMOVED** - Dead code cluttering imports

---

## 2. LEGACY DOCUMENT NAMING (00_MASTER_INDEX ... 11_DOCUMENTARY_BLUEPRINT)

### Currently Active References

The following legacy document names are **actively used**:

| Document Name | File | Lines | Purpose | Status |
|---|---|---|---|---|
| `00_MASTER_INDEX` | `backend/pipeline/stages/output.py` | 33 | Master index creation | Active |
| `01_RESEARCH_MAP` | `backend/pipeline/stages/output.py` | 34 | Research map output | Active |
| `02_SOURCE_SHORTLIST` | `backend/pipeline/stages/output.py` | 35 | Source list output | Active |
| `03_YOUTUBE_INDEX` | `backend/pipeline/stages/output.py` | 36 | YouTube index | Active |
| `04_TRANSCRIPTS` | `backend/pipeline/stages/output.py` | 37 | Transcript documents | Active |
| `05_WEB_EXTRACTS` | `backend/pipeline/stages/output.py` | 38 | Web source extracts | Active |
| `06_QUOTE_BANK` | `backend/pipeline/stages/output.py` | 39 | Quote collection | Active |
| `07_CLAIMS_LEDGER` | `backend/pipeline/stages/output.py` | 40 | Claims ledger | Active |
| `08_EVIDENCE_TABLE` | `backend/pipeline/stages/output.py` | 41 | Evidence table | Active |
| `09_MISSING_ANGLES` | `backend/pipeline/stages/output.py` | 42 | Missing angles analysis | Active |
| `10_NOTEBOOKLM_PACKET` | `backend/pipeline/stages/output.py` | 47 | NotebookLM output | Conditional |
| `11_DOCUMENTARY_BLUEPRINT` | `backend/pipeline/stages/output.py` | 49 | Documentary blueprint | Conditional |

### Files Using Legacy Document Names

1. **`backend/pipeline/stages/output.py`** (Lines 33-49)
   - Creates doc_contents dictionary with all 09_* naming
   - Also handles newer docs (20_SOURCE_LEDGER, 21_JUMP_START, 22_SEMANTIC_BRIEF)
   - **Assessment:** Actively used, not deprecated

2. **`backend/integrations/google_drive_docs.py`** (Lines 24-35)
   - DOC_NAMES constant lists 00_MASTER_INDEX through 09_MISSING_ANGLES
   - **Assessment:** Reference constant, actively used

3. **`backend/pipeline/document_helpers.py`**
   - `generate_master_index()` function (lines 11-41)
   - `generate_transcripts_md()` function (lines 44-68)
   - `generate_web_extracts_md()` function (lines 71-99)
   - **Assessment:** Helper functions, actively used

4. **`backend/scripts/test_google_write.py`** (Line 105)
   - Test script creates "00_MASTER_INDEX" document
   - **Assessment:** Test utility, not production code

5. **`App Improvement Strategy Evaluation (3).md`** & **`App Improvement Strategy Evaluation.md`**
   - Archive Docs referencing legacy output format
   - **Assessment:** Historical documentation, not active code

### Status Assessment

✅ **These are NOT legacy** - they are the **current output document naming convention**. They represent the OLD pipeline outputs that coexist with the NEW semantic pipeline outputs (Doc 0, 1, 2 prefixed as 20_, 21_, 22_).

The system maintains backward compatibility by generating both:
- **Old format:** 00_MASTER_INDEX through 11_DOCUMENTARY_BLUEPRINT
- **New format:** 20_SOURCE_LEDGER (Doc 0), 21_JUMP_START (Doc 1), 22_SEMANTIC_BRIEF (Doc 2)

---

## 3. LEGACY PROMPT MECHANISM

### Location
`backend/pipeline/prompts/semantic_extraction_prompt.py` (Lines 605-695)

### References

| Function | Lines | Type | Status |
|---|---|---|---|
| `get_confidence_ceiling_for_mode()` | 605-616 | DEPRECATED | Has replacement |
| `build_semantic_extraction_prompt()` | 619-695 | Current | Has fallback |
| Parameter: `use_legacy_prompt` | 625 | Fallback | Defensive |

### Code Details

**Deprecated Function:**
```python
def get_confidence_ceiling_for_mode(analysis_mode: str) -> str:
    """
    DEPRECATED: Use backend.pipeline.mode_selector.get_confidence_ceiling_string() instead.
    """
    return get_confidence_ceiling_string(analysis_mode)  # Delegates to new function
```

**Fallback Mechanism:**
```python
def build_semantic_extraction_prompt(
    ...
    use_legacy_prompt: bool = False,  # Backward compatibility parameter
) -> str:
    """
    This function now delegates to mode-specific prompts in prompts/modes/
    unless use_legacy_prompt=True is specified.
    """
    if not use_legacy_prompt:
        try:
            return get_prompt_for_mode(...)  # NEW approach
        except (ImportError, ValueError):
            pass  # Fall back to legacy
    
    # Legacy inline prompt (backward compatibility)
```

### Assessment

✅ **Properly handled defensive fallback.** The legacy prompt system:
- Is marked DEPRECATED with clear replacement path
- Has a safe fallback mechanism (if new prompt dispatch fails)
- Is NOT actively called in current code (use_legacy_prompt defaults to False)
- Allows graceful degradation if mode-specific prompts fail

---

## 4. LEGACY ARTIFACT GENERATION (Fallback Comment)

### Location
`backend/pipeline/stages/initialization.py` (Line 77)

### Reference
```python
def _build_inline_artifacts(ctx: PipelineContext) -> dict:
    """Build artifacts dict with inline document data (fallback/legacy)."""
```

### Assessment

✅ **Fallback mechanism for document storage.** When Supabase Storage is unavailable, system falls back to inline artifacts. This is:
- Correctly labeled "fallback/legacy"
- Used only when primary storage unavailable
- Provides graceful degradation
- Not actively causing problems

---

## 5. LEGACY TEST REFERENCES

### Location
`backend/tests/test_prompt_templates.py`

### References
- Line: "Identify legacy prompts missing guardrails"
- Lines: Multiple pytest.skip() calls for legacy prompts
  - `research_starter_prompt` (needs Source Identity Lock)
  - `structure_analysis_prompt` (needs Confidence Ceiling)

### Assessment

✅ **Test documentation of known gaps.** Tests explicitly document which legacy prompts lack guardrails. This is:
- Used for test tracking, not production
- Clearly marked as legacy
- Provides visibility into technical debt

---

## 6. ARCHIVE DIRECTORIES

### Location 1: `/Users/maz/Documents/GitHub/Research_Agent/Archive Docs/`

**Contents:** 54 files including:
- `AI Research Assistant Blueprint Chat.md`
- `Conversation_Notes_1.md`, `Conversation_Notes_2.md` (900K+ each)
- `IMPLEMENTATION_SUMMARY.md`
- `MEMORY_FIX_SUMMARY.md`
- Subdirectories: `authoritative-examples/`, `authoritative-spec/`, `claude-rules/`

**Assessment:** 
- ✅ Properly archived outside main code
- Contains historical conversation logs and old specs
- Not imported or referenced by active code
- Safe to leave as-is for historical reference

### Location 2: `/Users/maz/Documents/GitHub/Research_Agent/backend/legacy/`

**Contents:** Empty (only `__pycache__`)

**Assessment:**
- ✅ Directory exists but unused
- Could be removed if no longer needed
- Or could be removed after legacy stages removed

---

## 7. PIPELINE STRUCTURE ANALYSIS

### Current Stage Files (Active)
```
backend/pipeline/stages/
├── __init__.py              # Exports 20+ stage functions
├── initialization.py        # stage_0_initialize, stage_10_completion
├── planning.py             # stage_1_planning, stage_2_research_mapping
├── discovery.py            # stage_3_source_shortlist, stage_3_5_quality_gate
├── youtube.py              # stage_4_youtube_enumeration, stage_5_transcripts
├── web_capture.py          # stage_6_web_capture, stage_6_5_reddit
├── output.py               # stage_9_drive_upload (HANDLES LEGACY NAMING)
├── semantic_extraction.py  # stage_semantic_extraction (NEW PIPELINE)
├── semantic_synthesis.py   # stage_semantic_synthesis (NEW PIPELINE)
├── document_assembly.py    # stage_document_assembly (NEW PIPELINE)
└── [8 more semantic/validation files]
```

### Missing Legacy Stage Files
The following legacy stage files are **completely absent** (properly removed):
- `stage_7_extraction.py` ❌ Not found
- `stage_7_5_timeline.py` ❌ Not found
- `stage_7_6_entities.py` ❌ Not found
- `stage_8_validation.py` ❌ Not found
- `stage_8_5_angle_discovery.py` ❌ Not found
- `stage_8_6_documentary_intelligence.py` ❌ Not found

**Assessment:** ✅ Legacy stage FILES are completely removed. Only REFERENCES in comments remain.

---

## 8. IMPORTS AND DISABLED CODE

### File: `backend/worker.py`

**Disabled Imports (Lines 119-125):**
```python
# LEGACY DISABLED (D5) - These stages replaced by semantic pipeline
# stage_7_extraction,
# stage_7_5_timeline,
# stage_7_6_entities,
# stage_8_validation,
# stage_8_5_angle_discovery,
# stage_8_6_documentary_intelligence,
```

**Disabled Function Call (Lines 231-240):**
```python
# LEGACY STAGES DISABLED (D5 - Decision: 2026-01-17)
# Legacy pipeline preserved but completely disabled.
# Semantic pipeline (stages A-E above) now produces Doc 0/1/2.
# run_stage_with_recovery(stage_7_extraction, ctx, "claim_extraction")
# extraction_group = StageGroup("extraction")
# [... more disabled code ...]
```

**Assessment:** 
⚠️ **This is dead code that should be cleaned up.** While clearly marked and documented, these commented lines:
- Clutter the imports
- Waste context when reading worker.py
- Won't be imported anyway (can be safely removed)
- Document is clear about why (D5 decision)

### File: `backend/pipeline/stages/__init__.py`

**Comment (Line 4):**
```python
"""Pipeline stages module - Semantic Pipeline (Phase 2-10).

Each stage function takes a PipelineContext and modifies it in place.
Legacy stages (7-8.6) removed per D5 decision (2026-01-17).
"""
```

**Assessment:** ✅ Clear documentation that legacy stages are removed by design.

---

## SUMMARY TABLE

| Category | Finding | Status | Action |
|---|---|---|---|
| **Numeric Stage Names (0-10)** | Currently active, not legacy | ✅ Keep | None |
| **Numeric Stage Names (7-8.6)** | Completely disabled, commented out | ⚠️ Remove comments | Delete dead code |
| **Legacy Document Names (00_-11_)** | Currently active, backward compat | ✅ Keep | None |
| **New Document Names (20_-22_)** | Semantic pipeline outputs | ✅ Keep | None |
| **Legacy Prompt Fallback** | Defensive, properly designed | ✅ Keep | None |
| **Fallback Artifact Gen** | Graceful degradation | ✅ Keep | None |
| **Archive Docs** | Historical, properly archived | ✅ Keep | None |
| **Empty Legacy Directory** | Unused | ⚠️ Remove | Delete /backend/legacy/ |
| **Test Legacy References** | Documentation, not production | ✅ Keep | None |

---

## RECOMMENDATIONS

### PRIORITY 1: Remove Dead Code (Cleanups)

1. **Delete commented-out stage imports from `backend/worker.py` (Lines 119-125)**
   - These imports can never execute
   - Clears ~6 lines of clutter
   - Cost: Minimal, highly safe

2. **Delete commented-out stage execution from `backend/worker.py` (Lines 231-240)**
   - This code path is unreachable
   - Clears ~10 lines, improves readability
   - Cost: Minimal, highly safe
   - Recommendation: Keep the comment block explaining D5 decision, just remove the actual code

3. **Delete `/backend/legacy/` directory**
   - Empty except for __pycache__
   - Cost: Minimal, zero impact
   - Keeps codebase clean

### PRIORITY 2: Keep As-Is (No Action Needed)

1. **Legacy document naming constants (00_MASTER_INDEX, etc.)**
   - Still used for backward compatibility
   - Part of current API contract
   - Users expect these document names in Drive output
   - Keep unchanged

2. **Legacy prompt fallback mechanism**
   - Defensive programming best practice
   - If mode-specific prompts fail, system gracefully degrades
   - Keep unchanged

3. **Archive Docs directory**
   - Good historical reference
   - Properly segregated from active code
   - Keep as-is for historical context

---

## DETAILED FINDINGS

### Finding 1: Legacy Stage Imports Are Never Used

**File:** `backend/worker.py`  
**Lines:** 119-125  
**Issue:** Imports are commented out and cannot execute

```python
from backend.pipeline.stages import (
    stage_0_initialize,
    # ... active stages ...
    # LEGACY DISABLED (D5) - These stages replaced by semantic pipeline
    # stage_7_extraction,
    # stage_7_5_timeline,
    # stage_7_6_entities,
    # stage_8_validation,
    # stage_8_5_angle_discovery,
    # stage_8_6_documentary_intelligence,
    stage_9_drive_upload,
    stage_10_completion,
)
```

**Impact:** None - commented code has no effect  
**Recommendation:** Delete these lines entirely

---

### Finding 2: Legacy Stage Execution Code Never Runs

**File:** `backend/worker.py`  
**Lines:** 227-240  
**Issue:** 14 lines of commented-out execution code

```python
# =====================================================================
# LEGACY STAGES DISABLED (D5 - Decision: 2026-01-17)
# Legacy pipeline preserved but completely disabled.
# Semantic pipeline (stages A-E above) now produces Doc 0/1/2.
# =====================================================================
# run_stage_with_recovery(stage_7_extraction, ctx, "claim_extraction")
# extraction_group = StageGroup("extraction")
# if enable_parallel:
#     run_extraction_stages_parallel(ctx)
# else:
#     extraction_group.run(stage_7_5_timeline, ctx, "timeline_extraction")
#     extraction_group.run(stage_7_6_entities, ctx, "entity_extraction")
#     extraction_group.run(stage_8_validation, ctx, "validation")
# run_stage_with_recovery(stage_8_5_angle_discovery, ctx, "angle_discovery")
# run_stage_with_recovery(stage_8_6_documentary_intelligence, ctx, "documentary_intelligence")
# =====================================================================
```

**Impact:** None - commented code has no effect  
**Recommendation:** Keep the comment block (documents D5 decision), delete the actual code lines

---

### Finding 3: Legacy Prompt Fallback Is Defensive

**File:** `backend/pipeline/prompts/semantic_extraction_prompt.py`  
**Lines:** 625, 645-655  
**Status:** ✅ Properly designed

The system uses mode-specific prompts by default:
```python
if not use_legacy_prompt:
    try:
        return get_prompt_for_mode(...)  # Modern approach
    except (ImportError, ValueError):
        pass  # Fall back if dispatch fails
```

**Assessment:** This is defensive programming. If mode-specific prompts are unavailable, system falls back gracefully. This is appropriate and should be kept.

---

### Finding 4: Legacy Document Names Are Active

**Files:**
- `backend/pipeline/stages/output.py` (lines 33-49)
- `backend/integrations/google_drive_docs.py` (lines 24-35)
- `backend/pipeline/document_helpers.py`

**Finding:** The "legacy" document names (00_MASTER_INDEX through 11_DOCUMENTARY_BLUEPRINT) are **actively created and uploaded to Google Drive in every job**.

**Status:** ✅ These are NOT legacy - they are the **current output format**.

The system actually creates **two sets** of documents:
1. **Old format** (from legacy pipeline): 00_-11_ naming
2. **New format** (from semantic pipeline): 20_-22_ naming

Both sets are generated and uploaded to provide backward compatibility while transitioning to the new semantic pipeline outputs.

**Recommendation:** Keep unchanged. These are part of the user-facing API contract.

---

### Finding 5: Archive Structure Is Clean

**Observations:**
1. `/Archive Docs/` - Properly segregated from code, contains historical conversation logs
2. `/backend/legacy/` - Empty directory with only __pycache__
3. No legacy code mixed into active pipeline files

**Assessment:** ✅ Archive structure is clean and appropriate

---

## UNRESOLVED QUESTIONS

1. **Should legacy stage 7-8.6 commented code be kept for historical reference?**
   - Current: Documented with D5 decision reference
   - Option A: Keep as documentation
   - Option B: Delete entirely (code can be found in git history)
   - **Recommendation:** Delete (git history is canonical, comments clutter active code)

2. **What is the timeline for moving users completely off legacy document names?**
   - Currently: Old names (00_-11_) generated alongside new names (20_-22_)
   - Question: When can old names be deprecated?
   - This is a product decision, not code cleanup decision

3. **Should /backend/legacy/ directory be removed?**
   - Currently: Empty (only __pycache__)
   - **Recommendation:** Yes, remove in next cleanup pass

---

## TECHNICAL DECISIONS REFERENCED

**Decision D5** (2026-01-17): Legacy stages 7-8.6 completely disabled, replaced by semantic pipeline stages A-E.

**References:**
- `backend/worker.py` line 119 comment
- `backend/worker.py` line 141 comment  
- `backend/worker.py` line 227 comment block
- `backend/pipeline/stages/__init__.py` line 4 comment

---

## FILES SCANNED

### Backend Pipeline Code
✅ `/backend/pipeline/` - All files
✅ `/backend/stages/` - All files
✅ `/backend/worker.py` - Full
✅ `/backend/integrations/google_drive_docs.py` - Relevant sections
✅ `/backend/pipeline/prompts/` - Semantic extraction prompt

### Tests
✅ `/backend/tests/test_pipeline_stages.py`
✅ `/backend/tests/test_youtube_stage.py`
✅ `/backend/tests/test_prompt_templates.py`
✅ `/backend/tests/test_error_recovery.py`

### Documentation
✅ `/docs/` - All markdown files
✅ `/Archive Docs/` - Scanned (historical, not active code)
✅ `/.claude/` - Rules and configurations
✅ Root `.md` files (CLAUDE.md, PROGRESS.md, etc.)

### Scripts
✅ `/backend/scripts/test_google_write.py`

---

**End of Audit Report**

Generated: 2026-01-19 10:04 UTC  
Audit Depth: Comprehensive (all referenced files scanned)  
Confidence: High (all major code paths verified)
