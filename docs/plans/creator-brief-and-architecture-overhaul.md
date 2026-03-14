# Implementation Plan: Creator Brief, Architecture Overhaul & Code Enforcement

**Date:** 2026-03-11
**Branch:** TBD (new branch from `feature/kimi-visual-analysis-and-optimizations`)
**Scope:** Backend pipeline, models, validation, frontend rendering, authoritative docs

---

## Overview

This plan implements everything discussed in the Sandcastles competitive analysis session:

1. **Document numbering shift** — Doc 3 becomes Creator Brief (core), Producer Packet moves to Doc 4 (optional)
2. **Creator Brief pipeline stage** — New ASSEMBLY stage that generates the narrative content blueprint
3. **Iterate system consolidation** — Booster → `deep_dive`, Addendum → `expand_sources`, unified under `iterate` with 5 modes
4. **Code enforcement gaps** — Fix 8 identified gaps where rules exist in prompts but NOT in code
5. **Document versioning** — 4-version rolling window (latest + 3 previous)
6. **Naming cleanup** — Systematic rename of Booster/Addendum/old Doc 3 references
7. **Authoritative doc updates** — RASS, architecture.md, Document_Output_Format.md, Operational_Definitions.md
8. **Frontend document rendering** — Update ArtifactCardGrid, DocumentViewerModal, document drawer for new Doc 0-3 core + Doc 4+ optional split

**NOT in scope (future work):**
- Script writer (Doc 5, v2)
- Voice mimicry feature (v2+)
- Search/discovery UX rebuild (separate plan after foundation is solid)
- Full frontend UI overhaul (progressive disclosure, narrated loading — separate plan)

---

## Phase 1: Code Enforcement Gaps (No New Features, Just Safety)

**Goal:** Fix the 8 identified gaps where pipeline rules are prompt-only. This is prerequisite work — we need the enforcement layer solid before building Creator Brief on top of it.

### 1.1 Claim source_id enforcement
**Files:**
- `backend/models/claims.py` — ClaimInstance model
**Change:** Add `source_id: str = Field(..., min_length=1)` to ClaimInstance. Currently it's a plain `str` field with no minimum length, meaning empty strings pass validation.
**Test:** Add test in `test_claim_extractor_v2.py` that a ClaimInstance with `source_id=""` raises ValidationError.

### 1.2 Tension source grounding
**Files:**
- `backend/models/semantic_units.py` — Tension model (if exists) or wherever tensions are defined
- `backend/pipeline/semantic_validation.py` — add tension source validation
**Change:** Add `source_ids: list[str] = Field(..., min_length=1)` to Tension model. Add validation in `validate_grounding()` that all tension source_ids exist in valid source set.
**Test:** Tension with empty source_ids fails validation. Tension referencing nonexistent source_id triggers warning.

### 1.3 Confidence ceiling for Themes/Tensions
**Files:**
- `backend/pipeline/semantic_validation.py` — `validate_confidence_ceiling()`
**Change:** Extend ceiling check. Themes don't have explicit confidence, but we can add a derived confidence (max of referenced KP confidences, capped at ceiling). If any theme references only LOW-confidence KPs, the theme inherits LOW. Add `effective_confidence` field to theme output.
**Test:** Theme composed entirely of LOW-confidence KPs cannot have effective_confidence > LOW.

### 1.4 Source Identity Lock validation
**Files:**
- `backend/pipeline/semantic_validation.py` — new function `validate_source_identity_lock()`
- `backend/pipeline/stages/semantic_validation_stage.py` — call it
**Change:** After LLM extraction, compare the `source_id` in the returned JSON to the `source_id` that was passed in the prompt. If they don't match → HARD FAIL. This catches LLM hallucinating or mixing source identifiers.
**Test:** Extraction returning `source_id: "SRC_999"` when prompt said `source_id: "SRC_001"` fails validation.

### 1.5 V1/V2 artifact version lock
**Files:**
- `backend/models/job_record.py` — add `@model_validator`
**Change:** Add model_validator that prevents both `booster_output` (V1) and `runs[].booster_expansion` (V2) from being set simultaneously. If V2 runs exist, V1 fields must be None. Log deprecation warning if V1 fields are populated on a job that also has V2 runs.
**Test:** Job with both `booster_output` and `runs[0].booster_expansion` raises ValidationError.

