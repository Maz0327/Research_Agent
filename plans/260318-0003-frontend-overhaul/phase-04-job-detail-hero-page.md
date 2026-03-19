# Phase 4: Job Detail — The Hero Page

## Context
- Plan: [plan.md](plan.md)
- Depends on: [Phase 2](phase-02-layout-system-sidebar-columns.md) (ThreeColumnLayout), [Phase 3](phase-03-core-pages-dashboard-queue.md) (stores adapted)
- Current: `pages/jobs/[id].tsx` (510 lines), 11 job-detail components, 20 job-card components
- Target: `app/(app)/jobs/[id]/page.tsx` with 3-column layout

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 |
| Status | pending |
| Effort | 8h |
| Description | Rebuild job detail as 3-column layout with document tabs, activity feed, and chat Sheet |

## Key Insights
- This is the MOST COMPLEX page — orchestrates documents, iteration, brainstorm, source explorer, exports
- Current page (510 lines) delegates to 11 `job-detail/` components and 20 `job-card/` components
- Left panel: job metadata (status, mode, sources count, timestamps) + document tab navigation
- Center: active document content rendered by document-type-specific renderers (Phase 5)
- Right panel: activity log/job events + toggle button for iterate/brainstorm Sheet
- Sheet slides in from right for iterate/brainstorm — overlays right panel
- Document version selector (RunSelector) moves into left panel
- Inline editing (EditableSection) preserved in center content area
- Export toolbar (PDF/DOCX) stays with center content, above document

## Requirements
1. 3-column layout using ThreeColumnLayout from Phase 2
2. Left panel: job metadata card, source summary, document nav tabs
3. Center: pipeline status bar + document content (delegated to renderers)
4. Right panel: activity log feed
5. Toggleable iterate/brainstorm Sheet (shadcn/ui Sheet, side="right")
6. Document version selector
7. Source explorer with tags and mode badges
8. Export toolbar (PDF/DOCX)
9. Real-time polling for running jobs
10. Mobile: single column, panels as drawers

## Architecture

### Page Component Tree
```
app/(app)/jobs/[id]/page.tsx              # Server: extract id param
  └── JobDetailContent.tsx                # 'use client': fetch job, orchestrate layout
       ├── ThreeColumnLayout
       │   ├── left: JobLeftPanel
       │   │   ├── JobMetaCard.tsx         # Status, mode, timestamps, source count
       │   │   ├── SourceSummary.tsx       # Source list with type tags, mode badges
       │   │   ├── DocumentNav.tsx         # Tab-style nav: Doc 0-7 (only available docs)
       │   │   └── VersionSelector.tsx     # Dropdown per document for version switching
       │   │
       │   ├── center: JobCenterPanel
       │   │   ├── PipelineStatusBar      # From Phase 2
       │   │   ├── ExportToolbar.tsx       # PDF/DOCX buttons
       │   │   └── DocumentViewer.tsx      # Renders active document (Phase 5 renderers)
       │   │
       │   └── right: JobRightPanel
       │       ├── ActivityFeed.tsx        # Job events/logs timeline
       │       └── ChatToggle.tsx          # Button to open iterate/brainstorm Sheet
       │
       └── ChatSheet.tsx                  # Sheet overlay (side="right")
            ├── IteratePanel.tsx           # Iterate form + mode selector
            └── BrainstormPanel.tsx        # Brainstorm form + angle cards
```

### Component Directory
```
components/job-detail/
├── JobDetailContent.tsx     # Main orchestrator ('use client')
├── JobLeftPanel.tsx         # Left column container
├── JobCenterPanel.tsx       # Center column container
├── JobRightPanel.tsx        # Right column container
├── JobMetaCard.tsx          # Metadata card
├── SourceSummary.tsx        # Source list with tags
├── DocumentNav.tsx          # Document tab navigation
├── VersionSelector.tsx      # Version dropdown
├── ExportToolbar.tsx        # PDF/DOCX export buttons
├── DocumentViewer.tsx       # Active doc renderer dispatcher
├── ActivityFeed.tsx         # Event timeline
├── ChatToggle.tsx           # Sheet trigger button
└── ChatSheet.tsx            # Iterate/brainstorm Sheet
```

