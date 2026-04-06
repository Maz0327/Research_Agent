# Research Agent: User Experience Flow Exploration

**Date:** 2026-04-05  
**Focus:** End-to-end UX flow for job submission, progress tracking, results presentation, iteration, and error handling.

---

## 1. JOB SUBMISSION UX

### Landing Flow
- **Root Page (`/`):** Server-side cookie check redirects authenticated users to `/dashboard`, others to `/login`
- **Dashboard Entry:** Loads `DashboardContent` which polls for jobs every 5s (when any job is active)

### Job Creation: 4-Step Wizard
Located: `frontend/components/dashboard/job-creation-wizard.tsx`

**Steps:**
1. **Topic Selection** → Plain text input (can be auto-detected intent)
2. **Sources (Optional)** → User can add URLs, text, or leave empty for web discovery
3. **Mode Selection** → Pipeline choice (quick, full, breaking_news, investigation, profile, controversy)
4. **Preview** → Calls `POST /jobs/preview` to fetch sample interpretations before commit

**Intelligence:** `StartInput` component detects intent in real-time:
- Plain text → topic/search discovery flow
- URLs → own sources flow
- Claim extraction language → claim mode
- Creator + style → creator analysis

**Form Validation:**
- Step 1: Requires topic (>0 chars)
- Step 3: Requires pipeline selection
- Step 4: Fetches preview before advancing (with error fallback)

**Navigation:** Back/Next buttons with progress bar showing current step

---

## 2. PROGRESS/WAITING UX

### Polling Strategy
- **useJobDetail Hook:** Polls job status every **3 seconds** while `status === 'running' | 'queued'`
- **useJobs Hook:** Polls jobs list every **5 seconds** when any job is active
- **Cache Invalidation:** Creating a job invalidates `['jobs']` query immediately

### On-Page Feedback
**PipelineStatusBar** (displays in center panel header):
- **Running:** Pulsing green dot + stage name + progress % + ETA
- **Completed:** Green checkmark + "Complete"
- **Failed:** Red X + error message
- **Queued:** Clock icon + "Waiting…"

**Progress Bar:** Horizontal bar animates 0-100% during running state

**Activity Feed** (right panel):
```
Timeline of events:
- Job created (clock icon)
- Running: [stage] (spinner)
- Doc 0 generated (file icon)
- Doc 1 generated (file icon)
- Doc 2 generated (file icon)
- Doc 3 generated (file icon) ← Hero doc
- Iteration X completed
- Job completed (checkmark)
```

### Dashboard-Level Feedback
**CompletionBanner:** Green success bar appears automatically when job finishes:
```
✓ Research complete — [job title] · [N documents] ready
```
Auto-dismisses after 5 seconds or on X click.

### No Real-Time Streaming
- No WebSocket or SSE implemented
- Purely polling-based with TanStack Query intervals
- Backend status via `GET /jobs/{job_id}` returns: status, stage, progress_percent, error, warnings

---

## 3. RESULTS PRESENTATION

### Document Navigation
**Left Panel (DocumentNav):**
```
Documents
├─ Doc 0: Source Ledger (zinc) — "What was analyzed"
├─ Doc 1: Jump-Start (blue) — "Where to go next"
├─ Doc 2: Semantic Brief (purple) — "What sources reveal"
├─ Doc 3: Creator Brief (amber) — "Your hero document"
└─ Doc 4: Producer Packet (green) — "Production-ready package"
```

Only available docs shown (conditionally rendered). Click to switch.

### Document Display
**DocumentViewer (center panel):**
- Header with doc label + subtitle + "Doc N" badge
- ScrollArea with typed renderer (not generic JSON dump)
- Typed renderers exist for:
  - Doc 0: `SourceLedgerRenderer` (table of sources)
  - Doc 1: `JumpStartRenderer` (search directions/gaps)
  - Doc 2: `SemanticBriefRenderer` (themes, claims, quotes)
  - Doc 3: `CreatorBriefRenderer` (angles, hooks, story arcs)
  - Doc 4: `ProducerPacketRenderer` (production assets)
  - Docs 5-7: Script, Social Kit, Blog Post renderers

