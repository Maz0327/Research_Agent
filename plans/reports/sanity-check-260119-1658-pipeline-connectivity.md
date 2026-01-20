# SANITY CHECK REPORT

**Date:** 2026-01-19
**Mode:** READ-ONLY verification
**Status:** ✅ PASSED (with expected test failures for deprecated endpoints)

---

## 1. REACHABLE SURFACES — Call Graph

### API Routes → Tasks

| Route | Handler | Task | Stages Called |
|-------|---------|------|---------------|
| `POST /jobs/video-analysis` | `create_video_analysis_job` | `run_gemini_video_job` | Gemini video analysis (standalone) |
| `POST /jobs/text-input` | `create_text_input_job` | `run_research_job` | semantic_extraction → validation → gap → synthesis → assembly → completion |
| `POST /jobs/screenshot-input` | `create_screenshot_input_job` | `run_research_job` | semantic_extraction → validation → gap → synthesis → assembly → completion |
| `POST /jobs/mixed-input` | `create_mixed_input_job` | `run_research_job` | semantic_extraction → validation → gap → synthesis → assembly → completion |
| `POST /jobs/{id}/sources` | `add_sources_to_job` | (direct) | Adds sources to pending_sources |
| `POST /jobs/{id}/process-pending` | `process_pending_sources` | `process_evolving_job` | cross_reference stage |
| `POST /jobs/{id}/booster` | `trigger_booster` | `run_booster` | booster_stage.run_booster |
| `POST /jobs/{id}/producer-packet` | `trigger_producer_packet` | `run_producer_task` | producer_stage.run_producer_pipeline |
| `POST /transcripts` | `create_transcript_job` | `run_transcript_job` | Supadata/Whisper acquisition |

### Deprecated Routes (410 Gone)

| Route | Reason |
|-------|--------|
| `POST /jobs` | Legacy topic-based discovery removed |
| `POST /jobs/preview` | Legacy topic planning removed |
| `POST /jobs/{id}/select-interpretation` | Disambiguation removed |
| `POST /jobs/{id}/export/google-docs` | Drive integration removed |
| `POST /slack/command` | Slack integration removed |

---

## 2. FORBIDDEN PATHS — VERIFIED UNREACHABLE

### ❌ Discovery/Search/Reddit/YouTube Enumeration
- **Status:** NOT IMPORTED, NOT CALLED
- `discovery.py` - NOT in `stages/__init__.py`, no imports found
- `planning.py` - NOT in `stages/__init__.py`, no imports found
- `youtube.py` - NOT in `stages/__init__.py` (YouTube enumeration unreachable)
- `web_capture.py` - NOT in `stages/__init__.py`
- Legacy stages 1-6.5: NOT exported, NOT imported

### ❌ Slack
- **Status:** DEPRECATED NO-OPS
- `slack_routes.py` - returns 410 Gone
- `slack.py` - all functions are no-ops with warnings
- `config.py/require_slack()` - always raises error
- `lazy_loader.py/get_slack_client()` - returns None
- `PipelineContext.slack_payload` - REMOVED

### ❌ Drive Upload/Doc Generation
- **Status:** COMPLETELY REMOVED
- `stage_9_drive_upload` - now generates exports to ctx.outputs only
- `google_drive_docs.py` - exists but NOT imported by worker
- No Drive uploads in `run_research_job`, `run_transcript_job`, `run_producer_task`

### ❌ Legacy Docs 00-11
- **Status:** NOT GENERATED
- `output.py/generate_exports_to_context()` only generates exports 12-17
- No code path generates doc_00 through doc_11

---

## 3. OUTPUTS — VERIFIED STORED CORRECTLY

### Doc 20/21/22 + Doc 3 + Booster

| Output | Location | Verified |
|--------|----------|----------|
| Doc 20 (Source Ledger) | `ctx.outputs["source_ledger"]` + `artifacts.source_ledger` | ✅ |
| Doc 21 (Jump Start) | `ctx.outputs["jump_start"]` + `artifacts.jump_start` | ✅ |
| Doc 22 (Semantic Brief) | `ctx.outputs["semantic_brief"]` + `artifacts.semantic_brief` | ✅ |
| Doc 3 (Producer Packet) | `ctx.outputs["producer_packet"]` + `artifacts.producer_packet` | ✅ |
| Booster Output | `ctx.outputs["booster_output"]` + `artifacts.booster_output` | ✅ |

### Exports + PDF in Supabase Storage

| Item | Storage Path | Manifest Key |
|------|--------------|--------------|
| 12_RESEARCH_DATA.json | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| 13_CITATIONS.bib | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| 14_CHAPTERS.json | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| 15_CLIPS.json | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| 16_SOCIAL_KIT.json | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| 17_RESEARCH_BRIEF.md | `research/{job_id}/attachments/` | `artifact_manifest.attachments.exports[]` |
| download.pdf | `research/{job_id}/attachments/` | `artifact_manifest.attachments.pdf` |

