# Scout Report: Research Agent Codebase Structure
**Date:** 2026-01-23  
**Scope:** Comprehensive codebase mapping for code review  
**Status:** Complete

---

## Executive Summary

Research Agent is a **semantic document analysis system** built on FastAPI + Next.js, currently running on production (Vercel + Railway). The system has evolved from a legacy discovery-based pipeline to a **semantic-only pipeline** with 6 analysis modes (transcript_grounded, caption_grounded, video_only, text_provided, ocr_extracted, article_fetched).

**Key Metrics:**
- **Backend:** 41,126 lines of Python (40% tests, 60% implementation)
- **Frontend:** Next.js with 8 pages + 10+ component directories
- **Tests:** 960+ passing tests across 40+ test files
- **Pipeline Stages:** 10 active stages (source_identity → completion)
- **Recent Work:** Iteration loop + job detail page refactor (Jan 23, 2026)

---

## Part 1: Backend Structure

### 1.1 Application Core

| File | Purpose | Key Exports |
|------|---------|-------------|
| **backend/app/main.py** | FastAPI app entry point (27 routes) | `app` (FastAPI instance) |
| **backend/config.py** | Settings with Pydantic validation | `get_settings()` |
| **backend/worker.py** | Celery task definitions (4 active tasks) | `run_research_job`, `run_gemini_video_job`, `run_booster_task`, `run_producer_task`, `run_iteration_task` |

**Recent Changes (Jan 2026):**
- Removed all legacy discovery stage calls
- Semantic pipeline is now the **only** active pipeline
- 4 Celery tasks handle: research jobs, video analysis, booster, producer, iteration

### 1.2 API Routes (backend/app/routes/)

