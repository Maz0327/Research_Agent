# Research Agent v2 — Full Implementation Plan

**Created:** 2026-03-11
**Status:** DRAFT — Awaiting owner approval
**Source of truth:** `docs/competitive/sandcastles-ux-deep-dive.md` + conversation decisions
**Scope:** Everything discussed and agreed — legacy cleanup, Creator Brief, document architecture, Iterate consolidation, enforcement gaps, search rebuild, UI overhaul

---

## Plan Overview

This plan is organized into **6 phases**, executed sequentially per implementation rules. Each phase has clear entry criteria, tasks, exit criteria, and the files that will be touched.

```
PHASE 0: Foundation — Legacy Cleanup & Enforcement Gap Fixes
PHASE 1: Architecture Updates — Docs, Models, Naming
PHASE 2: Creator Brief — The New Doc 3 (Backend)
PHASE 3: Document Versioning & Iterate Consolidation
PHASE 4: Frontend — Document Layer Model & UI Overhaul
PHASE 5: Search/Discovery Flow (Entry Point A)
```

**Out of scope for this plan (v2+ future):**
- Script Writer (Doc 5) — requires Creator Brief to be stable first
- Voice Mimicry — requires Script Writer to exist first
- Inline editing of Brief/Script — v3 feature
- Social Media Kit, Blog Post, Thread Writer (Doc 6+)

---

## The Four Entry Points

The UI must support 4 distinct entry points, each with its own flow:

```
ENTRY POINT 1: Topic-First (Search/Discovery)
  User enters topic
  → System discovers sources
  → Quick Brief generated (same format as Creator Brief, but from system-discovered sources — a PREVIEW)
  → User reviews Quick Brief + approves/rejects sources
  → Approved sources enter full pipeline
  → Full Creator Brief + Doc 0/1/2 generated

ENTRY POINT 2: Sources-First (Skip-to-Sources)
  User pastes URLs / uploads docs
  → Pipeline runs immediately
  → Creator Brief + Doc 0/1/2 generated

ENTRY POINT 3: Claim Extractor (Standalone Tool)
  User provides text/sources
  → Claims extracted (no full pipeline, no synthesis, no Creator Brief)
  → Claim extraction results displayed directly

ENTRY POINT 4: YouTube Transcript Extractor (Standalone Tool)
  User provides YouTube URLs
  → Transcripts extracted independently
  → Solo functionality — NOT part of the research pipeline
  → Has its own output view (transcript display, download, copy)
```

**Key concept: Quick Brief (Entry Point 1 only)**
The Quick Brief is a lightweight Creator Brief generated from system-discovered sources BEFORE the user approves them. It's a preview — "here's what your research could look like based on what we found." This lets the user evaluate the research quality before committing to the full pipeline. If they approve, the same sources flow into the full pipeline and produce the real Creator Brief (which will be richer due to full extraction + synthesis).

The Quick Brief uses the same format/schema as the Creator Brief but is generated from a faster, lighter extraction pass. It's NOT a separate document type — it's a preview that gets replaced by the real Doc 3 after the full pipeline runs.

---

## PHASE 0: Foundation — Legacy Cleanup, Enforcement Gaps & Transcript Fixes

**Goal:** Clean codebase before adding new functionality. Fix enforcement gaps so the pipeline is airtight. Fix broken transcript extractor so Entry Point 4 works.

**Entry criteria:** Current branch `feature/kimi-visual-analysis-and-optimizations` is stable, all tests pass.

### Phase 0.1: Legacy Code Audit

**Task 0.1.1:** Identify and catalog all deprecated/legacy code
- Scan for deprecated API endpoints: `POST /jobs` (legacy topic research), `POST /jobs/{job_id}/sources` (legacy), `POST /jobs/{job_id}/process-pending` (legacy), `POST /jobs/{job_id}/iterate` (deprecated)
- Scan for V1-only artifact fields that shouldn't coexist with V2: `booster_output` in `job_record.py:125`, any direct `doc_3_path` references that assume Producer Packet
- Catalog results in a `LEGACY_AUDIT.md` document
- **Files to read:** `backend/app/routes/jobs_routes.py`, `backend/models/job_record.py`, `backend/worker.py`

**Task 0.1.2:** Archive deprecated endpoints
- Move deprecated route handlers to `backend/archive/`
- Keep the endpoint paths registered but returning 410 Gone with migration message
- Per Rule 14: archive, don't delete
- **Files to modify:** `backend/app/routes/jobs_routes.py`

**Task 0.1.3:** Clean V1/V2 artifact mixing
- Add a version field or migration check to `JobRecord` so V1 and V2 artifacts can't coexist ambiguously
- The `booster_output` field in `job_record.py:125` should be marked deprecated and V2 code should never read it
- **Files to modify:** `backend/models/job_record.py`

**Task 0.1.4:** API Key audit cleanup (from memory file)
- Document `ADMIN_EMAILS` env var usage in `auth/admin.py`
- Add `JINA_AI_READER_API_KEY` to `config.py` Settings model
- Migrate `whisper_client`, `supadata_client`, `kimi_vision_client` from `os.getenv()` to Settings
- Remove 2 deprecated Slack keys from Settings
- **Files to modify:** `backend/config.py`, `backend/integrations/whisper_client.py`, `backend/integrations/supadata_client.py`, `backend/integrations/kimi_vision_client.py`

### Phase 0.2: Enforcement Gap Fixes

