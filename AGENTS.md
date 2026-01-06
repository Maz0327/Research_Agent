# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI API (`app/`), Celery worker (`worker.py`), pipeline (`pipeline/`), integrations (`integrations/`), data models (`models/`), state stores (`state/`), SQL migrations (`migrations/`), and backend tests (`backend/tests/`).
- `frontend/`: Next.js app with pages, components, Zustand stores, and Jest tests in `__tests__/`.
- `tests/`: Additional Python tests focused on integrations and pipeline utilities.
- `scripts/`: Helper scripts (e.g., Slack command tester, OAuth tooling).
- `docs/`, `plans/`, `Active Docs/`, `Archive Docs/`: Reference materials and planning.

## Build, Test, and Development Commands
Backend
- Create env: `python3.11 -m venv venv && source venv/bin/activate`
- Install deps: `pip install -r requirements.txt` (and `playwright install chromium` once)
- API (dev): `uvicorn backend.app.main:app --reload --port 8000`
- Worker: `celery -A backend.worker worker --loglevel=INFO`
- All via Docker: `docker-compose up --build`
- Lint/format: `ruff check .` and `ruff format .`; types: `mypy backend`

Frontend (from `frontend/`)
- Dev server: `npm run dev`
- Build/start: `npm run build && npm start`
- Lint/format: `npm run lint` and Prettier (on save or CI)

## Coding Style & Naming Conventions
- Python: 4-space indent, type hints for public functions, modules and files `snake_case.py`, constants `UPPER_SNAKE_CASE`. Prefer `loguru` over prints. Keep functions focused and testable.
- TypeScript/React: follow ESLint + Prettier. Components `PascalCase.tsx` in `components/*`; hooks `useSomething.ts`; stores `*.ts` in `store/`.
- Config lives in `.env` (copy from `.env.example`). Never commit secrets.

## Testing Guidelines
- Python (pytest): run `pytest -q` (root or `backend/tests`). Aim to cover new branches and error paths. Name tests `test_*.py`.
- Frontend (Jest): run `npm test` or `npm run test:watch`. Tests live in `frontend/__tests__/` and near components as `*.test.ts(x)`.
- Coverage: prefer meaningful assertions over thresholds; include tests in PRs that change behavior.

## Commit & Pull Request Guidelines
- Use Conventional Commits (seen in history): `feat(scope): …`, `fix(scope): …`, `docs: …`, `chore: …`, `refactor: …`, `test: …`.
- PRs: clear description, link issues, screenshots/GIFs for UI, include test updates, and note any config/env changes. Run linters and tests locally before opening.

## Security & Configuration Tips
- Required services: Redis (local) and Supabase (for DB/auth). Set `FRONTEND_ORIGINS` to enable CORS.
- Keep API keys only in `.env`; avoid logging secrets. Rotate credentials if accidentally exposed.

## Recent Maintenance Notes
- Rate limiting: backend now keys limits by `user_id` (fallback to `X-Forwarded-For` then IP) to avoid throttling users behind one IP. See `backend/app/rate_limiter.py` and auth deps wiring `request.state.user_id`.
- Job cancellation: Celery tasks are enqueued with `task_id=job_id` for reliable revoke. Updated in `jobs_routes.py`, `slack_routes.py`, and `transcripts_routes.py`.
- Validation/status codes: Job creation returns 422 for empty/overlong prompts and invalid options; align tests and UI.
- Prompt length parity: Frontend `MAX_PROMPT_LENGTH` set to 2000 to match backend.
- In‑memory store: Safely initializes `Outputs`/`Artifacts` before merging partial updates.
- Exports: Export endpoints read `JobRecord` attributes, verify ownership, and handle sync store access.
- Scripts: `scripts/get_google_refresh_token.py` now reads `GOOGLE_OAUTH_CLIENT_SECRETS_PATH` instead of a local absolute path.
