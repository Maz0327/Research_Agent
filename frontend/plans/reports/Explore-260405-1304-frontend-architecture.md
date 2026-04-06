# Frontend Architecture Exploration Report
**Date:** 2026-04-05  
**Scope:** Complete mapping of job creation, job detail, iterate system, API layer, routing, state management, UI components, export, and progress tracking.

---

## 1. JOB CREATION FLOW

### Entry Point: Dashboard
- **File:** `/app/(app)/dashboard/page.tsx` (server component wrapper)
- **Main Component:** `DashboardContent` in `/components/dashboard/dashboard-content.tsx`
  - Renders `DashboardStats` (stats cards)
  - Renders `RecentJobsList` (paginated job table)
  - Renders "New Research" button that opens `JobCreationWizard` in a Dialog
  - Polls jobs every 5s while any job is `running` or `queued` (via `useJobs` hook)
  - Shows completion banner for 5s when job completes

### Wizard Component Tree
**File:** `/components/dashboard/job-creation-wizard.tsx`

```
JobCreationWizard (orchestrator, manages step state)
├── Step 1: WizardStepTopic
│   └── Topic input field with validation
├── Step 2: WizardStepSources
│   └── SourceEntry[] (url + type dropdown)
│   └── Each source has: url, type (video/article/reddit/text)
├── Step 3: WizardStepMode
│   └── Pipeline selector dropdown
│   └── Niche dropdown (auto/category-based)
└── Step 4: WizardStepPreview
    └── Shows interpreted_topic, ambiguities, interpretations[]
    └── Calls previewJob() before advancing

Wizard Flow:
  - Topic validation required (non-empty)
  - Sources optional (empty array allowed for text)
  - Pipeline required (quick/full/etc)
  - Preview fetch on step 4 (calls POST /jobs/preview)
  - Disabled: previewJob endpoint is deprecated (410 Gone since 2026-01-26)
```

### Data Flow: Creating a Job
1. User enters topic + sources + pipeline + niche in wizard
2. Clicks "Submit" → calls `createJob()` from Zustand store
3. Store action: `POST /jobs` with `{prompt, pipeline, niche, options}`
4. Response: `{job_id}` 
5. New job added to local state at top of jobs list
6. Dialog closes, polling starts immediately (5s interval)

**Key Methods:**
- `createJob(prompt, pipeline, niche?, options?)` → Promise<string> (returns jobId)
- `previewJob(prompt, pipeline, niche)` → Promise<JobPreview> (DEPRECATED)

---

## 2. JOB RESULTS/DETAIL PAGE

### Route & Layout
- **Route:** `/app/(app)/jobs/[id]/page.tsx`
- **Server Wrapper:** `JobDetailPage` component
  - Gets jobId from params
  - Delegates to `JobDetailContent` (client component)

### Three-Column Layout
**File:** `/components/job-detail-v2/job-detail-content.tsx`

```
JobDetailContent (orchestrator + polling)
│
├── TanStack Query Hook: useJobDetail(jobId)
│   └── Polls GET /jobs/{jobId} every 3s while job.status ∈ {running, queued}
│
├── Left Panel (JobLeftPanel)
│   ├── Job meta card (title, status, progress, eta)
│   ├── Source summary (number of sources analyzed)
│   └── Stage indicator (current pipeline stage)
│
├── Center Panel (JobCenterPanel)
│   ├── DocumentNav (doc selector: 0/1/2/3/4/5/6/7)
│   ├── DocumentViewer (renders selected doc with typed renderer)
│   ├── VersionSelector (shows available versions of doc)
│   └── ExportToolbar (PDF/DOCX buttons)
│
└── Right Panel (JobRightPanel)
    └── ActivityFeed
        ├── Shows job status updates
        ├── Shows iteration history
        └── Shows booster/producer runs
```

