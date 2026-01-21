# FULL SYSTEM SANITY CHECK REPORT

**Date:** 2026-01-19
**Branch:** feature/vision-alignment-v1
**Mode:** READ-ONLY AUDIT
**Purpose:** Verify internal consistency after legacy+Slack+Drive purge

---

## EXECUTIVE SUMMARY

| Category | Status | Issues |
|----------|--------|--------|
| 1. Entrypoints Audit | ✅ PASS | 0 critical |
| 2. Pipeline Reachability | ✅ PASS | 0 critical |
| 3. Output Contract | ✅ PASS | 0 critical |
| 4. Quote/Observation Policy | ✅ PASS | 0 critical |
| 5. Transcript Chain | ✅ PASS | 0 critical |
| 6. Failure Semantics | ✅ PASS | 0 critical |
| 7. Doc Authority | ⚠️ WARN | 2 conflicts (non-blocking) |

**Overall Status: ✅ SYSTEM INTERNALLY CONSISTENT**

---

## 1. ENTRYPOINTS AUDIT

### API Routes Status

| Result | Category | Count | Evidence |
|--------|----------|-------|----------|
| ✅ PASS | Active Routes | 43 | jobs_routes.py, export_routes.py, etc. |
| ✅ PASS | Deprecated (410 Gone) | 7 | See below |
| ✅ PASS | Slack Endpoints | 0 | Removed; note at main.py:265 |

### Deprecated Endpoints (410 Gone)

| Endpoint | File:Line | Reason |
|----------|-----------|--------|
| POST `/jobs` | jobs_routes.py:1498-1521 | Legacy topic pipeline |
| POST `/jobs/preview` | jobs_routes.py:1524-1547 | Legacy topic pipeline |
| POST `/jobs/{id}/select-interpretation` | jobs_routes.py:1601-1623 | Legacy disambiguation |
| POST `/jobs/{id}/export/google-docs` | export_routes.py:311-331 | Drive removed |
| POST `/settings/validate-folder` | settings_routes.py:59-69 | Drive removed |
| GET `/settings/oauth-status` | settings_routes.py:72-82 | Drive removed |
| POST `/slack/command` | DELETED | Slack removed |

### Active Job Creation Routes

| Route | Handler | Task | Status |
|-------|---------|------|--------|
| POST `/jobs/video-analysis` | `create_video_analysis_job` | `run_gemini_video_job` | ✅ Active |
| POST `/jobs/text-input` | `create_text_input_job` | `run_research_job` | ✅ Active |
| POST `/jobs/screenshot-input` | `create_screenshot_input_job` | `run_research_job` | ✅ Active |
| POST `/jobs/mixed-input` | `create_mixed_input_job` | `run_research_job` | ✅ Active |

**Verdict: ✅ PASS** — All legacy endpoints return 410. No Slack endpoints exist.

---

## 2. PIPELINE REACHABILITY AUDIT

### Celery Tasks

| Task | Routes | Pipeline | Status |
|------|--------|----------|--------|
| `run_research_job` | text-input, screenshot-input, mixed-input | Semantic | ✅ Active |
| `run_gemini_video_job` | video-analysis | Gemini-Only | ✅ Active |
| `run_transcript_job` | /transcripts | Utility | ✅ Active |
| `process_evolving_job` | sources, process-pending | Semantic Extension | ✅ Active |
| `run_booster_task` | booster | Optional | ✅ Active |
| `run_producer_task` | producer-packet | Optional | ✅ Active |

### Legacy Pipeline Stage References

| Stage File | Status | Evidence |
|------------|--------|----------|
| planning.py | ✅ DELETED | No file found |
| discovery.py | ✅ DELETED | No file found |
| youtube.py (stage) | ✅ DELETED | No file found |
| web_capture.py (stage) | ✅ DELETED | No file found |
| parallel_executor.py | ✅ DELETED | No file found |

### Task Import Verification

| Check | Result | Evidence |
|-------|--------|----------|
| No legacy stage imports in worker.py | ✅ PASS | Grep: 0 matches |
| `_run_disambiguated_job` removed | ✅ PASS | worker.py:372-374 has removal note |
| Mixed-input → semantic stages only | ✅ PASS | worker.py:171-355 |

**Verdict: ✅ PASS** — No tasks trigger legacy pipeline. Semantic pipeline only.

---

## 3. OUTPUT CONTRACT AUDIT