### 1.6 video_only timestamp requirement → HARD FAIL
**Files:**
- `backend/pipeline/semantic_validation.py` — `validate_grounding()` around line 368
**Change:** Change the video_only timestamp check from soft fail (warning) to hard fail. If a claim in video_only mode has no `timestamp_range`, it's a validation failure, not a warning.
**Test:** Claim in video_only mode without timestamp_range triggers hard fail.

### 1.7 based_on field cleanup
**Files:**
- `backend/pipeline/semantic_validation.py` — `validate_based_on_references()`
**Change:** This validation function expects a `based_on` field that doesn't exist in models. Two options: (a) remove the dead validation code, or (b) add `based_on: Optional[list[str]]` to KeyPoint/Claim models. Decision: Remove the dead code — based_on was never populated by the LLM, so the validation never fires. Dead code creates false confidence.
**Test:** Verify removal doesn't break any existing tests.

### 1.8 Quote V5 table conflict fix
**Files:**
- `docs/authoritative/spec/Validation_and_Retry_Rules.md`
**Change:** Fix V5 table to match Owner Decision (2026-01-15): `text_provided` and `ocr_extracted` ALLOW quotes with unverified flag. Currently says FORBIDDEN, which contradicts `Operational_Definitions.md` and `architecture.md` Rule 6.
**Test:** N/A (doc fix only, but verify `semantic_validation.py` matches the corrected spec).

---

## Phase 2: Document Numbering Shift & Naming Cleanup

**Goal:** Shift Producer Packet from Doc 3 → Doc 4. Rename Booster → Deep Dive, Addendum → Source Expansion. This is a renaming/restructuring phase — no new features yet.

### 2.1 Model updates
**Files:**
- `backend/models/job_record.py` — JobArtifacts, any doc_3_path references
- `backend/models/run_models.py` — Run artifacts
- `backend/models/job.py` — Response schemas
**Changes:**
- `doc_3_path` → `doc_3_path` stays (but now references Creator Brief, not Producer Packet)
- Add `doc_4_path: Optional[str]` for Producer Packet
- Add `creator_brief_md: Optional[str]` inline field (parallel to `producer_packet_md`)
- Rename `booster_output` → deprecated, add `deep_dive_output`
- Add migration logic: if `doc_3_path` exists and job predates the change → treat as Producer Packet (backward compat)

### 2.2 API route updates
**Files:**
- `backend/app/routes/jobs_routes.py`
**Changes:**
- `GET /jobs/{job_id}/documents/doc_3` → returns Creator Brief (new behavior)
- `GET /jobs/{job_id}/documents/doc_4` → returns Producer Packet
- `POST /jobs/{job_id}/booster` → alias to `POST /jobs/{job_id}/iterate/deep-dive` (backward compat)
- Add `POST /jobs/{job_id}/iterate/{mode}` unified endpoint with modes: `deep_dive`, `expand_sources`, `deeper`, `different_angle`, `custom`
- Legacy endpoints kept for backward compat but log deprecation warnings

### 2.3 Pipeline stage naming
**Files:**
- `backend/pipeline/stages/booster_stage.py` → rename to `deep_dive_stage.py`
- `backend/pipeline/stages/producer_stage.py` — update to produce Doc 4 (not Doc 3)
- `backend/pipeline/stages/document_assembly.py` — update doc numbering comments
**Changes:**
- Class `BoosterStage` → `DeepDiveStage` (keep `BoosterStage` as deprecated alias)
- All internal references to "booster" → "deep_dive" in logs, metrics, status updates
- `booster_prompt.py` → `deep_dive_prompt.py` (keep old file as import alias)

### 2.4 Worker/Celery task naming
**Files:**
- `backend/worker.py` or equivalent Celery task definitions
**Changes:**
- Task `run_booster` → `run_deep_dive` (keep old name as alias for in-flight jobs)
- Task `process_addendum` → `run_expand_sources`
- Add `run_iterate` dispatcher task that routes to the correct mode

