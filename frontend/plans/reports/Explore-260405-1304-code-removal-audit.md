# Code Removal & Simplification Audit

**Generated:** 2026-04-05
**Scope:** Full Research Agent codebase (backend + frontend)
**Thoroughness:** Comprehensive with file paths and line numbers

---

## 1. youtube-transcript-api (BROKEN on Cloud IPs)

### Status
**KNOWN BROKEN** — Fails on Railway, AWS, GCP cloud IPs. Still in requirements.txt but disabled in code.

### Current Implementation
- **Primary Location:** `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/transcript_acquisition.py`
  - Lines 220-252: `_try_youtube_captions()` function
  - Lines 233-234: Import statement (lazy import with try/except)
  - **Status:** Tier 3 in fallback chain, documented as failing on cloud
  
- **requirements.txt** (Line 55):
  ```
  youtube-transcript-api>=0.6.0  # Tier 3 fallback for captions (local only, fails on cloud IPs)
  ```

### Where It's Referenced (NOT USED)
1. `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/transcript_acquisition.py:234`
   - Import statement inside try/except (defensive import)
   - Function `_try_youtube_captions()` catches ImportError if not installed
   
2. `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/transcripts.py:4`
   - Comment: "REMOVED - fails on cloud IPs (Railway, AWS, GCP)"
   - Lines 267-270: Dead code section (commented explanation)

### Dead Code Evidence
- **Line 267-270** in `transcript_acquisition.py`:
  ```python
  # Tier 3: YouTube captions tier uses youtube-transcript-api which fails on
  # cloud IPs (Railway, AWS, GCP). On cloud deployments, Tier 3 will always
  # fall through to video_only. This is documented behavior.
  ```

### Fallback Chain Status (Tier 3 is BROKEN)
```
Tier 1: Supadata (WORKS - primary)
Tier 2: Whisper (WORKS - expensive)
Tier 3: YouTube captions via youtube-transcript-api (BROKEN on cloud)
Tier 4: None (video_only analysis mode)
```

### Recommendation
- **REMOVE** from requirements.txt (line 55)
- Remove defensive import in `_try_youtube_captions()` (lines 233-234)
- Simplify fallback chain to 3 tiers (remove Tier 3 entirely)
- Update docstrings referencing Tier 3

---

## 2. Transcript Fallback Chain Implementation

### Files Involved
1. **Primary:** `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/transcript_acquisition.py`
   - Lines 258-347: `acquire_transcript()` function (main entry point)
   - Lines 164-196: `_try_supadata()` - **WORKS**
   - Lines 199-217: `_try_whisper()` - **WORKS but expensive**
   - Lines 220-252: `_try_youtube_captions()` - **BROKEN on cloud**

2. **Legacy (deprecated):** `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/transcripts.py`
   - Contains `fetch_transcript_v2()` (delegated to, not directly called)
   - Lines 191-305: Cloud-compatible implementation (legacy module)

3. **Service Layer:** `/Users/maz/Documents/GitHub/Research_Agent/backend/services/transcript_service.py`
   - Wraps `fetch_transcript_v2()` from legacy module

### Tier Status
```
Tier 1: Supadata native + AI
- File: transcript_acquisition.py:164-196 (_try_supadata)
- Status: ✅ WORKS (primary, cheapest)
- Cost: ~1 credit per native, ~2 credits per AI generation

Tier 2: Whisper
- File: transcript_acquisition.py:199-217 (_try_whisper)
- Status: ✅ WORKS (expensive: ~$0.006/min)
- Conversion: result.get("cost") / 0.006 = credits

Tier 3: YouTube Captions
- File: transcript_acquisition.py:220-252 (_try_youtube_captions)
- Status: ❌ BROKEN on cloud IPs
- Evidence: Lines 247-250 catch "blocked" errors
```

### Dead Code
- `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/transcript_acquisition.py`
  - Lines 244-245: Import guard ("youtube-transcript-api not installed")
  - Lines 247-250: Cloud-blocking error handler

---

## 3. Four-Step Wizard Frontend

### Location
`/Users/maz/Documents/GitHub/Research_Agent/frontend/components/dashboard/job-creation-wizard.tsx`

### Step Mapping
1. **Step 1: Topic** (Lines 95-96)
   - Component: `WizardStepTopic`
   - File: `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/dashboard/wizard-step-topic.tsx`
   - Input: topic text
   
2. **Step 2: Sources** (Lines 98-99)
   - Component: `WizardStepSources`
   - File: `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/dashboard/wizard-step-sources.tsx`
   - Input: URLs, text, images, screenshots
   