**Empty State:** If doc not generated: "Doc N not yet generated — Complete the pipeline to generate this document"

### Document Content
- **Self-contained:** Each doc reads independently
- **Quoted content:** Inline prose + quote blocks with source attribution
- **Expandable sections:** Collapsible content with section headers
- **Confidence badges:** Visual indicators (HIGH/MEDIUM/LOW with color coding)
- **Searchable/copyable:** Text selectable and copyable

### No Tabs, Sidebar-Based Nav
- Fixed left panel with doc buttons (not tab bar)
- Vertical scrolling in center panel
- Active doc highlighted with blue background + border

---

## 4. ITERATION/REFINEMENT UX

### Trigger: "AI Actions" Button
Located in right panel (JobRightPanel):
```
[✨ AI Actions (Iterate / Brainstorm)]
```

Opens **ChatSheet** (right-side modal) with two tabs:

### Iterate Tab
```
Mode [dropdown v]
├─ Deep Dive — gaps/search directions
├─ Expand Sources — add sources and re-run
├─ Go Deeper — re-extract with more depth
├─ Different Angle — same data, new perspective
├─ Custom — user-defined instructions
└─ Inline Edit — edit existing content

Instructions [text area]
[Submit Button]
```

- User selects mode + writes instructions
- `POST /jobs/{job_id}/iterate` with mode + user_prompt
- UI closes sheet on success
- Activity feed updates with "Iteration N running"

### Brainstorm Tab
```
Topic [text area]
[Submit Button]
```
- Ideation mode for exploring angles without running pipeline
- Returns brainstorm results (displayed elsewhere)

### Iteration Status Tracking
- Shows in Activity Feed as "Iteration N [running/completed/failed]"
- Each iteration gets RefreshCw icon + status color

### No Document Versioning UI Yet
- Version selector exists but only shows v1 (future feature)
- Versions stored per-document (rolling 4-version window)

---

## 5. DASHBOARD/HISTORY

### Job List View
**RecentJobsList:**
```
[New Research] button (top right)

Job Table:
┌─────────────────────────────────────────┐
│ Title        │ Status    │ Progress │ ETA │
├─────────────────────────────────────────┤
│ Topic XYZ    │ completed │ 100%    │ -   │
│ Topic ABC    │ running   │ 45%     │ 2m  │
│ Topic QWE    │ queued    │ -       │ -   │
└─────────────────────────────────────────┘
```

**Row Features:**
- Clickable to expand for details
- Status badge with color (green/yellow/red/gray)
- Progress bar inline
- ETA calculated from stage + historical speed
- Checkbox for batch operations (when not running)

**Status States:**
- queued (gray, spinner)
- running (blue, progress bar)
- completed (green, checkmark)
- completed_with_warnings (amber)
- failed (red)
- failed_insufficient (red, "insufficient data")

**ETA Calculation:**
From `useETA` hook:
- Estimates time remaining based on progress % and stage
- Updates every 30-60 seconds
- Falls back to stage description if no ETA

### Job Details Meta Card (left panel)
```
Title: [topic/prompt truncated]
Pipeline: quick / full / etc
Created: [relative timestamp]
Status: [badge]
```

### Source Summary (left panel)
```
Sources analyzed: N
├─ Videos: X
├─ Articles: Y
└─ Text: Z
```

### Completion Notification (dashboard level)
Green banner appears when job transitions to completed:
```
✓ Research complete — Topic XYZ · 4 documents ready
```
Dismissible, auto-hides after 5s.

---

## 6. MOBILE RESPONSIVENESS

### Breakpoints
- **Desktop (≥1280px):** 3-column grid (280px left | flex center | 320px right)
- **Tablet (768-1279px):** 2-column (280px left fixed | center main | right Sheet on toggle)
- **Mobile (<768px):** 1-column (left Collapsible | center main | right bottom Sheet)