### 2.5 Frontend updates (naming only)
**Files:**
- `frontend/components/job-detail/ArtifactCardGrid.tsx`
- `frontend/components/job-detail/ArtifactCard.tsx`
- `frontend/lib/constants.ts` — STAGE_LABELS
- `frontend/store/jobs.ts` — interfaces
**Changes:**
- Card labels: "Booster" → "Deep Dive", "Producer Packet" → keep name but now Doc 4
- Stage labels: `booster_running` → `deep_dive_running`
- Artifact card order: Doc 0, Doc 1, Doc 2, Doc 3 (Creator Brief — placeholder until Phase 3), Doc 4 (Producer Packet)
- Add `doc_4_path` to TypeScript interfaces

### 2.6 Authoritative doc updates
**Files:**
- `docs/authoritative/spec/RASS.md`
- `docs/authoritative/spec/Document_Output_Format.md`
- `docs/authoritative/spec/Operational_Definitions.md`
- `.claude/rules/architecture.md`
**Changes:**
- Rule 12: "Three Core Documents" → "Four Core Documents (Doc 0-3)"
- Rule 13: Doc 3 = Creator Brief (core, auto-generated). Doc 4 = Producer Packet (optional, user-triggered). Remove "Booster" and "Addendum" — replace with Iterate system modes.
- RASS: Update Stage F (Booster → Deep Dive), add Stage G (Creator Brief Assembly)
- Document_Output_Format.md: Add `creator_brief` document_type, update doc_3 schema, add doc_4 schema
- Operational_Definitions.md: Update document set definition

---

## Phase 3: Creator Brief Pipeline Stage (The Main Build)

**Goal:** Build the new ASSEMBLY stage that takes Doc 2 (Semantic Brief) claims and produces Doc 3 (Creator Brief) — the narrative content blueprint.

### 3.1 Creator Brief data model
**Files:**
- `backend/models/creator_brief.py` (NEW)
**Model:**
```python
class HookOption(BaseModel):
    hook_text: str
    hook_type: str  # "question", "statistic", "contrast", "story"
    source_claim_id: str  # traces to Doc 2
    significance: float  # 0-1

class CoreFact(BaseModel):
    fact_text: str  # "say it like this" phrasing
    supporting_claim_ids: list[str]  # traces to Doc 2
    source_ids: list[str]  # traces to Doc 0
    significance: float
    rhetorical_framing: str  # from claim enrichments

class TwistMoment(BaseModel):
    setup: str
    twist: str
    claim_ids: list[str]  # the contradicting claims
    contrast_type: str  # "reversal", "escalation", "misconception"

class Analogy(BaseModel):
    analogy_text: str
    what_it_explains: str
    source_claim_id: str

class PersonalStakes(BaseModel):
    stakes_text: str  # "what this means for YOU"
    claim_ids: list[str]

class Cliffhanger(BaseModel):
    cliffhanger_text: str
    unanswered_question: str
    gap_id: Optional[str]  # from Doc 2 gaps

class CreatorBrief(BaseModel):
    document_type: Literal["creator_brief"] = "creator_brief"
    version: str = "1.0"
    topic: str
    hook_options: list[HookOption] = Field(..., min_length=2, max_length=5)
    core_facts: list[CoreFact] = Field(..., min_length=3, max_length=10)
    twist: Optional[TwistMoment]
    analogies: list[Analogy] = Field(default_factory=list, max_length=3)
    personal_stakes: PersonalStakes
    cliffhanger: Optional[Cliffhanger]
    metadata: BriefMetadata  # source_count, claim_count, confidence_summary
```
**Key enforcement:** Every field that references claims has `claim_ids` or `source_claim_id` that MUST exist in Doc 2. Validated post-generation (see 3.4).

### 3.2 Creator Brief prompt
**Files:**
- `backend/pipeline/prompts/creator_brief_prompt.py` (NEW)
**Design:**
- Input: Doc 2 (Semantic Brief) — all claims with enrichments, themes, tensions, gaps
- Input: Doc 0 (Source Ledger) — source metadata for citation
- Output: CreatorBrief JSON matching the model above
- Temperature: 0.3 (creative enough for phrasing, constrained enough for accuracy)
- Rules embedded in prompt:
  1. Every hook must reference a real claim_id from the input
  2. Every core fact must trace to source_ids from Doc 0
  3. Twist must use actually contradicting claims (check `claim_relations` for `contradicts` type)
  4. Analogies must simplify a real claim, not invent new information
  5. Personal stakes must connect verified facts to viewer impact
  6. NO new facts — everything comes from Doc 2 claims
  7. Significance scores must match or be lower than source claim significance

