# Scout Quick Reference — Research Agent
**Generated:** 2026-01-23 18:26  
**Full Report:** scout-260123-1826-codebase-structure.md

---

## Critical Paths

### Backend Entry Points
```
backend/app/main.py          → FastAPI app setup, CORS, exception handlers
backend/worker.py             → Celery tasks (research, booster, producer, iteration)
backend/app/routes/jobs_routes.py → Job CRUD + new endpoints
```

### Database & Storage
```
backend/state/impl/supabase.py    → Job CRUD operations
backend/models/job_record.py      → Job/Artifacts/Iteration models
Supabase: jobs table, documents bucket
```

### Pipeline (10 stages)
```
backend/pipeline/stages/
  initialization.py          → Stage 0: Setup
  source_identity.py         → Stage 1: Mode resolution
  semantic_extraction.py     → Stage 2: Gemini (per-source isolated)
  semantic_validation_stage.py → Stage 3: Validation + ceilings
  gap_analysis.py            → Stage 4: Gaps
  semantic_synthesis.py      → Stage 5: Cross-source themes
  document_assembly.py       → Stage 6: Assemble Doc 0/1/2
  producer_stage.py          → Stage 8: Creative interpretation (optional)
  booster_stage.py           → Booster: Research directions (optional)
  cross_reference.py         → Add-on: Compare versions
```

### Frontend Entry Points
```
frontend/pages/
  dashboard.tsx              → Job list (L0/L1)
  jobs/[id].tsx             → Job detail (NEW Jan 23)
  index.tsx, settings.tsx   → Other pages
```

---

## Architecture Rules (CRITICAL)

**Rule 1: Source Isolation**
- Each source → separate LLM call (no cross-contamination)

**Rule 2: Confidence Ceilings**
- Mode-specific limits (HIGH/MEDIUM/LOW)
- Enforced in validation stage

**Rule 3: 5 Prompt Components**
- Source Identity Lock
- Confidence Ceiling
- Empty Output Permission
- Layered Extraction (L1 → L2 → L3)
- Output Schema (Pydantic)

**Rule 4: Prompt Order**
```
INGESTION → EXTRACTION → VALIDATION → SYNTHESIS → ASSEMBLY → UPLOAD → COMPLETION
```

---

## Recent Changes (Jan 2026)

**Jan 23:**
- ✅ Iteration loop (run_iteration_task, POST /jobs/{id}/iterate)
- ✅ Job detail page (/jobs/[id], ArtifactCard, IterationDialog)
- ✅ Migration 022: iteration_claim UNIQUE (TOCTOU fix)

**Jan 21-22:**
- ✅ Storage unwrapping logic (doc path vs inline)
- ✅ ADHD-friendly UI (spacing, dividers, status dots)
- ✅ Booster accordion, defensive b_roll parsing

**Jan 19-20:**
- ✅ Semantic pipeline = only pipeline (legacy disabled)
- ✅ Removed: discovery stages, Slack, Playwright, unused integrations
- ✅ Created INDEX.md (single source of truth)

---

## Test Suite

**960+ tests** across 41 files:
- Models: 200+ tests
- Stages: 250+ tests
- Routes: 150+ tests
- Integration: 100+ tests
- Edge cases: 100+ tests

**All passing.** Run: `pytest backend/tests/ -v`

---

## Key Files by Review Priority

**P0 (Review First):**
- backend/app/main.py (app setup, exception handlers)
- backend/worker.py (Celery task orchestration)
- backend/app/routes/jobs_routes.py (endpoints)
- backend/pipeline/stages/semantic_extraction.py (Gemini calls)
- backend/state/impl/supabase.py (database layer)

**P1 (Review Second):**
- backend/models/job_record.py (Artifacts, Iteration)
- backend/models/semantic_units.py (KeyPoint, Quote, Claim)
- backend/pipeline/prompts/modes/base.py (5 required components)
- backend/pipeline/context.py (PipelineContext)

**P2 (Spot Check):**
- backend/tests/test_semantic_pipeline_integration.py (full flow)
- frontend/pages/jobs/[id].tsx (new detail page)
- frontend/store/jobs.ts (state management)

---

## Deployment Readiness

- ✅ All 960+ tests passing
- ✅ No TypeScript errors (frontend builds)
- ✅ No import/contract drift (validate-contracts.py)
- ✅ PROGRESS.md up-to-date
- ✅ New migrations applied (migration 022)

**Ready to merge to main and deploy** (Vercel + Railway)

---

## Analysis Modes (Confidence Ceilings)

| Mode | Ceiling | Quotes | Example |
|------|---------|--------|---------|
| transcript_grounded | HIGH (0.8-1.0) | ✅ Verbatim | YouTube transcript |
| caption_grounded | MEDIUM (0.5-0.8) | ✅ Approx | YouTube captions |
| video_only | LOW (0.3-0.5) | ❌ NO | Video visual only |
| text_provided | MEDIUM | ✅ Unverified | User copy-paste |
| ocr_extracted | MEDIUM | ✅ Unverified | Screenshot OCR |
| article_fetched | HIGH | ✅ Verbatim | Web article |

---

## Documents Output

- **Doc 0:** Source Ledger (full transcripts, metadata)
- **Doc 1:** Jump-Start (gaps, research directions)
- **Doc 2:** Semantic Brief (themes, tensions, confidence)
- **Doc 3:** Producer Packet (creative interpretation, optional, gated)
- **Booster:** Research direction suggestions (optional)
- **Iterations:** New Doc 0/1/2 per iteration (baseline frozen)

---

## Unresolved Questions

1. Is `iteration_claim` UNIQUE constraint preventing TOCTOU races?
2. Storage path vs inline data precedence when both exist?
3. V10 producer gating enforced everywhere (4+ sources + 1+ high-confidence)?
4. Booster/producer failure graceful degradation working?
5. Provenance chain validation catching all broken references?

---