### Doc Creation & Storage

| Doc | Created In | Stored As | Status |
|-----|------------|-----------|--------|
| Doc 0 (Source Ledger) | document_assembly.py:51-156 | `artifacts["source_ledger"]` | ✅ Active |
| Doc 1 (Jump Start) | document_assembly.py:159-244 | `artifacts["jump_start"]` | ✅ Active |
| Doc 2 (Semantic Brief) | document_assembly.py:247-354 | `artifacts["semantic_brief"]` | ✅ Active |
| Doc 3 (Producer Packet) | producer/gating.py | `artifacts["producer_packet"]` | ✅ Active |

### Export Endpoints

| Endpoint | Format | Status |
|----------|--------|--------|
| GET `/jobs/{id}/export?format=json` | JSON | ✅ Active |
| GET `/jobs/{id}/export?format=bibtex` | BibTeX | ✅ Active |
| GET `/jobs/{id}/export/markdown` | Markdown | ✅ Active |
| GET `/jobs/{id}/download.pdf` | PDF | ✅ Active |
| POST `/jobs/{id}/export/google-docs` | Drive | ❌ 410 Gone |

### Google Drive Generation

| Check | Result | Evidence |
|-------|--------|----------|
| No Drive imports in active code | ✅ PASS | transcript_service.py fixed |
| No Drive upload calls | ✅ PASS | Removed from worker.py |
| google_drive_docs.py deleted | ✅ PASS | File not found |

### Legacy Doc Names (00-11)

| Check | Result | Evidence |
|-------|--------|----------|
| `00_MASTER_INDEX` generated | ✅ NONE | Grep: 0 matches in backend/ |
| Legacy DOC_NAMES constant | ✅ DELETED | Was in google_drive_docs.py |

**Verdict: ✅ PASS** — Docs 0/1/2/3 exist. No Drive generation. No legacy docs.

---

## 4. QUOTE/OBSERVATION POLICY AUDIT

### Policy by Mode

| Mode | Confidence | Quotes | Enforcement | Status |
|------|------------|--------|-------------|--------|
| `transcript_grounded` | HIGH | Yes (verbatim) | Validation accepts | ✅ PASS |
| `caption_grounded` | MEDIUM | Yes (approximate) | `approximate: true` flag | ✅ PASS |
| `video_only` | LOW | **NO** | HARD FAIL if quotes | ✅ PASS |
| `text_provided` | MEDIUM | Yes (unverified) | `_accuracy_unverified` flag | ✅ PASS |
| `ocr_extracted` | MEDIUM | Yes (unverified) | `_accuracy_unverified` flag | ✅ PASS |
| `article_fetched` | HIGH | Yes (verbatim) | Validation accepts | ✅ PASS |

### video_only Enforcement

| Check | Result | Evidence |
|-------|--------|----------|
| Prompt forbids quotes | ✅ PASS | video_only.py: "NO QUOTES ALLOWED" (3x) |
| Schema uses observations | ✅ PASS | ApproximateObservation class |
| Validation HARD FAILs quotes | ✅ PASS | semantic_validation.py:605-619 |
| Confidence always LOW | ✅ PASS | mode_selector.py:29 |

### OCR Messy Lines

| Check | Result | Evidence |
|-------|--------|----------|
| Labeled as observations? | ✅ PASS | Uses quotes with `_accuracy_unverified` per owner decision |
| OCR warnings added | ✅ PASS | ocr_extracted.py:70-76 |

**Verdict: ✅ PASS** — video_only cannot produce quotes. All modes enforce correct policy.

---

## 5. TRANSCRIPT CHAIN AUDIT

### Fallback Chain Order

| Tier | Service | Mode Result | Evidence |
|------|---------|-------------|----------|
| 1 | Supadata (native + AI) | TRANSCRIPT_GROUNDED | transcript_acquisition.py:184-191 |
| 2 | Whisper | TRANSCRIPT_GROUNDED | transcript_acquisition.py:297-313 |
| 3 | YouTube captions | CAPTION_GROUNDED | transcript_acquisition.py:316-332 |
| 4 | video_only fallback | VIDEO_ONLY | transcript_acquisition.py:334-347 |

### Chain Verification