### Mobile App Shell
**Header:**
```
[≡ Menu] [Research Agent Logo] [Avatar ⋮]
```
- Hamburger menu (SidebarMobile) with nav items
- Logo clickable to dashboard
- User avatar opens menu

**Main Content:**
- Full-width scrollable area

**Bottom Fixed Button (mobile job detail page):**
```
[► Activity] button fixed bottom-right
```
Triggers bottom Sheet with activity feed.

### Responsive Components
- **ThreeColumnLayout:** Adapts all 3 layout variants
- **DocumentNav:** Vertical button list works at any width
- **PipelineStatusBar:** Text + progress bar wraps responsively
- **ChatSheet:** Drawer from right (desktop/tablet) or bottom (mobile)

### Touch Optimization
- Min 44px button heights (accessibility)
- Adequate touch targets (10px+ padding)
- Swipe-friendly Sheet dismissal

---

## 7. ERROR STATES

### Error Display Component
`ErrorDisplay` renders user-friendly messages with expandable technical details:

**Mapping Examples:**
```
"OpenAI API error" → "The AI service is temporarily unavailable"
"rate limit" → "The system is busy. Your request will be processed shortly"
"SIGKILL" → "Processing interrupted due to resource limits"
"memory" → "Processing interrupted. Try with smaller research scope"
"timeout" → "The request took too long. Please try again"
"authentication" → "Your session has expired. Please log in again"
"network" → "Unable to connect. Check internet connection"
```

**UI:**
- Red border + red background
- Error icon + user message
- "Show/Hide technical details" toggle
- Technical details in mono font (collapsed by default)

### Job-Level Errors
**Failed Job:**
- PipelineStatusBar shows red X + error message
- Status badge shows "failed"
- Activity Feed shows "Job failed — [error]"
- DocumentViewer shows "Doc N not yet generated"

**Completed with Warnings:**
- Amber status badge
- Activity Feed shows "Completed with warnings"
- warnings_list returned in API response
- Can still view completed docs

**Insufficient Data:**
- status: "failed_insufficient"
- Red error state
- Suggests trying fewer sources or different topic

### In-Form Errors
- Inline error messages below inputs
- Motion animation (fade in)
- Red text + icon

### Navigation Errors
- Error boundary at app level (`/app/error.tsx`)
- Shows 500 error modal with retry button
- Dev mode shows error details
- Production shows generic message

### Job Creation Errors
- Preview fetch failure: Still advances to step 4 (graceful)
- Job creation failure: Shows error toast, prevents wizard close
- Network error: "Failed to create job" message with retry

---

## 8. BACKEND API: STATUS & PROGRESS ENDPOINTS

### Job Status Endpoint
```
GET /jobs/{job_id}
Response: JobStatusResponse
{
  job_id: string
  status: "queued" | "running" | "completed" | "completed_with_warnings" | 
          "failed" | "failed_insufficient" | "disambiguating"
  stage: "ingestion" | "extraction" | "validation" | "synthesis" | "assembly" | null
  stage_started_at: datetime | null
  progress_percent: 0-100
  error: string | null           // Only if failed
  warnings: [string] | null      // Only if completed_with_warnings
  warning_count: int | null
  artifacts: {                   // Generated documents
    doc_0_path?: string
    doc_1_path?: string
    doc_2_path?: string
    doc_3_path?: string
    source_ledger?: SourceLedger
    jump_start?: JumpStart
    semantic_brief?: SemanticBrief
    creator_brief_md?: string
    iterations?: [IterationRecord]
  }
  interpretations?: [string]     // If disambiguating
}
```

### Job List Endpoint
```
GET /jobs
Response: Job[]
```
Each job has same fields as above.

### Stage Names (STAGE_LABELS)
```python
{
  "queued": "Queued",
  "ingestion": "Gathering sources",
  "extraction": "Analyzing content",
  "validation": "Validating findings",
  "synthesis": "Synthesizing insights",
  "assembly": "Building documents"
}
```

### Polling Configuration
- **Active:** Refetch every 3-5s (TanStack Query refetchInterval)
- **Inactive:** No polling (false)
- Frontend disables polling once status leaves running/queued