### 3.3 Creator Brief pipeline stage
**Files:**
- `backend/pipeline/stages/creator_brief_stage.py` (NEW)
**Flow:**
1. Load Doc 2 (Semantic Brief) from storage
2. Load Doc 0 (Source Ledger) for source metadata
3. Build prompt with claims, enrichments, themes, tensions
4. Call Gemini `generate_json()` with CreatorBrief schema
5. Unwrap `{"data": {...}, "cost": ...}` response (same pattern as all Gemini calls)
6. Validate output (see 3.4)
7. Render to markdown (see 3.5)
8. Upload to Supabase Storage as `doc_3`
9. Update job artifacts with `doc_3_path`

### 3.4 Creator Brief validation (CODE ENFORCEMENT)
**Files:**
- `backend/pipeline/creator_brief_validation.py` (NEW)
**Validations:**
1. **Claim reference integrity** — every `claim_id` and `source_claim_id` in the Brief must exist in Doc 2's claim list. HARD FAIL if not.
2. **Source reference integrity** — every `source_id` in core_facts must exist in Doc 0. HARD FAIL if not.
3. **Cardinality checks** — 2-5 hooks, 3-10 core facts, 0-3 analogies. WARNING if outside range.
4. **Significance bounds** — no significance score in the Brief can exceed the source claim's significance. Auto-downgrade if violated.
5. **No novel facts** — compare Brief fact_text against Doc 2 claims using fuzzy matching. If a fact doesn't match any claim at ≥0.5 similarity, flag as potential hallucination. WARNING (not hard fail — phrasing will differ).
6. **Twist claim validation** — if twist references claim_ids, verify those claims actually have a `contradicts` relationship in Doc 2's claim_relations. WARNING if not.
7. **Gap reference validation** — if cliffhanger references a gap_id, verify it exists in Doc 2's gaps. HARD FAIL if not.

### 3.5 Creator Brief markdown renderer
**Files:**
- `backend/pipeline/renderers/creator_brief_renderer.py` (NEW)
**Output format:** Consistent with Doc 0/1/2 visual language. Sections:
```markdown
# Creator Brief: {topic}
> {source_count} sources · {claim_count} verified claims · Generated {date}

## Hook Options
1. **[Question]** "Have you ever wondered..." _(from claim CLM_007, significance: 0.9)_
2. **[Statistic]** "The dollar's share just hit..." _(from claim CLM_012, significance: 0.85)_

## Core Facts (What You'll Say)
### Fact 1: {fact_text}
- Sources: [Source Title](url), [Source Title](url)
- Significance: ★★★★☆
- Framing: {rhetorical_framing}

## The Twist
**Setup:** {setup}
**But:** {twist}
_(Based on contradicting claims CLM_003 ↔ CLM_015)_

## The Analogy
"{analogy_text}"
— explains: {what_it_explains}

## What This Means For You
{stakes_text}

## Cliffhanger
{cliffhanger_text}
> Unanswered: {unanswered_question}
```

### 3.6 Integration into main pipeline
**Files:**
- `backend/pipeline/orchestrator.py` or `backend/worker.py` — wherever the pipeline stages are sequenced
- `backend/pipeline/stages/__init__.py`
**Changes:**
- Add `creator_brief_stage` after `document_assembly` stage
- Pipeline order becomes: ingestion → extraction → validation → gap_analysis → synthesis → document_assembly → **creator_brief_assembly** → completion
- New stage label: `creator_brief_assembly` (shown in UI as "Building Creator Brief...")
- Progress: allocate ~10% of total progress to this stage

### 3.7 Tests
**Files:**
- `backend/tests/test_creator_brief.py` (NEW)
**Coverage:**
- Model validation (cardinality, required fields, claim_id format)
- Brief validation (reference integrity, significance bounds, novel fact detection)
- Markdown rendering (output format, section presence)
- Integration test with sample Doc 2 → Creator Brief generation
- Edge cases: Doc 2 with 0 tensions (no twist), Doc 2 with 0 gaps (no cliffhanger), Doc 2 with only 3 claims (minimal brief)

---

## Phase 4: Document Versioning (4-Version Rolling Window)

**Goal:** When documents are re-generated (via iterate modes), retain latest + 3 previous versions.

