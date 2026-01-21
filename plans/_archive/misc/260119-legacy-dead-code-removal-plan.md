# Legacy Dead Code Removal Plan

**Date Created:** 2026-01-19
**Status:** DOCUMENTED - NOT YET EXECUTED
**Branch:** feature/vision-alignment-v1

---

## Summary

This document identifies all dead code, deprecated endpoints, and legacy topic discovery artifacts in the Research Agent codebase following the 2026-01-19 pipeline cleanup.

---

## Context

On 2026-01-19, the Research Agent was surgically cleaned up to:
- Remove legacy topic-based discovery pipeline
- Remove Google Drive integration
- Remove Slack integration
- Keep only user-supplied source pipeline (semantic pipeline)

This cleanup left behind orphaned files and deprecated endpoint stubs that should be removed.

---

## FILES TO DELETE (Dead Code)

### 1. `backend/pipeline/stages/discovery.py`
- **Lines:** 303
- **Contains:**
  - `stage_3_source_shortlist()` - Topic-based web source discovery
  - `stage_3_5_quality_gate()` - Source filtering with BM25 scoring
  - `_search_with_exa()`, `_fetch_gdelt_sources()`, `_generate_shortlist_md()`
- **Status:** NOT imported in `stages/__init__.py`, NOT called anywhere
- **Impact:** Zero - completely orphaned

### 2. `backend/pipeline/stages/planning.py`
- **Lines:** 148
- **Contains:**
  - `stage_1_planning()` - Topic-based job planning with OpenAI
  - `stage_2_research_mapping()` - Research map generation with Perplexity
  - `DisambiguationRequired` exception class
- **Status:** NOT imported in `stages/__init__.py`, NOT called anywhere
- **Impact:** Zero - completely orphaned

### 3. `backend/integrations/slack.py`
- **Lines:** 48
- **Contains:**
  - `verify_slack_signature()` - Always returns False (no-op)
  - `post_slack_message()` - No-op with warning log
  - `post_slack_message_api()` - No-op with warning log
- **Status:** Functions exist but are all stubs
- **Impact:** Zero - all functions are no-ops

### 4. `backend/app/routes/slack_routes.py`
- **Lines:** 37
- **Contains:**
  - `POST /slack/command` - Returns 410 Gone
- **Status:** Endpoint exists but always returns 410
- **Impact:** Zero - deprecated stub

### 5. `backend/tests/test_slack_routes.py`
- **Lines:** 51
- **Contains:**
  - `TestSlackSignature` class - All tests skipped
  - `TestSlackCommandParsing` class - All tests skipped
- **Status:** All tests marked with `pytest.mark.skip`
- **Impact:** Zero - tests never run

### 6. `scripts/test_slack_command.py`
- **Lines:** 39
- **Contains:**
  - Prints deprecation message and exits with code 1
- **Status:** Script is non-functional stub
- **Impact:** Zero - does nothing

---

## DEPRECATED ENDPOINTS TO CONSOLIDATE

These endpoints currently return 410 Gone. They should be moved to a single file named `deprecated_endpoints.py`:

### In `backend/app/routes/jobs_routes.py`:
1. `POST /jobs` (line ~118) - Legacy topic-based job creation
2. `POST /jobs/preview` (line ~1283) - Legacy preview endpoint
3. `POST /jobs/{id}/select-interpretation` (line ~1601) - Legacy disambiguation

### In `backend/app/routes/export_routes.py`:
4. `POST /jobs/{id}/export/google-docs` (line ~311) - Legacy Drive export

### In `backend/app/routes/slack_routes.py`:
5. `POST /slack/command` (line ~17) - Legacy Slack integration

---

## TESTS TO REMOVE

### In `backend/tests/test_export_routes.py`:
- `TestGoogleDocsExportEndpoint` class (4 tests)
  - `test_google_docs_not_found`
  - `test_google_docs_no_artifacts`
  - `test_google_docs_success`
  - `test_google_docs_not_configured`

### In `backend/tests/test_jobs_routes.py`:
- `TestCreateJobEndpoint` class
  - `test_create_job_requires_prompt`
  - `test_create_job_success`

---

## CONFIG CLEANUP

### In `backend/config.py`:
- Remove `require_slack()` function (lines ~308-326)
- Slack env vars (`slack_signing_secret`, `slack_bot_token`) already marked deprecated

### In `backend/integrations/lazy_loader.py`:
- Remove `get_slack_client()` function (already returns None)

---

## FILES TO KEEP (Still Active)

### `backend/pipeline/stages/youtube.py`
- **Status:** ACTIVE - Used by `parallel_executor.py`
- **Contains:** YouTube enumeration and transcript fetching
- **DO NOT DELETE**

### `backend/pipeline/stages/web_capture.py`
- **Status:** ACTIVE - Used by `parallel_executor.py`
- **Contains:** Web content extraction and Reddit collection
- **DO NOT DELETE**

### `backend/integrations/google_drive_docs.py`
- **Status:** PARTIALLY ACTIVE
- **Used for:** OAuth validation in settings_routes.py
- **Dead code:** Document creation functions
- **Recommendation:** Keep for now, refactor later

---

## EXECUTION PLAN

When ready to execute this cleanup:

```bash
# Step 1: Delete dead files
rm backend/pipeline/stages/discovery.py
rm backend/pipeline/stages/planning.py
rm backend/integrations/slack.py
rm backend/app/routes/slack_routes.py
rm backend/tests/test_slack_routes.py
rm scripts/test_slack_command.py

# Step 2: Create deprecated_endpoints.py (consolidate all 410 stubs)
# Move deprecated endpoints from jobs_routes.py and export_routes.py

# Step 3: Edit test files to remove deprecated test classes

# Step 4: Edit config.py and lazy_loader.py for cleanup

# Step 5: Verify
python -m compileall backend -q
pytest backend/tests/ -v
```

---

## CURRENT TEST STATUS

```
Before cleanup: 981 passed, 5 failed, 8 skipped
After cleanup:  986+ passed, 0 failed, 2 skipped (expected)
```

The 5 failing tests are for deprecated endpoints and will be removed.

---

## ESTIMATED IMPACT

- **Lines removed:** ~700
- **Files deleted:** 6
- **Test failures fixed:** 5
- **Breaking changes:** None (deprecated endpoints already return 410)

---

## NOTES

- youtube.py and web_capture.py are used by parallel_executor.py for source collection
- google_drive_docs.py has OAuth helpers that are still used by settings_routes
- The deprecated endpoints should be kept as 410 stubs in a clearly named file for client compatibility

---

## RELATED DOCUMENTS

- `plans/reports/sanity-check-260119-1658-pipeline-connectivity.md` - Full system verification
- `plans/reports/scout-260119-1004-legacy-code-findings.md` - Initial legacy code audit