3. **Step 3: Mode** (Lines 101-107)
   - Component: `WizardStepMode`
   - File: `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/dashboard/wizard-step-mode.tsx`
   - Inputs: pipeline (quick/deep), niche selection
   
4. **Step 4: Preview** (Lines 109-118)
   - Component: `WizardStepPreview`
   - File: `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/dashboard/wizard-step-preview.tsx`
   - Fetches job preview (line 56: `await previewJob()`)

### Step Constants
- Line 17: `STEP_LABELS = ['Topic', 'Sources', 'Mode', 'Preview']`
- Line 18: `TOTAL_STEPS = STEP_LABELS.length` (4)

### Progress Tracking
- Lines 74: Progress calculation: `((step - 1) / (TOTAL_STEPS - 1)) * 100`
- Lines 79-91: Visual progress bar with step labels

### Navigation Logic
- Line 43-47: `canNext` state validation per step
- Line 49-70: `handleNext()` function
  - Step 3→4: Fetches preview via `previewJob()` hook
  - Line 56-60: Source URL filtering and preview request

---

## 4. Multiple Document Display (Doc 0, 1, 2, 3)

### Primary Component
**File:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentCardGrid.tsx`

### Document Configuration
```typescript
// Lines 29-81: Core documents (always shown)
coreDocConfigs = [
  { key: 'doc_0', docNumber: 0, title: 'Source Ledger' },
  { key: 'doc_1', docNumber: 1, title: 'Jump-Start' },
  { key: 'doc_2', docNumber: 2, title: 'Semantic Brief' },
]

// Lines 102-118: Doc 3 (Creator Brief)
doc3Config = {
  key: 'doc_3', docNumber: 3, title: 'Creator Brief'
}

// Lines 84-100: Optional booster
boosterConfig = { key: 'booster', docNumber: 'B' }
```

### Default Display
- **Lines 28-81:** Core docs (0, 1, 2) always rendered when available
- **Lines 102-118:** Doc 3 (Creator Brief) always rendered when available
- **Line 84-100:** Booster optional (conditional: `boosterStatus !== null`)

### Lazy Loading Flags
- Lines 134-137: Path fields for lazy loading from storage
  ```
  doc_0_path?: string;
  doc_1_path?: string;
  doc_2_path?: string;
  doc_3_path?: string;
  ```

### Rendering All 4 by Default
- `hasCoreDoc()` function (lines ~165-171): Checks availability of docs 0, 1, 2
- Doc 3 rendered whenever `artifacts.creator_brief` exists (line ~102-118)
- Result: All 4 documents shown in grid layout by default if available

---

## 5. Dead/Unused Code

### 5.1 Archive Directories

#### Backend Archive
`/Users/maz/Documents/GitHub/Research_Agent/backend/archive/`
- `booster_prompt_archived.py` — Booster prompt (removed from pipeline)
- `booster_stage_archived.py` — Booster stage (removed from pipeline)
- `deprecated_route_handlers.py` — Legacy endpoints (410 Gone)
- `deprecated_validation.py` — Old validation code

#### Frontend Archive
`/Users/maz/Documents/GitHub/Research_Agent/frontend/archive/`
- `AdminLayout.tsx` — Old admin panel
- `Layout.tsx` — Legacy layout (was Pages Router)
- `ThemeContext.tsx` — Old theme toggle code (see section 5.3)
- `MobileBottomNav.tsx` — Old mobile nav
- `PublicHeader.tsx` — Old header
- `pages-router/` — Legacy Pages Router implementation (15 files)
- `iterate-legacy/` — V1 iteration dialog (1 file: `IterateDialog.tsx`)

### 5.2 Deprecated Route Handlers
**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/archive/deprecated_route_handlers.py`

Contents:
1. Lines 8-23: `create_job_endpoint()` — Topic-based job creation (410 Gone)
2. Lines 30-33: `preview_job_endpoint()` — Legacy preview (410 Gone)
3. Lines 40-43: `select_interpretation()` — Disambiguation (410 Gone)
4. Lines 46-80+: `run_job_iteration()` — V1 iteration handler (deprecated 2026-01-26)
5. Reference code: Full implementation preserved for historical context

### 5.3 Theme Toggle Code (Dark-Only Now)
**Files to Remove:**
1. `/Users/maz/Documents/GitHub/Research_Agent/frontend/archive/ThemeContext.tsx`
   - Old ThemeProvider with light/dark/system modes
   - No longer used (dark-only now)

