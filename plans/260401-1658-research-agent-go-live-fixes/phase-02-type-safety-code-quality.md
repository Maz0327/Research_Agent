# Phase 2: Type Safety & Code Quality

## Context Links
- [plan.md](plan.md)
- Store file: `frontend/store/jobs.ts` (line 511)
- LLM Judge: `backend/pipeline/llm_judge.py` (line 376)
- Share routes: `backend/app/routes/share_routes.py`
- Config: `backend/config.py` (lines 65, 188)
- Admin auth: `backend/auth/admin.py`

## Overview
- **Priority:** HIGH
- **Status:** Pending
- **Effort:** 2h
- **Description:** Fix `as any` type casts, centralize os.getenv usage, resolve audit-H8 TODO, document ADMIN_EMAILS

## Key Insights
- `actionInProgress` type union at `jobs.ts:511` is `'booster' | 'producer' | 'iteration' | 'cancel' | 'delete' | 'archive' | 'unarchive' | null`
- New content types (`script`, `social_kit`, `blog_post`) use `as any` cast in 6 places (lines 1022, 1047, 1061, 1086, 1100, 1125)
- `llm_judge.py:376` is the ONLY non-script `os.getenv` call — reads `KIMI_API_KEY` directly instead of from Settings
- `ADMIN_EMAILS` is already in `config.py:65` and `admin.py` loads from it — just needs `.env.example` documentation
- `JINA_AI_READER_API_KEY` is already in `config.py:188` — may just need Settings UI entry
- `audit-H8` referenced in migration 026 comment — `share_routes.py` has working atomic view count via Supabase RPC; TODO likely resolved

## Requirements

### Functional
- `actionInProgress` type includes all content generation types
- No `as any` casts for known types in jobs store
- All non-script backend files use Settings (not os.getenv)
- audit-H8 verified and TODO comment removed if resolved

### Non-Functional
- `npx tsc --noEmit` must pass with zero errors
- `pytest backend/tests/ -v` must pass

## Related Code Files

| File | Action | Lines |
|------|--------|-------|
| `frontend/store/jobs.ts` | Modify — expand union type | 511, 1022, 1047, 1061, 1086, 1100, 1125 |
| `backend/pipeline/llm_judge.py` | Modify — use Settings instead of os.getenv | 376 |
| `backend/app/routes/share_routes.py` | Modify — remove TODO comment if H8 resolved | — |
| `backend/migrations/026_atomic_share_view_count.sql` | Read-only — verify H8 context | 5 |
| `.env.example` | Modify — document ADMIN_EMAILS | — |

## Implementation Steps

### 2.1 — Fix actionInProgress Union Type

In `frontend/store/jobs.ts`, line 511, expand the union:

```typescript
// Before:
actionInProgress: 'booster' | 'producer' | 'iteration' | 'cancel' | 'delete' | 'archive' | 'unarchive' | null;

// After:
actionInProgress: 'booster' | 'producer' | 'script' | 'social_kit' | 'blog_post' | 'iteration' | 'cancel' | 'delete' | 'archive' | 'unarchive' | null;
```

Then remove all 6 `as any` casts:
- Line 1022: `'social_kit' as any` → `'social_kit'`
- Line 1047: `'queued' as any` on social_kit_status — check if job type needs `social_kit_status` field too
- Line 1061: `'script' as any` → `'script'`
- Line 1086: `'queued' as any` on script_status
- Line 1100: `'blog_post' as any` → `'blog_post'`
- Line 1125: `'queued' as any` on blog_post_status

For the `*_status: 'queued' as any` casts (lines 1047, 1086, 1125), check the Job interface/type definition. If `social_kit_status`, `script_status`, `blog_post_status` fields are missing from the Job type, add them:

```typescript
// In Job type/interface (likely in jobs.ts or a types file):
social_kit_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
script_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
blog_post_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
```

### 2.2 — Fix os.getenv in llm_judge.py

In `backend/pipeline/llm_judge.py`, line 376:

```python
# Before:
kimi_api_key = os.getenv("KIMI_API_KEY")

# After:
from backend.config import get_settings
settings = get_settings()
kimi_api_key = settings.kimi_api_key
```

Verify `kimi_api_key` field exists in `backend/config.py` Settings model (it should, since Kimi is a core integration).

### 2.3 — Verify & Close audit-H8

1. Read `backend/app/routes/share_routes.py` around view_count logic
2. Migration 026 created `increment_share_view_count` RPC for atomic counting
3. `share_routes.py:344` calls this RPC — confirms H8 is resolved
4. Remove the TODO comment from migration 026 (line 5) or mark as DONE
5. Search for any other `audit-H8` references: `grep -r "audit-H8" backend/`

### 2.4 — Document ADMIN_EMAILS

`ADMIN_EMAILS` is already in `config.py:65` with `alias="ADMIN_EMAILS"`. Just ensure `.env.example` has it:

```bash
# Admin
ADMIN_EMAILS=admin@example.com,admin2@example.com  # Comma-separated list of admin emails
```

### 2.5 — Verify JINA_AI_READER_API_KEY in Settings

`JINA_AI_READER_API_KEY` is already in `config.py:188`. Check if the frontend Settings page exposes it. If not, it's acceptable as a backend-only env var (user doesn't need to set it via UI — it's a service key). Document in `.env.example` if missing.

## Todo Checklist

- [ ] 2.1 Expand `actionInProgress` union type with `script`, `social_kit`, `blog_post`
- [ ] 2.1 Add `social_kit_status`, `script_status`, `blog_post_status` to Job type if missing
- [ ] 2.1 Remove all 6 `as any` casts in jobs.ts
- [ ] 2.1 Run `npx tsc --noEmit` — zero errors
- [ ] 2.2 Replace `os.getenv("KIMI_API_KEY")` with Settings in llm_judge.py
- [ ] 2.2 Run `pytest backend/tests/ -v` — passes
- [ ] 2.3 Verify share_routes.py uses atomic RPC for view count (audit-H8 resolved)
- [ ] 2.3 Remove or mark TODO(audit-H8) comment as DONE
- [ ] 2.4 Add ADMIN_EMAILS to .env.example with description
- [ ] 2.5 Verify JINA_AI_READER_API_KEY documented in .env.example

## Success Criteria
- Zero `as any` casts for known types in `jobs.ts`
- `npx tsc --noEmit` passes
- No `os.getenv` calls in non-script backend code
- `.env.example` documents all env vars including ADMIN_EMAILS
- No open `TODO(audit-H8)` references

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Job type change causes downstream TS errors | LOW | Run full tsc check |
| llm_judge.py Settings import creates circular import | LOW | Use lazy import pattern |
| audit-H8 not actually resolved | MED | Read share_routes.py carefully before removing TODO |

## Security Considerations
- ADMIN_EMAILS should not contain PII beyond email addresses
- Ensure `.env.example` uses placeholder values, not real admin emails