---

## 4. TRANSCRIPT CHAIN — VERIFIED

**File:** `backend/pipeline/transcript_acquisition.py`

```
Tier 1: Supadata native → TRANSCRIPT_GROUNDED
Tier 2: Supadata AI generate → TRANSCRIPT_GROUNDED
Tier 3: Whisper → TRANSCRIPT_GROUNDED
Tier 4: YouTube captions → CAPTION_GROUNDED (fails on cloud IPs)
Tier 5: None → VIDEO_ONLY
```

### Failure Handling
- ✅ Transcript failure NEVER fails job
- ✅ Returns `VIDEO_ONLY` analysis mode when all tiers fail
- ✅ Job continues with degraded output

### VIDEO_ONLY Mode Constraints
- ✅ NO QUOTES - verified in `video_only.py` mode prompt
- ✅ Uses `approximate_observations` instead
- ✅ Confidence ceiling: LOW (always, no exceptions)
- ✅ Extraction prompt explicitly forbids quotes

---

## 5. VERIFICATION RESULTS

### Compile Check
```
python -m compileall backend -q
```
**Result:** ✅ PASSED (no errors)

### Test Results
```
981 passed, 5 failed, 8 skipped
```

### Expected Failures (Deprecated Endpoints)
| Test | Expected | Actual | Reason |
|------|----------|--------|--------|
| `test_google_docs_not_found` | 404 | 410 | Endpoint deprecated |
| `test_google_docs_no_artifacts` | 400 | 410 | Endpoint deprecated |
| `test_google_docs_success` | 200 | 410 | Endpoint deprecated |
| `test_google_docs_not_configured` | 200 | 410 | Endpoint deprecated |
| `test_create_job_success` | 200 | 410 | POST /jobs deprecated |

**Note:** These tests need to be updated to expect 410 Gone.

---

## 6. LINGERING UNREACHABLE LEGACY CODE

| File | Status | Impact |
|------|--------|--------|
| `backend/pipeline/stages/discovery.py` | Unreachable | ✅ OK - not imported |
| `backend/pipeline/stages/planning.py` | Unreachable | ✅ OK - not imported |
| `backend/pipeline/stages/youtube.py` | Unreachable | ✅ OK - not imported |
| `backend/pipeline/stages/web_capture.py` | Unreachable | ✅ OK - not imported |
| `backend/integrations/google_drive_docs.py` | Unreachable | ✅ OK - not imported by worker |
| `backend/scripts/test_slack_command.py` | Deprecated | ✅ OK - exits with error |

---

## 7. BROKEN IMPORTS / DEAD TESTS / CONFIG DRIFT

### Broken Imports
- None detected

### Dead Tests (need updates)
| Test File | Issue |
|-----------|-------|
| `test_export_routes.py::TestGoogleDocsExportEndpoint` | Tests expect old status codes, need 410 |
| `test_jobs_routes.py::TestCreateJobEndpoint` | Tests expect old status codes, need 410 |

### Config Drift
- `SLACK_SIGNING_SECRET`, `SLACK_BOT_TOKEN` - still in config but marked deprecated
- No functional impact (require_slack always raises error)

---

## 8. ENDPOINTS CALLING WRONG TASKS

**Result:** ✅ NONE FOUND

All routes call appropriate tasks:
- `/video-analysis` → `run_gemini_video_job` ✅
- `/text-input`, `/screenshot-input`, `/mixed-input` → `run_research_job` ✅
- `/process-pending` → `process_evolving_job` ✅
- `/booster` → `run_booster` ✅
- `/producer-packet` → `run_producer_task` ✅
- `/transcripts` → `run_transcript_job` ✅

---

## SUMMARY

| Check | Status |
|-------|--------|
| Legacy discovery unreachable | ✅ VERIFIED |
| Slack unreachable | ✅ VERIFIED |
| Drive upload unreachable | ✅ VERIFIED |
| Legacy docs 00-11 unreachable | ✅ VERIFIED |
| Doc 20/21/22 stored correctly | ✅ VERIFIED |
| Exports in Supabase Storage | ✅ VERIFIED |
| Transcript chain correct | ✅ VERIFIED |
| video_only has no quotes | ✅ VERIFIED |
| Compile passes | ✅ VERIFIED |
| Tests pass (excluding deprecated) | ✅ 981/986 |

**CONCLUSION:** System is fully connected. No forbidden legacy behavior is reachable.

**Action Required:** Update 5 tests to expect 410 Gone for deprecated endpoints.