2. `/Users/maz/Documents/GitHub/Research_Agent/frontend/app/providers.tsx`
   - **Lines 17, 31-41:** Still using next-themes + forcedTheme="dark"
   - `forcedTheme="dark"` means theme toggle is disabled
   - **Simplification:** Remove next-themes dependency entirely if dark-only

**Current State:**
- Lines 31-41 in providers.tsx:
  ```typescript
  <ThemeProvider
    attribute="class"
    defaultTheme="dark"
    forcedTheme="dark"         // ← Forces dark, disables toggle
    enableSystem={false}
    disableTransitionOnChange
  >
  ```
- next-themes still imported (line 17) and configured despite being forced to dark

### 5.4 Unused Topic-Based Mode References
**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py`

- Lines 70-72: Comment: "Legacy topic-based jobs are no longer supported"
- Lines 110-118: Rejects topic-based jobs with 410 error
- Lines 125: "semantic-only pipeline (user-supplied sources)"

**Status:** Code is defensive (rejects legacy jobs) — not dead, but documents removed mode

### 5.5 Unused/Legacy Code Patterns

**Pipeline Stage Removals:**
- `booster_stage_archived.py` — Booster no longer in main pipeline
- Status: Archived, not removed (per Rule 14)

**Legacy Imports in Worker:**
- Line 14: Comment: "NOTE: Legacy fallbacks removed (2026-01-19 - new pipeline only)"

---

## 6. Gap Analysis + Synthesis as Separate Stages

### Files Involved
1. **Gap Analysis Stage**
   - **File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/gap_analysis.py`
   - **Lines:** 1-150+ (full file)
   - **Key Functions:**
     - `build_source_manifest()` (lines 50-67): Source context for gap ID
     - `aggregate_semantic_units()` (lines 70-100): Key points/themes/tensions
     - `parse_gap_response()` (lines 24-47): Parse Gemini response into Gap objects

2. **Semantic Synthesis Stage**
   - **File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/semantic_synthesis.py`
   - **Lines:** 1-250+ (full file)
   - **Key Functions:**
     - `aggregate_for_synthesis()` (lines 34-84): Aggregate units for synthesis
     - `aggregate_for_synthesis_with_attribution()` (lines 87-100+): Extended version

### Pipeline Order (Worker)
**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py`

Execution sequence:
- Line 465-466: Gap Analysis stage
  ```python
  run_stage_with_recovery(stage_gap_analysis, ctx, "gap_analysis")
  ```
- Line 468-469: Semantic Synthesis stage
  ```python
  run_stage_with_recovery(stage_semantic_synthesis, ctx, "semantic_synthesis")
  ```

### Data Flow
```
semantic_extraction → gap_analysis → semantic_synthesis → document_assembly
     ↓                     ↓                  ↓
  key_points          identified_gaps    synthesized_themes
  themes              gap descriptions   semantic_core
  tensions                                speculative_obs
```

### Can They Be Merged?
- **Gap Analysis** consumes: semantic_extractions (key_points, themes, tensions)
- **Synthesis** consumes: identified_gaps (from gap analysis) + semantic_extractions
- **Verdict:** Synthesis depends on Gap Analysis output → **Cannot merge directly**
- **Optimization:** Could combine into single "Analysis" stage with internal phases

---

## 7. Creator Brief (Doc 3) Generation Trigger

### Current Implementation (ALWAYS ON)

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/worker.py`

- **Lines 474-475:** Unconditional execution
  ```python
  # Stage F: Creator Brief assembly (Doc 3) — non-fatal
  run_stage_with_recovery(run_creator_brief_stage, ctx, "creator_brief")
  ```

- **Status:** `run_stage_with_recovery()` wrapper means non-fatal (warnings don't fail job)
- **Trigger:** Always runs after document_assembly stage completes

### Creator Brief Stage
**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/creator_brief_stage.py`

- **Lines:** 1-250+ (full implementation)
- **Function:** `run_creator_brief_stage(ctx: PipelineContext) -> PipelineContext`
- **Inputs:** ctx.semantic_synthesis, ctx.identified_gaps, ctx.semantic_extractions
- **Output:** 
  - `ctx.outputs["creator_brief"]` — Full document dict
  - `ctx.outputs["creator_brief_md"]` — Markdown version

### How to Make On-Demand
1. **Remove line 475** in worker.py (unconditional call)
2. **Add to job iteration endpoint** (when user requests)
3. **Add condition:** Only generate if job status is "completed"
4. **Cost consideration:** Creator Brief runs Gemini synthesis (expensive)

