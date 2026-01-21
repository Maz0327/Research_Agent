# DRIFT + DEPLOYMENT AUDIT REPORT

**Date:** 2026-01-20 13:47
**Authority Lock:** `docs/authoritative/INDEX.md`
**Mode:** READ-ONLY AUDIT (no implementation)

---

## A) EXECUTIVE SUMMARY

| Status | Count | Top Issues |
|--------|-------|------------|
| **P0 (Blockers)** | 1 | `/jobs/video-analysis` still reachable → triggers legacy 4-pass Gemini pipeline |
| **P1 (High)** | 3 | Frontend drift (4 legacy endpoints), Dockerfile has Playwright, No retention cleanup |
| **P2 (Medium)** | 5 | Docs out of sync, DB schema missing retention fields, messy OCR logic missing |

### VERDICT: **WARN** — Not deploy-ready until P0/P1 resolved

**Top 5 Blockers:**

1. **P0: `POST /jobs/video-analysis` triggers legacy pipeline** — The endpoint exists and calls `run_gemini_video_job` which runs the old 4-pass Gemini pipeline (not semantic-only). User intent states semantic-only should be the ONLY reachable pipeline.

2. **P1: Frontend calls 4 deprecated endpoints** — `jobs.ts` still calls `/jobs`, `/jobs/preview`, `/jobs/video-analysis`, `/jobs/{id}/select-interpretation`.

3. **P1: Dockerfile installs Playwright + Chromium** — ~400MB+ bloat, Railway builds will be slow/fragile. Playwright is no longer needed (web capture removed).

4. **P1: No retention/cleanup for 30-day HARD DELETE** — No `expires_at` column, no cleanup job, no user warning. User intent requires 30-day retention with hard delete.

5. **P2: Messy OCR → observations behavior missing** — INDEX.md states "if OCR messy, treat as observations + warning" but no code implements OCR quality detection.

---

## B) REACHABILITY + ENDPOINT AUDIT

### Active Job-Creating Endpoints

| Endpoint | Status | Triggers Task | Pipeline Path | Notes |
|----------|--------|---------------|---------------|-------|
| `POST /jobs` | **410 GONE** | - | - | ✅ Deprecated correctly (line 118-146) |
| `POST /jobs/preview` | **410 GONE** | - | - | ✅ Deprecated correctly (line 1283-1309) |
| `POST /jobs/{id}/select-interpretation` | **410 GONE** | - | - | ✅ Deprecated correctly (line 1601-1623) |
| `POST /jobs/video-analysis` | **ACTIVE** | `run_gemini_video_job` | Legacy 4-pass Gemini | ⚠️ **P0: SHOULD BE REMOVED** |
| `POST /jobs/text-input` | **ACTIVE** | `run_research_job` | Semantic pipeline | ✅ |
| `POST /jobs/screenshot-input` | **ACTIVE** | `run_research_job` | Semantic pipeline | ✅ |
| `POST /jobs/mixed-input` | **ACTIVE** | `run_research_job` | Semantic pipeline | ✅ |
| `POST /jobs/{id}/sources` | **ACTIVE** | `process_evolving_job` | Evolving job pattern | ✅ |
| `POST /jobs/{id}/booster` | **ACTIVE** | `run_booster_task` | Booster (Doc 1 expansion) | ✅ |
| `POST /jobs/{id}/producer-packet` | **ACTIVE** | `run_producer_task` | Producer (Doc 3) | ✅ |

### Deprecated Endpoints Returning 410

| Endpoint | File | Line | Status |
|----------|------|------|--------|
| `POST /jobs` | jobs_routes.py | 118 | ✅ 410 |
| `POST /jobs/preview` | jobs_routes.py | 1283 | ✅ 410 |
| `POST /jobs/{id}/select-interpretation` | jobs_routes.py | 1601 | ✅ 410 |
| `POST /export/google-docs` | export_routes.py | 311 | ✅ 410 |
| `POST /settings/validate-folder` | settings_routes.py | 59 | ✅ 410 (JSONResponse) |
| `GET /settings/oauth-status` | settings_routes.py | 72 | ✅ 410 (JSONResponse) |

### ⚠️ P0 ISSUE: `/jobs/video-analysis` Still Reachable

