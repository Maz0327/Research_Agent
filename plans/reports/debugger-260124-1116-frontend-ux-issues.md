# Frontend UI/UX Issues Investigation Report

**Date:** 2026-01-24
**Investigator:** Claude (Debugger Agent)
**Scope:** Document expansion mechanism, visual hierarchy, loading states

---

## Executive Summary

Investigated three UI/UX issues in Research Agent frontend:

1. **Document expansion using dropdown instead of fullscreen overlay** - Currently uses `DocumentAccordion` with inline collapse/expand. Need fullscreen modal.
2. **Documents need better visual hierarchy** - Markdown rendering is basic, lacks proper section titles, spacing, formatting.
3. **Loading states appear at top instead of on card** - `ActiveTaskBanner` shows at page top; should show on individual artifact cards.

All issues identified with clear remediation paths. No blocking technical constraints found.

---

## Issue 1: Document Expansion Mechanism

### Current Implementation

**Component:** `DocumentAccordion.tsx` (lines 111-346)

**Behavior:**
- Documents expand inline using framer-motion `AnimatePresence`
- Max height constraint: `max-h-[20rem] sm:max-h-[28rem]` (line 296)
- Scrollable content within accordion
- Uses accordion pattern with chevron icon rotation

**Usage Locations:**
- NOT currently used in job detail page (`/pages/jobs/[id].tsx`)
- Used in legacy dashboard/job cards via `JobResults.tsx`

**Current Modal Implementation:**
- `DocumentViewerModal.tsx` EXISTS and implements fullscreen overlay (lines 1-334)
- Supports slide-in from right with backdrop blur
- Mobile swipe-to-close gesture
- Already integrated in `DocumentCardGrid.tsx` (line 416-425)

### Root Cause

Two parallel document display systems exist:

1. **New system** (`DocumentCardGrid` + `DocumentViewerModal`): Used in job detail page, opens fullscreen modal ✓
2. **Old system** (`DocumentAccordion`): Used in job card components, expands inline ✗

### Evidence

```typescript
// JobResults.tsx line 242-260 - Uses DocumentCardGrid (good)
<DocumentCardGrid
  jobId={jobId}
  jobTitle={jobTitle}
  artifacts={artifacts}
  // ... opens DocumentViewerModal on click
/>

// DocumentAccordion.tsx line 264-308 - Inline expansion (bad)
<AnimatePresence>
  {isExpanded && (
    <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }}>
      {/* Content limited to max-h-[20rem] */}
    </motion.div>
  )}
</AnimatePresence>
```

### Recommendation

**Remove `DocumentAccordion` entirely.** Replace all usages with `DocumentCardGrid` which already opens `DocumentViewerModal` fullscreen.

**Action Items:**
1. Search for `DocumentAccordion` imports: `frontend/components/**/*.tsx`
2. Replace with `DocumentCardGrid` calls
3. Archive `DocumentAccordion.tsx` to prevent future use
4. Update any mobile-specific job card views

---

## Issue 2: Document Visual Hierarchy

### Current Implementation

**Markdown Rendering Components:**
- `DocumentAccordion.MarkdownRenderer` (lines 313-343)
- `DocumentViewerModal.MarkdownRenderer` (lines 288-331)

**Current Formatting:**

```typescript
// Basic regex-based markdown parsing
.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold...">$1</h3>')
.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold...">$1</h2>')
.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold...">$1</h1>')
```

**Problems:**
- No section dividers between major sections
- Insufficient spacing between document parts
- Headers don't use document structure semantics
- No visual distinction for document metadata vs content
- Lists lack proper indentation hierarchy
- Code blocks lack syntax highlighting

### Document Structure Analysis

Documents follow semantic structure (from `doc/authoritative/spec/Document_Output_Format.md`):

```
# Document Title
## Metadata Section
- Source count, key points, etc.

## Key Points
- Bulleted list with details

## Claims
- High-confidence claims

## Cross-Source Patterns
- Themes, tensions, gaps
```

### Recommendation

**Create dedicated document formatter component:**

```typescript
// New: DocumentViewer.tsx
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';

const DOCUMENT_PROSE_STYLES = {
  h1: 'text-3xl font-bold text-white mb-6 pb-3 border-b-2 border-gray-700',
  h2: 'text-2xl font-semibold text-gray-100 mt-8 mb-4 pb-2 border-b border-gray-700/50',
  h3: 'text-xl font-medium text-gray-200 mt-6 mb-3',
  ul: 'space-y-2 my-4 ml-4',
  li: 'list-disc text-gray-300 leading-relaxed',
  code: 'bg-gray-800 px-2 py-0.5 rounded text-blue-300 font-mono text-sm',
  pre: 'bg-gray-800 rounded-lg p-4 my-4 overflow-x-auto',
  p: 'text-gray-300 leading-relaxed my-3',
  strong: 'font-semibold text-gray-100',
  em: 'italic text-gray-400',
};
```

**Action Items:**
1. Install `react-markdown` and `rehype-highlight`
2. Create `DocumentViewer.tsx` with proper prose styles
3. Replace `MarkdownRenderer` in both modal components
4. Add section dividers for major headings
5. Implement collapsible sections for long documents
6. Add "Table of Contents" for docs > 1000 lines

---

## Issue 3: Loading States Location

### Current Implementation

**Top-Level Banner:** `ActiveTaskBanner.tsx` (lines 1-152)

**Rendered at:** `/pages/jobs/[id].tsx` lines 366-375

```typescript
{/* Active Task Banner - RENDERS AT TOP OF PAGE */}
<AnimatePresence>
  {activeTask && (
    <ActiveTaskBanner
      taskType={activeTask.type}
      status={activeTask.status}
      progressPercent={activeTask.progress}
      iterationId={activeTask.iterationId}
    />
  )}
</AnimatePresence>
```