### Current Cost
- Line 1808-1821 in worker.py shows fallback generation during iteration
- Implies Creator Brief is expensive (only run on demand)

---

## 8. Unused Dependencies

### Not Actually Used in Code
1. **praw** (Line 61, requirements.txt)
   - Status: Imported in requirements but NO usage found
   - Grep result: No `import praw` or `from praw` in any .py file
   - **Recommendation:** REMOVE from requirements.txt

2. **tavily-python** (Line 96, requirements.txt)
   - Status: Imported in requirements but NO usage found
   - Grep result: No `from tavily` or `import tavily` in any .py file
   - **Recommendation:** REMOVE from requirements.txt

3. **exa-py** (Line 44, requirements.txt)
   - Status: Imported in requirements but NO usage found
   - Grep result: No `from exa` or `import exa` in any .py file
   - **Recommendation:** REMOVE from requirements.txt

### Dependencies with Missing Actual Usage
4. **datasketch** (Line 72, requirements.txt)
   - Comment: "MinHash LSH for O(n) claim deduplication"
   - Grep result: NO imports found
   - **Recommendation:** REMOVE or clarify intent

5. **rank-bm25** (Line 75, requirements.txt)
   - Comment: "BM25 for source relevance scoring"
   - Grep result: NO imports found
   - **Recommendation:** REMOVE or implement

6. **rapidfuzz** (Line 78, requirements.txt)
   - Comment: "RapidFuzz for fuzzy string matching (quote verification)"
   - Grep result: NO imports found
   - **Recommendation:** REMOVE or implement

7. **spacy** (Line 82, requirements.txt)
   - Comment: "spaCy transformer model (optional, 500MB)"
   - Grep result: NO imports found
   - **Recommendation:** REMOVE (marked as optional but never used)

### Actually Used
- ✅ mutagen: NOT used (imported in requirements but NO grep hits)
- ✅ yt-dlp: USED in whisper_client.py and semantic_extraction.py
- ✅ All core dependencies: USED

### Summary Table
```
Dependency          | Used? | Location/Status
--------------------|-------|----------------------------------
praw               | ❌ NO | requirements.txt:61 — REMOVE
tavily-python      | ❌ NO | requirements.txt:96 — REMOVE
exa-py             | ❌ NO | requirements.txt:44 — REMOVE
datasketch         | ❌ NO | requirements.txt:72 — REMOVE
rank-bm25          | ❌ NO | requirements.txt:75 — REMOVE
rapidfuzz          | ❌ NO | requirements.txt:78 — REMOVE
spacy              | ❌ NO | requirements.txt:82 — REMOVE
mutagen            | ❌ NO | requirements.txt:54 — REMOVE
yt-dlp             | ✅ YES | whisper_client.py, semantic_extraction.py
youtube-transcript | ❌ NO | requirements.txt:55 — BROKEN (remove)
```

---

## 9. Frontend Dependencies (package.json)

### Potentially Unnecessary
1. **next-themes** (Line 40)
   - Currently: `forcedTheme="dark"` (line 34 in providers.tsx)
   - Status: Disabled (dark-only)
   - **Recommendation:** REMOVE dependency if no light mode planned

2. **All others:** Actually used (checked against imports)

---

## Summary of Actions

### REMOVE (Broken/Unused)
- [ ] **requirements.txt line 55:** youtube-transcript-api (broken on cloud)
- [ ] **requirements.txt line 61:** praw (never used)
- [ ] **requirements.txt line 44:** exa-py (never used)
- [ ] **requirements.txt line 96:** tavily-python (never used)
- [ ] **requirements.txt line 72:** datasketch (never used)
- [ ] **requirements.txt line 75:** rank-bm25 (never used)
- [ ] **requirements.txt line 78:** rapidfuzz (never used)
- [ ] **requirements.txt line 82:** spacy (never used)
- [ ] **requirements.txt line 54:** mutagen (never used)
- [ ] **package.json line 40:** next-themes (disabled, dark-only)

### SIMPLIFY
- [ ] **transcript_acquisition.py:** Remove Tier 3 (youtube-transcript-api)
- [ ] **worker.py line 475:** Make Creator Brief on-demand (remove unconditional call)
- [ ] **providers.tsx:** Remove next-themes or implement light mode

### CLEAN UP (Already Archived)
- Backend: `/backend/archive/*` (already done)
- Frontend: `/frontend/archive/*` (already done)

### MONITOR
- Gap Analysis + Synthesis: Currently separate, could combine (no action needed)
- Four-step wizard: No issues, well-structured