**Evidence:**
- `jobs_routes.py:153-219` — Endpoint defined and active
- `jobs_routes.py:211` — Calls `run_gemini_video_job.apply_async()`
- `worker.py:580-729` — `run_gemini_video_job` runs legacy 4-pass Gemini pipeline

**Impact:** Users can trigger non-semantic pipeline, violating the "semantic-only" constraint.

**Required Fix:** Return 410 GONE or remove endpoint entirely.

---

## C) CELERY TASK AUDIT

### All Registered Tasks

| Task | Line | Pipeline Type | Status |
|------|------|---------------|--------|
| `run_research_job` | worker.py:52 | Semantic (mixed-input only) | ✅ ACTIVE |
| `run_transcript_job` | worker.py:381 | Transcript extraction | ✅ ACTIVE |
| `run_gemini_video_job` | worker.py:580 | **LEGACY 4-pass Gemini** | ⚠️ **P0: Still callable** |
| `process_evolving_job` | worker.py:842 | Evolving job (add sources) | ✅ ACTIVE |
| `run_booster_task` | worker.py:1220 | Booster (Doc 1 expansion) | ✅ ACTIVE |
| `run_producer_task` | worker.py:1392 | Producer Packet (Doc 3) | ✅ ACTIVE |

### Task → Pipeline Mapping

```
run_research_job (semantic)
  └── ONLY accepts input_mode="mixed"
  └── Rejects legacy topic-based jobs (line 102-115)
  └── _run_mixed_input_job() → semantic pipeline stages

run_gemini_video_job (LEGACY)
  └── Runs 4-pass Gemini pipeline
  └── Uses client.run_full_analysis_pipeline()
  └── Produces ProducerPacket (old format)
  └── NOT semantic-compliant
```

### Legacy Pipeline Confirmation

`run_gemini_video_job` (worker.py:580-729) explicitly runs:
- Pass 1: Extraction (clips, quotes) → ProducerPacket
- Pass 2: Structure Analysis → ContentBlueprint per video
- Pass 3: Gap Analysis → Missing perspectives
- Pass 4: Research Starter → Search queries

This is NOT the semantic pipeline. It's the old 4-pass approach that was supposed to be replaced per ADR-001.

---

## D) SEMANTIC PIPELINE AUDIT

### Pipeline Stages (in order)

| Stage | File | Function | Notes |
|-------|------|----------|-------|
| Source Identity | stages/source_identity.py | `build_source_identity_from_*` | Pre-LLM identity resolution |
| Semantic Extraction | stages/semantic_extraction.py | `stage_semantic_extraction` | Per-source isolated LLM calls |
| Semantic Validation | stages/semantic_validation_stage.py | `stage_semantic_validation` | Confidence ceilings, quote checks |
| Gap Analysis | stages/gap_analysis.py | `stage_gap_analysis` | Identify missing coverage |
| Semantic Synthesis | stages/semantic_synthesis.py | `stage_semantic_synthesis` | Cross-source themes/tensions |
| Document Assembly | stages/document_assembly.py | `stage_document_assembly` | Build Doc 0/1/2 |
| Completion | stages/output.py | `stage_10_completion` | Manifest, storage, finalize |

### Source Isolation Rule ✅ ENFORCED

**Evidence:** `worker.py:157-179` — `_run_mixed_input_job()` processes each source type individually:
- Videos: Line 207-217 (loop per URL)
- Articles: Line 220-245 (loop per URL)
- Text inputs: Line 248-262 (loop per input)
- Screenshots: Line 265-327 (loop per screenshot)

Each source gets its own `build_source_identity_from_*` call and isolated LLM extraction.

---

## E) TRANSCRIPT CHAIN + MODE MAPPING

### Fallback Order ✅ CORRECT

**File:** `backend/pipeline/transcript_acquisition.py:4-8`

```
LOCKED ORDER (per RASS.md Section 8.1):
1. Supadata → transcript_grounded
2. Whisper → transcript_grounded
3. YouTube captions → caption_grounded (local only, fails on cloud IPs)
4. None → video_only
```

### Mode Assignment Evidence