| Route Module | Endpoints | Status |
|--------------|-----------|--------|
| **jobs_routes.py** | POST/GET /jobs, /iterate, /booster, /producer-packet | Active (main) |
| **settings_routes.py** | GET/PUT /settings, /validate-folder | Active |
| **transcripts_routes.py** | POST /transcripts, GET status | Active |
| **admin_routes.py** | GET /admin/*, user mgmt, error logs | Active |
| **export_routes.py** | PDF/CSV export, clip packaging | Active |
| **share_routes.py** | Job sharing & guest access | Active |

**Critical File: jobs_routes.py**
- 400+ lines
- New endpoints: `POST /jobs/{id}/iterate`, `POST /jobs/{id}/booster`, `POST /jobs/{id}/producer-packet`
- Input modes: video, text, screenshot, mixed, article
- Iteration tracking with status polling

### 1.3 Models (backend/models/)

| Model | Purpose | Lines |
|-------|---------|-------|
| **job_record.py** | Job storage, artifacts, iterations | 300+ |
| **semantic_units.py** | SemanticExtractionResult, KeyPoint, Quote, Claim, Theme, Tension, Gap | 250+ |
| **document_outputs.py** | SourceLedger, JumpStartDirections, SemanticBrief, Addendum | 300+ |
| **producer_models.py** | ProducerPacket with 8 sub-models | 400+ |
| **booster_models.py** | BoosterOutput, ContextBundle, research directions | 150+ |
| **job_config.py** | JobConfig, HallucinationConfig, AnalysisMode enum | 200+ |
| **semantic_extraction_schema.py** | Pydantic schema for Gemini response (no defaults) | 80+ |

**Key Design Decisions:**
- `Artifacts` model stores: doc_0/1/2 paths (storage) or inline data, producer_packet, booster_output, iterations
- `IterationRequest` captures mode + user_prompt
- `IterationOutputs` stores doc paths (baseline vs iteration versions kept separate)

### 1.4 Pipeline Stages (backend/pipeline/stages/)

**Order of Execution:**

```
stage_0:   initialization          (load job config, set up context)
stage_1:   source_identity         (resolve analysis modes from inputs)
stage_2:   semantic_extraction     (Gemini per-source isolation)
stage_3:   semantic_validation     (quote verification, confidence ceilings)
stage_4:   gap_analysis            (identify missing coverage)
stage_5:   semantic_synthesis      (cross-source themes/tensions)
stage_6:   document_assembly       (assemble Doc 0/1/2)
stage_9:   drive_upload            (upload to Drive/Supabase)
stage_10:  completion              (finalize artifacts manifest)
```

**Extended Pipeline (on-demand):**
```
stage_booster:        deep research directions
stage_cross_ref:      cross-reference new sources vs originals
stage_producer:       4-stage creative interpretation pipeline
stage_iteration:      iterate on completed jobs with new research angle
```

| Stage File | Responsibility | Confidence Ceiling |
|------------|------------------|------|
| **source_identity.py** | Map inputs to AnalysisMode (6 modes) | – |
| **semantic_extraction.py** | Call Gemini per source (isolated calls) | Mode-specific |
| **semantic_validation_stage.py** | Quote verification, ceiling enforcement | Enforced |
| **gap_analysis.py** | Identify gaps in coverage | – |
| **semantic_synthesis.py** | Cross-source theme synthesis | Medium |
| **document_assembly.py** | Assemble Doc 0/1/2 markdown | – |
| **booster_stage.py** | Generate research direction suggestions | Low |
| **cross_reference.py** | Find supports/contradicts between versions | – |
| **producer_stage.py** | 4-stage creative interpretation | Variable (0.3-0.5) |

**Atomic Operations:**
- Each stage wraps logic in try/except with `ctx.add_warning()`
- Non-fatal errors don't stop pipeline
- Failures logged to job.warnings

### 1.5 Prompts (backend/pipeline/prompts/)

**Structure:**
```
prompts/
├── modes/               (6 analysis mode prompts)
│   ├── base.py          (shared 5 components: lock, ceiling, empty output, layers, schema)
│   ├── transcript_grounded.py
│   ├── caption_grounded.py
│   ├── video_only.py
│   ├── text_provided.py
│   ├── ocr_extracted.py
│   └── article_fetched.py
├── semantic_extraction_prompt.py  (dispatcher to mode prompts)
├── semantic_synthesis_prompt.py   (cross-source analysis)
├── gap_analysis_prompt.py
├── booster_prompt.py              (hallucination protection rules)
├── producer_prompt.py             (4 stage prompts with temp variation)
└── cross_reference_prompt.py
```

**Critical: 5 Required Components (per architecture.md)**
1. **Source Identity Lock** - Prevents mode confusion
2. **Confidence Ceiling Declaration** - Enforces mode limits
3. **Empty Output Permission** - Returns [] if no content found
4. **Layered Extraction** - LAYER 1 (explicit) → LAYER 2 (patterns) → LAYER 3 (themes)
5. **Output Schema** - Pydantic model for JSON response

### 1.6 State Management (backend/state/)

| Component | Responsibility |
|-----------|-----------------|
| **factory.py** | Job store factory (Supabase impl) |
| **impl/supabase.py** | CRUD operations for jobs (400+ lines) |
| **impl/supabase_store.py** | Atomic job updates, partial updates, migrations |

**Key Functions:**
- `create_job()` - Creates new job record
- `get_job(job_id)` - Fetches job with full context
- `update_job()` - Atomic or partial updates
- `_update_job_atomic()` - Handles writes with `needs_atomic=True`

**Recent Bug Fix (Jan 21):**
- Guard added: If `needs_atomic=True` AND `artifacts!=None`, raise `ValueError`
- Prevents silent data loss from mixing atomic + non-atomic update paths

### 1.7 Integrations (backend/integrations/)

| Client | Purpose | Status |
|--------|---------|--------|
| **gemini_client.py** | Google Gemini API (extraction, synthesis) | Active |
| **openai_client.py** | OpenAI GPT-4o (LLM Judge fallback) | Active |
| **youtube_client.py** | YouTube Data API (transcripts) | Active |
| **whisper_client.py** | OpenAI Whisper (fallback transcription) | Active |
| **jina_reader_client.py** | Jina Reader (article extraction) | Active |
| **supabase_storage.py** | Supabase Storage (Doc upload) | Active |

**Gemini Client (gemini_client.py):**
- `generate_json()` - Structured JSON response with schema validation
- Max output tokens: 16384 (prevents truncation)
- Temperature: 0.1 (extraction) → 0.2-0.5 (synthesis/creative)

### 1.8 Validation & Quality (backend/pipeline/)

| Module | Purpose |
|--------|---------|
| **quote_verification.py** | Fuzzy matching against source (80%+ threshold) |
| **semantic_validation.py** | Confidence penalty weights, ceiling enforcement |
| **llm_judge.py** | GPT-4o cross-model validation (optional flag) |
| **rag_grounding.py** | RAG-style claim verification (optional flag) |
| **quality_gate.py** | Source deduplication, junk filtering |

**Confidence Ceilings (from mode_selector.py):**
```
transcript_grounded: HIGH (0.8-1.0)
caption_grounded: MEDIUM (0.5-0.8)
video_only: LOW (0.3-0.5)
text_provided: MEDIUM + unverified warning
ocr_extracted: MEDIUM + OCR warning
article_fetched: HIGH
```

---

## Part 2: Frontend Structure

### 2.1 Pages (frontend/pages/)

| Page | Purpose | Status |
|------|---------|--------|
| **index.tsx** | Landing page | Active |
| **dashboard.tsx** | Job list + L0/L1 expansion | Active (refactored Jan 23) |
| **jobs/[id].tsx** | Job detail page with artifact grid | NEW (Jan 23) |
| **settings.tsx** | User settings, Drive integration | Active |
| **login.tsx** | Supabase auth | Active |
| **transcripts.tsx** | Standalone transcript extraction | Active |
| **admin/** | Admin dashboard | Active |

**Recent Refactor (Jan 23):**
- **Progressive Disclosure Pattern:**
  - Dashboard (L0): Job list with status + badges
  - Job Detail Page: Full artifact grid (Doc 0/1/2/3, booster, iterations)
  - Reduces cognitive load on dashboard

### 2.2 Components (frontend/components/)

**Main Component Groups:**

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **job-card/** | Dashboard card UI | JobCard.tsx, ProgressBar.tsx, StatusBadge.tsx, TaskBadges.tsx |
| **job-detail/** | Detail page components | ArtifactCardGrid.tsx, ArtifactCard.tsx, IterationDialog.tsx, IterationSelector.tsx |
| **ui/** | Reusable UI primitives | AnimatedButton, GlowCard, ProgressRing, Skeleton |
| **common/** | Layout, navigation | Layout.tsx, Header.tsx, ErrorBoundary |
| **unified-input/** | Multi-mode input forms | source-forms/, SelectionUI |
| **dashboard/** | Dashboard utilities | JobList.tsx |
| **settings/** | Settings forms | FolderSelector.tsx, OAuthSettings |

**NEW Components (Jan 23):**
- `ArtifactCard.tsx` - Card for each doc/iteration with status
- `ArtifactCardGrid.tsx` - 2-3 column grid with 6 artifact slots
- `IterationDialog.tsx` - Modal for iteration mode selection
- `IterationSelector.tsx` - Dropdown to switch baseline vs iterations
- `TaskBadges.tsx` - Mini badges for booster/iteration/producer status
- `jobs/[id].tsx` - Full detail page

### 2.3 State Management (frontend/store/)

**Zustand Stores:**

| Store | Responsibility |
|-------|-----------------|
| **jobs.ts** | Job CRUD, refresh, iteration tracking, booster/producer status |
| **auth.ts** | User auth, Supabase client |
| **settings.ts** | User settings, folder preferences |

**Key `jobs.ts` Fields:**
```typescript
interface Job {
  id: string;
  title: string;
  status: "queued"|"running"|"completed"|"failed";
  progress: number;
  stage: string;
  artifacts: JobArtifacts;
  // Iteration tracking
  iteration_status: string;
  iteration_progress_percent: number;
  iterations: Iteration[];
  // Booster/Producer status
  booster_status: string;
  producer_status: string;
}
```

### 2.4 Utilities (frontend/lib/)

| File | Purpose |
|------|---------|
| **constants.ts** | API endpoints, HTTPS enforced |
| **pdf-export.ts** | PDF generation from documents |
| **date.ts** | DateTime formatting |

---

## Part 3: Database & Storage

### 3.1 Database Schema (Supabase PostgreSQL)

**Key Tables:**
- `jobs` - Job records with status, progress
- `job_sources` - User inputs (URLs, text, screenshots)
- `users` - User profiles, settings
- `error_logs` - Error tracking for admin
- `audit_logs` - User activity logging (optional)

**Recent Migrations:**
- **Migration 022** (Jan 23): Added `iteration_claim` column with UNIQUE constraint
  - Prevents TOCTOU race condition (user double-clicking iteration button)

### 3.2 Storage (Supabase Storage)

**Bucket Structure:**
```
documents/
  {user_id}/
    {job_id}/
      doc_0.md       (Source Ledger)
      doc_1.md       (Jump-Start Directions)
      doc_2.md       (Semantic Brief)
      doc_3.md       (Producer Packet, if generated)
      iteration_{id}/
        doc_0.md
        doc_1.md
        doc_2.md
```

**Field Mapping (job_record.py):**
```
artifacts.doc_0_path → documents/{user_id}/{job_id}/doc_0.md
artifacts.doc_1_path → documents/{user_id}/{job_id}/doc_1.md
artifacts.doc_2_path → documents/{user_id}/{job_id}/doc_2.md
artifacts.iterations[i].outputs.doc_0_path → documents/{user_id}/{job_id}/iteration_{id}/doc_0.md
```

---

## Part 4: Testing

### 4.1 Test Coverage

**Test Files by Category:**

| Category | Files | Tests | Coverage |
|----------|-------|-------|----------|
| **Models** | test_semantic_models.py, test_document_outputs.py, test_*_models.py | 200+ | 85% |
| **Stages** | test_semantic_extraction_stages.py, test_validation_stages.py, etc | 250+ | 80% |
| **Routes** | test_jobs_routes.py, test_admin_routes.py, etc | 150+ | 75% |
| **Integration** | test_semantic_pipeline_integration.py, test_worker_semantic_tasks.py | 100+ | 90% |
| **Edge Cases** | test_negative_inputs.py, test_edge_cases.py | 100+ | – |

**Total: 960+ passing tests** (41 test files)

### 4.2 Test Infrastructure

| Component | Purpose |
|-----------|---------|
| **conftest.py** | Pytest fixtures (mocked Gemini, Supabase) |
| **test_*.py** | Test files (no real API calls) |

**Recent Test Additions (Jan 23):**
- Iteration loop integration tests
- Job detail page component tests (not yet added)
- TOCTOU race condition tests (migration 022)

---

## Part 5: Recent Changes & Decisions

### 5.1 January 23, 2026: Iteration Loop + Job Detail Page

**Commits:**
- `14c3f34` - feat(backend): Add Iteration Loop with TOCTOU protection
- `09a59bb` - feat(frontend): Job Detail Page UX Refactor

**What Changed:**

**Backend:**
- Added `IterationRequest`, `IterationBundle`, `Iteration` models
- New Celery task: `run_iteration_task`
- New endpoint: `POST /jobs/{job_id}/iterate`
- Migration 022: `iteration_claim` column for atomicity

**Frontend:**
- New page: `/jobs/[id]` (job detail)
- New components: ArtifactCard, IterationDialog, ArtifactCardGrid
- Dashboard simplified: removed L2 expansion, added navigation
- Added iteration version switching UI

### 5.2 January 21-22: Bug Fixes & UI Improvements

**Booster/Producer Storage Fix:**
- Added unwrapping logic for storage-wrapped documents
- Fixed defensive parsing for b_roll field

**ADHD-Friendly UI (6 phases):**
- Increased spacing (p-3 → p-5, space-y-2 → space-y-4)
- Added section headers + dividers
- Larger status dots with glow effect
- Progressive disclosure (docs collapsed by default)

**Commits:**
- `db5b6c5` - fix: Backend storage unwrapping
- `3a02d5c` - feat: Booster accordion
- `a19fab7` - feat: ADHD-friendly UI
- `73d690b` - fix: AuthProvider hooks

### 5.3 Pre-Phase Changes (Jan 19-20): Constitution Finalization

**Major Cleanup:**
- Removed legacy discovery pipeline (stages 0-6 disabled)
- Removed unused integrations (Exa, Perplexity, Reddit, Serper, Tavily)
- Removed Slack integration
- Removed Playwright dependency
- Created `docs/authoritative/INDEX.md` as single source of truth
- Archived `Active Docs/` → `docs/_archive_do_not_read/`

**Key Decision:** Semantic pipeline is now the **only** pipeline

---

## Part 6: Architecture Decisions (From CLAUDE.md & INDEX.md)

### 6.1 Source Isolation Rule (CRITICAL)

Each source extracted in a **SEPARATE LLM call:**
```
Source 1 → LLM Call 1 → Extraction 1
Source 2 → LLM Call 2 → Extraction 2
Source 3 → LLM Call 3 → Extraction 3
[Extraction 1, 2, 3] → Synthesis Call
```

**Rationale:** Prevents cross-source hallucination

### 6.2 6 Analysis Modes with Confidence Ceilings

| Mode | Ceiling | Quotes | Source |
|------|---------|--------|--------|
| `transcript_grounded` | HIGH | Verbatim | YouTube transcript |
| `caption_grounded` | MEDIUM | Approximate | YouTube captions |
| `video_only` | LOW | NO | Video visual content only |
| `text_provided` | MEDIUM | Unverified | User copy-paste |
| `ocr_extracted` | MEDIUM | Unverified | Screenshot OCR |
| `article_fetched` | HIGH | Verbatim | Web article via Jina |

### 6.3 Three Core Documents

- **Doc 0 (Source Ledger)** - Full transcripts, metadata, indexes
- **Doc 1 (Jump-Start)** - Gaps, research directions, next steps
- **Doc 2 (Semantic Brief)** - Themes, key points, tensions, confidence
- **Doc 3 (Producer Packet)** - Creative interpretation (optional, gated)

### 6.4 Pipeline Order (Never Skip)

```
INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY → UPLOAD → COMPLETION
```

### 6.5 Prompt Components (Required in ALL prompts)

1. Source Identity Lock
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction
5. Output Schema

---

## Part 7: Key Files for Code Review

### Critical Files (Review First)

| Priority | File | Lines | Purpose |
|----------|------|-------|---------|
| 🔴 P0 | backend/app/main.py | 200+ | App entry, exception handlers, CORS |
| 🔴 P0 | backend/worker.py | 1800+ | Celery tasks, pipeline orchestration |
| 🔴 P0 | backend/app/routes/jobs_routes.py | 500+ | Job CRUD + new endpoints |
| 🔴 P0 | backend/pipeline/stages/initialization.py | 150+ | Stage 0: job setup |
| 🔴 P0 | backend/pipeline/stages/semantic_extraction.py | 250+ | Stage 2: Gemini calls |
| 🔴 P0 | backend/state/impl/supabase.py | 400+ | Database CRUD |

### Models (Review Second)

| File | Lines | Review Focus |
|------|-------|--------------|
| backend/models/semantic_units.py | 250+ | Quote.source_id requirement, confidence ordering |
| backend/models/document_outputs.py | 300+ | Doc 0/1/2 structure, Addendum model |
| backend/models/job_record.py | 300+ | Artifacts, Iteration models |

### Prompts (Review Third)

| File | Lines | Review Focus |
|------|-------|--------------|
| backend/pipeline/prompts/modes/base.py | 100+ | 5 required components present? |
| backend/pipeline/prompts/semantic_extraction_prompt.py | 80+ | Mode dispatcher working? |

### Tests (Spot Check)

| File | Focus |
|------|-------|
| backend/tests/test_semantic_models.py | Model validation |
| backend/tests/test_pipeline_stages.py | Stage execution |
| backend/tests/test_semantic_pipeline_integration.py | Full pipeline flow |

---

## Part 8: Unresolved Questions

1. **Iteration Loop:**
   - Are baseline docs properly frozen when iterations are added?
   - Is `iteration_claim` UNIQUE constraint working correctly for atomicity?

2. **Storage Paths:**
   - When both storage path and inline data exist, which takes precedence?
   - Is unwrapping logic (extracting `data` key) correctly applied everywhere?

3. **Producer Packet Gating:**
   - V10 gating requires 4+ sources + 1+ high-confidence. Is this enforced in all code paths?

4. **Booster/Producer Fallback:**
   - If Gemini fails, does booster/producer properly degrade (status='failed' but job='completed')?

5. **Document Assembly:**
   - Provenance chain validation catches broken references - are all references consistently named?

---

## Part 9: Deployment Checklist

**Before Deployment:**
- [ ] All 960+ tests passing
- [ ] No TypeScript errors in frontend
- [ ] No import/contract drift (validate-contracts.py)
- [ ] PROGRESS.md updated with commit messages
- [ ] New migrations applied to Supabase

**Deployment:**
- [ ] `git push` to feature/vision-alignment-v1
- [ ] Deploy backend to Railway (docker push)
- [ ] Deploy frontend to Vercel (git push)
- [ ] Verify API endpoints responding
- [ ] Test job creation → completion pipeline

---

**Report Generated:** 2026-01-23 18:26  
**Scout Version:** Haiku 4.5  
**Codebase Status:** PRODUCTION (960+ tests, semantic pipeline active)
