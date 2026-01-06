# Changelog

All notable changes to this repository will be documented in this file.

## 2026-01-06

### Added - Phase 3 Full Research Assistant Pipeline
- **4-Pass Gemini Analysis Pipeline**: Pass 1 (Extraction), Pass 2 (Structure), Pass 3 (Gap Analysis), Pass 4 (Research Starter)
- **New dataclasses**: `ContentBlueprint`, `GapAnalysis`, `ResearchStarter` with `parse_error` flags
- **Frontend components**: `ContentBlueprintView`, `GapAnalysisView`, `ResearchStarterView`
- **Shared components**: `CopyButton` extracted to `frontend/components/common/`
- **37 new tests** in `backend/tests/test_phase3_pipeline.py`

### Fixed - Critical Pipeline Issues (32 issues resolved)
- **C-001**: Silent JSON parse failures → Added `GeminiParseError` exception and `parse_json_from_llm_response()` utility
- **C-002**: No timeout protection → Added `API_TIMEOUT_SECONDS = 300` for all Gemini API calls
- **C-003**: Unbounded video loop → Added `MAX_VIDEOS_PER_JOB = 20` limit
- **C-005**: Timeout handling → Added `SoftTimeLimitExceeded` handler for graceful 25-min timeout with clear error message
- **State wrapper**: Added missing `config_json`, `artifacts`, `warnings`, `error` params to `update_job()` in `backend/state/__init__.py`
- Full list: See `plans/reports/bug-tracker-260106-1126-phase3-pipeline-issues.md`

### Changed
- **Rate limiting**: 500ms delay between video analyses to prevent API throttling
- **Progress updates**: Per-video progress in Pass 2 ("Analyzing video X of Y")
- **Cost tracking**: All passes now return and accumulate costs

### Documentation
- `plans/reports/bug-tracker-260106-1126-phase3-pipeline-issues.md` - Complete issue tracking
- `plans/reports/fix-report-260106-phase3-pipeline.md` - Detailed fix report

---

## 2026-01-01

### Changed
- Route rate limiting now keys primarily by authenticated `user_id`, with fallbacks to `X-Forwarded-For` and client IP to avoid throttling users behind shared IPs. See `backend/app/rate_limiter.py` and auth deps wiring in `backend/auth/dependencies.py`, `backend/auth/ban_check.py`.
- Job creation validation returns HTTP 422 for empty/overlong prompts and invalid options to align with tests and common API semantics. See `backend/app/routes/jobs_routes.py`.
- Frontend prompt length limit updated to match backend (2000 chars). See `frontend/lib/constants.ts`.

### Fixed
- Reliable job cancellation: Celery tasks are enqueued with deterministic `task_id=job_id` so admin/user cancellation can revoke the correct task. Updated in:
  - `backend/app/routes/jobs_routes.py`
  - `backend/app/routes/slack_routes.py`
  - `backend/app/routes/transcripts_routes.py`
- In‑memory job store now initializes `Outputs`/`Artifacts` when merging partial updates to prevent silent drops. See `backend/state/impl/in_memory.py`.

### Security/Tooling
- Removed hardcoded local path in `scripts/get_google_refresh_token.py`; now reads `GOOGLE_OAUTH_CLIENT_SECRETS_PATH` env var.

### Documentation
- Updated `AGENTS.md` with a “Recent Maintenance Notes” section summarizing the above changes and operational tips.

---

Prior changes are tracked in Git history (`git log`). Future releases may adopt semantic versioning and Keep a Changelog format.

