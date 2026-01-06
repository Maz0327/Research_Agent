# Changelog

All notable changes to this repository will be documented in this file.

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