### Document Types & Renderers
| Doc | Label | Renderer | Content Source |
|-----|-------|----------|-----------------|
| 0 | Source Ledger | `SourceLedgerRenderer` | `artifacts.source_ledger` or `doc_0_path` |
| 1 | Jump-Start | `JumpStartRenderer` | `artifacts.jump_start` or `doc_1_path` |
| 2 | Semantic Brief | `SemanticBriefRenderer` | `artifacts.semantic_brief` or `doc_2_path` |
| 3 | Creator Brief | `CreatorBriefRenderer` | `artifacts.creator_brief_md` or `doc_3_path` |
| 4 | Producer Packet | (inline) | `artifacts.producer_packet_md` or `doc_4_path` |
| 5 | Script | `ScriptRenderer` | `artifacts.script` |
| 6 | Social Kit | `SocialKitRenderer` | `artifacts.social_kit` |
| 7 | Blog Post | `BlogPostRenderer` | `artifacts.blog_post` |

**Key Insight:** Documents 0-3 are the main pipeline; 4-7 are optional extended outputs.

### Document Navigation
**File:** `/components/job-detail-v2/document-nav.tsx`
- Renders doc tabs only if doc path or inline content exists
- Clicking tab sets `selectedDoc` in parent state
- Defaults to highest-numbered available doc (Doc 3 > 2 > 1 > 0)

### Export Functionality
**File:** `/components/job-detail-v2/export-toolbar.tsx`
- **PDF Export:** `exportToPdf(markdown, filename)` from `/lib/pdf-export.ts`
  - Uses `html2pdf.js` library
  - Converts markdown to PDF
- **DOCX Export:** `exportToDocx(markdown, filename)` from `/lib/docx-export.ts`
  - Uses `docx` npm package
  - Creates Word documents from markdown
- Both extract markdown from `getDocMarkdown(job, docType)`
- Disabled if no markdown content available

---

## 3. CHAT SHEET / ITERATION SYSTEM

### Iteration Interface
**File:** `/components/job-detail-v2/chat-sheet.tsx`
- Right-side Sheet component with two tabs: **Iterate** | **Brainstorm**

#### Iterate Tab
**Supported Modes:**
1. `deep_dive` — Find gaps and search directions (Doc 1 only)
2. `expand_sources` — Add new sources + re-run pipeline (Doc 0/1/2/3)
3. `deeper` — Re-extract with more depth (Doc 0/1/2/3)
4. `different_angle` — Same data, new perspective (Doc 2/3)
5. `custom` — User-defined instructions (varies)
6. `inline_edit` — Edit specific sections of docs

UI:
- Dropdown to select mode
- Text area for user prompt/instruction
- Submit button (sends to backend)
- Error display

**Data Flow:**
1. User selects mode + enters prompt
2. Calls `iterateJob(jobId, {mode, user_prompt, max_new_sources, angle})`
3. Backend: `POST /jobs/{jobId}/iterate`
4. Response: `{iterate_id}` 
5. Job status updates: `iteration_status = 'queued'`, `iteration_id = iterate_id`
6. Polling detects iteration and updates progress

#### Brainstorm Tab
- Simple topic input
- Calls `brainstormTopic(topic)`
- Used for pre-research ideation (Phase 2A)

### Refine Panel (Alternative UI)
**File:** `/components/iterate/RefinePanel.tsx`
- Natural language iteration dialog
- Users describe what they want in plain English
- System infers mode via keyword matching (`inferIterateMode()`)
- Generates contextual suggestion chips based on job data
- Hides technical mode names from users
- Motion animations (Framer Motion)

**Key Benefit:** Better UX than mode selector dropdown

---

## 4. API CLIENT LAYER

### Fetch Utilities
**File:** `/lib/api-client.ts`
- `apiFetch(endpoint, options)` — Basic fetch with timeout (default 30s)
- `authFetch(endpoint, token, options)` — Adds Authorization header
- `parseJsonResponse<T>(response)` — Parse with error handling

**Feature:** Timeout support via AbortController

### Zustand Store Methods
**File:** `/store/jobs.ts`

