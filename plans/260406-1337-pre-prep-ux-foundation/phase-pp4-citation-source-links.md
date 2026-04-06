# Phase PP-4: Citation Pills & Source Links

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 1-2 days
- **Depends on:** PP-1 (tokens)
- **Description:** Make citation pills (SRC_1, SRC_2) clickable — navigate to source URL or scroll to source in sidebar. This is the trust moat — make it visible.

## Key Insights
- Citation pills appear in every document renderer (Key Findings, Story Angles, etc.)
- `citation-pill.tsx` has an `onClick` prop but it's NEVER wired to anything
- Source Ledger (Doc 0) contains URLs for each source
- Clicking SRC_1 should either: open source URL in new tab, OR scroll to that source in the Sources sidebar

## Related Code Files

| File | Change |
|------|--------|
| `components/document-v2/shared/citation-pill.tsx` | Wire onClick, add keyboard handler, add role="button" |
| `components/document-v2/shared/source-reference.tsx` | If exists, update to link |
| `components/job-detail-v2/document-nav.tsx` | Source sidebar scroll-to-source |
| Document renderer files | Pass source URL map to citation pills |

## Implementation Steps

### Task PP-4.1: Build source URL lookup
1. When job completes, Doc 0 (Source Ledger) contains source_id → URL mapping
2. Create a utility: `getSourceUrl(jobData, sourceId) → string | null`
3. Pass this into document renderers as a prop or via context

### Task PP-4.2: Wire citation pills
1. In `citation-pill.tsx`:
   - Accept `href?: string` prop
   - On click: open URL in new tab (`window.open(href, '_blank')`)
   - Add `role="link"` (or `role="button"` if scroll), `tabIndex={0}`, `onKeyDown` (Enter/Space)
   - Add external-link icon indicator (tiny, inline)
   - Style: `cursor-pointer`, hover underline or highlight
2. If no URL available: pill stays as-is (non-interactive) with tooltip "Source not available"

### Task PP-4.3: Add tooltip with source title
1. On hover: show source title + type (e.g., "YouTube: 'The Dark Side of AI' by TechAltar")
2. Use shadcn Tooltip component (already in project)

### Task PP-4.4: Verify
1. Click citation pill → opens source URL in new tab
2. Keyboard: Tab to pill → Enter opens link
3. Hover shows source title
4. Non-linked pills gracefully degrade
5. `npm run build` passes

## Todo Checklist
- [ ] PP-4.1 Build source URL lookup utility
- [ ] PP-4.2 Wire citation pills with onClick + keyboard + external link icon
- [ ] PP-4.3 Add hover tooltip with source title
- [ ] PP-4.4 Verify interaction + keyboard + build

## Success Criteria
- Citation pills with known source URLs are clickable (open in new tab)
- Keyboard accessible (Tab + Enter)
- Hover tooltip shows source title
- Build passes