### State Flow
```
URL param [id] → JobDetailContent fetches job → populates useJobsStore
  → selectedDocIndex (which doc tab is active)
  → selectedVersion (which version within that doc)
  → iterateMode (deep_dive|expand_sources|deeper|different_angle|custom)
  → chatSheetOpen (boolean for Sheet visibility)
  → polling active if job.status === 'running'
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `pages/jobs/[id].tsx` | Reference → decompose | 510 lines |
| `components/job-detail/*` | Reference → migrate | 11 components |
| `components/job-card/DocumentCard.tsx` | Reference | Document display logic |
| `components/job-card/DocumentCardGrid.tsx` | Reference | Grid layout |
| `components/job-card/DocumentViewerModal.tsx` | Superseded | Replaced by center panel |
| `components/job-card/ExportButton.tsx` | Reference → migrate | Export logic |
| `components/job-card/ShareButton.tsx` | Reference → migrate | Share functionality |
| `components/document-drawer/*` | Reference → migrate | Drawer + version selector |
| `components/iterate/IterateDialog.tsx` | Reference → ChatSheet | Iterate form |
| `components/iterate/RefinePanel.tsx` | Reference → ChatSheet | Refine UI |
| `components/brainstorm/BrainstormPanel.tsx` | Reference → ChatSheet | Brainstorm form |
| `components/brainstorm/AngleCard.tsx` | Preserve | Angle display card |
| `components/search/SearchApprovalView.tsx` | Reference → migrate | Search approval flow |
| `lib/document-formatters.ts` | Preserve | 16.8KB of formatting logic |
| `lib/pdf-export.ts` | Preserve | PDF export |
| `lib/docx-export.ts` | Preserve | DOCX export |
| `lib/intent-router.ts` | Reference | Navigation routing |
| `lib/iterate-intent.ts` | Reference | Iterate intent classification |

## Implementation Steps

### 4.1 Create app/(app)/jobs/[id]/page.tsx
- Server component: extract `id` from params
- Render `<JobDetailContent jobId={id} />`

### 4.2 Build JobMetaCard
- shadcn/ui Card with:
  - Job title (large)
  - StatusBadge (from Phase 3)
  - Analysis mode badge
  - Source count
  - Created / updated timestamps
  - Topic description

### 4.3 Build SourceSummary
- Compact list of sources with:
  - Source title (truncated)
  - Type tag (transcript, article, video, text)
  - Mode badge (transcript_grounded, caption_grounded, etc.)
  - Confidence ceiling indicator
- Collapsible if >5 sources

### 4.4 Build DocumentNav
- Vertical tab-style navigation
- Lists available documents: Doc 0 (Source Ledger), Doc 1 (Jump-Start), etc.
- Only shows docs that exist for this job
- Active doc highlighted
- Click updates selectedDocIndex in local state
- Badge showing version count per doc

### 4.5 Build VersionSelector
- shadcn/ui Select dropdown
- Shows versions for active document (v1, v2, v3, v4)
- Displays version metadata: date, trigger (initial/iterate/expand)
- Default to latest version

### 4.6 Build ExportToolbar
- Two buttons: PDF, DOCX
- Uses existing `lib/pdf-export.ts` and `lib/docx-export.ts`
- Loading state during export generation
- Download triggers browser save dialog

### 4.7 Build DocumentViewer
- Dispatcher component that renders the correct renderer based on doc type
- Props: `document`, `version`, `jobId`
- Maps doc index to renderer:
  - 0 → SourceLedgerRenderer
  - 1 → JumpStartRenderer
  - 2 → SemanticBriefRenderer
  - 3 → CreatorBriefRenderer
  - 5 → ScriptRenderer
  - 6 → SocialKitRenderer
  - 7 → BlogPostRenderer
- Wraps in ScrollArea
- Shows skeleton while loading

### 4.8 Build ActivityFeed
- Timeline-style event list
- Events: job created, stage started, stage completed, document generated, iteration triggered
- Each event: timestamp, icon, description
- Auto-scroll to latest event
- Maps from job status/progress data

### 4.9 Build ChatSheet
- shadcn/ui Sheet (side="right", modal=false for desktop overlay)
- Two modes via tabs: Iterate, Brainstorm
- **Iterate tab**: mode selector (deep_dive, expand_sources, deeper, different_angle, custom) + text input + submit
- **Brainstorm tab**: prompt input + angle cards display
- Submit triggers store actions (iterate/brainstorm)
- Close button returns to right panel

### 4.10 Build ChatToggle
- Floating-action-style button in right panel
- Opens ChatSheet on click
- Badge indicator if iteration is in progress

### 4.11 Build JobLeftPanel, JobCenterPanel, JobRightPanel
- Container components that compose their children
- Handle responsive behavior (collapsible on mobile)
- Left panel: collapsible on tablet, Sheet on mobile
- Right panel: hidden on tablet, Sheet on mobile

### 4.12 Build JobDetailContent
- Main orchestrator ('use client')
- Fetches job by ID on mount via store
- Sets up polling for running jobs
- Manages local state: selectedDocIndex, selectedVersion, chatSheetOpen
- Passes data to all child components
- Handles loading/error states
- Composes: ThreeColumnLayout with all three panels

### 4.13 Integration test
- Navigate to job detail from dashboard
- Verify 3-column layout on desktop
- Switch document tabs
- Switch versions
- Open/close Chat Sheet
- Test iterate submission
- Test export buttons
- Verify polling updates
- Test mobile responsive collapse

## Todo
- [ ] 4.1 Create jobs/[id]/page.tsx
- [ ] 4.2 JobMetaCard
- [ ] 4.3 SourceSummary
- [ ] 4.4 DocumentNav
- [ ] 4.5 VersionSelector
- [ ] 4.6 ExportToolbar
- [ ] 4.7 DocumentViewer dispatcher
- [ ] 4.8 ActivityFeed
- [ ] 4.9 ChatSheet (iterate + brainstorm)
- [ ] 4.10 ChatToggle
- [ ] 4.11 Panel containers (left, center, right)
- [ ] 4.12 JobDetailContent orchestrator
- [ ] 4.13 Integration test

## Success Criteria
- 3-column layout renders correctly on desktop (>1280px)
- Left panel shows job metadata and document navigation
- Center panel shows active document content
- Right panel shows activity feed
- Chat Sheet opens/closes with iterate and brainstorm tabs
- Document tab switching works
- Version switching works
- Export buttons trigger PDF/DOCX download
- Polling updates status for running jobs
- Mobile: single column with drawers for panels
- `npm run build` passes

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Complex state orchestration bugs | High | High | Keep state minimal, local for UI, store for data |
| Export functionality regression | Medium | High | Preserve existing export libs exactly, test manually |
| Polling interference with Sheet interactions | Low | Medium | Polling updates store, Sheet reads from store, no conflicts |
| Mobile layout broken | Medium | Medium | Test at 375px early, use Sheet components for all panels |
| DocumentViewer rendering wrong doc type | Low | High | Type-safe dispatcher with exhaustive switch |

## Security Considerations
- Job ID from URL params must be validated (not used in raw SQL, backend handles this)
- Export downloads should not include sensitive data beyond job content
- Iterate/brainstorm submissions go through authenticated API calls
- Shared view (Phase 7) must NOT show iterate/brainstorm panel

## Next Steps
Phase 5: Build all 7 document type renderers that plug into DocumentViewer.