Main operations:
```
// Job CRUD
createJob(prompt, pipeline, niche?, options?)
createTextInputJob(request)
createScreenshotInputJob(file, topic, platform, context)
createMixedInputJob(request)
createClaimExtractionJob(request)
fetchJobs()
refreshJob(jobId)
cancelJob(jobId)
deleteJob(jobId)
archiveJob(jobId)
unarchiveJob(jobId)

// Iteration
iterateJob(jobId, request) → POST /jobs/{jobId}/iterate
  request: {mode, user_prompt?, max_new_sources?, angle?, ...}
  response: {iterate_id, ...}

// Search & Brief (Phase 5)
searchTopic(topic, depth?, category?)
fetchQuickBrief(searchId)
approveSearchSources_v2(searchId, selectedUrls)

// Extended outputs
triggerBooster(jobId, runId?)
triggerProducerPacket(jobId, runId?)

// Brainstorm & Analysis (Phases 2A/3A)
brainstormTopic(topic, audienceHint?, styleGuideId?)
analyzeCreator(creatorName, videoUrls)
```

### TanStack Query Hooks
**Polling Logic:**

**useJobs()** (`/hooks/use-jobs.ts`)
- Fetches `GET /jobs`
- Refetch interval: 5s if any job is `running` or `queued`, else false
- Used in dashboard for live job list

**useJobDetail(jobId)** (`/hooks/use-job-detail.ts`)
- Fetches `GET /jobs/{jobId}`
- Refetch interval: 3s if job is `running` or `queued`, else false
- Used in job detail page for live updates

**usePreviewJob()** (`/hooks/use-preview-job.ts`)
- Mutation for preview (DEPRECATED, returns 410 Gone)

**useCreateJob()** (`/hooks/use-create-job.ts`)
- Mutation for creating job
- Invalidates ['jobs'] query on success

### Error Handling
- `formatApiError()` from `/lib/error-utils.ts`
- Extracts error messages from API responses
- Falls back to generic message if JSON parsing fails

---

## 5. ROUTING STRUCTURE

### Next.js App Router Layout
```
/app
├── layout.tsx (root layout with AuthProvider)
├── page.tsx (landing page — redirects to /dashboard or /login)
├── login/page.tsx (auth page)
├── error.tsx (global error boundary)
├── not-found.tsx (404 page)
├── providers.tsx (TanStack Query ClientProvider)
│
├── (app)/ (authenticated route group)
│   ├── layout.tsx (AppShell wrapper with sidebar)
│   ├── dashboard/page.tsx (main dashboard)
│   ├── jobs/[id]/page.tsx (job detail for single job)
│   ├── queue/page.tsx (job queue view)
│   ├── transcripts/page.tsx (transcript management)
│   ├── settings/page.tsx (user settings)
│   ├── usage/page.tsx (usage stats)
│   └── loading.tsx (loading skeleton)
│
├── (admin)/ (admin route group)
│   ├── layout.tsx (admin shell)
│   ├── admin/page.tsx (admin dashboard)
│   ├── admin/jobs/page.tsx (admin job view)
│   ├── admin/users/page.tsx (user management)
│   └── admin/errors/page.tsx (error logs)
│
└── shared/[token]/page.tsx (shared job links)
```

### Route Groups
- `(app)` — Authenticated pages with standard app shell
- `(admin)` — Admin pages with admin shell
- No group — Public pages (login, landing)

### Auth Flow
- Root page checks for Supabase session cookie → redirects to /dashboard or /login
- AuthProvider in providers.tsx (pages/ integration, legacy)
- middleware.ts enforces auth for /app routes

---

## 6. STATE MANAGEMENT

### Zustand Store
**File:** `/store/jobs.ts` (main store)

**State Structure:**
```typescript
interface JobsState {
  // Core data
  jobs: Job[]
  archivedJobs: Job[]
  
  // Loading states
  isLoading: boolean
  isLoadingArchived: boolean
  isRefreshing: boolean
  actionInProgress: 'booster' | 'producer' | 'iteration' | 'cancel' | 'delete' | 'archive' | null
  
  // Preview
  preview: JobPreview | null
  isPreviewLoading: boolean
  
  // Bulk selection
  selectedJobIds: Set<string>
  isEditMode: boolean
  bulkErrors: BulkError[]
  
  // Document versioning
  documentVersions: Record<string, DocumentVersion[]>
  
  // Search discovery (Phase 5)
  searchResults: SearchDiscoveryResponse | null
  isSearching: boolean
  quickBrief: QuickBriefResponse | null
  isLoadingQuickBrief: boolean
  
  // Brainstorm pre-stage
  brainstormResult: any | null
  isBrainstorming: boolean
  
  // Creator analysis
  creatorAnalysisResult: any | null
  isAnalyzingCreator: boolean
  
  // Methods (see section 4 for full list)
  fetchJobs, createJob, iterateJob, ...
}
```