### No WebSocket/SSE
- Purely REST-based polling
- No real-time push updates
- TanStack Query manages refetch intervals

---

## 9. ARCHITECTURE DIAGRAM

```
USER INTERFACE
└─ Dashboard (/dashboard)
   ├─ New Research Button → Job Creation Wizard (4 steps)
   │  └─ Submits: POST /jobs [topic, sources, pipeline, niche]
   │     └─ Returns: job_id, enqueued Celery task
   │
   ├─ Job List Table
   │  └─ Polls: GET /jobs every 5s (when active)
   │     └─ Shows: status, progress, ETA, documents_ready
   │
   └─ Completion Banner (auto-dismiss 5s)
      └─ Triggers on: job.status "completed" → "completed_with_warnings"

DETAIL PAGE (/jobs/{id})
├─ Left Panel (280px fixed)
│  ├─ Job Meta Card (title, pipeline, created, status)
│  ├─ Source Summary (count by type)
│  ├─ Document Nav (clickable doc list)
│  └─ Version Selector (future)
│
├─ Center Panel (flex-1)
│  ├─ Pipeline Status Bar (stage, progress, ETA, error)
│  ├─ Export Toolbar
│  └─ Document Viewer
│     ├─ Typed renderers (Doc 0-7)
│     ├─ Scrollable content
│     └─ Empty state if not generated
│
├─ Right Panel (320px, or Sheet on mobile/tablet)
│  ├─ AI Actions Button → ChatSheet
│  │  ├─ Iterate Tab (mode + instructions)
│  │  └─ Brainstorm Tab (topic prompt)
│  │
│  └─ Activity Feed
│     ├─ Job created (clock)
│     ├─ Stage transitions (spinner)
│     ├─ Docs generated (file icons)
│     ├─ Iterations (refresh icons)
│     └─ Job complete (checkmark) or failed (X)
│
└─ Polling: GET /jobs/{id} every 3s (while active)
   └─ Updates: status, stage, progress_percent, stage_started_at, artifacts

ERROR HANDLING
├─ Failed job → Red error box with message + technical details toggle
├─ Validation errors → Inline red text in forms
├─ Network errors → Error toast (bottom-right)
├─ App-level errors → Error page with retry button
└─ Graceful degradation (preview fetch fails → still advance to step 4)
```

---

## 10. KEY METRICS

| Aspect | Value | Notes |
|--------|-------|-------|
| **Poll Interval (job detail)** | 3s | While running/queued |
| **Poll Interval (job list)** | 5s | While any job active |
| **Completion Banner Duration** | 5s | Auto-dismiss |
| **Wizard Steps** | 4 | Topic → Sources → Mode → Preview |
| **Documents per Job** | 0-4 (core) | Docs 0-3 always, 4+ optional |
| **Activity Timeline Events** | 5-8+ | Created, stages, docs, complete |
| **Responsive Breakpoints** | 3 | Mobile <768, Tablet 768-1279, Desktop ≥1280 |
| **Pipeline Stages** | 5 | Ingestion, Extraction, Validation, Synthesis, Assembly |
| **Job Statuses** | 7 | queued, running, completed, completed_with_warnings, failed, failed_insufficient, disambiguating |

---

## 11. SUMMARY: WHAT A USER EXPERIENCES

### Happy Path (End-to-End)
1. **Land on dashboard** → See previous jobs + "New Research" button
2. **Click "New Research"** → Wizard opens (4-step form)
3. **Fill topic** → Auto-detect intent (topic/sources/claims)
4. **Select mode** (quick/full) → Preview fetch before committing
5. **Submit** → Wizard closes, dashboard shows new job with spinner
6. **Green banner appears** → "Research complete · 4 documents ready" (5s auto-dismiss)
7. **Auto-navigated to job detail** OR click job row
8. **See 3-column layout** (desktop):
   - Left: meta + sources + doc nav
   - Center: status bar + full document viewer
   - Right: activity feed + AI Actions button