### 4.1 Version storage model
**Files:**
- `backend/models/job_record.py` — add version tracking
**Changes:**
- Add `DocumentVersion` model:
  ```python
  class DocumentVersion(BaseModel):
      version: str  # "1.0", "2.0", etc.
      storage_path: str
      created_at: datetime
      trigger: str  # "initial", "deep_dive", "expand_sources", "deeper", "different_angle"
      diff_summary: Optional[str]  # "+3 sources, +15 claims"
  ```
- Add `doc_versions: dict[str, list[DocumentVersion]]` to job artifacts
  - Key: `"doc_0"`, `"doc_1"`, `"doc_2"`, `"doc_3"`, `"doc_4"`
  - Value: list of versions, max 4, newest first

### 4.2 Version management logic
**Files:**
- `backend/pipeline/version_manager.py` (NEW)
**Functions:**
- `create_version(job_id, doc_type, storage_path, trigger)` — adds new version, prunes to 4
- `get_latest_version(job_id, doc_type)` → DocumentVersion
- `get_version_history(job_id, doc_type)` → list[DocumentVersion] (max 4)
- `prune_old_versions(job_id, doc_type)` — deletes storage for versions beyond the 4th
- `compute_diff_summary(old_doc, new_doc)` — generates human-readable diff ("+3 sources, +15 claims, +2 themes")

### 4.3 Pipeline integration
**Files:**
- `backend/pipeline/stages/document_assembly.py`
- `backend/pipeline/stages/creator_brief_stage.py`
**Changes:**
- After generating any doc, call `version_manager.create_version()` instead of directly overwriting
- On iterate re-runs, old version is preserved before new one is written

### 4.4 API endpoint
**Files:**
- `backend/app/routes/jobs_routes.py`
**Changes:**
- `GET /jobs/{job_id}/documents/{doc_type}` — add optional `?version=1.0` query param. Default = latest.
- `GET /jobs/{job_id}/documents/{doc_type}/versions` — returns version history list
- Response includes `version`, `created_at`, `trigger`, `diff_summary`

### 4.5 Frontend version selector
**Files:**
- `frontend/components/job-card/DocumentViewerModal.tsx`
**Changes:**
- Add version dropdown in document header (similar to existing `RunSelector.tsx` pattern)
- Shows version number + trigger + diff summary
- Switching versions fetches the historical document from storage
- Latest version is default, badge shows "Latest"

### 4.6 Storage cleanup
**Files:**
- `backend/integrations/supabase_storage.py`
**Changes:**
- Add `delete_document(storage_path)` for pruning old versions
- Version manager calls this when pruning beyond 4th version
- Versioned paths: `research-jobs/{job_id}/doc_{type}_v{version}.json`

---

## Phase 5: Iterate System Consolidation

**Goal:** Unify Booster, Addendum, and existing iteration modes into a single `iterate` system with 5 modes.

### 5.1 Iterate mode definitions
**Files:**
- `backend/models/iterate_models.py` (NEW, replaces parts of job_record.py)
**Models:**
```python
class IterateMode(str, Enum):
    DEEP_DIVE = "deep_dive"           # was: Booster
    EXPAND_SOURCES = "expand_sources" # was: Addendum / more_sources
    DEEPER = "deeper"                 # re-extract with deeper prompts
    DIFFERENT_ANGLE = "different_angle" # re-extract with angle focus
    CUSTOM = "custom"                 # user-provided prompt

class IterateRequest(BaseModel):
    mode: IterateMode
    prompt: Optional[str]  # required for custom, optional for different_angle
    source_urls: Optional[list[str]]  # for expand_sources manual mode
    max_new_sources: int = Field(default=4, ge=0, le=10)  # for expand_sources auto mode
```

### 5.2 Unified iterate endpoint
**Files:**
- `backend/app/routes/jobs_routes.py`
**Changes:**
- `POST /jobs/{job_id}/iterate` — single endpoint, mode in request body
- Routes to appropriate stage based on mode
- Returns `iterate_id` for tracking
- Legacy endpoints (`/booster`, `/iterate`) redirect here with deprecation headers