**Task 0.2.1:** Fix Claim source_id enforcement (Gap #1 — HIGH priority)
- Add `min_length=1` constraint on Claim's `source_ids` field in Pydantic model
- Ensure validation catches claims with empty source_ids
- **Files to modify:** `backend/models/claims.py`, `backend/pipeline/semantic_validation.py`
- **Tests to add:** Test that claims with empty source_ids fail validation

**Task 0.2.2:** Add source_ids to Tensions (Gap #2 — HIGH priority)
- Add `source_ids: list[str]` field to Tension model
- Update synthesis prompts to include source_ids in tension output
- Update provenance validation to check Tension→Source refs
- **Files to modify:** `backend/models/semantic_units.py`, `backend/pipeline/prompts/semantic_synthesis_prompt.py`, `backend/pipeline/stages/document_assembly.py`
- **Tests to add:** Test that tensions without source_ids fail validation

**Task 0.2.3:** Extend confidence ceiling to Themes/Tensions (Gap #3 — MEDIUM)
- Add confidence field to Theme and Tension models if not present
- Extend `validate_confidence_ceiling()` to check themes and tensions
- **Files to modify:** `backend/pipeline/semantic_validation.py`, `backend/models/semantic_units.py`

**Task 0.2.4:** Add Source Identity Lock validation (Gap #5 — MEDIUM)
- After LLM extraction, compare returned `source_id` against the `source_id` passed in the prompt
- Hard fail if they don't match (LLM hallucinated a different source identity)
- **Files to modify:** `backend/pipeline/semantic_validation.py`
- **Tests to add:** Test that mismatched source_ids fail validation

**Task 0.2.5:** Fix V5 quote rule conflict in Validation_and_Retry_Rules.md
- V5 currently says text_provided and ocr_extracted FORBID quotes
- Owner Decision (2026-01-15) says they ALLOW quotes with unverified flag
- Fix V5 table to match the owner decision
- **Files to modify:** `docs/authoritative/spec/Validation_and_Retry_Rules.md`

**Task 0.2.6:** Clean up dead `based_on` validation code (Gap #7 — LOW)
- `validate_based_on_references()` expects a field that doesn't exist in models
- Either remove the dead code or add the field — recommend removing since it's unused
- **Files to modify:** `backend/pipeline/semantic_validation.py`

### Phase 0.3: Validate sandcastles-analysis.md

**Task 0.3.1:** Read `docs/competitive/sandcastles-analysis.md` — every line
- Cross-reference all competitive claims with objective data
- Web research to validate market positioning claims, user base assertions, feature comparisons
- Flag any claims that are unsubstantiated or incorrect
- Update the document with validation notes
- **Files to modify:** `docs/competitive/sandcastles-analysis.md`

### Phase 0.4: Fix YouTube Transcript Extractor (Entry Point 4)

The transcript extractor has 4 bugs discovered in audit. These must be fixed so Entry Point 4 works as a standalone tool.

**Task 0.4.1:** Fix async status endpoint (CRITICAL)
- `GET /transcripts/{job_id}` crashes with AttributeError — references `drive_folder_url` and `doc_urls` fields that were removed when Google Drive was replaced with Supabase (2026-01-19)
- Fix: Replace Drive references with Supabase Storage signed URL from artifacts manifest
- **Files to modify:** `backend/app/routes/transcripts_routes.py` (lines 125-127)
- **Tests to add:** Test async job status endpoint returns valid response

**Task 0.4.2:** Fix sync response empty links
- `process_transcripts_sync()` returns empty strings for `doc_url` and `folder_url`
- Fix: Return Supabase Storage signed URL for the transcript document
- **Files to modify:** `backend/services/transcript_service.py` (lines 220-221)

**Task 0.4.3:** Wire real Whisper fallback
- `_fetch_with_whisper()` in `transcripts.py` is a stub that returns None
- Real implementation exists in `whisper_client.py` (317 lines, fully functional)
- Fix: Replace stub with actual call to `transcribe_with_whisper()` from whisper_client
- **Files to modify:** `backend/integrations/transcripts.py` (lines 144-172, 291-294)
- **Tests to add:** Test Whisper fallback fires when Supadata fails

**Task 0.4.4:** Fix frontend transcript links
- Frontend shows "Open Doc" and "Open Drive Folder" links that go nowhere
- Fix: Show Supabase Storage signed URL download link, remove Drive references
- **Files to modify:** `frontend/pages/transcripts.tsx` (lines 315-369)

**Exit criteria Phase 0:**
- All legacy code archived (not deleted)
- All HIGH priority enforcement gaps fixed
- YouTube transcript extractor fully functional (sync + async + Whisper fallback)
- All tests pass
- sandcastles-analysis.md validated with objective data
- V5 quote conflict resolved
- Commit per task

---

## PHASE 1: Architecture Updates — Docs, Models, Naming

**Goal:** Update all authoritative documents and code to reflect the new architecture BEFORE building new features. This ensures everything we build in Phase 2+ is grounded in correct specs.

**Entry criteria:** Phase 0 complete, all tests pass.

### Phase 1.1: Update Authoritative Specs

**Task 1.1.1:** Update `architecture.md` (`.claude/rules/`)
- Rule 12: "Three Core Documents" → "Four Core Documents" (Doc 0/1/2/3)
- Rule 13: Doc 3 = Creator Brief (auto-generated). Doc 4 = Producer Packet (optional, user-triggered). Replace "Booster" with "Iterate: deep_dive". Replace "Addendum" with "Iterate: expand_sources".
- Add Rule for Iterate system: 5 modes, one endpoint, one storage pattern
- Add Rule for document versioning: 4-version rolling window
- **Files to modify:** `.claude/rules/architecture.md`

**Task 1.1.2:** Update RASS.md
- Add Creator Brief as Doc 3 (core)
- Move Producer Packet to Doc 4 (optional)
- Add ASSEMBLY stage that generates Creator Brief
- Replace Stage F (Booster) with Iterate system description
- Add all 5 Iterate modes with their document effects
- **Files to modify:** `docs/authoritative/spec/RASS.md`

**Task 1.1.3:** Update Document_Output_Format.md
- Add `creator_brief` to document_type enum
- Define Creator Brief schema (hook_options, core_facts, twist, analogy, personal_stakes, cliffhanger, disputed_claims, sources_for_description)
- Update Doc 3 from Producer Packet to Creator Brief
- Add Doc 4 schema for Producer Packet
- **Files to modify:** `docs/authoritative/spec/Document_Output_Format.md`

**Task 1.1.4:** Update Operational_Definitions.md
- Update document set definition (4 core + optional)
- Add Creator Brief to vocabulary
- Add Iterate system modes to vocabulary
- Replace Booster/Addendum definitions with Iterate modes
- **Files to modify:** `docs/authoritative/spec/Operational_Definitions.md`

### Phase 1.2: Backend Model Updates

**Task 1.2.1:** Create CreatorBrief Pydantic model
- Define `CreatorBriefDocument` with sections: `hook_options`, `setup`, `twist`, `core_facts`, `analogy`, `personal_stakes`, `cliffhanger`, `disputed_claims`, `description_sources`
- Each `core_fact` must reference `claim_id` from Doc 2 and `source_id` from Doc 0
- Each `hook_option` must reference the claim(s) it's derived from
- Disputed claims must include `framing` and `speaker` from enrichments
- Add validation: every reference must point to a valid claim/source
- **Files to create:** `backend/models/creator_brief.py`
- **Tests to add:** Model validation tests for all constraints

**Task 1.2.2:** Update JobRecord for Doc 3 = Creator Brief
- Current: `doc_3_path` / `producer_packet` fields reference Producer Packet
- New: `doc_3_path` references Creator Brief. Producer Packet moves to `doc_4_path`
- Add `creator_brief` field to artifacts
- Shift `producer_packet` references to Doc 4
- Update run models similarly
- **Files to modify:** `backend/models/job_record.py`, `backend/models/run_models.py`

**Task 1.2.3:** Add document versioning to storage model
- Each document version gets metadata: `version`, `created_at`, `trigger`, `source_count`, `claim_count`, `diff_summary`
- Rolling window: latest + 3 previous = 4 max
- Version cleanup: when 5th version created, oldest is dropped
- **Files to modify:** `backend/models/job_record.py`
- **Tests to add:** Version rotation tests

### Phase 1.3: Naming Renames

**Task 1.3.1:** Rename Booster → Iterate deep_dive
- Rename `booster_prompt.py` → keep file but update internal naming
- Rename `booster_stage.py` → `iterate_deep_dive_stage.py` (or integrate into unified iterate handler)
- Update all references in worker, routes, tests
- **Files to modify:** `backend/pipeline/stages/booster_stage.py`, `backend/pipeline/prompts/booster_prompt.py`, `backend/app/routes/jobs_routes.py`, `backend/worker.py`

**Task 1.3.2:** Rename more_sources → expand_sources
- Update mode enum in `job_record.py`
- Update iteration mode handler
- Update API endpoint and route
- **Files to modify:** `backend/models/job_record.py`, `backend/app/routes/jobs_routes.py`

**Task 1.3.3:** Shift Producer Packet from Doc 3 to Doc 4
- Update `producer/gating.py` references
- Update `producer_stage.py` references
- Update storage paths: `doc_3_path` → `doc_4_path` for producer
- Update API document endpoint: `GET /jobs/{job_id}/documents/doc_3` now returns Creator Brief, `doc_4` returns Producer Packet
- **Files to modify:** `backend/pipeline/producer/gating.py`, `backend/pipeline/stages/producer_stage.py`, `backend/app/routes/jobs_routes.py`

**Exit criteria Phase 1:**
- All authoritative docs updated and internally consistent
- CreatorBrief Pydantic model exists with full validation
- All naming renames complete
- All tests pass (existing tests updated for renames)
- No references to old naming in active code (only in archive/)

---

## PHASE 2: Creator Brief — The New Doc 3 (Backend)

**Goal:** Build the Creator Brief generation pipeline. This is the hero document — the most important deliverable of the entire plan.

**Entry criteria:** Phase 1 complete, all models and specs updated.

### Phase 2.1: Creator Brief Prompt

**Task 2.1.1:** Write the Creator Brief assembly prompt
- Input: Doc 2 (Semantic Brief) data — all claims with enrichments, themes, tensions, key points
- Input: Doc 0 (Source Ledger) data — source metadata for citation formatting
- Output: CreatorBriefDocument schema
- Prompt must include all 5 required components (Source Identity Lock, Confidence Ceiling, Empty Output Permission, Layered Extraction rules, Output Schema)
- Prompt must instruct the LLM to:
  - Select 2 hook options from highest-significance claims
  - Build setup from the core theme/thesis
  - Build twist from `framing: contradicts` or `framing: disputed` claim relationships
  - Select 3-5 core facts ranked by significance, each with "say it like this" plain English phrasing
  - Build analogy from claim relationships or theme patterns
  - Build personal stakes from "why it matters" claims
  - Build cliffhanger from `framing: speculative` claims or open questions
  - Flag all disputed/speculative claims explicitly
  - Format sources for description box inclusion
- Temperature: TBD (recommend 0.3 — creative but grounded)
- **Files to create:** `backend/pipeline/prompts/creator_brief_prompt.py`

**Task 2.1.2:** Define temperature for Creator Brief stage
- Recommendation: 0.3 (same range as Producer stage 1-3 — creative but controlled)
- Get owner approval on temperature choice
- Update architecture.md Rule 16 with Creator Brief temperature
- **Files to modify:** `.claude/rules/architecture.md`

### Phase 2.2: Creator Brief Assembly Stage

**Task 2.2.1:** Build Creator Brief assembly stage
- New pipeline stage: runs after synthesis + document assembly
- Reads Doc 2 claims/themes/tensions and Doc 0 source metadata
- Calls LLM with creator_brief_prompt
- Validates output against CreatorBriefDocument schema
- Stores as Doc 3 in Supabase storage
- **Files to create:** `backend/pipeline/stages/creator_brief_stage.py`
- **Tests to add:** Unit tests with mocked LLM responses

**Task 2.2.2:** Add provenance validation for Creator Brief
- Every `core_fact` must reference a valid `claim_id` from Doc 2
- Every `claim_id` referenced must exist in the actual extraction
- Every `source_id` referenced must exist in Doc 0
- Hook options must trace to real claims
- Disputed claims must match actual framing from enrichments
- **Files to modify:** `backend/pipeline/stages/creator_brief_stage.py` (or new validation function)
- **Tests to add:** Provenance chain validation tests

**Task 2.2.3:** Integrate Creator Brief into main pipeline
- Add creator_brief_stage to the pipeline execution order (after document_assembly)
- Update job progress reporting to include Creator Brief stage
- Update narrated loading states: "Assembling Creator Brief..."
- Store Creator Brief as `doc_3_path` in job artifacts
- **Files to modify:** `backend/worker.py` (or pipeline orchestrator), `backend/models/job_record.py`

### Phase 2.3: Creator Brief Output Format

**Task 2.3.1:** Build Creator Brief markdown renderer
- Convert CreatorBriefDocument JSON → polished markdown
- Match the format from Section 8.1 of sandcastles-ux-deep-dive.md:
  - Header with topic, date, source count
  - HOOK OPTIONS (A/B) with "why it works"
  - THE SETUP
  - THE TWIST / CONTRAST MOMENT
  - CORE FACTS with "say it like" phrasing + source links
  - THE ANALOGY
  - WHAT THIS MEANS FOR YOU
  - CLIFFHANGER / OPEN LOOP ENDING
  - SOURCES (for description box)
  - CLAIMS FLAGGED AS DISPUTED OR SPECULATIVE
- Must share consistent visual language with Doc 0/1/2 markdown
- **Files to create:** `backend/pipeline/formatters/creator_brief_formatter.py`
- **Tests to add:** Formatter output tests

**Task 2.3.2:** Update document endpoint to serve Creator Brief
- `GET /jobs/{job_id}/documents/doc_3` returns Creator Brief (not Producer Packet)
- `GET /jobs/{job_id}/documents/doc_4` returns Producer Packet
- Update the document type routing in jobs_routes.py
- **Files to modify:** `backend/app/routes/jobs_routes.py`

**Task 2.3.3:** Update export pipeline (PDF/DOCX) for Creator Brief
- Creator Brief should export with the same visual language
- Consistent headers, formatting, citation style
- **Files to modify:** `backend/app/routes/export_routes.py` (or related export logic)

**Exit criteria Phase 2:**
- Creator Brief generates successfully from real pipeline output
- Provenance chain validated (every fact → claim → source)
- Markdown output matches the agreed format
- API endpoint serves Creator Brief as Doc 3
- All tests pass
- Integration test: run full pipeline, verify Doc 3 is Creator Brief with valid references

---

## PHASE 3: Document Versioning & Iterate Consolidation

**Goal:** Implement the 4-version rolling window and consolidate Booster/Addendum/Iterate into one system.

**Entry criteria:** Phase 2 complete, Creator Brief generating correctly.

### Phase 3.1: Document Versioning Backend

**Task 3.1.1:** Implement version storage schema
- Each document version stored at: `research-jobs/{job_id}/doc_{N}/v{version}.json`
- Version metadata: `version`, `created_at`, `trigger`, `source_count`, `claim_count`, `diff_summary`
- Latest version pointer: `research-jobs/{job_id}/doc_{N}/latest.json` (symlink or metadata file)
- **Files to modify:** `backend/integrations/supabase_storage.py`, `backend/models/job_record.py`

**Task 3.1.2:** Implement rolling window cleanup
- When 5th version created, drop oldest
- Independent per document (Doc 0 can be v5 while Doc 3 is v2)
- Cleanup happens at write time, not async
- **Files to create:** `backend/pipeline/version_manager.py`
- **Tests to add:** Version rotation tests (create 5, verify oldest dropped)

**Task 3.1.3:** Implement diff summary generation
- When new version created, compare to previous version
- Generate diff summary: "+N sources, +N claims, +N themes" (or "-N" for removals)
- Store in version metadata
- **Files to modify:** `backend/pipeline/version_manager.py`

**Task 3.1.4:** Update document API to support versions
- `GET /jobs/{job_id}/documents/doc_{N}` — returns latest version (default)
- `GET /jobs/{job_id}/documents/doc_{N}?version=2.0` — returns specific version
- `GET /jobs/{job_id}/documents/doc_{N}/versions` — lists all available versions with metadata
- **Files to modify:** `backend/app/routes/jobs_routes.py`

### Phase 3.2: Iterate System Consolidation

**Task 3.2.1:** Create unified Iterate API endpoint
- `POST /jobs/{job_id}/iterate` with body: `{ "mode": "deep_dive|expand_sources|deeper|different_angle|custom", ...mode_specific_params }`
- This replaces: `POST /jobs/{job_id}/booster`, `POST /jobs/{job_id}/iterate` (old), and the addendum flow
- Route to mode-specific handlers
- **Files to modify:** `backend/app/routes/jobs_routes.py`

**Task 3.2.2:** Create unified Iterate task dispatcher
- One Celery task: `iterate_job(job_id, mode, params)`
- Dispatches to mode-specific handler based on `mode` field
- Each handler knows which docs it affects (see Iterate mode table in deep-dive doc)
- All handlers create new versions via version_manager
- **Files to create:** `backend/pipeline/iterate/dispatcher.py`
- **Files to modify:** `backend/worker.py`

**Task 3.2.3:** Migrate deep_dive (formerly Booster)
- Move booster_stage.py logic into `backend/pipeline/iterate/modes/deep_dive.py`
- Same validation: gap_id/theme_id ref checking, anti-generic detection
- Output: new version of Doc 1 only
- **Files to create:** `backend/pipeline/iterate/modes/deep_dive.py`
- **Files to archive:** `backend/pipeline/stages/booster_stage.py` (move to archive/)

**Task 3.2.4:** Migrate expand_sources (formerly Addendum + more_sources)
- Consolidate addendum logic and more_sources iteration into one handler
- Triggers full pipeline re-run with expanded source set
- Output: new versions of Doc 0, 1, 2, 3
- **Files to create:** `backend/pipeline/iterate/modes/expand_sources.py`

**Task 3.2.5:** Migrate deeper, different_angle, custom modes
- These largely exist already — wrap them in the new iterate structure
- Ensure each creates new versions via version_manager
- Ensure each updates the correct documents per the Iterate mode table
- **Files to create:** `backend/pipeline/iterate/modes/deeper.py`, `backend/pipeline/iterate/modes/different_angle.py`, `backend/pipeline/iterate/modes/custom.py`

**Task 3.2.6:** Update iterate storage pattern
- All iterations stored under: `jobs/{job_id}/iterations/{iteration_id}/`
- Each iteration records: mode, params, which doc versions were created, timestamp
- One source of truth for iteration history
- **Files to modify:** `backend/models/job_record.py`

**Exit criteria Phase 3:**
- Document versioning works: create, retrieve by version, list versions, rolling window cleanup
- All 5 Iterate modes work through unified endpoint
- Old booster/addendum/iterate endpoints deprecated (return 410 with migration message)
- All tests pass
- Integration test: run deep_dive → expand_sources → deeper cycle, verify version chain

---

## PHASE 4: Frontend — Document Layer Model & UI Overhaul

**Goal:** Transform the frontend from tab-based document display to the layer model with Creator Brief as hero. Implement progressive disclosure, narrated loading, card-based selection.

**Entry criteria:** Phase 3 complete, backend API stable.

### Phase 4.1: Creator Brief Hero View

**Task 4.1.1:** Build CreatorBriefView component
- Full-width document view matching the Section 8.1 format
- Sections: Hook Options, Setup, Twist, Core Facts, Analogy, Personal Stakes, Cliffhanger
- Each core fact is clickable → shows claim detail inline (slide-over or expansion)
- Disputed claims section with warning icons and framing labels
- Sources section formatted for description box copy-paste
- **Files to create:** `frontend/components/creator-brief/CreatorBriefView.tsx`

**Task 4.1.2:** Build contextual navigation from hero view
- "View Research" button → navigates to Doc 2 (Semantic Brief)
- "Go Deeper" button → navigates to Doc 1 (Jump-Start)
- "View Sources" button → navigates to Doc 0 (Source Ledger)
- "Generate Script" button → greyed out / locked with "Coming Soon" (v2)
- Navigation is contextual, not tab-based
- **Files to modify:** `frontend/components/creator-brief/CreatorBriefView.tsx`

**Task 4.1.3:** Build fact drill-down component
- When user clicks a fact in the Creator Brief
- Slide-over or inline expansion shows:
  - The specific claim from Doc 2
  - Speaker attribution
  - Rhetorical framing
  - Significance score
  - Related claims (supports, contradicts, qualifies)
  - Direct link to the source in Doc 0
- **Files to create:** `frontend/components/creator-brief/ClaimDrillDown.tsx`

### Phase 4.2: Document Drawer

**Task 4.2.1:** Build Document Drawer sidebar
- Collapsible sidebar listing all documents
- CORE section: Creator Brief (star badge), Semantic Brief, Jump-Start, Source Ledger
- OPTIONAL section: Producer Packet (greyed if not generated), Script (locked until v2)
- Click any document → full-width view replaces current content
- Creator Brief always has hero badge
- **Files to create:** `frontend/components/document-drawer/DocumentDrawer.tsx`

**Task 4.2.2:** Integrate version selector into document drawer
- Each document shows current version (e.g., "v3.0")
- Version dropdown shows all available versions with metadata (date, trigger, diff summary)
- Selecting a version switches the document view
- **Files to create:** `frontend/components/document-drawer/VersionSelector.tsx`

### Phase 4.3: Iterate UI Consolidation

**Task 4.3.1:** Build unified Iterate dialog
- Replace separate Booster button + Iterate dialog with one "Improve Research" button
- Shows 5 mode cards:
  - Deep Dive — "Find gaps, get search directions"
  - Expand Sources — "Add more sources"
  - Go Deeper — "Re-extract with more detail"
  - Different Angle — "Same data, new perspective"
  - Custom — "Your own instructions"
- Mode-specific input forms (e.g., URLs for expand_sources, angle text for different_angle)
- Submits to unified `POST /jobs/{job_id}/iterate` endpoint
- **Files to create:** `frontend/components/iterate/IterateDialog.tsx`
- **Files to modify:** `frontend/pages/jobs/[id].tsx`

### Phase 4.4: Narrated Loading States

**Task 4.4.1:** Update pipeline progress display
- Replace spinner/generic progress with narrated stage descriptions
- Map pipeline stages to human-readable descriptions:
  - `source_identity` → "Analyzing your sources..."
  - `semantic_extraction` → "Extracting claims from N sources..."
  - `semantic_validation` → "Verifying quotes and citations..."
  - `gap_analysis` → "Identifying research gaps..."
  - `semantic_synthesis` → "Connecting themes across sources..."
  - `document_assembly` → "Building your documents..."
  - `creator_brief_assembly` → "Assembling your Creator Brief..."
- Show real counts where available (N claims found, N themes detected)
- **Files to modify:** `frontend/lib/constants.ts` (STAGE_LABELS), `frontend/components/job-detail/` (progress display components)

### Phase 4.5: Output Format Consistency

**Task 4.5.1:** Create unified document header component
- Shared header for ALL documents: document type badge, topic, date, source count, version
- Color-coded by document type (consistent with existing scheme but extended for Creator Brief)
- **Files to create:** `frontend/components/common/DocumentHeader.tsx`

**Task 4.5.2:** Create unified visual language tokens
- Disputed claim styling: warning icon + framing label (same everywhere)
- Verified fact styling: checkmark + source link (same everywhere)
- Source citation styling: consistent format across Brief, Research, and Ledger
- Significance indicators: visual ranking (high/medium/low)
- **Files to create:** `frontend/components/common/ClaimIndicators.tsx`

**Task 4.5.3:** Retrofit existing document views with unified components
- Update DocumentViewerModal to use new header and visual language
- Ensure Doc 0, 1, 2 views match the same design language as Creator Brief
- **Files to modify:** `frontend/components/job-card/DocumentViewerModal.tsx`

### Phase 4.6: All Four Entry Points in the UI

**Task 4.6.1:** Build unified dashboard with 4 entry points
- Dashboard shows 4 clear entry cards/sections:
  1. **"What do you want to research?"** — Topic input → Entry Point 1
  2. **"I have my own sources"** — URL/doc input → Entry Point 2
  3. **"Extract claims from text"** — Text input → Entry Point 3
  4. **"Get YouTube transcripts"** — URL input → Entry Point 4
- Each entry point has its own visual identity but shares the same design language
- Progressive disclosure: user picks an entry → form expands → they submit
- **Files to modify:** `frontend/pages/dashboard.tsx`

**Task 4.6.2:** Build Entry Point 2 flow (Sources-First)
- User pastes URLs / uploads documents
- Sources auto-validated for accessibility
- Pipeline runs with narrated loading
- User lands on Creator Brief hero view
- This is largely the existing flow — ensure it works with new Creator Brief hero landing
- **Files to modify:** `frontend/components/unified-input/UnifiedInputPanel.tsx`

**Task 4.6.3:** Build Entry Point 3 flow (Claim Extractor — Standalone)
- User provides text via textarea or document upload
- Submits to `POST /jobs/claim-extraction` (existing endpoint)
- Results displayed in a standalone claims viewer (NOT the full pipeline hero view)
- Claims shown with confidence, speaker, framing, significance enrichments
- No Creator Brief, no Doc 0/1/2 — just claim extraction results
- **Files to create:** `frontend/components/claim-extractor/ClaimExtractorView.tsx`

**Task 4.6.4:** Ensure Entry Point 4 flow works (YouTube Transcript Extractor — Standalone)
- User provides YouTube URLs
- Submits to `POST /transcripts` (existing endpoint, fixed in Phase 0.4)
- Results displayed in the existing transcript viewer
- Must work independently from the research pipeline
- Verify the fixes from Phase 0.4 render correctly in the frontend
- **Files to verify:** `frontend/pages/transcripts.tsx`

**Task 4.6.5:** Build card-based source approval UI (Entry Point 1 uses this)
- When sources are discovered (Entry Point 1), show them as cards
- Each card shows: title, URL, quality score, source type, brief description
- User can approve/reject each source
- Approved sources auto-flow into pipeline (requirement #4)
- **Files to modify:** `frontend/components/job-detail/SourceReviewPanel.tsx` (exists — enhance with card UI)

**Exit criteria Phase 4:**
- Creator Brief is the hero landing view after pipeline completion (Entry Points 1 & 2)
- All 4 entry points accessible from dashboard
- Claim Extractor has its own standalone output view (Entry Point 3)
- YouTube Transcript Extractor works independently with fixed links (Entry Point 4)
- Document drawer provides access to all docs with version selector
- Iterate dialog shows 5 modes in unified UI
- Narrated loading states show real pipeline stages
- All documents share consistent visual language
- Source approval uses card-based UI
- All frontend tests pass, no TypeScript errors, build succeeds

---

## PHASE 5: Search/Discovery Flow (Entry Point 1) + Quick Brief

**Goal:** Build the topic-first entry point with source discovery, relevance validation, Quick Brief preview, and auto-pipeline injection.

**Entry criteria:** Phase 4 complete, frontend stable.

### Phase 5.1: Search Backend

**Task 5.1.1:** Design search/discovery API
- `POST /jobs/search` — takes a topic, returns candidate sources
- Internally: uses existing search integrations (web search, news, YouTube) to discover sources
- Returns sources with metadata: title, URL, snippet, estimated quality, source type
- Does NOT start the full pipeline — discovers sources for the Quick Brief + approval
- **Files to create:** `backend/app/routes/search_routes.py`

**Task 5.1.2:** Implement relevance validation (Requirement #3)
- Each discovered source goes through a relevance check before being shown to the user
- Scoring: topic relevance, source authority, content freshness, accessibility
- Filter out: paywalled content, login walls, ad-heavy pages, irrelevant results
- Only sources passing the quality threshold flow into Quick Brief generation
- **Files to create:** `backend/pipeline/search/relevance_validator.py`

### Phase 5.2: Quick Brief (Entry Point 1 Preview)

**Task 5.2.1:** Build Quick Brief generation pipeline
- After sources are discovered and relevance-validated, run a LIGHTWEIGHT extraction + synthesis
- Uses the same CreatorBrief schema/format as the full Creator Brief
- But generated from a faster pass — lighter extraction, less depth
- Purpose: show the user "here's what your research could look like" BEFORE they commit
- The Quick Brief is a PREVIEW, not a final document — it gets replaced by the real Doc 3 after approval
- **Files to create:** `backend/pipeline/stages/quick_brief_stage.py`
- **Key design decision:** Quick Brief should be fast (seconds, not minutes). Consider using a single LLM call that takes source snippets + topic → Creator Brief format directly, bypassing full per-source extraction. This is acceptable because it's a preview, not the final product.

**Task 5.2.2:** Design Quick Brief → Approval → Full Pipeline flow
- API endpoint: `POST /jobs/search` returns `{ sources: [...], quick_brief: {...} }`
- Or: Quick Brief generated async after search, returned via polling
- User sees Quick Brief + source cards side by side
- User reviews the preview, decides if the sources are worth a full pipeline run
- User approves sources → triggers `POST /jobs/mixed-input` with approved sources
- Full pipeline runs → real Creator Brief replaces Quick Brief
- **Files to modify:** `backend/app/routes/search_routes.py`, `backend/app/routes/jobs_routes.py`

**Task 5.2.3:** Define Quick Brief vs Creator Brief distinction
- Quick Brief uses the SAME schema as Creator Brief (CreatorBriefDocument)
- Quick Brief is tagged with `is_preview: true` or `brief_type: "quick"` in metadata
- Quick Brief is NOT stored as a document version — it's ephemeral
- When the full pipeline completes, the real Creator Brief (Doc 3 v1.0) replaces it
- Frontend must clearly communicate "this is a preview" vs "this is your final brief"
- **Files to modify:** `backend/models/creator_brief.py`

### Phase 5.3: Search Frontend

**Task 5.3.1:** Build topic-first entry UI (Entry Point 1)
- Entry point on dashboard: "What do you want to research?"
- Single text input for topic
- Optional depth/category selection (reuse existing controls)
- Submits to search API → shows narrated loading ("Finding sources...")
- **Files to modify:** `frontend/pages/dashboard.tsx`

**Task 5.3.2:** Build Quick Brief + Source Approval view
- Split view or stacked view:
  - LEFT/TOP: Quick Brief preview (Creator Brief format with "Preview" badge)
  - RIGHT/BOTTOM: Source cards with approve/reject controls
- User reads the Quick Brief to evaluate research quality
- User approves/rejects individual sources
- "Run Full Research" button → approved sources enter full pipeline
- Narrated loading transitions to job detail page
- **Files to create:** `frontend/components/search/QuickBriefPreview.tsx`, `frontend/components/search/SearchApprovalView.tsx`

**Task 5.3.3:** Build full flow: Topic → Quick Brief → Approval → Pipeline → Creator Brief
- End-to-end flow:
  1. User enters topic on dashboard
  2. Narrated loading: "Discovering sources..."
  3. Quick Brief + source cards appear
  4. User reviews preview, approves sources
  5. "Run Full Research" → narrated loading: "Extracting claims from N sources..."
  6. Full pipeline completes → Creator Brief hero view replaces Quick Brief
  7. Document drawer shows all 4 core docs
- **Files to modify:** `frontend/pages/dashboard.tsx`, `frontend/pages/jobs/[id].tsx`

**Task 5.3.4:** Ensure Entry Point 2 still works (Requirement #2 — skip-to-sources)
- The existing sources-first entry point must remain fully functional
- User can still paste URLs / upload documents directly
- No Quick Brief for Entry Point 2 — user already has their sources, skip to full pipeline
- Both entry points converge to the same pipeline → same Creator Brief hero view
- **Files to verify:** `frontend/components/unified-input/UnifiedInputPanel.tsx`

**Exit criteria Phase 5:**
- Topic-first entry: user enters topic → sources discovered → Quick Brief preview → approval → full pipeline → Creator Brief
- Quick Brief shows same format as Creator Brief with "Preview" badge
- Sources-first entry: user pastes URLs → pipeline → Creator Brief (no regression, no Quick Brief)
- Claim Extractor and Transcript Extractor still work independently (no regression)
- Relevance validation filters low-quality sources before Quick Brief
- Auto-flow: approved sources enter pipeline without manual intervention
- All 4 entry points produce their expected outputs
- All tests pass

---

## Cross-Phase Concerns

### Testing Strategy
- **Unit tests:** Every new model, validator, stage, and component
- **Integration tests:** Full pipeline run producing Doc 0, 1, 2, 3 with valid provenance chain
- **Regression tests:** Existing pipeline behavior must not break — Doc 0, 1, 2 should still generate correctly
- **Frontend tests:** Component rendering, navigation flow, document switching

### Rollback Strategy
- Each phase is independently deployable
- Phase 0-1 are non-breaking (cleanup + spec updates)
- Phase 2 adds new functionality (Creator Brief) without removing existing
- Phase 3 deprecates old endpoints but keeps them returning 410
- Phase 4 is frontend-only — can be reverted without backend changes
- Phase 5 adds new entry point — doesn't modify existing sources-first flow

### Files NOT to Touch
- `backend/pipeline/prompts/modes/*.py` — extraction mode prompts are stable
- `backend/pipeline/mode_selector.py` — single source of truth, no changes needed
- `backend/pipeline/quote_verification.py` — working correctly
- Core extraction and synthesis stages — these are stable

### Migration Path for Existing Jobs
- Existing jobs (pre-Creator Brief) will NOT have Doc 3
- Frontend must handle missing Doc 3 gracefully (show Doc 2 as hero fallback)
- No retroactive Creator Brief generation for old jobs
- Version selector only appears for docs that have multiple versions

---

## Summary: What Gets Built, In Order

| Phase | What | Key Deliverable |
|---|---|---|
| 0 | Clean house | No legacy contamination, enforcement gaps fixed, transcript extractor working, competitive claims validated |
| 1 | Update specs + models | All docs and models reflect new architecture (4 core docs, Iterate system, versioning) |
| 2 | Build Creator Brief | Doc 3 generates with full provenance chain, polished markdown output |
| 3 | Versioning + Iterate | 4-version rolling window, 5 unified Iterate modes |
| 4 | Frontend overhaul | 4 entry points on dashboard, layer model, hero view, document drawer, narrated loading, consistent design language, standalone views for Claim Extractor + Transcript Extractor |
| 5 | Search + Quick Brief | Topic-first entry with Quick Brief preview, relevance validation, source approval, auto-flow to full pipeline |

**The Four Entry Points:**

| # | Entry Point | Flow | Output |
|---|---|---|---|
| 1 | Topic-First | Topic → discover sources → Quick Brief preview → approve → full pipeline | Creator Brief + Doc 0/1/2 |
| 2 | Sources-First | Paste URLs → full pipeline | Creator Brief + Doc 0/1/2 |
| 3 | Claim Extractor | Provide text → extraction only | Standalone claim results |
| 4 | Transcript Extractor | YouTube URLs → transcript extraction | Standalone transcript output |

**Total estimated tasks:** ~50 across 6 phases
**Sequential execution:** One phase at a time, one task at a time, commit per task

---

## Appendix A: Cross-References to sandcastles-ux-deep-dive.md

This plan is the implementation roadmap. The strategic context, competitive analysis, and design rationale live in `docs/competitive/sandcastles-ux-deep-dive.md`. **If this session crashes or compacts, that document is the complete record of WHY we're doing everything in this plan.**

| Topic | Where to Find It |
|---|---|
| Sandcastles full app structure (all 7 sections) | `sandcastles-ux-deep-dive.md` Section 2 (lines 16-111) |
| Sandcastles 5-step creation flow with internal pipeline steps | Section 2.3 (lines 29-95) |
| Full example script (174 words, dollar reserve currency) | Section 3 (lines 114-127) |
| Script analysis: human-ness 7.5/10, quality 6.5/10, fatal flaw | Section 4 (lines 130-176) |
| Sandcastles structural weaknesses we exploit | Section 5 (lines 179-194) |
| Research Agent competitive positioning & core promise | Section 6 (lines 197-204) |
| The 6 requirements before rebuilding search | Section 7 (lines 208-217) |
| Creator Brief format (section-by-section structure) | Section 8.1 (lines 225-274) |
| How v3 claim enrichments power each brief section | Section 8.3 (lines 285-297) |
| "Best of both worlds" synthesis statement | Section 9 (lines 300-313) |
| What we're taking from Sandcastles (6 items) | Section 10.1 (lines 318-342) |
| What we're NOT taking (6 items) | Section 10.2 (lines 344-357) |
| Core differentiators table | Section 10.3 (lines 358-371) |
| Document architecture: Doc 0/1/2/3 reconciliation | Section 11.0 (lines 375-739) |
| Jump-Start is a research compass, NOT a Creator Brief | Section 11.0.1 (lines 388-392) |
| Entry Point A vs Entry Point B journey differences | Section 11.0.2 (lines 404-449) |
| Document access from hero view (contextual nav + drawer) | Section 11.0.3 (lines 451-506) |
| Complete document registry (core + optional + iterate) | Section 11.1.4 (lines 629-704) |
| Iterate system: 5 modes consolidated | Section 11.2 (lines 741-842) |
| Document versioning: 4-version rolling window | Section 11.2.4 (lines 843-959) |
| Output format consistency requirements | Section 11.3 (lines 963-972) |
| Script Writer v2 vision (tone/length/style controls) | Section 12 (lines 991-1027) |
| Voice Mimicry v2+ feature (requires separate design cycle) | Section 12.4 (lines 1006-1027) |
| Full user journey (end state vision) | Section 13 (lines 1031-1061) |
| UI patterns worth adopting from Sandcastles | Section 14 (lines 1065-1071) |
| Rule enforcement audit (what's enforced vs gaps) | Section 16 (lines 1091-end) |
| Enforcement gaps: 8 rules in prompts but NOT in code | Section 16.3 (lines 1157-1170) |
| Authoritative doc conflicts found | Section 16.4 (lines 1172-1182) |
| Naming audit: old → new | Section 16.5 (lines 1184-1194) |

---

## Appendix B: Strategic Decisions Made (Not to Be Re-Litigated)

These decisions were made during the planning conversation. They are FINAL unless the owner explicitly reopens them.

1. **Creator Brief is Doc 3 (auto-generated, core).** Producer Packet moves to Doc 4 (optional). This was decided after clarifying that Jump-Start Directions is a research compass, not a production document.

2. **4 entry points, not 2.** Topic-First, Sources-First, Claim Extractor (standalone), YouTube Transcript Extractor (standalone). Each has its own flow and output.

3. **Quick Brief for Entry Point 1.** A lightweight preview in Creator Brief format, generated from discovered sources BEFORE approval. Ephemeral — replaced by real Doc 3 after full pipeline.

4. **Iterate system consolidates Booster + Addendum + old Iterate.** One API endpoint, 5 modes (deep_dive, expand_sources, deeper, different_angle, custom), one storage pattern, one versioning system.

5. **Booster renamed to deep_dive. Addendum renamed to expand_sources. more_sources renamed to expand_sources.**

6. **4-version rolling window.** Latest + 3 previous per document. Independent versioning per document. Triggered by Iterate modes.

7. **Documents are layers, not tabs.** Creator Brief is the hero. User navigates contextually (View Research, Go Deeper, View Sources) or via the document drawer. Never shown all at once.

8. **Everything traces back to Doc 0.** The provenance chain is: Script → Creator Brief → Semantic Brief → Source Ledger. No document can contain a fact that doesn't trace through this chain. This is the core differentiator vs Sandcastles (which has no chain at all).

9. **Script Writer is v2, Voice Mimicry is v2+.** Not in this plan. Creator Brief must be stable first.

10. **Enforcement via code, not just prompts.** Every constraint that can be checked programmatically MUST be. Prompts are suggestions; code is guarantees.

11. **The user is never overwhelmed.** One document at a time. Progressive disclosure. The Creator Brief is always the center of gravity.

---

## Appendix C: Transcript Extractor Bugs Found (Phase 0.4 Reference)

Full audit results for the YouTube Transcript Extractor:

**Bug 1 — Async status endpoint crashes (CRITICAL)**
- File: `backend/app/routes/transcripts_routes.py` lines 125-127
- Cause: References `drive_folder_url` and `doc_urls` fields removed when Google Drive was replaced with Supabase (2026-01-19)
- Impact: `GET /transcripts/{job_id}` throws AttributeError, frontend polling fails for async jobs (>5 videos)

**Bug 2 — Sync response returns empty links**
- File: `backend/services/transcript_service.py` lines 220-221
- Cause: `doc_url` and `folder_url` hardcoded to `""` after Drive removal
- Impact: Frontend "Open Doc" button goes nowhere

**Bug 3 — Whisper fallback is a stub**
- File: `backend/integrations/transcripts.py` lines 144-172
- Cause: `_fetch_with_whisper()` is a placeholder returning None. Real implementation exists in `whisper_client.py` (317 lines, fully functional) but never called.
- Impact: If Supadata fails, transcript extraction fails entirely. No fallback.

**Bug 4 — Frontend shows dead Google Drive links**
- File: `frontend/pages/transcripts.tsx` lines 315-369
- Cause: Still rendering "Open Doc" and "Open Drive Folder" links from pre-Supabase era
- Impact: Links go nowhere

**What works:** Sync extraction (if Supadata configured), Celery task, Supabase storage upload, progress tracking, frontend form/URL validation.

**Fallback chain status:** Supadata Native → Supadata AI → Whisper (BROKEN stub) → youtube-transcript-api (REMOVED, fails on cloud). Only Supadata tiers functional.

---

*Plan status: DRAFT — 2026-03-11. Awaiting owner approval before implementation begins.*
*Reference document: `docs/competitive/sandcastles-ux-deep-dive.md` — read this for full strategic context.*