9. **Read Document 3 (Creator Brief)** ← Hero document with full narrative
10. **Click "AI Actions"** → Iterate mode, select "Deep Dive", write prompt, submit
11. **Watch Activity Feed** → "Iteration 1 running" → "Iteration 1 completed"
12. **New doc version appears** → Can compare before/after

### Error Path
1. **Job fails during extraction** → Red error in status bar + activity shows "Job failed"
2. **User sees error message** → "Unable to fetch video content" (user-friendly translation)
3. **Click "Show technical details"** → Expands to show raw error
4. **Can browse partial results** if completed_with_warnings
5. **Can iterate with different mode** → Brainstorm or expand sources

### Mobile Path
1. **Hamburger menu** opens in header
2. **Tap "New Research"** → Same 4-step wizard (responsive)
3. **Job list** full-width table on mobile (scrollable)
4. **Job detail** single-column:
   - Left panel collapsed (toggle with icon)
   - Center: document viewer (scrolls vertically)
   - Bottom fixed button "► Activity" opens Sheet from bottom
5. **Zoom/scale** inherits system settings (no custom zoom)

---

## UNRESOLVED QUESTIONS

1. **Streaming responses?** Currently pure polling, no SSE/WebSocket. Is this intentional for MVP?
2. **Document versioning UI?** Version selector exists but only shows v1. When rolling window of 4 versions available?
3. **Iteration polling?** Does job detail page auto-fetch while iteration running? Or manual refresh?
4. **Download/export?** ExportToolbar component exists but endpoints not reviewed—how many formats supported?
5. **Comparison mode?** Can users view side-by-side versions of docs 3 across iterations?
6. **Offline support?** No service worker found—is offline mode out of scope?
7. **Analytics/tracking?** No Segment/GA integration visible—is telemetry planned?
8. **Rate limiting?** Frontend shows rate_limit error, but no client-side rate limiting (only server-side HTTP 429)?

---

## FILES REFERENCED

**Frontend:**
- `/frontend/app/page.tsx` — Root redirect logic
- `/frontend/app/(app)/dashboard/page.tsx` — Dashboard server wrapper
- `/frontend/app/(app)/jobs/[id]/page.tsx` — Job detail server wrapper
- `/frontend/components/dashboard/dashboard-content.tsx` — Dashboard orchestrator + completion banner
- `/frontend/components/dashboard/job-creation-wizard.tsx` — 4-step wizard
- `/frontend/components/dashboard/StartInput.tsx` — Intent detection input
- `/frontend/components/job-detail-v2/job-detail-content.tsx` — Job detail orchestrator
- `/frontend/components/job-detail-v2/job-center-panel.tsx` — Center column (status + doc viewer)
- `/frontend/components/job-detail-v2/job-left-panel.tsx` — Left column (meta + nav)
- `/frontend/components/job-detail-v2/job-right-panel.tsx` — Right column (activity + AI actions)
- `/frontend/components/job-detail-v2/document-nav.tsx` — Doc list navigator
- `/frontend/components/job-detail-v2/document-viewer.tsx` — Doc renderer dispatcher
- `/frontend/components/job-detail-v2/chat-sheet.tsx` — Iterate + brainstorm UI
- `/frontend/components/job-detail-v2/activity-feed.tsx` — Timeline of events
- `/frontend/components/layout/pipeline-status-bar.tsx` — Running status indicator
- `/frontend/components/layout/three-column-layout.tsx` — Responsive grid layout
- `/frontend/components/layout/app-shell.tsx` — App root wrapper (header + sidebar)
- `/frontend/components/ErrorDisplay.tsx` — Error rendering with tech details
- `/frontend/app/error.tsx` — App-level error boundary
- `/frontend/hooks/use-jobs.ts` — List jobs polling hook
- `/frontend/hooks/use-job-detail.ts` — Single job polling hook
- `/frontend/hooks/use-create-job.ts` — Job creation mutation
- `/frontend/components/dashboard/JobTable.tsx` — Job list table view

**Backend:**
- `/backend/app/routes/jobs_routes.py` — Job creation + status endpoints
- `/backend/models/job.py` — JobStatusResponse model

