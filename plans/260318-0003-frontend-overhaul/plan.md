---
title: "Frontend Overhaul: App Router + shadcn/ui"
description: "Complete frontend redesign with 3-column dashboard, App Router migration, shadcn/ui components"
status: pending
priority: P1
effort: 44h
branch: feature/kimi-visual-analysis-and-optimizations
tags: [frontend, redesign, app-router, shadcn-ui, dashboard]
created: 2026-03-18
---

# Frontend Overhaul: App Router + shadcn/ui

Big-bang migration from Pages Router to App Router with shadcn/ui design system,
3-column job detail layout, and toggleable chat panel.

## Scope

- 14 pages migrated to `app/` directory
- 27 component directories refactored into new hierarchy
- 6 Zustand stores adapted for client/server split
- Tailwind class-based dark mode to CSS variables
- New 3-column layout for job detail (hero page)
- Toggleable iterate/brainstorm Sheet panel

## Phases

| # | Phase | Effort | Status | File |
|---|-------|--------|--------|------|
| 1 | Foundation: App Router + shadcn/ui | 5h | pending | [phase-01](phase-01-foundation-app-router-shadcn.md) |
| 2 | Layout System: Sidebar + 3-Column | 5h | pending | [phase-02](phase-02-layout-system-sidebar-columns.md) |
| 3 | Core Pages: Dashboard + Queue + TanStack Query | 8h | pending | [phase-03](phase-03-core-pages-dashboard-queue.md) |
| 4 | Job Detail: Hero Page | 8h | pending | [phase-04](phase-04-job-detail-hero-page.md) |
| 5 | Document Renderers: All 7 Types | 6h | pending | [phase-05](phase-05-document-renderers.md) |
| 6 | Supporting Pages | 5h | pending | [phase-06](phase-06-supporting-pages.md) |
| 7 | Auth, Shared, Polish | 5h | pending | [phase-07](phase-07-auth-shared-polish.md) |

## Key Decisions

- **Big bang rollout** — no incremental migration, replace `pages/` entirely
- **shadcn/ui** — copy-paste components, full control, CSS variable theming
- **next-themes** — replaces custom ThemeContext.tsx
- **Zustand stays** — all stores get `'use client'` directive, server components pass data via props
- **Framer Motion** — page transitions only; Tailwind/CSS for micro-interactions
- **TanStack Query** — replaces manual Zustand polling for data fetching
- **3-column layout** — left (job meta + nav), center (documents), right (activity + chat Sheet)

## Risk Summary

- Job detail page (510 lines) is the most complex migration target
- jobs.ts store (1926 lines) needs careful client-boundary handling
- dashboard.tsx (945 lines) has deeply embedded job creation logic
- Export functionality (PDF/DOCX) must be preserved exactly

## Validation Summary

**Validated:** 2026-03-18
**Questions asked:** 7

### Confirmed Decisions
- **Theme:** Dark-only (CSS vars still structured for future light mode)
- **Job creation:** Redesign as multi-step wizard with progress indicator (+2h to Phase 3)
- **Auth package:** `@supabase/ssr` for server-side session checks in middleware
- **E2E tests:** Deferred to separate effort — plan stays focused on UI migration
- **Animations:** Framer Motion for page transitions only; Tailwind animations for everything else
- **Data fetching:** Add TanStack Query — replaces manual polling in Zustand stores
- **Old UI components:** Archive all except GlowCard (keep + adapt for new design system)

### Action Items (all applied)
- [x] Update Phase 1: add `@tanstack/react-query` to deps, add QueryClientProvider to root layout
- [x] Update Phase 3: redesign job creation as multi-step wizard (+2h effort, 6h → 8h)
- [x] Update Phase 3+4: refactor Zustand stores to use TanStack Query for fetching, keep Zustand for UI state only
- [x] Update Phase 7: use `@supabase/ssr` instead of auth-helpers; remove Playwright from scope
- [x] Update Phase 7: keep GlowCard, archive GradientText + FloatingActionButton
- [x] Update effort total: 40h → 44h (wizard +2h, TanStack Query integration +2h)
