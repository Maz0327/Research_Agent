# Phase 1: Infrastructure & DevOps

## Context Links
- [plan.md](plan.md)
- Migration file: `backend/migrations/027_add_voice_profiles.sql`
- Migration runner: `backend/migrations/run_migrations.py`
- OpenAI billing: https://platform.openai.com/settings/organization/billing

## Overview
- **Priority:** CRITICAL
- **Status:** Pending
- **Effort:** 3h
- **Description:** Deploy pending migration, verify API balance, add CI/CD, clean stale branches

## Key Insights
- Migration 027 exists locally but never run on Supabase prod. Creates `voice_profiles` table with RLS policies.
- OpenAI likely $0 balance — Whisper transcription silently fails (no error surfaced to user).
- No `.github/workflows/` directory exists at project root (only in node_modules).
- Stale branches: `claude/review-video-insights-de0aU` (remote), `feature/tier-5-content-generation` (local).

## Requirements

### Functional
- Migration 027 applied to Supabase prod
- OpenAI balance checked and topped up if needed
- GitHub Actions workflow for lint + test on PR
- Stale branches removed

### Non-Functional
- CI must complete in <5 min
- Migration must be idempotent (uses `IF NOT EXISTS`)

## Related Code Files

| File | Action |
|------|--------|
| `backend/migrations/027_add_voice_profiles.sql` | Deploy to Supabase |
| `.github/workflows/ci.yml` | Create |
| `backend/migrations/run_migrations.py` | Reference for migration execution |

## Implementation Steps

### 1.1 — Deploy Migration 027 to Supabase
1. Open Supabase Dashboard > SQL Editor (or use `psql` with prod connection string)
2. Run contents of `backend/migrations/027_add_voice_profiles.sql`
3. Verify table exists: `SELECT * FROM information_schema.tables WHERE table_name = 'voice_profiles';`
4. Verify RLS enabled: `SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'voice_profiles';`
5. Verify 4 policies exist: `SELECT policyname FROM pg_policies WHERE tablename = 'voice_profiles';`

### 1.2 — Check & Top Up OpenAI Balance
1. Visit https://platform.openai.com/settings/organization/billing
2. Check current balance and usage
3. If $0 or near-zero, add credits (minimum $10 recommended for Whisper testing)
4. Alternatively, run `python backend/scripts/check_api_balances.py` to check all API balances at once

### 1.3 — Create CI/CD Pipeline
Create `.github/workflows/ci.yml`:

```yaml
name: CI
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest backend/tests/ -v --tb=short

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
```

**Notes:**
- Backend tests mock all external APIs (per testing rules), no secrets needed
- Frontend `npm run build` includes TypeScript type-checking
- No Redis/Supabase service containers needed (tests don't hit real DB)

### 1.4 — Clean Stale Branches
```bash
# Delete remote stale branch
git push origin --delete claude/review-video-insights-de0aU

# Delete local merged branch
git branch -d feature/tier-5-content-generation
```

## Todo Checklist

- [ ] 1.1 Run migration 027 on Supabase prod
- [ ] 1.1 Verify voice_profiles table + RLS + 4 policies
- [ ] 1.2 Check OpenAI balance
- [ ] 1.2 Top up if needed
- [ ] 1.3 Create `.github/workflows/ci.yml`
- [ ] 1.3 Push and verify Actions run green
- [ ] 1.4 Delete `claude/review-video-insights-de0aU` remote branch
- [ ] 1.4 Delete `feature/tier-5-content-generation` local branch

## Success Criteria
- `voice_profiles` table queryable in Supabase prod
- OpenAI balance > $5
- CI passes on current branch
- `git branch -a` shows only `main` + current feature branch + `origin/main` + `origin/feature/kimi-...`

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration 027 fails on prod (table already partially exists) | LOW — uses IF NOT EXISTS | Verify idempotency before running |
| OpenAI balance top-up requires billing admin access | MED — blocks Whisper testing | Confirm billing access beforehand |
| CI takes >10min due to pytest count (1188 tests) | LOW | Can add `--timeout=120` or parallelize later |

## Security Considerations
- Do NOT commit any API keys or Supabase connection strings
- CI workflow does not need secrets for backend tests (all mocked)
- Frontend build needs no env vars (build-time only)