### Other Stores
- `/store/settings.ts` — User preferences, voice profiles
- `/store/style-guides.ts` — User-defined style guides
- `/store/ui-preferences.ts` — UI theme/layout prefs
- `/store/admin.ts` — Admin operations
- `/store/voice-profiles.ts` — Voice/tone preferences

### TanStack Query Integration
- QueryClient created in `/lib/query-client.ts`
- Wrapped in `<QueryClientProvider>` in `providers.tsx`
- All hooks use `@tanstack/react-query` v5.91.0

---

## 7. UI COMPONENT LIBRARY

### Component Structure
```
/components/ui/ (shadcn/ui primitives)
├── button.tsx
├── card.tsx
├── dialog.tsx
├── select.tsx
├── sheet.tsx (right-side drawer)
├── tabs.tsx
├── input.tsx
├── progress.tsx
├── badge.tsx
├── accordion.tsx
├── avatar.tsx
├── scroll-area.tsx
├── tooltip.tsx
├── separator.tsx
├── collapsible.tsx
├── Skeleton.tsx
├── Spinner.tsx
├── ProgressRing.tsx (circular progress)
├── GradientText.tsx (styled text)
├── FloatingActionButton.tsx
└── StageIndicator.tsx (custom progress indicator)
```

### Layout Components
```
/components/layout/
├── app-shell.tsx (main app wrapper)
├── three-column-layout.tsx (job detail layout)
├── sidebar.tsx (desktop nav)
├── sidebar-mobile.tsx (mobile nav)
├── sidebar-nav.tsx (nav items)
├── pipeline-status-bar.tsx (stage progress)
├── user-menu.tsx (account dropdown)
└── theme-toggle-button.tsx (dark/light switch)
```

### Feature Components
```
/components/
├── dashboard/ (job list, wizard, stats)
├── job-detail-v2/ (main job detail)
├── job-detail/ (legacy version)
├── job-card/ (job card renderers)
├── document-v2/ (doc renderers)
│   ├── source-ledger-renderer.tsx
│   ├── jump-start-renderer.tsx
│   ├── semantic-brief-renderer.tsx
│   ├── creator-brief-renderer.tsx
│   ├── script-renderer.tsx
│   ├── social-kit-renderer.tsx
│   └── blog-post-renderer.tsx
├── document-drawer/ (legacy doc display)
├── document/ (legacy doc components)
├── iterate/ (RefinePanel.tsx for iteration UI)
├── unified-input/ (multi-source input forms)
│   ├── UnifiedInputPanel.tsx
│   ├── AddSourceModal.tsx
│   ├── SourceCard.tsx
│   └── source-forms/ (VideoSourceForm, ArticleSourceForm, TextSourceForm, ScreenshotSourceForm)
├── queue/ (job queue view)
├── settings/ (user settings)
├── settings-v2/ (new settings UI)
├── transcripts/ (transcript management)
├── brainstorm/ (brainstorm component)
├── search/ (search discovery)
├── claim-extractor/ (claim extraction UI)
├── creator-analysis/ (creator analysis)
├── creator-brief/ (creator brief gen)
└── common/ (reusable utilities)
```

### Design System
- **Styling:** Tailwind CSS + custom utilities
- **Theme:** Dark/light mode via next-themes
- **Icons:** lucide-react
- **Animations:** Framer Motion
- **Markdown:** react-markdown + remark-gfm + rehype-sanitize

---

## 8. EXPORT FUNCTIONALITY

### Supported Formats
1. **PDF Export** → `exportToPdf(markdown, filename)`
   - Library: `html2pdf.js`
   - Input: Markdown string
   - Output: PDF file download
   - File: `/lib/pdf-export.ts`