### 5.3 Stage routing
**Files:**
- `backend/pipeline/iterate_dispatcher.py` (NEW)
**Logic:**
```
deep_dive      → DeepDiveStage (was BoosterStage) → appends to Doc 1 (new version)
expand_sources → ExpandSourcesStage → re-runs full pipeline → new versions of Doc 0-3
deeper         → re-runs extraction + synthesis with "go deeper" system prompt → new versions of Doc 1-3
different_angle → re-runs extraction + synthesis with angle focus → new versions of Doc 1-3
custom         → re-runs with user prompt injected into extraction → new versions of Doc 1-3
```

### 5.4 Iterate status tracking
**Files:**
- `backend/models/job_record.py`
**Changes:**
- Add `iterations: list[IterateRecord]` to job
- Each `IterateRecord` has: `id`, `mode`, `status`, `created_at`, `completed_at`, `versions_produced`
- Replaces both V1 `booster_output` and V2 `runs[]` with a unified tracking model

---

## Phase 6: Frontend Document Architecture

**Goal:** Update the frontend to reflect the new Doc 0-3 core + Doc 4+ optional split, document drawer, and hero view.

### 6.1 ArtifactCardGrid update
**Files:**
- `frontend/components/job-detail/ArtifactCardGrid.tsx`
**Changes:**
- Core section: Doc 0 (Source Ledger), Doc 1 (Jump-Start), Doc 2 (Semantic Brief), Doc 3 (Creator Brief)
- Optional section: Doc 4 (Producer Packet), Deep Dive button
- Creator Brief card gets hero styling (larger, primary color, star badge)
- Producer Packet card shows gating status (greyed out if prerequisites not met, with tooltip explaining why)

### 6.2 Document drawer concept
**Files:**
- `frontend/components/job-detail/DocumentDrawer.tsx` (NEW)
**Design:**
- Collapsible sidebar listing all documents
- Sections: "Core" (Doc 0-3) and "Optional" (Doc 4+)
- Each item shows: doc name, version badge, status indicator
- Click → opens DocumentViewerModal for that doc
- Creator Brief has star/hero indicator
- This replaces the current flat card grid as the primary navigation

### 6.3 DocumentViewerModal enhancements
**Files:**
- `frontend/components/job-card/DocumentViewerModal.tsx`
**Changes:**
- Add color scheme for Doc 3 (Creator Brief) — distinct from Doc 2
- Add version dropdown (Phase 4)
- Add "View Research" and "View Sources" contextual links in Creator Brief view
- Inline claim expansion: clicking a claim_id reference opens a popover with the claim detail from Doc 2

### 6.4 TypeScript interface updates
**Files:**
- `frontend/store/jobs.ts`
- `frontend/lib/constants.ts`
**Changes:**
- Add `doc_3_path` (Creator Brief), `doc_4_path` (Producer Packet) to artifact interfaces
- Add `creator_brief_md` inline field
- Update `STAGE_LABELS` with `creator_brief_assembly: "Building Creator Brief..."`
- Add `deep_dive_running` stage label
- Add `IterateMode` enum matching backend

---

## Execution Order & Dependencies

```
Phase 1: Code Enforcement Gaps          ← No dependencies, pure safety fixes
  ↓
Phase 2: Document Numbering & Naming    ← Depends on Phase 1 (models updated)
  ↓
Phase 3: Creator Brief Pipeline Stage   ← Depends on Phase 2 (Doc 3 slot available)
  ↓
Phase 4: Document Versioning            ← Depends on Phase 3 (versioning applies to all docs including new Doc 3)
  ↓
Phase 5: Iterate System Consolidation   ← Depends on Phase 2 (naming), Phase 4 (versioning)
  ↓
Phase 6: Frontend Document Architecture ← Depends on all above (renders everything)
```

**Phases 1 and 2 can be done as one PR** (enforcement + renaming).
**Phase 3 is the main feature PR** (Creator Brief).
**Phases 4 and 5 can be one PR** (versioning + iterate).
**Phase 6 is the frontend PR** (renders everything).

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Breaking existing jobs that have Doc 3 = Producer Packet | Migration logic: check job creation date. Pre-change jobs → doc_3_path is Producer Packet. Post-change → doc_3_path is Creator Brief. |
| In-flight Celery tasks using old Booster/Addendum names | Keep old task names as aliases for 2 weeks. Log deprecation warnings. |
| Creator Brief prompt quality | Start with temperature 0.3. Validate output against Doc 2 claims. Iterate on prompt based on real outputs. |
| Version storage costs | 4-version window limits storage. Prune function deletes old versions from Supabase. |
| Frontend regression | Existing Doc 0/1/2 rendering unchanged. Doc 3 card shifts from Producer Packet to Creator Brief. Producer Packet moves to Doc 4. |