| Tier | Transcript Source | Analysis Mode | File:Line |
|------|-------------------|---------------|-----------|
| 1 | Supadata | `transcript_grounded` | transcript_acquisition.py:96 |
| 2 | Whisper | `transcript_grounded` | transcript_acquisition.py:97 |
| 3 | YouTube captions | `caption_grounded` | transcript_acquisition.py:77-78 |
| 4 | None | `video_only` | transcript_acquisition.py:83-88, 334-343 |

### Mode → Doc 0 Metadata

Mode assignment flows through `TranscriptResult.to_provenance()` (line 64-99) which creates `TranscriptProvenance` for Doc 0.

---

## F) QUOTE VS OBSERVATION ENFORCEMENT

### Policy Table (from mode_selector.py)

| Mode | Quotes Allowed | Enforcement | Evidence |
|------|----------------|-------------|----------|
| `transcript_grounded` | ✅ Yes | - | mode_selector.py:43 |
| `caption_grounded` | ✅ Yes (approximate) | DEGRADED_QUOTE_MODES | mode_selector.py:57 |
| `video_only` | ❌ **NO** | NO_QUOTE_MODES, HARD_FAIL | mode_selector.py:45,62 |
| `text_provided` | ✅ Yes (unverified) | DEGRADED_QUOTE_MODES | mode_selector.py:48,55 |
| `ocr_extracted` | ✅ Yes (unverified) | DEGRADED_QUOTE_MODES | mode_selector.py:49,56 |
| `article_fetched` | ✅ Yes | - | mode_selector.py:50 |

### video_only HARD FAIL ✅ ENFORCED

**Evidence:** `semantic_validation.py:604-612`

```python
# Check for quotes in FORBIDDEN mode (video_only only)
if analysis_mode in NO_QUOTE_MODES:
    if any_quotes_present:
        results.append(ValidationResult(
            level=ValidationLevel.HARD_FAIL,
            message=f"video_only mode FORBIDS quotes. Found {len(quotes)} quotes. Use observations instead.",
            field="quotes",
        ))
```

### ⚠️ P2 ISSUE: Messy OCR → Observations Missing

**User Intent:** "if OCR quality is 'messy' then quote-like lines must be treated as observations + warning"

**Evidence:** No OCR quality detection in code. `ocr_extracted` mode always allows quotes.

**Required Fix:** Add OCR quality scoring and conditional degradation to observations.

---

## G) DOCUMENT CONTRACT AUDIT

### Doc 0/1/2/3 Construction

| Doc | File | Function | Content |
|-----|------|----------|---------|
| Doc 0 (Source Ledger) | document_assembly.py | `build_source_ledger()` | Sources, provenance, full text |
| Doc 1 (Jump-Start) | document_assembly.py | `build_jump_start_directions()` | Gaps, next steps, research queries |
| Doc 2 (Semantic Brief) | document_assembly.py | `build_semantic_brief()` | Themes, key points, tensions |
| Doc 3 (Producer Packet) | producer_stage.py | `stage_producer()` | Creative interpretation (gated) |

### Doc 1/2 No New Facts Rule ✅ DOCUMENTED

**File:** `document_assembly.py:17-19`

```python
# Rules:
# - DOC 1 and DOC 2 may not introduce new data
# - All references must trace to DOC 0
# - If DOC 0 is thin → DOC 1 and DOC 2 must reflect this explicitly
```

### Doc 3 Isolation ✅ ENFORCED

Producer Packet is:
- Gated via `can_generate_producer_packet()` (jobs_routes.py:1229)
- Stored separately in `artifacts.producer_packet`
- Does not modify Doc 0/1/2

---

## H) BOOSTER AUDIT

### Deep Research Booster

**File:** `booster_stage.py`

| Aspect | Implementation | Evidence |
|--------|----------------|----------|
| Reads | Context bundle (themes, gaps, key points) | booster_stage.py:44-83 |
| Outputs | `BoosterOutput` with search queries, directions | booster_stage.py:88+ |
| Writes to | Doc 1 only (via `booster_output`, `booster_expansion_md`) | job_record.py:46-47 |
| Adds facts to Doc 0? | **NO** | Produces directions, not facts |

### Producer Packet

**File:** `producer_stage.py`

