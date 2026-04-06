# Phase 01: Single-Screen Input

## Context Links
- [Brainstorm -- UX Overhaul](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#single-screen-input-kill-4-step-wizard)
- [UX Patterns Report](../../plans/reports/researcher-260405-1552-ai-research-product-ux-patterns.md)
- Current wizard: `frontend/components/dashboard/job-creation-wizard.tsx` (143 lines)

## Overview
- **Priority:** P1 (MVP)
- **Status:** pending
- **Effort:** 3-5 days
- **Depends on:** Phase 00 (cleanup)
- **Description:** Replace 4-step wizard (Topic -> Sources -> Mode -> Preview) with single-screen input. Auto-detect URLs pasted into text field. One click to start.

## Key Insights
- Current wizard forces users to learn pipeline's mental model (4 steps)
- Every successful AI product (Perplexity, ChatGPT, NotebookLM) uses single-input UX
- URL auto-detection is trivial (regex for youtube.com, youtu.be, http(s)://)
- Mode selection (Quick/Full) can be a toggle, not a step
- Niche selection and preview step can be removed (pipeline auto-detects)

## Requirements

### Functional
- Single text area: "What do you want to research?"
- Paste URLs directly into text area -- auto-detect and show as chips/tags
- Dedicated "Add source" buttons: YouTube, article/webpage, text/notes
- Mode toggle: Quick (30s) / Full (3min) -- default Full
- Single "Start Research" button
- Topic extracted from non-URL text in the field
- If only URLs and no topic text, pipeline infers topic from sources

### Non-Functional
- < 200 lines for new component (per modularization rule)
- Keyboard accessible (Enter to submit, Tab between fields)
- Mobile-friendly layout

## Architecture

### Frontend Only Change
No backend API changes needed. The existing `POST /jobs` endpoint accepts `{ topic, sources, pipeline }` -- same payload, just collected from single screen instead of wizard.

### URL Detection Logic
```typescript
const URL_PATTERNS = {
  youtube: /(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/,
  generic: /https?:\/\/[^\s]+/
};
```
Parse input text, extract URLs, remainder = topic text.

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `frontend/components/dashboard/job-creation-wizard.tsx` | REPLACE with new `SingleScreenInput` component |
| `frontend/components/dashboard/StartInput.tsx` | May merge into new component or keep as sub-component |
| `frontend/components/dashboard/dashboard-content.tsx` | Update to render `SingleScreenInput` instead of wizard |
| `frontend/store/jobs.ts` | Verify `createJob()` action accepts same payload shape |
| `frontend/hooks/use-preview-job.ts` | Remove if preview step eliminated; or keep for optional preview |

### Files to DELETE/ARCHIVE
| File | Reason |
|------|--------|
| `frontend/components/dashboard/wizard-step-topic.tsx` | Wizard step -- no longer needed |
| `frontend/components/dashboard/wizard-step-sources.tsx` | Wizard step -- replaced by inline source chips |
| `frontend/components/dashboard/wizard-step-mode.tsx` | Replaced by toggle |
| `frontend/components/dashboard/wizard-step-preview.tsx` | Preview step eliminated |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/components/dashboard/single-screen-input.tsx` | Main input component | ~120 |
| `frontend/components/dashboard/source-chip.tsx` | Individual source tag with remove button | ~40 |
| `frontend/lib/url-detector.ts` | URL regex extraction utility | ~30 |

## Implementation Steps

### Task 1.1: Create URL detection utility
1. Create `frontend/lib/url-detector.ts`
2. Export `extractUrls(text: string): { urls: ParsedUrl[], remainingText: string }`
3. `ParsedUrl` type: `{ raw: string, type: 'youtube' | 'article', videoId?: string }`
4. Handle: youtube.com/watch?v=, youtu.be/, generic https://
5. Return remaining text (non-URL portions) as topic

### Task 1.2: Create SourceChip component
1. Create `frontend/components/dashboard/source-chip.tsx`
2. Props: `{ url: ParsedUrl, onRemove: () => void }`
3. Show favicon/icon for YouTube vs article
4. Show truncated URL or video title
5. X button to remove
6. Use shadcn `Badge` variant

### Task 1.3: Create SingleScreenInput component
1. Create `frontend/components/dashboard/single-screen-input.tsx`
2. Layout:
   ```
   [Textarea: "What do you want to research?"]
   [Source chips row -- auto-populated from pasted URLs]
   [+ Add YouTube] [+ Add Article] [+ Add Notes]
   [Mode: Quick | Full toggle]
   [Start Research button]
   ```
3. `onChange` handler on textarea: run `extractUrls()`, update source chips
4. Manual "Add" buttons open small input for URL entry
5. Mode toggle: two-option segmented control (shadcn `ToggleGroup`)
6. Submit handler: call `createJob({ topic, sources, pipeline: mode })`
7. Loading state on submit button

### Task 1.4: Integrate into dashboard
1. In `frontend/components/dashboard/dashboard-content.tsx`, replace wizard trigger with `SingleScreenInput`
2. Remove wizard modal/dialog pattern if present
3. `SingleScreenInput` can be always-visible at top of dashboard (Perplexity pattern)
4. Remove `usePreviewJob` hook usage if preview step eliminated

### Task 1.5: Archive old wizard files
1. Move `wizard-step-topic.tsx`, `wizard-step-sources.tsx`, `wizard-step-mode.tsx`, `wizard-step-preview.tsx` to `frontend/archive/wizard/`
2. Move `job-creation-wizard.tsx` to `frontend/archive/wizard/`
3. Remove `usePreviewJob` hook if no longer used anywhere
4. Run `npm run lint && npm run build`

### Task 1.6: Test
1. `npm run build` -- no TypeScript errors
2. Manual test: paste YouTube URL, verify chip appears
3. Manual test: paste mixed text + URLs, verify topic extracted
4. Manual test: click Start Research, verify job created
5. Manual test: mobile layout responsive

## Todo Checklist
- [ ] 1.1 Create `url-detector.ts` utility
- [ ] 1.2 Create `source-chip.tsx` component
- [ ] 1.3 Create `single-screen-input.tsx` component
- [ ] 1.4 Integrate into dashboard, replace wizard
- [ ] 1.5 Archive old wizard files
- [ ] 1.6 Build + manual test

## Success Criteria
- Users go from landing to "Start Research" in ONE screen
- URLs auto-detected from pasted text
- Job creation payload identical to existing API contract
- Old wizard code archived (not deleted)
- Frontend builds clean

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| URL regex misses edge cases | LOW | Common patterns only. Can improve later. |
| Removing preview step loses useful validation | LOW | Preview was mostly showing inferred topic. Single screen shows same info inline. |
| Power users miss niche selection | LOW | Pipeline auto-detects niche. Can add optional "Advanced" toggle later if needed. |

## Security Considerations
- Validate URLs client-side AND server-side (existing backend validation)
- Sanitize pasted text (XSS prevention via React's default escaping)
