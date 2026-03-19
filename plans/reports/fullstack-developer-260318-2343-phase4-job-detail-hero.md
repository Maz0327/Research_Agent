# Phase Implementation Report

## Executed Phase
- Phase: Phase 4 — Job Detail Hero Page (3-Column Layout)
- Plan: plans/260318-0003-frontend-overhaul/
- Status: completed

## Files Modified
- `frontend/pages/jobs/[id].tsx` → renamed to `[id].tsx.bak` (routing conflict prevention)

## Files Created
| File | Lines |
|------|-------|
| `frontend/hooks/use-job-detail.ts` | 38 |
| `frontend/components/job-detail-v2/job-meta-card.tsx` | 57 |
| `frontend/components/job-detail-v2/source-summary.tsx` | 88 |
| `frontend/components/job-detail-v2/document-nav.tsx` | 86 |
| `frontend/components/job-detail-v2/version-selector.tsx` | 55 |
| `frontend/components/job-detail-v2/export-toolbar.tsx` | 80 |
| `frontend/components/job-detail-v2/document-viewer.tsx` | 78 |
| `frontend/components/job-detail-v2/activity-feed.tsx` | 99 |
| `frontend/components/job-detail-v2/chat-sheet.tsx` | 130 |
| `frontend/components/job-detail-v2/job-left-panel.tsx` | 55 |
| `frontend/components/job-detail-v2/job-center-panel.tsx` | 60 |
| `frontend/components/job-detail-v2/job-right-panel.tsx` | 37 |
| `frontend/components/job-detail-v2/job-detail-content.tsx` | 107 |
| `frontend/app/(app)/jobs/[id]/page.tsx` | 14 |

## Tasks Completed
- [x] Step 1: `hooks/use-job-detail.ts` — TanStack Query hook with 3s polling for active jobs
- [x] Step 2: `job-meta-card.tsx` — title, StatusBadge, mode, source count, timestamps
- [x] Step 3: `source-summary.tsx` — collapsible source list from semantic_extractions
- [x] Step 4: `document-nav.tsx` — vertical tab nav, filters to existing docs only
- [x] Step 5: `version-selector.tsx` — shadcn Select with version label/date/trigger
- [x] Step 6: `export-toolbar.tsx` — PDF + DOCX buttons wired to existing lib exports
- [x] Step 7: `document-viewer.tsx` — dispatcher with Phase 5 placeholder notice
- [x] Step 8: `activity-feed.tsx` — timeline of job events, auto-scroll to latest
- [x] Step 9: `chat-sheet.tsx` — shadcn Sheet with Iterate + Brainstorm tabs
- [x] Step 10: `job-left-panel.tsx` — composes meta + sources + nav + version
- [x] Step 11: `job-center-panel.tsx` — composes PipelineStatusBar + export + viewer
- [x] Step 12: `job-right-panel.tsx` — activity feed + chat trigger button
- [x] Step 13: `job-detail-content.tsx` — orchestrator with loading/error/not-found states
- [x] Step 14: `app/(app)/jobs/[id]/page.tsx` — server component wrapper
- [x] Step 15: Renamed `pages/jobs/[id].tsx` → `.bak`
- [x] Step 16: Build verified — zero errors

## Tests Status
- Type check: pass (tsc bundled in next build — no errors)
- Build: pass — `/jobs/[id]` renders as `ƒ (Dynamic)` server-rendered route
- Unit tests: not run (no test runner configured for frontend in scope)

## Issues Encountered
- None — clean first-pass build

## Notes
- `params` typed as `Promise<{ id: string }>` per Next.js 14 async params pattern
- Existing `lib/pdf-export.ts`, `lib/docx-export.ts`, `lib/document-formatters.ts` untouched
- Existing `components/job-detail/` untouched
- All new files under 200 lines; all use kebab-case naming

## Next Steps
- Phase 5: typed document renderers to replace placeholder in `document-viewer.tsx`
- Version list should be populated from real API version metadata when backend exposes it
- `SourceSummary` currently reads from `semantic_extractions`; may need to handle other source shapes

## Unresolved Questions
- Backend does not yet expose per-document version history — `VersionSelector` shows static `v1` until that endpoint exists
- `brainstormTopic` in the store is scoped to new-job flow; confirm it works from job detail context (no job_id passed)
