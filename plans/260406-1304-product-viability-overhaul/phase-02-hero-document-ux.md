# Phase 02: Hero Document UX

## Context Links
- [Brainstorm -- One Hero Document](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#one-hero-document--upsells)
- Current results: `frontend/components/job-detail-v2/job-detail-content.tsx` (129 lines)
- Document grid: `frontend/components/job-card/DocumentCardGrid.tsx`
- Document viewer: `frontend/components/job-detail-v2/document-viewer.tsx`

## Overview
- **Priority:** P1 (MVP)
- **Status:** pending
- **Effort:** 3-5 days
- **Depends on:** Phase 00
- **Description:** Restructure job results to show ONE hero document (Research Brief / Doc 2) with "Untold Angle" prominently featured. Make other docs secondary. Add inline source citations. Verify exports work.

## Key Insights
- Currently shows 4+ documents equally via `DocumentCardGrid`. Information overload.
- The "Untold Angle" (gap analysis output) is buried inside Doc 1 (Jump-Start Directions). It should be the HERO section of Doc 2.
- Inline citations are the trust moat -- every fact must visibly link back to `[Creator Name] at [timestamp]`
- PDF/DOCX exports already exist in `export-toolbar.tsx`. Need to verify working + add Markdown + clipboard.

## Requirements

### Functional
- **Primary view:** Research Brief (Doc 2) rendered full-width as hero content
- **"Untold Angle" section:** Extracted from gap analysis, displayed prominently at top of hero doc (callout/card)
- **Source sidebar:** Doc 0 data rendered as collapsible left sidebar (source cards with titles, thumbnails, key stats)
- **Secondary tabs:** "Research Gaps" (Doc 1 content), "Creator Brief" (Doc 3, on-demand button)
- **Upsell buttons:** "Generate Script", "Generate Blog", "Generate Social Kit" -- trigger on-demand generation
- **Inline citations:** Every fact/claim shows `[Source Name, timestamp]` as clickable link
- **Exports:** PDF (existing), DOCX (existing), Markdown (new), Copy to Clipboard (new)

### Non-Functional
- Hero document renders in < 500ms
- Citations link to source sidebar entry (scroll-to)
- Mobile: source sidebar collapses to bottom sheet

## Architecture

### Frontend Restructure
Current flow: `job-detail-content.tsx` -> `DocumentCardGrid` -> individual `DocumentCard` for each doc.

New flow: `job-detail-content.tsx` -> `HeroDocumentView` (Doc 2 full-width) + `SourceSidebar` (Doc 0) + `SecondaryTabs` (Doc 1, Doc 3).

### Citation Format
Backend already produces `source_ids` on key points and claims. Frontend needs to render these as inline links.

```typescript
// Map source_id -> source metadata for display
type CitationLink = {
  sourceId: string;
  creatorName: string;
  timestamp?: string;
  url: string;
};
```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `frontend/components/job-detail-v2/job-detail-content.tsx` | Replace `DocumentCardGrid` with hero layout: `HeroDocumentView` + sidebar + tabs |
| `frontend/components/job-detail-v2/job-center-panel.tsx` | May need layout adjustment for hero doc full-width |
| `frontend/components/job-detail-v2/document-viewer.tsx` | Add citation rendering logic |
| `frontend/components/job-detail-v2/export-toolbar.tsx` | Add Markdown export + clipboard copy |
| `frontend/components/job-card/DocumentCardGrid.tsx` | Keep for backward compat but no longer primary view |
| `frontend/lib/document-formatters.ts` | Add Markdown formatter |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/components/job-detail-v2/hero-document-view.tsx` | Full-width Doc 2 renderer with untold angle callout | ~150 |
| `frontend/components/job-detail-v2/untold-angle-callout.tsx` | Prominent gap analysis card | ~60 |
| `frontend/components/job-detail-v2/source-sidebar.tsx` | Collapsible Doc 0 source list | ~100 |
| `frontend/components/job-detail-v2/citation-link.tsx` | Inline `[Source, timestamp]` component | ~40 |
| `frontend/components/job-detail-v2/generate-document-buttons.tsx` | "Generate Script/Blog/Social" upsell row | ~60 |
| `frontend/lib/markdown-export.ts` | Markdown export utility | ~50 |
| `frontend/lib/citation-mapper.ts` | Map source_ids to display-friendly citation objects | ~40 |

## Implementation Steps

### Task 2.1: Create citation mapper utility
1. Create `frontend/lib/citation-mapper.ts`
2. `buildCitationMap(doc0Sources: Source[]): Map<string, CitationLink>`
3. Maps `SRC_1` -> `{ creatorName: "...", timestamp: "...", url: "..." }`
4. Used by all document renderers to resolve source_ids to display names

### Task 2.2: Create CitationLink component
1. Create `frontend/components/job-detail-v2/citation-link.tsx`
2. Renders as `[Creator Name, 12:34]` in a subtle badge/pill style
3. `onClick`: scroll to source in sidebar (emit event or use ref)
4. Tooltip shows full source title + URL

### Task 2.3: Create UntoldAngleCallout component
1. Create `frontend/components/job-detail-v2/untold-angle-callout.tsx`
2. Extract gaps from Doc 1 or from job artifacts (`identified_gaps`)
3. Render as eye-catching callout card at top of hero doc
4. Header: "The Untold Angle" with lightbulb icon
5. List top 2-3 gaps with brief descriptions
6. Styled: gradient border, slightly elevated, distinct from body text

### Task 2.4: Create HeroDocumentView component
1. Create `frontend/components/job-detail-v2/hero-document-view.tsx`
2. Renders Doc 2 (Semantic Brief / Research Brief) content:
   - `UntoldAngleCallout` at top
   - Semantic core summary
   - Synthesized themes with inline `CitationLink` components
   - Key points organized by theme
3. Parse Doc 2 JSON structure, render with proper heading hierarchy
4. Replace raw text rendering with structured sections

### Task 2.5: Create SourceSidebar component
1. Create `frontend/components/job-detail-v2/source-sidebar.tsx`
2. Renders Doc 0 (Source Ledger) data as a list of source cards
3. Each card: thumbnail (YouTube), title, creator name, confidence badge, key stats
4. Collapsible on desktop (toggle button), bottom sheet on mobile
5. Source cards have `id` attributes for citation scroll-to

### Task 2.6: Create generate-document buttons
1. Create `frontend/components/job-detail-v2/generate-document-buttons.tsx`
2. Row of buttons: "Generate Script" / "Generate Blog" / "Generate Social Kit"
3. Each triggers existing iterate endpoint with appropriate mode
4. Loading state per button
5. When doc generated, show in new tab or below hero doc

### Task 2.7: Restructure job-detail-content
1. Modify `frontend/components/job-detail-v2/job-detail-content.tsx`
2. New layout:
   ```
   [SourceSidebar (left, collapsible)] [HeroDocumentView (center, main)] [ChatSheet trigger (right)]
   ```
3. Below hero doc: `GenerateDocumentButtons` row
4. Below buttons: tabbed area for secondary docs (Doc 1 gaps detail, Doc 3 if generated, Script/Blog if generated)
5. Keep `ExportToolbar` at top of hero doc

### Task 2.8: Add Markdown export + clipboard
1. Create `frontend/lib/markdown-export.ts`
2. Convert Doc 2 JSON -> clean Markdown with citations as `[text](url)`
3. In `frontend/components/job-detail-v2/export-toolbar.tsx`:
   - Add "Copy Markdown" button -> copies to clipboard
   - Add "Copy to Clipboard" button -> copies plain text
4. Verify existing PDF and DOCX exports still work

### Task 2.9: Test
1. `npm run build` -- clean
2. Manual test: complete a job, verify hero doc renders with citations
3. Test untold angle callout visibility
4. Test source sidebar collapse/expand
5. Test all 4 export formats: PDF, DOCX, Markdown, clipboard
6. Test on mobile viewport

## Todo Checklist
- [ ] 2.1 Create `citation-mapper.ts` utility
- [ ] 2.2 Create `CitationLink` component
- [ ] 2.3 Create `UntoldAngleCallout` component
- [ ] 2.4 Create `HeroDocumentView` component
- [ ] 2.5 Create `SourceSidebar` component
- [ ] 2.6 Create `GenerateDocumentButtons` component
- [ ] 2.7 Restructure `job-detail-content.tsx`
- [ ] 2.8 Add Markdown export + clipboard copy
- [ ] 2.9 Build + manual test all views + exports

## Success Criteria
- Job results page shows ONE hero document (Research Brief) prominently
- "Untold Angle" is the first thing users see in results
- Every factual claim has visible inline citation
- Sources accessible in sidebar, not as separate document
- All 4 export formats work (PDF, DOCX, MD, clipboard)
- Generate Script/Blog/Social buttons visible and functional

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Doc 2 JSON structure varies by job | MEDIUM | Parse defensively, handle missing fields gracefully |
| Citation links don't have enough metadata | LOW | Falls back to source_id display if metadata missing |
| Existing DocumentCardGrid users confused | LOW | Grid still available as "All Documents" tab |

## Security Considerations
- Sanitize all rendered document content (React handles by default)
- Citation URLs must be validated before rendering as links
