# Phase 5: PR Strategy & Release

## Context Links
- [plan.md](plan.md)
- PR #19: `gh pr view 19`
- Branch: `feature/kimi-visual-analysis-and-optimizations`
- 22 commits, 294 files, 32K+ insertions

## Overview
- **Priority:** HIGH
- **Status:** Pending
- **Effort:** 2-3h
- **Blocked by:** Phases 1-4 (all fixes landed before merge)
- **Description:** Review and merge PR #19, cut first release tag

## Key Insights
- Splitting PR #19 into smaller PRs is NOT recommended — 294 files across tightly coupled backend+frontend changes would create unresolvable merge conflicts if split
- Better strategy: thorough review on the single PR, then squash-merge or merge with clean history
- No release tags exist yet. First tag should be `v1.0.0` (or `v0.1.0` if treating as beta)
- CI (from Phase 1) will gate the merge

## Requirements

### Functional
- PR #19 reviewed and merged to main
- First release tag created
- CHANGELOG.md updated

### Non-Functional
- All CI checks pass before merge
- No regressions on main after merge

## Implementation Steps

### 5.1 — PR Review Strategy

Given the size (294 files, 32K lines), use a structured review approach:

**Review in logical groups (not file-by-file):**

1. **Backend pipeline changes** (~30 files) — visual analysis, Kimi integration, script/blog/social stages
2. **Backend models + migrations** (~15 files) — new Pydantic models, migration 025-027
3. **Backend routes** (~10 files) — new endpoints, share routes
4. **Frontend store + API** (~5 files) — jobs.ts, voice-profiles.ts, api-client
5. **Frontend components** (~80 files) — new components, admin-v2, settings-v2
6. **Frontend pages + layout** (~20 files) — app router migration, layouts
7. **Config + DevOps** (~10 files) — Dockerfile, config.py, CI
8. **Tests** (~20 files) — new test files
9. **Docs + plans** (~100 files) — reports, plans, PROGRESS/DECISIONS/CHANGELOG

**Per-group checklist:**
- [ ] No secrets/API keys committed
- [ ] No `console.log` / `print()` debug statements left
- [ ] Type safety (no unresolved `any`)
- [ ] Error handling present on all external calls
- [ ] Tests exist for new backend logic

### 5.2 — Pre-Merge Checklist

Run locally before approving:
```bash
# Backend
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate
pytest backend/tests/ -v --tb=short

# Frontend
cd frontend
npm run lint
npm run build
```

Verify CI passes on GitHub Actions (from Phase 1).

### 5.3 — Merge Strategy

**Recommended: Regular merge commit (not squash)**
- 22 commits preserve granular history
- Commit messages follow `Phase X.Y:` convention — useful for bisect
- Squash would lose this context

```bash
# On main:
git checkout main
git pull origin main
git merge feature/kimi-visual-analysis-and-optimizations --no-ff
git push origin main
```

Alternative (if commit history is messy):
```bash
gh pr merge 19 --merge
```

### 5.4 — Create First Release Tag

Decide versioning scheme:
- `v0.1.0` if treating as pre-release / beta
- `v1.0.0` if treating as first production release

```bash
git tag -a v1.0.0 -m "v1.0.0: Kimi visual analysis, Tier 5 content generation, frontend overhaul

Features:
- Kimi K2.5 Vision frame-level video analysis (Gemini fallback)
- Tier 5 content: blog post, script, social kit generation
- Voice profile analysis for script mimicry
- Frontend App Router migration (Next.js 14)
- Admin dashboard v2
- Settings v2 with style guides
- Share links with view tracking
- Pipeline speed optimizations (parallel fetching)
- CI/CD via GitHub Actions

Breaking changes:
- Frontend migrated from Pages Router to App Router
- Admin layout completely rebuilt
"

git push origin v1.0.0
```

### 5.5 — Create GitHub Release

```bash
gh release create v1.0.0 \
  --title "v1.0.0 — Visual Analysis & Content Generation" \
  --notes "$(cat <<'EOF'
## Highlights

### Kimi K2.5 Visual Analysis
- Frame-level video content classification
- Content type, originality, third-party detection
- Automatic Gemini 2.5 Flash fallback

### Tier 5 Content Generation
- Blog post generation from research
- Script generation with tone/length controls
- Social media kit (multi-platform)
- Voice profile analysis for mimicry (foundation)

### Frontend Overhaul
- Next.js 14 App Router migration
- Admin dashboard v2
- Settings v2 with style guides
- Accessibility improvements (ARIA, focus, motion)

### Infrastructure
- GitHub Actions CI (lint + test on PR)
- Pipeline speed optimizations
EOF
)"
```

### 5.6 — Post-Merge Verification

1. Verify Railway auto-deploys from main (if configured)
2. If not auto-deploy, trigger manual deploy
3. Run smoke test: create a video analysis job via prod UI
4. Check Railway logs for any startup errors
5. Verify frontend loads on Vercel

## Todo Checklist

- [ ] 5.1 Review PR #19 in logical groups
- [ ] 5.1 Verify no secrets committed
- [ ] 5.1 Verify no debug statements
- [ ] 5.2 All tests pass locally
- [ ] 5.2 CI passes on GitHub
- [ ] 5.3 Merge PR #19 to main
- [ ] 5.4 Create release tag
- [ ] 5.5 Create GitHub Release with notes
- [ ] 5.6 Verify Railway deployment
- [ ] 5.6 Verify Vercel frontend
- [ ] 5.6 Smoke test: create job on prod

## Success Criteria
- PR #19 merged to main
- CI green on main branch
- Release tag exists: `git tag -l` shows `v1.0.0`
- GitHub Releases page has entry with notes
- Prod services healthy after deploy

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Merge conflicts with main | LOW — main hasn't diverged | `git fetch origin main` before merge |
| Railway deploy fails (new deps, env vars) | HIGH | Check Dockerfile, verify all new env vars set on Railway |
| Vercel build fails (App Router migration) | MED | Verify `next.config.js` + build locally first |
| Regression on main | HIGH | Full test suite + smoke test |

## Security Considerations
- Review diff for any accidental secret commits before merge
- Verify `.env.example` is committed, `.env` is in `.gitignore`
- Check that no test files contain real API keys
