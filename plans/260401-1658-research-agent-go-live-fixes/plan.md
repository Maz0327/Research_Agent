---
title: "Research Agent Go-Live Blockers & Fixes"
description: "Comprehensive plan addressing all CRITICAL/HIGH/MEDIUM/LOW blockers before production go-live"
status: pending
priority: P1
effort: 14-18h
branch: feature/kimi-visual-analysis-and-optimizations
tags: [go-live, devops, type-safety, frontend, testing, release]
created: 2026-04-01
---

# Research Agent — Go-Live Fixes

**Scope:** 18 issues across 6 phases. All blockers from status report + frontend UX plan residuals.
**Branch:** `feature/kimi-visual-analysis-and-optimizations` (PR #19)
**Approach:** Fix all blockers on current branch, then merge PR #19 as a single reviewed unit.

## Phases

| # | Phase | File | Effort | Priority | Status | Blocked By |
|---|-------|------|--------|----------|--------|------------|
| 1 | [Infrastructure & DevOps](phase-01-infrastructure-devops.md) | CI/CD, migration 027, OpenAI, branches | 3h | CRITICAL | Pending | — |
| 2 | [Type Safety & Code Quality](phase-02-type-safety-code-quality.md) | actionInProgress types, llm_judge os.getenv, audit-H8 | 2h | HIGH | Pending | — |
| 3 | [Frontend Polish](phase-03-frontend-polish.md) | Design tokens, a11y, focus colors, JobRow extraction | 3-4h | HIGH/MED | Pending | — |
| 4 | [Live Testing & Validation](phase-04-live-testing-validation.md) | Test endpoints, Whisper, voice mimicry | 2-3h | CRITICAL | Pending | Phase 1 |
| 5 | [PR Strategy & Release](phase-05-pr-strategy-release.md) | PR #19 review, release tag | 2-3h | HIGH | Pending | Phase 1-4 |
| 6 | [Deferred Decisions](phase-06-deferred-decisions.md) | CURRENT_PLAN phases 2-5, dialogs, voice UI | 1-2h | LOW | Pending | — |

## Dependency Graph

```
Phase 1 (Infra) ─────────────┐
Phase 2 (Types) ──── parallel ├──► Phase 4 (Live Test) ──► Phase 5 (PR + Release)
Phase 3 (Frontend) ───────────┘
Phase 6 (Deferred) ─── independent, decision-only
```

## Issue-to-Phase Map

| # | Issue | Sev | Phase |
|---|-------|-----|-------|
| 1 | Migration 027 not deployed | CRIT | 1 |
| 2 | OpenAI balance likely $0 | CRIT | 1 |
| 3 | Live testing not done | CRIT | 4 |
| 4 | PR #19 massive | CRIT | 5 |
| 5 | No CI/CD | HIGH | 1 |
| 6 | Design token gaps (3 admin tables) | HIGH | 3 |
| 7 | Keyboard navigation missing | HIGH | 3 |
| 8 | actionInProgress `as any` casts | HIGH | 2 |
| 9 | API key audit (ADMIN_EMAILS, JINA, os.getenv) | MED | 2 |
| 10 | Missing ScriptOptionsDialog / SocialKitOptionsDialog | MED | 6 |
| 11 | Voice profile options not wired to UI | MED | 6 |
| 12 | audit-H8 TODO in share_routes.py | MED | 2 |
| 13 | No-op hover in recent-jobs-list | LOW | 3 |
| 14 | Hardcoded focus:border-blue-500 | LOW | 3 |
| 15 | Stale branches | LOW | 1 |
| 16 | No releases/tags | LOW | 5 |
| 17 | CURRENT_PLAN phases 2-5 | PLAN | 6 |
| 18 | 8 open code review items | MED | 3 |

## Principles

- Fix on current branch, do NOT split PR #19 (splitting 294 files is riskier than reviewing)
- Run `pytest` + `npm run build` after every phase
- Commit per-phase with conventional commits
- No new features — fixes and polish only