**Card-Level Indicators:** `ArtifactCard.tsx` lines 218-233

```typescript
{/* Progress bar for running state - ON CARD */}
{state === 'running' && (
  <div className="mt-3">
    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <motion.div animate={{ width: `${progressPercent}%` }} />
    </div>
  </div>
)}
```

### Root Cause

**Dual rendering of loading states:**

1. **Top banner** shows when booster/iteration/producer running (redundant global indicator)
2. **Card progress bar** shows inline on specific artifact card (correct local indicator)

Banner duplicates information already visible on cards, pushes content down, creates visual clutter.

### Evidence - Flow Analysis

**User triggers booster:**
1. Clicks "Expand with Deep Research" button
2. `ArtifactCard` (booster) state changes to `running`
3. Shows progress bar ON THE CARD ✓
4. ALSO triggers `ActiveTaskBanner` at page top ✗ (redundant)

**Visual hierarchy conflict:**
- Banner draws attention AWAY from the card actually processing
- User must look at top of page, then scroll to find which card is running
- Mobile: banner pushes artifact grid below fold

### Recommendation

**Remove `ActiveTaskBanner` from job detail page.**

**Rationale:**
- `ArtifactCard` already shows `running` state with progress bar (lines 96-101, 218-233)
- Card has spinning loader icon during `running` state (line 209-211)
- Card shows queued pulsing indicator (line 212-214)
- All information in banner is redundant with card state

**Preserve banner for main job running:**
Keep lines 378-407 in `/pages/jobs/[id].tsx` for primary job execution (not secondary tasks).

**Action Items:**
1. Remove `ActiveTaskBanner` import and usage for secondary tasks (lines 366-375)
2. Keep banner ONLY for main job status (lines 378-407)
3. Enhance `ArtifactCard` running state visibility:
   - Increase progress bar height from `h-1.5` to `h-2`
   - Add pulse animation to card border when running
   - Add percentage text above progress bar
4. Archive `ActiveTaskBanner.tsx` for secondary tasks (only use for primary job)

**Alternative (if banner must stay):**
- Move banner INSIDE artifact grid, positioned above the running card
- Use portal to render banner adjacent to active card
- Collapse banner to small chip on mobile

---

## Technical Dependencies

### Safe to Modify

✓ `DocumentAccordion.tsx` - No critical dependencies
✓ `ActiveTaskBanner.tsx` - Only used in one location
✓ `MarkdownRenderer` functions - Local to each component
✓ CSS/styling changes - No breaking changes

### Requires Testing

⚠️ `DocumentCardGrid.tsx` - Core document display logic
⚠️ `DocumentViewerModal.tsx` - Modal interactions
⚠️ `ArtifactCard.tsx` - State management
⚠️ Mobile responsive behavior - Touch targets, swipe gestures

### External Dependencies to Add

📦 `react-markdown` - Better markdown rendering
📦 `rehype-highlight` - Code syntax highlighting
📦 `remark-gfm` - GitHub Flavored Markdown support

---

## Prioritized Action Plan

### Phase 1: Loading States (Low Risk, High Impact)
1. Remove `ActiveTaskBanner` for secondary tasks in `/pages/jobs/[id].tsx`
2. Enhance `ArtifactCard` running state visual prominence
3. Test booster/iteration/producer triggering flows
4. Verify mobile behavior

### Phase 2: Document Expansion (Medium Risk, High Impact)
1. Audit all `DocumentAccordion` usages
2. Replace with `DocumentCardGrid` + `DocumentViewerModal`
3. Archive `DocumentAccordion.tsx`
4. Regression test document viewing across all job states

### Phase 3: Visual Hierarchy (Low Risk, Medium Impact)
1. Install markdown rendering dependencies
2. Create `DocumentViewer.tsx` with enhanced prose styles
3. Replace inline `MarkdownRenderer` functions
4. Add table of contents for long documents
5. Implement collapsible sections

---

## Unresolved Questions

1. **Mobile experience:** Should document modal slide from bottom on mobile instead of right?
2. **Keyboard navigation:** Should arrow keys navigate between documents in modal?
3. **Document search:** Should modal include in-document search/highlight?
4. **Print styles:** Do documents need print-optimized CSS?
5. **A11y:** Screen reader testing needed for modal focus trap?

---

## Supporting Files

**Key Components:**
- `/frontend/components/job-card/DocumentAccordion.tsx` - Replace
- `/frontend/components/job-card/DocumentViewerModal.tsx` - Enhance
- `/frontend/components/job-card/DocumentCardGrid.tsx` - Keep
- `/frontend/components/job-detail/ActiveTaskBanner.tsx` - Remove from secondary tasks
- `/frontend/components/job-detail/ArtifactCard.tsx` - Enhance running state
- `/frontend/pages/jobs/[id].tsx` - Remove banner for secondary tasks

**Test Coverage Needed:**
- Document modal open/close flows
- Card state transitions (ready → running → completed)
- Mobile swipe gestures
- Keyboard navigation
- Loading state race conditions

---

## Conclusion

All three issues stem from legacy code coexisting with newer implementations. DocumentAccordion is superseded by DocumentCardGrid+Modal. ActiveTaskBanner duplicates ArtifactCard states. Markdown rendering is basic regex instead of proper parsing.

**Estimated Effort:**
- Phase 1: 2-3 hours
- Phase 2: 4-6 hours
- Phase 3: 3-4 hours

**Total:** ~10-13 hours with testing

**Risk:** Low - Changes are mostly removals of redundant code + styling improvements. No database/backend changes required.