| Aspect | Implementation | Evidence |
|--------|----------------|----------|
| Reads | Semantic summaries, themes from extractions | - |
| Outputs | `ProducerPacket` with story angles, hooks | - |
| Writes to | Doc 3 only (via `producer_packet`, `producer_packet_md`) | job_record.py:50-51 |
| Adds facts to Doc 0? | **NO** | Creative interpretation layer |

---

## I) STORAGE STRATEGY AUDIT (Option B)

### Core Docs in Artifacts JSON ✅

**File:** `job_record.py:27-37`

| Artifact Key | Document | Field |
|--------------|----------|-------|
| `source_ledger` | Doc 0 | `artifacts.source_ledger` |
| `jump_start` | Doc 1 | `artifacts.jump_start` |
| `semantic_brief` | Doc 2 | `artifacts.semantic_brief` |
| `producer_packet` | Doc 3 | `artifacts.producer_packet` |

### Storage Paths (lazy loading) ✅

| Path Field | Purpose |
|------------|---------|
| `doc_0_path` | Storage path for Source Ledger |
| `doc_1_path` | Storage path for Jump-Start |
| `doc_2_path` | Storage path for Semantic Brief |
| `doc_3_path` | Storage path for Producer Packet |

### Supabase Storage Buckets ✅

**File:** `supabase_storage.py:19-20`

| Bucket | Purpose | MIME Types |
|--------|---------|------------|
| `screenshots` | User uploads | image/png, image/jpeg, image/webp |
| `documents` | Research job docs | application/json |

### Manifest + Lazy-Load Endpoints ✅

| Endpoint | Line | Purpose |
|----------|------|---------|
| `GET /jobs/{id}/manifest` | jobs_routes.py:1700 | Artifact manifest |
| `GET /jobs/{id}/doc/{doc_id}` | jobs_routes.py:1744 | Lazy-load document |
| `GET /jobs/{id}/attachments` | jobs_routes.py:1823 | List attachments |
| `GET /jobs/{id}/download.pdf` | jobs_routes.py:1982 | On-demand PDF |

### Storage Mapping Table

| Item | In artifacts JSON? | In Supabase Storage? | Endpoint |
|------|-------------------|---------------------|----------|
| Doc 0-2 content | ✅ Yes (inline) | Optional (paths) | `/doc/{id}` |
| Doc 3 content | ✅ Yes (inline) | Optional (paths) | `/doc/3` |
| Manifest | ✅ Yes | - | `/manifest` |
| PDF | - | ✅ Generated on-demand | `/download.pdf` |
| Screenshots | - | ✅ Yes | `/attachments/{filename}` |

---

## J) DATABASE SCHEMA AUDIT

### Jobs Table Columns (inferred from code)

| Column | Type | Evidence |
|--------|------|----------|
| `job_id` | UUID | Primary key |
| `user_id` | UUID | Foreign key to users |
| `status` | VARCHAR | Job status enum |
| `stage` | VARCHAR | Current pipeline stage |
| `progress_percent` | INT | 0-100 |
| `config_json` | JSONB | Job configuration |
| `artifacts` | JSONB | Output artifacts |
| `outputs` | JSONB | Legacy outputs |
| `warnings` | TEXT[] | Array of warnings |
| `created_at` | TIMESTAMP | Creation time |
| `title` | VARCHAR | Job title |
| `error` | TEXT | Error message |

### Existing Migrations

Found 17 migrations in `backend/migrations/*.sql`:
- 001-013: Core schema
- 014: Atomic JSONB merge RPC
- 015: Performance improvements
- 016: Disambiguation fields
- 017: Restrict RPC permissions

### ⚠️ P1 ISSUE: Missing Retention Fields

**User Intent:** "Retention: stored for 30 days then HARD DELETE (with user warning / countdown)"

**Current State:** No `expires_at`, `deleted_at`, or retention-related columns exist.

**Required DB Changes:**

```sql
-- 1. Add retention fields
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retention_warned_at TIMESTAMP WITH TIME ZONE;

-- 2. Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_expired_jobs()
RETURNS INTEGER AS $$
DECLARE deleted_count INTEGER;
BEGIN
  DELETE FROM jobs WHERE expires_at < NOW() AND deleted_at IS NULL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Add index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs(expires_at) WHERE deleted_at IS NULL;
```

### Other Missing DB Elements

