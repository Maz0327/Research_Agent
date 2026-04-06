---
title: "Pre-Prep: UX Foundation & Design System"
description: "Fix design system debt, creator-facing copy, and UX foundations before building new features"
status: pending
priority: P0
effort: 2-3w
branch: feature/product-viability-overhaul
tags: [ux, design-system, accessibility, copy, cleanup]
created: 2026-04-06
---

# Pre-Prep: UX Foundation & Design System

**Why this exists:** The UI/UX audit scored 5.2/10. Building new features (single-screen input, hero doc, streaming) on top of 998 hardcoded colors, engineer-speak copy, and broken citations would compound the debt. Fix the foundation first.

**Audit source:** `plans/reports/ui-ux-audit-260406-1329-current-state.md`
**Follows:** Phase 00 (Cleanup & Removals) from product-viability-overhaul plan
**Blocks:** Phases 01-10 of product-viability-overhaul

---

## Phase Map

| Phase | Name | Status | Effort | Blocking |
|-------|------|--------|--------|----------|
| PP-1 | [Design Token Migration](phase-pp1-design-token-migration.md) | complete | 3-5d | None |
| PP-2 | [Font & Type Scale](phase-pp2-font-type-scale.md) | complete | 1-2d | None |
| PP-3 | [Creator Copy Rewrite](phase-pp3-creator-copy-rewrite.md) | complete | 2-3d | None |
| PP-4 | [Citation Pills & Source Links](phase-pp4-citation-source-links.md) | pending | 1-2d | PP-1 |
| PP-5 | [Progress UX Polish](phase-pp5-progress-ux-polish.md) | pending | 1-2d | PP-1 |
| PP-6 | [Iteration UX Redesign](phase-pp6-iteration-ux-redesign.md) | pending | 2-3d | PP-1, PP-3 |
| PP-7 | [First Impressions & Onboarding](phase-pp7-first-impressions.md) | pending | 2-3d | PP-2, PP-3 |

**PP-1, PP-2, PP-3 complete** (3/7).
**PP-4, PP-5 unblocked** (ready to start).
**PP-6, PP-7 unblocked** (all dependencies met).

---

## Session 260406 Checkpoint

**Completed this session:**
- PP-1: Design Token Migration — 1464 color replacements across 100 files, emoji→Lucide icons in 7 files. Zero hardcoded zinc/gray. Commit: `a2e3b63`
- PP-2: Font & Type Scale — Inter → Plus Jakarta Sans, type scale defined. 66 files updated. Commit: `a2e3b63`
- PP-3: Creator Copy Rewrite — 22 files rewritten. All user-facing strings updated. Commit: `d51cc18`

**Ready to start next session:**
- PP-4: Citation Pills (unblocked, all design tokens available)
- PP-5: Progress UX Polish (unblocked, all design tokens available)
- PP-6: Iteration UX Redesign (unblocked, all copy rewritten)
- PP-7: First Impressions (unblocked, all copy + fonts ready)

---

## Success Criteria

- Zero hardcoded `text-zinc-*`, `bg-zinc-*`, `text-gray-*`, `bg-gray-*` in component code
- Plus Jakarta Sans as primary font with defined type scale
- All user-facing strings use creator language (no "Semantic Brief", "Iterate", "Pipeline")
- Citation pills clickable → navigate to source URL
- Stage descriptions shown during pipeline progress with ETA
- Iteration redesigned as quick-action cards with descriptions
- Login page shows positioning statement + creator-focused copy
- WCAG AA contrast (4.5:1) on all text
- All tests pass, build succeeds
