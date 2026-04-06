# Frontend Architecture — Quick Reference
**Date:** 2026-04-05 | **Full Report:** `Explore-260405-1304-frontend-architecture.md`

---

## Entry Points (User Journeys)

### 1. Create a Job
**Path:** Dashboard → New Research button → JobCreationWizard dialog
- Steps: Topic → Sources → Mode → Preview → Submit
- Store method: `createJob(prompt, pipeline, niche)`
- Endpoint: `POST /jobs`
- Result: Job queued, polling starts (5s interval)

### 2. View Job Results
**Path:** Dashboard job card → Click → Job detail page
- Route: `/jobs/[id]`
- Hook: `useJobDetail(jobId)` (polls every 3s)
- Layout: Three-column (left=meta, center=docs, right=activity)
- Default doc: Doc 3 (Creator Brief) if available, else 2 → 1 → 0

### 3. Iterate on Results
**Path:** Job detail → "AI Actions" sheet (right side)
- Modes: deep_dive | expand_sources | deeper | different_angle | custom | inline_edit
- Store method: `iterateJob(jobId, request)`
- Endpoint: `POST /jobs/{jobId}/iterate`
- Alternative UI: `RefinePanel` (natural language)

---

## Key Component Files

| Component | File | Purpose |
|-----------|------|---------|
| Dashboard | `/components/dashboard/dashboard-content.tsx` | Job list + stats + wizard trigger |
| Wizard | `/components/dashboard/job-creation-wizard.tsx` | 4-step job creation flow |
| Job Detail | `/components/job-detail-v2/job-detail-content.tsx` | Main orchestrator + polling |
| Chat Sheet | `/components/job-detail-v2/chat-sheet.tsx` | Iterate + Brainstorm tabs |
| Doc Viewer | `/components/job-detail-v2/document-viewer.tsx` | Renders selected doc |
| Export | `/components/job-detail-v2/export-toolbar.tsx` | PDF/DOCX buttons |
| Layout | `/components/layout/three-column-layout.tsx` | 3-column container |

---

## Data Flow

```
User Input (Wizard)
    ↓
Store Action (createJob)
    ↓
API Call (POST /jobs)
    ↓
Local State Update
    ↓
Polling Hook (useJobs/useJobDetail)
    ↓
TanStack Query Cache
    ↓
Component Re-render
    ↓
UI Update
```

---

## Polling Logic

| Hook | Interval | Enabled When | Used In |
|------|----------|--------------|---------|
| `useJobs()` | 5s | Any job is `running` or `queued` | Dashboard |
| `useJobDetail(jobId)` | 3s | Job is `running` or `queued` | Job detail page |

**Key:** Polling automatically stops when all jobs are idle (completed/failed/cancelled).

---

## Document Types (Doc 0-7)

### Core Pipeline (Always Generated)
- **Doc 0:** Source Ledger — sources analyzed
- **Doc 1:** Jump-Start — research directions
- **Doc 2:** Semantic Brief — patterns & themes
- **Doc 3:** Creator Brief — hero document (usually selected by default)

### Optional Extended Outputs
- **Doc 4:** Producer Packet — production-ready (user-triggered)
- **Doc 5:** Script — video script draft
- **Doc 6:** Social Kit — social media content
- **Doc 7:** Blog Post — long-form article

---

## State Management

### Main Store: `/store/jobs.ts` (Zustand)
- `jobs: Job[]` — Active jobs
- `archivedJobs: Job[]` — Archived jobs
- `actionInProgress: string | null` — Loading state
- Methods: `createJob()`, `iterateJob()`, `brainstormTopic()`, `fetchJobs()`, etc.

### Query Cache: TanStack Query
- `['jobs']` — Dashboard job list
- `['job', jobId]` — Single job detail
- Auto-manages refetch intervals

---

## API Layer

### Utilities
- `apiFetch(endpoint, options)` — Basic fetch + timeout
- `authFetch(endpoint, token, options)` — Add auth header
- `parseJsonResponse<T>(response)` — Parse + error handling

### Main Endpoints (via Zustand)
- `POST /jobs` — Create job
- `GET /jobs` — List jobs
- `GET /jobs/{jobId}` — Get job detail
- `POST /jobs/{jobId}/iterate` — Start iteration
- `POST /jobs/search` — Search discovery (Phase 5)
- `POST /jobs/text-input` — Text input job
- `POST /jobs/screenshot-input` — Screenshot input job

---

## UI Components Used

### From shadcn/ui
Button, Card, Dialog, Select, Sheet, Tabs, Input, Progress, Badge, Accordion, ScrollArea, Tooltip, Spinner, Skeleton

### Custom Components
- StageIndicator (circular progress)
- GradientText
- FloatingActionButton
- ProgressRing
- ThemeToggle

---

## Export Formats

| Format | Library | Method |
|--------|---------|--------|
| PDF | html2pdf.js | `exportToPdf(markdown, filename)` |
| DOCX | docx npm package | `exportToDocx(markdown, filename)` |
| Clipboard | Navigator API | Not yet implemented |

---

## Routing Structure

```
/                          → Redirect (/dashboard or /login)
/login                     → Auth page
/dashboard                 → Main dashboard (authenticated)
/jobs/[id]                 → Job detail (authenticated)
/queue                     → Job queue view
/settings                  → User settings
/usage                     → Usage stats
/admin/*                   → Admin pages
/shared/[token]            → Shared job (public)
```

---

## Critical Thresholds & Limits

| Limit | Value | Enforced Where |
|-------|-------|-----------------|
| Max prompt length | 2000 chars | `/lib/constants.ts` |
| Max text content | 50k chars | Form validation |
| Max screenshot size | 10MB | File upload |
| API timeout | 30s | `apiFetch()` |
| Poll interval (dashboard) | 5s | `useJobs()` |
| Poll interval (detail) | 3s | `useJobDetail()` |
| ETA update | 1s | `useETA()` hook |

---

## Dependencies

**Key Libraries:**
- **Next.js 14** — Framework
- **Zustand** — State management
- **TanStack Query 5** — Server state
- **Supabase JS** — Auth
- **shadcn/ui** — Components
- **Tailwind CSS** — Styling
- **Framer Motion** — Animations
- **react-markdown** — Markdown rendering

---

## Common Modifications

### Add Polling Interval
Edit `/lib/constants.ts` → `POLLING_INTERVALS` object

### Add New Document Type
1. Create renderer in `/components/document-v2/`
2. Update `DocumentViewer` switch statement
3. Add to `DOC_META` mapping
4. Add to `getDocMarkdown()` in ExportToolbar

### Add New Iterate Mode
1. Add mode to `IterateMode` type in `/types/run.ts`
2. Add config in `ITERATE_MODE_CONFIG`
3. Update ChatSheet mode selector
4. Add case in `RefinePanel.ts` keyword matching

### Change Job Creation Steps
Edit `/components/dashboard/job-creation-wizard.tsx` → `WizardStep*` components

---

## Performance Notes

- **Dashboard:** Polls every 5s (conditional) — low CPU impact
- **Job Detail:** Polls every 3s (conditional) — acceptable for single job view
- **Memory:** Zustand store kept minimal (no large caches)
- **Network:** TanStack Query caches responses, reduces redundant calls
- **Rendering:** React memo used in lists, conditional polling prevents constant re-renders

---

## Testing Approach

- Unit tests for store methods: `__tests__/store/`
- Component tests for wizards/modals: `__tests__/components/`
- Integration tests via React Testing Library
- Run: `npm test` or `npm run test:watch`

---

**For detailed architecture, see: `Explore-260405-1304-frontend-architecture.md`**