2. **DOCX Export** → `exportToDocx(markdown, filename)`
   - Library: `docx` (npm package)
   - Input: Markdown string
   - Output: Word document download
   - File: `/lib/docx-export.ts`

3. **Clipboard Copy** (implicit)
   - Copy button in document header (if implemented)
   - Would use `navigator.clipboard.writeText(markdown)`

### Export Entry Point
- `ExportToolbar` component in job detail center panel
- Calls `getDocMarkdown(job, docType)` to extract markdown
- PDF/DOCX buttons load state while exporting
- Error message if no markdown available

### Markdown Processing
- **File:** `/lib/document-formatters.ts`
- Functions:
  - `formatInternalId(id)` — Format IDs for display
  - `preprocessDocumentMarkdown(markdown)` — Fix rendering issues
  - `transformMarkdownForDisplay(markdown)` — User-friendly transforms
  - Handles URLs, internal references, branch diagrams

---

## 9. PROGRESS/POLLING LOGIC

### Job Status States
```typescript
type JobStatus = 
  | 'queued'                  // Waiting to run
  | 'running'                 // Active processing
  | 'completed'               // Success
  | 'completed_with_warnings' // Success + warnings
  | 'failed'                  // Error
  | 'failed_insufficient'     // Not enough data
  | 'cancelled'               // User cancelled
  | 'disambiguating'          // Waiting for user to clarify topic
```

### Polling Strategy
**Dashboard (useJobs hook):**
- Interval: 5 seconds (when any job is active)
- Disabled when all jobs are completed/failed/cancelled
- Refetch triggered by TanStack Query's `refetchInterval` function

**Job Detail (useJobDetail hook):**
- Interval: 3 seconds (when job is active)
- Faster polling for single job view
- Disabled when job completes

**Polling Interval Constants:**
```typescript
POLLING_INTERVALS = {
  JOB_STATUS: 2000,      // Legacy: 2s
  TRANSCRIPTS: 2000,     // 2s
  ETA_UPDATE: 1000,      // 1s
  DASHBOARD_REFRESH: 30000 // 30s (unused in new system)
}
```

### Progress Tracking
**Job Object Fields:**
```typescript
{
  id: string                  // Job UUID
  status: JobStatus           // Current status
  progress_percent: number    // 0-100
  stage: string              // Current pipeline stage
  stage_started_at: string   // ISO timestamp for ETA
  pass_detail: string        // Detail like "Analyzing video 2/5"
  
  // Iteration progress
  iteration_status: string
  iteration_progress_percent: number
  
  // Booster progress
  booster_status: string
  booster_progress_percent: number
  
  // Producer progress
  producer_status: string
  producer_progress_percent: number
}
```

### ETA Calculation
**File:** `/hooks/useETA.ts`
- Estimates time remaining based on:
  - Current stage
  - Time stage_started_at
  - Historical stage durations
- Updates every 1 second during active job

### Stage Labels
**File:** `/lib/constants.ts` → `STAGE_LABELS`
- Maps backend snake_case names to user-friendly labels
- Includes descriptions for additional context
- Examples:
  - `source_identity` → "Identifying Sources"
  - `semantic_extraction` → "Extracting Claims"
  - `semantic_synthesis` → "Connecting Themes"
  - `creator_brief_assembly` → "Assembling Creator Brief"

### Completion Detection
- Dashboard detects when job transitions from `running/queued` → `completed/completed_with_warnings`
- Shows "Research complete" banner for 5 seconds
- Auto-dismisses or can be manually closed

---

## COMPONENT TREE SUMMARY

### Dashboard Flow
```
RootPage (redirect)
└── DashboardContent
    ├── DashboardStats (stats cards)
    ├── RecentJobsList (paginated table)
    │   └── DashboardJobCard[] or JobTable[]
    └── JobCreationWizard (in Dialog)
        ├── WizardStepTopic
        ├── WizardStepSources
        ├── WizardStepMode
        └── WizardStepPreview
```