| Check | Result | Evidence |
|-------|--------|----------|
| Order locked Supadata→Whisper→Captions→video_only | ✅ PASS | transcript_acquisition.py:278-347 |
| Captions fallback sets caption_grounded | ✅ PASS | Line 321: `analysis_mode=CAPTION_GROUNDED` |
| Cloud IP handling documented | ✅ PASS | Lines 244-250: "blocked (cloud IP)" |
| Pre-LLM mode derivation | ✅ PASS | source_identity.py:137-165 |

**Verdict: ✅ PASS** — Transcript chain correctly implemented.

---

## 6. FAILURE SEMANTICS AUDIT

### Gemini Invalid JSON

| Check | Result | Evidence |
|-------|--------|----------|
| Max retries = 2 | ✅ PASS | gemini_client.py:425 |
| JSON error returns degraded dict | ✅ PASS | gemini_client.py:603-632 |
| No exception raised to caller | ✅ PASS | Returns `{"error": ..., "truncated": True}` |
| Job continues with warning | ✅ PASS | semantic_extraction.py:812-815 |

### Bad Source Isolation

| Check | Result | Evidence |
|-------|--------|----------|
| Per-source try/catch | ✅ PASS | semantic_extraction.py:687-815 |
| Exception caught, no raise | ✅ PASS | Line 812: `except Exception` |
| Loop continues to next source | ✅ PASS | Line 815: `continue` |
| Job completes with partial results | ✅ PASS | worker.py:817-833 |

### Stage Error Handling

| Check | Result | Evidence |
|-------|--------|----------|
| Stages non-critical by default | ✅ PASS | stage_runner.py:38 |
| Fallback functions supported | ✅ PASS | stage_runner.py:62-87 |
| Worker catches fatal only | ✅ PASS | worker.py:96-154 |

**Verdict: ✅ PASS** — Graceful degradation implemented correctly.

---

## 7. DOC AUTHORITY AUDIT

### INDEX.md Constitution Status

| Check | Result | Evidence |
|-------|--------|----------|
| INDEX.md declares constitution | ✅ PASS | Line 4: "single, repo-level pointer" |
| Lists authoritative docs | ✅ PASS | Lines 237-266 |
| Defines legacy policy | ✅ PASS | Lines 270-279 |

### Competing Authority Claims

| File | Claim | Status |
|------|-------|--------|
| Context_Handoff.md | "single authoritative source of truth" | ⚠️ CONFLICT |
| Database_Schema.md | "Authoritative Specification" (wrong location) | ⚠️ CONFLICT |

### Rule Files Compliance

| File | References INDEX.md | Status |
|------|---------------------|--------|
| CLAUDE.md | Yes (line 70) | ✅ Compliant |
| architecture.md | No (declares "CRITICAL" rules) | ✅ Compliant |
| implementation.md | No competing claims | ✅ Compliant |
| testing.md | No competing claims | ✅ Compliant |

**Verdict: ⚠️ WARN** — INDEX.md is constitution but 2 docs have competing claims (non-blocking).

---

## FORBIDDEN REFERENCE SEARCH

### Search Results

| Term | Count | Assessment |
|------|-------|------------|
| `slack` | 28 | BENIGN: Variable names, config fields, comments noting removal |
| `google_drive` | 10 | BENIGN: Config field, rate limiter entry, comments |
| `perplexity` | 26 | BENIGN: Config, cost tracking, error messages |
| `tavily` | 10 | BENIGN: Config, cost tracking |
| `serper` | 8 | BENIGN: Config, rate limiter |
| `exa_` | 6 | BENIGN: Config, cost tracking |
| `reddit` | 90+ | VALID: Reddit is supported source type |
| `00_MASTER_INDEX` | 0 | ✅ CLEAN |

### Benign Reference Details

| Category | Files | Reason to Keep |
|----------|-------|----------------|
| Config fields | config.py | Backward compat, potential future use |
| Cost tracking | cost_tracker.py | May track costs if re-enabled |
| Rate limiter | rate_limiter.py | Pre-configured limits |
| Error handling | error_handling.py | Token sanitization regex |
| Variable names | run_job.py, openai_client.py | Just parameter naming |

**Verdict: ✅ CLEAN** — No active code uses forbidden integrations. All references benign.

---

## DEAD CODE SAFE TO REMOVE

### Config Functions (Optional Cleanup)