| Element | Purpose | Status |
|---------|---------|--------|
| `expires_at` column | 30-day retention countdown | ❌ Missing |
| `cleanup_expired_jobs()` RPC | Automated deletion | ❌ Missing |
| Retention warning endpoint | User countdown notification | ❌ Missing |

---

## K) FRONTEND DRIFT AUDIT

### Frontend → Backend Endpoint Calls

**File:** `frontend/store/jobs.ts`

| Function | Endpoint Called | Status | Line |
|----------|-----------------|--------|------|
| `fetchJobs` | `GET /jobs` | ✅ OK | 378 |
| `previewJob` | `POST /jobs/preview` | ⚠️ **DEPRECATED** | 420 |
| `createJob` | `POST /jobs` | ⚠️ **DEPRECATED** | 467 |
| `createVideoAnalysisJob` | `POST /jobs/video-analysis` | ⚠️ **LEGACY** | 528 |
| `createTextInputJob` | `POST /jobs/text-input` | ✅ OK | 577 |
| `createScreenshotInputJob` | `POST /jobs/screenshot-input` | ✅ OK | 642 |
| `createMixedInputJob` | `POST /jobs/mixed-input` | ✅ OK | 691 |
| `triggerBooster` | `POST /jobs/{id}/booster` | ✅ OK | 746 |
| `triggerProducer` | `POST /jobs/{id}/producer-packet` | ✅ OK | 785 |
| `refreshJob` | `GET /jobs/{id}` | ✅ OK | 824 |
| `selectInterpretation` | `POST /jobs/{id}/select-interpretation` | ⚠️ **DEPRECATED** | 870 |
| `cancelJob` | `POST /jobs/{id}/cancel` | ✅ OK | 910 |
| `deleteJob` | `DELETE /jobs/{id}` | ✅ OK | 947 |
| `archiveJob` | `POST /jobs/{id}/archive` | ✅ OK | 980 |

### Frontend Drift Summary

| Issue | Endpoint | Required Fix |
|-------|----------|--------------|
| Calls deprecated | `POST /jobs` | Remove `createJob()`, use `createMixedInputJob()` |
| Calls deprecated | `POST /jobs/preview` | Remove `previewJob()` entirely |
| Calls legacy | `POST /jobs/video-analysis` | Remove `createVideoAnalysisJob()`, normalize to mixed-input |
| Calls deprecated | `POST /jobs/{id}/select-interpretation` | Remove `selectInterpretation()` entirely |

---

## L) DEPLOYMENT / RAILWAY BUILD AUDIT

### Dockerfile Analysis

**File:** `Dockerfile`

| Step | Issue | Severity |
|------|-------|----------|
| Line 11-34: Install Playwright deps | ~200MB system packages no longer needed | P1 |
| Line 46: `playwright install chromium` | ~150MB browser binary no longer needed | P1 |
| Line 31: Install ffmpeg | Still needed for yt-dlp | Keep |
| Line 43: `pip install -r requirements.txt` | Single requirements file for API+worker | P2 |

### ⚠️ P1 ISSUE: Playwright + Chromium Bloat

**Evidence:**
- `backend/pipeline/stages/web_capture.py` — **DELETED** (no longer exists)
- `backend/integrations/playwright*` — **DELETED**
- No remaining code uses Playwright

**Impact:** ~350MB+ unnecessary in image, slower builds, potential Railway failures.

**Required Fix:** Remove all Playwright lines from Dockerfile:
```dockerfile
# REMOVE these lines:
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \

# REMOVE this line:
RUN playwright install chromium
```

### Requirements.txt Analysis

**Heavy/Unused Dependencies:**

| Package | Size | Status |
|---------|------|--------|
| `playwright==1.40.0` | ~50MB | ❌ REMOVE (web_capture deleted) |
| `spacy>=3.7.0` | ~200MB+ with model | ⚠️ Check if used |
| `exa-py>=1.0.0` | Small | ❌ REMOVE (exa_client deleted) |
| `praw>=7.7.0` | Small | ❌ REMOVE (reddit_client deleted) |
| `tavily-python>=0.5.0` | Small | ❌ REMOVE (tavily_client deleted) |

### Dependency Conflicts