---

## Test Strategy

- **Phase 1:** Unit tests for each enforcement fix. Run full test suite (1135 tests) to ensure no regressions.
- **Phase 2:** Integration tests that verify old jobs still render correctly. New jobs produce correct doc numbering.
- **Phase 3:** Unit tests for CreatorBrief model, validation, rendering. Integration test: sample Doc 2 → Creator Brief → validate all references.
- **Phase 4:** Unit tests for version_manager (create, prune, retrieve). Integration test: iterate re-run produces new versions, old versions retrievable.
- **Phase 5:** Unit tests for iterate dispatcher routing. Integration test: each mode produces expected doc version updates.
- **Phase 6:** Manual frontend testing (no automated frontend tests currently).

---

## Files Created (New)

| File | Purpose |
|---|---|
| `backend/models/creator_brief.py` | CreatorBrief Pydantic model |
| `backend/models/iterate_models.py` | IterateMode enum, IterateRequest, IterateRecord |
| `backend/pipeline/prompts/creator_brief_prompt.py` | LLM prompt for generating Creator Brief from Doc 2 |
| `backend/pipeline/stages/creator_brief_stage.py` | Pipeline stage that runs the Creator Brief generation |
| `backend/pipeline/creator_brief_validation.py` | Post-LLM validation (reference integrity, significance bounds, etc.) |
| `backend/pipeline/renderers/creator_brief_renderer.py` | JSON → Markdown renderer for Creator Brief |
| `backend/pipeline/version_manager.py` | Document versioning (create, prune, retrieve, diff) |
| `backend/pipeline/iterate_dispatcher.py` | Routes iterate requests to correct stage |
| `backend/tests/test_creator_brief.py` | Tests for Creator Brief model, validation, rendering |
| `frontend/components/job-detail/DocumentDrawer.tsx` | Collapsible document sidebar |

## Files Modified (Existing)

| File | Changes |
|---|---|
| `backend/models/claims.py` | Enforce source_id min_length on ClaimInstance |
| `backend/models/semantic_units.py` | Add source_ids to Tension model |
| `backend/models/job_record.py` | Add doc_4_path, DocumentVersion, iterations[], V1/V2 version lock |
| `backend/models/job.py` | Update response schemas for new doc numbering |
| `backend/models/run_models.py` | Update run artifact references |
| `backend/pipeline/semantic_validation.py` | Fix gaps 1-6 (source_id, tensions, ceiling, identity lock, timestamps, based_on) |
| `backend/pipeline/stages/booster_stage.py` | Rename to deep_dive_stage.py (keep alias) |
| `backend/pipeline/stages/producer_stage.py` | Update to produce Doc 4 |
| `backend/pipeline/stages/document_assembly.py` | Update doc numbering, integrate versioning |
| `backend/pipeline/prompts/booster_prompt.py` | Rename to deep_dive_prompt.py (keep alias) |
| `backend/app/routes/jobs_routes.py` | New iterate endpoint, doc_4 endpoint, version query param |
| `backend/integrations/supabase_storage.py` | Add delete_document, versioned paths |
| `frontend/components/job-detail/ArtifactCardGrid.tsx` | Core/Optional split, Creator Brief hero card |
| `frontend/components/job-detail/ArtifactCard.tsx` | New card types |
| `frontend/components/job-card/DocumentViewerModal.tsx` | Version selector, contextual links, claim expansion |
| `frontend/store/jobs.ts` | New interfaces for doc_3/doc_4, iterate modes |
| `frontend/lib/constants.ts` | New stage labels |
| `docs/authoritative/spec/RASS.md` | Update stages, doc definitions |
| `docs/authoritative/spec/Document_Output_Format.md` | Add creator_brief type, update doc_3/doc_4 |
| `docs/authoritative/spec/Operational_Definitions.md` | Update document set |
| `docs/authoritative/spec/Validation_and_Retry_Rules.md` | Fix V5 table conflict |
| `.claude/rules/architecture.md` | Update Rules 12, 13 |