| Function | File:Line | Reason |
|----------|-----------|--------|
| `require_perplexity()` | config.py:293-306 | Not called by active code |
| `require_tavily()` | config.py:335-350 | Not called by active code |
| `require_serper()` | config.py:392-407 | Not called by active code |
| `require_exa()` | config.py:374-389 | Not called by active code |
| `require_reddit()` | config.py:446-466 | Reddit client removed |

### Rate Limiter Entries (Optional Cleanup)

| Entry | File:Line | Reason |
|-------|-----------|--------|
| `"google_drive"` | rate_limiter.py:53 | Drive removed |
| `"perplexity"` | rate_limiter.py:42 | Client removed |
| `"tavily"` | rate_limiter.py:43 | Client removed |
| `"serper"` | rate_limiter.py:44 | Client removed |

### Cost Tracker Entries (Optional Cleanup)

| Entry | File:Line | Reason |
|-------|-----------|--------|
| `"perplexity_search"` | cost_tracker.py:19 | Client removed |
| `"tavily_search"` | cost_tracker.py:35 | Client removed |
| `"exa_search"` | cost_tracker.py:36 | Client removed |
| `"reddit_api"` | cost_tracker.py:37 | Client removed |

### Job Config Legacy Mode Presets (Optional Cleanup)

| Location | Contains | Reason |
|----------|----------|--------|
| job_config.py:46-87 | `"perplexity"`, `"reddit"` in DEFAULT_MODES | Legacy discovery modes |

**Note:** These are safe to remove but NOT breaking. Keep for potential future re-enablement.

---

## DOCUMENTATION CONFLICTS TO RESOLVE

### Priority 1: Context_Handoff.md

**Issue:** Claims "single authoritative source of truth" (line 5)
**Resolution Options:**
1. Demote to "meta/build instruction" category
2. Move to docs/legacy/
3. Add explicit disclaimer: "Defers to INDEX.md for spec authority"

### Priority 2: Database_Schema.md

**Issue:** Claims to be in `docs/authoritative/spec/` but lives in `/docs/`
**Resolution Options:**
1. Move to `docs/authoritative/spec/Database_Schema.md`
2. Remove authority claim ("Reference Document" instead)
3. Absorb into RASS.md Section 7 (Data Layer)

---

## FINAL CHECKLIST

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | All API routes mapped | ✅ PASS | 43 active, 7 deprecated |
| 2 | Legacy endpoints gone/410 | ✅ PASS | All return 410 Gone |
| 3 | No Slack endpoints | ✅ PASS | main.py:265 removal note |
| 4 | All Celery tasks mapped | ✅ PASS | 6 tasks, 0 legacy |
| 5 | No legacy stage triggers | ✅ PASS | Files deleted |
| 6 | Mixed-input → semantic only | ✅ PASS | worker.py:171-355 |
| 7 | Doc 0/1/2/3 in artifacts | ✅ PASS | document_assembly.py |
| 8 | Exports in Supabase Storage | ✅ PASS | supabase_store.py |
| 9 | No Drive generation | ✅ PASS | google_drive_docs.py deleted |
| 10 | No legacy docs 00-11 | ✅ PASS | Grep: 0 matches |
| 11 | video_only → no quotes | ✅ PASS | HARD FAIL enforcement |
| 12 | OCR quotes unverified | ✅ PASS | Owner decision implemented |
| 13 | Transcript chain correct | ✅ PASS | 4-tier fallback verified |
| 14 | Captions → caption_grounded | ✅ PASS | transcript_acquisition.py:321 |
| 15 | Gemini error → degrade | ✅ PASS | Returns dict with error |
| 16 | Bad source → continue | ✅ PASS | Loop continues |
| 17 | INDEX.md is constitution | ✅ PASS | Self-declares line 4 |
| 18 | No tooling uses non-auth | ⚠️ WARN | 2 competing claims exist |

---

## CONCLUSION

**System Status: ✅ INTERNALLY CONSISTENT**

The Research Agent codebase is clean after the legacy+Slack+Drive purge:
- All legacy pipeline code removed
- All deprecated endpoints return 410 Gone
- Only semantic pipeline is reachable
- Doc contracts properly implemented
- Quote/observation policy enforced
- Transcript chain correctly ordered
- Failure semantics gracefully degrade

**Minor Issues (Non-Blocking):**
- 2 docs have competing authority claims (Context_Handoff.md, Database_Schema.md)
- ~15 dead config/cost entries could be cleaned up (optional)

**No Critical Issues Found.**

---

**END OF SANITY CHECK REPORT**