### Job Detail Flow
```
JobDetailPage (server component)
└── JobDetailContent (client, uses useJobDetail hook)
    └── ThreeColumnLayout
        ├── JobLeftPanel
        │   ├── JobMetaCard
        │   └── SourceSummary
        ├── JobCenterPanel
        │   ├── DocumentNav
        │   ├── DocumentViewer
        │   │   └── DocRenderer (typed renderer)
        │   │       └── SourceLedgerRenderer | JumpStartRenderer | ...
        │   ├── VersionSelector
        │   └── ExportToolbar
        └── JobRightPanel
            └── ActivityFeed
    └── ChatSheet
        ├── IterateTab
        │   └── Mode selector + prompt input
        └── BrainstormTab
            └── Topic input
```

---

## KEY FINDINGS FOR UX OVERHAUL

### What to Keep
1. ✅ Three-column layout (proven, works well)
2. ✅ Document navigation tabs (simple, effective)
3. ✅ TanStack Query polling (robust, conditional)
4. ✅ Zustand store (lightweight, performant)
5. ✅ ChatSheet for iterations (good right-side UX)
6. ✅ RefinePanel natural language mode (better than dropdown)
7. ✅ Export toolbar (PDF/DOCX working)

### What to Redesign
1. 🔄 Job creation wizard — 4 steps could be condensed to 2-3
2. 🔄 Dashboard job list — Consider card layout vs table
3. 🔄 Document renderers — May need refresh for new doc formats
4. 🔄 Progress visualization — Stage indicator could be more detailed
5. 🔄 ChatSheet tabs — Could be combined or redesigned
6. 🔄 Activity feed — Might benefit from timeline visualization

### Data Points for New Features
- All polling intervals configurable in `/lib/constants.ts`
- All API endpoints routed through store methods
- All UI components use shadcn/ui (easy to customize)
- Markdown processing pipeline exists (can enhance)
- Document versioning infrastructure in place
- Iteration modes well-defined (can add new modes)

---

## FILE PATHS REFERENCE

### Critical Files
- `/app/(app)/dashboard/page.tsx` — Dashboard entry
- `/app/(app)/jobs/[id]/page.tsx` — Job detail entry
- `/components/dashboard/job-creation-wizard.tsx` — Job wizard
- `/components/job-detail-v2/job-detail-content.tsx` — Job detail orchestrator
- `/components/job-detail-v2/chat-sheet.tsx` — Iteration UI
- `/components/iterate/RefinePanel.tsx` — Natural language iteration
- `/store/jobs.ts` — Main state store (1800+ lines)
- `/lib/api-client.ts` — Fetch utilities
- `/hooks/use-jobs.ts` — Dashboard polling hook
- `/hooks/use-job-detail.ts` — Detail page polling hook
- `/components/layout/three-column-layout.tsx` — Main layout
- `/components/layout/app-shell.tsx` — App wrapper

### Document Renderers
- `/components/document-v2/source-ledger-renderer.tsx`
- `/components/document-v2/jump-start-renderer.tsx`
- `/components/document-v2/semantic-brief-renderer.tsx`
- `/components/document-v2/creator-brief-renderer.tsx`

### Export
- `/lib/pdf-export.ts` — PDF conversion
- `/lib/docx-export.ts` — Word document conversion
- `/lib/document-formatters.ts` — Markdown preprocessing

### Configuration
- `/lib/constants.ts` — All constants (stages, limits, polling)
- `/package.json` — Dependencies (Next.js 14, Zustand, TanStack Query, shadcn/ui, Framer Motion)

---

## UNRESOLVED QUESTIONS

1. **Upcoming UX Changes:** What specific aspects of the current UX need overhaul? (Flows, visual design, performance, accessibility?)
2. **New Document Types:** Will Doc 5-7 (Script, Social Kit, Blog Post) renderers need enhancement?
3. **Mobile Experience:** Should the three-column layout adapt differently on mobile vs current responsive design?
4. **Iteration Feedback:** Should iterations show diff view between baseline and new versions?
5. **Batch Operations:** Will bulk job operations (delete, archive) need better UX?
6. **Search Integration:** Phase 5 search discovery—how will this integrate into main wizard flow?
7. **Error Handling:** Should job failures show more granular error details or remain simplified?
8. **Document Versioning:** Current system shows v1 only—will users need to browse all 4 versions?