| Conflict | Issue |
|----------|-------|
| `httpx>=0.28.1` + `supabase>=2.10.0` | Supabase previously required `httpx<0.28.0`, now compatible |
| `google-genai==1.56.0` | Pinned for stability, may need update |

### Railway Build Rescue Plan Checklist

1. [ ] Remove Playwright system deps from Dockerfile
2. [ ] Remove `playwright install chromium` step
3. [ ] Remove `playwright` from requirements.txt
4. [ ] Remove `exa-py`, `praw`, `tavily-python` from requirements.txt
5. [ ] Consider API vs Worker split (two Dockerfiles, two requirements files)
6. [ ] Audit spacy usage — remove if unused
7. [ ] Test build locally: `docker build -t research-agent .`
8. [ ] Test Railway build in staging

---

## M) DOC MISMATCH AUDIT

### Docs Claiming Authority Outside `docs/authoritative/`

| File | Issue | Recommendation |
|------|-------|----------------|
| `docs/QUICK_START.md` | References `/jobs/video-analysis`, `/jobs/{id}/documents/doc_0` | Rewrite |
| `docs/architecture.md` | Full legacy endpoint list (lines 32-43) | Rewrite |
| `docs/gemini-pivot-implementation.md` | Describes legacy 4-pass approach | Archive |
| `docs/TROUBLESHOOTING.md` | References `/jobs/{job_id}/warnings` (doesn't exist) | Rewrite |

### Files Already Correctly Archived

| File | Location | Status |
|------|----------|--------|
| `PRD_v6.md` | `docs/_archive_do_not_read/` | ✅ |
| `CLAUDE.md` (old) | `docs/_archive_do_not_read/` | ✅ |
| `TEP_v2.md` | `docs/_archive_do_not_read/` | ✅ |
| `DEPLOYMENT_GUIDE.md` | `docs/_archive_do_not_read/` | ✅ |

### Recommended Archive Actions

| File | Action |
|------|--------|
| `docs/gemini-pivot-implementation.md` | Move to `docs/_archive_do_not_read/` |
| `docs/architecture.md` | Rewrite with current endpoints or archive |
| `docs/QUICK_START.md` | Rewrite with `/jobs/mixed-input` flow |

### .claudeignore Recommendations

No `.claudeignore` file exists. Recommend creating:

```
# .claudeignore
docs/_archive_do_not_read/
Archive Docs/
Active Docs/
*.backup
*.bak
```

---

## PRIORITIZED FIX LIST

### P0 (Blockers — Must fix before deploy)

| # | Issue | File | Fix |
|---|-------|------|-----|
| 1 | `/jobs/video-analysis` triggers legacy pipeline | jobs_routes.py:153 | Return 410 GONE |

### P1 (High — Fix in next sprint)

| # | Issue | File | Fix |
|---|-------|------|-----|
| 2 | Frontend calls deprecated endpoints | store/jobs.ts | Remove 4 functions |
| 3 | Dockerfile has Playwright | Dockerfile | Remove lines 11-34, 46 |
| 4 | No retention/cleanup mechanism | migrations/ | Add 018_retention_fields.sql |
| 5 | requirements.txt has dead deps | requirements.txt | Remove playwright, exa, praw, tavily |

### P2 (Medium — Fix when convenient)

| # | Issue | File | Fix |
|---|-------|------|-----|
| 6 | Messy OCR → observations missing | semantic_extraction.py | Add OCR quality detection |
| 7 | Docs out of sync | docs/*.md | Rewrite or archive |
| 8 | Single requirements.txt | requirements.txt | Split API vs worker |
| 9 | No .claudeignore | root | Create file |
| 10 | Worker still has legacy task code | worker.py:580-729 | Remove after endpoint deprecated |

---

## Unresolved Questions

1. **spacy usage** — Is spacy actually used anywhere? Consider removing if not.
2. **video_only + scene description** — User intent mentions "scene description / on-screen OCR / footage recognition must NOT run here" — need to verify Gemini video analysis doesn't do this.
3. **Supabase bucket MIME restrictions** — User intent says documents bucket should only allow `application/json` but code allows other types for exports.
4. **Retention warning UI** — How should users be warned about approaching 30-day deletion?

---

**END OF AUDIT REPORT**
