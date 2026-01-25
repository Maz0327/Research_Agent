# Implementation Plan: Document Renderer Components

**Date:** 2026-01-25
**Branch:** `claude/fix-metadata-supadata-ABW4P`
**Goal:** Replace markdown-based document viewing with rich React components

---

## Overview

Current state: Documents rendered via markdown string → DOMPurify → raw HTML
Target state: JSON data → typed React components → interactive UI

**Benefits:**
- Interactive elements (collapse, filter, search)
- Better accessibility
- Type-safe rendering
- Consistent styling via Tailwind
- Smaller bundle (no markdown parser for viewing)

---

## Phase 1: Shared Components (Foundation)

**Files to create:**
```
frontend/components/documents/
├── index.ts
└── shared/
    ├── ConfidenceBadge.tsx
    ├── StatusBadge.tsx
    ├── AlertBox.tsx
    ├── CollapsibleSection.tsx
    └── DataTable.tsx
```

### Task 1.1: ConfidenceBadge.tsx
```tsx
interface Props {
  level: 'high' | 'medium' | 'low';
  size?: 'sm' | 'md';
  showLabel?: boolean;
}
// Output: 🟢 HIGH (green bg) | 🟡 MEDIUM (yellow) | 🔴 LOW (red)
```
**Effort:** 15 min

### Task 1.2: StatusBadge.tsx
```tsx
interface Props {
  status: 'ingested' | 'partial' | 'failed';
}
// Output: ✅ Ingested | ⚠️ Partial | ❌ Failed
```
**Effort:** 10 min

### Task 1.3: AlertBox.tsx
```tsx
interface Props {
  type: 'note' | 'tip' | 'important' | 'warning' | 'caution';
  title?: string;
  children: React.ReactNode;
}
// Colors: note=blue, tip=green, important=purple, warning=yellow, caution=red
```
**Effort:** 20 min

### Task 1.4: CollapsibleSection.tsx
```tsx
interface Props {
  title: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
}
// Uses Radix Collapsible or native details/summary
```
**Effort:** 25 min

### Task 1.5: DataTable.tsx
```tsx
interface Props<T> {
  data: T[];
  columns: { key: keyof T; label: string; render?: (val: T[keyof T]) => React.ReactNode }[];
  maxRows?: number;
}
// Generic sortable/filterable table with truncation
```
**Effort:** 30 min

### Task 1.6: index.ts barrel export
**Effort:** 5 min

**Phase 1 Total:** ~2 hours

---

## Phase 2: Source Ledger Components (Doc 0)

**Files to create:**
```
frontend/components/documents/source-ledger/
├── SourceLedger.tsx
├── SourceManifest.tsx
├── SourceCard.tsx
└── TranscriptQuality.tsx
```

### Task 2.1: Type definitions
```tsx
// frontend/types/documents.ts
interface SourceEntry {
  source_id: string;
  source_type: string;
  title: string;
  url: string;
  status: 'ingested' | 'partial' | 'failed';
  creator?: string;
  published?: string;
  duration?: string;
  word_count?: number;
  skim_summary?: string[];
  extracted_index?: {
    claim_ids: string[];
    entity_names: string[];
    theme_ids: string[];
  };
  full_text?: string;
  transcript_provenance?: TranscriptProvenance;
  failure_reason?: string;
}

interface SourceLedgerData {
  document_type: 'source_ledger';
  topic: string;
  source_manifest: { source_id: string; type: string; title: string; status: string }[];
  sources: SourceEntry[];
  created_at: string;
}
```
**Effort:** 20 min

### Task 2.2: SourceLedger.tsx (main container)
- Executive summary AlertBox
- Source stats (total, ingested, failed)
- SourceManifest table
- List of SourceCards
**Effort:** 40 min

### Task 2.3: SourceManifest.tsx
- DataTable with: #, ID, Type icon, Title, Status badge
- Click row → scroll to SourceCard
**Effort:** 25 min

### Task 2.4: SourceCard.tsx
- Header: ID + Title + Type icon + StatusBadge
- Metadata table (creator, published, duration, URL)
- CollapsibleSection for skim summary
- CollapsibleSection for full text (if available)
- TranscriptQuality component (if video)
**Effort:** 45 min

### Task 2.5: TranscriptQuality.tsx
- Small table showing transcript source, mode, confidence
- ConfidenceBadge for semantic precision
**Effort:** 20 min

**Phase 2 Total:** ~2.5 hours

---

## Phase 3: Jump-Start Components (Doc 1)

**Files to create:**
```
frontend/components/documents/jump-start/
├── JumpStart.tsx
├── ScopeLock.tsx
├── KeyPointsList.tsx
├── GapCard.tsx
└── NextSteps.tsx
```

### Task 3.1: Type definitions
```tsx
interface JumpStartData {
  document_type: 'jump_start';
  scope_lock: { in: string[]; out: string[] };
  current_corpus: { source_count: number; perspectives_represented: string[] };
  key_points: KeyPoint[];
  tensions: Tension[];
  gaps: Gap[];
  research_directions: ResearchDirection[];
  next_steps: string[];
  confidence: string;
}
```
**Effort:** 15 min

### Task 3.2: JumpStart.tsx (main container)
- Summary AlertBox with stats
- ScopeLock component
- KeyPointsList (collapsible if >5)
- Tensions list
- Gaps with GapCards
- NextSteps (prominent)
**Effort:** 35 min

### Task 3.3: ScopeLock.tsx
- Two-column table: IN scope | OUT scope
- Green checkmarks for IN, red X for OUT
**Effort:** 15 min

### Task 3.4: KeyPointsList.tsx
- List of key points with confidence badges
- Show first 5, collapse rest
- Click to expand all
**Effort:** 25 min

### Task 3.5: GapCard.tsx
- Gap description as title
- "Why it matters" as body
- Suggested research direction (if available)
**Effort:** 20 min

### Task 3.6: NextSteps.tsx
- Numbered list (1, 2, 3) with prominent styling
- AlertBox type="important" wrapper
**Effort:** 15 min

**Phase 3 Total:** ~2 hours

---

## Phase 4: Semantic Brief Components (Doc 2)

**Files to create:**
```
frontend/components/documents/semantic-brief/
├── SemanticBrief.tsx
├── SemanticCore.tsx
├── ThemeCard.tsx
├── KeyPointsTable.tsx
├── TensionCard.tsx
└── ConfidenceCard.tsx
```

### Task 4.1: Type definitions
```tsx
interface SemanticBriefData {
  document_type: 'semantic_brief';
  semantic_core: { text: string; based_on: string[] };
  themes: Theme[];
  key_points: KeyPoint[];
  tensions: Tension[];
  gaps: Gap[];
  confidence_assessment: { level: string; reasoning: string[] };
  triage: string;
  warnings: string[];
}
```
**Effort:** 15 min

### Task 4.2: SemanticBrief.tsx (main container)
- Triage banner (if degraded/thin)
- Summary AlertBox
- SemanticCore
- Grid of ThemeCards
- KeyPointsTable
- TensionCards (if any)
- Gaps list
- ConfidenceCard
**Effort:** 40 min

### Task 4.3: SemanticCore.tsx
- Blockquote styling for core text
- "Based on" source links
**Effort:** 15 min

### Task 4.4: ThemeCard.tsx
- Theme label as title
- Description
- Related key points as clickable badges
**Effort:** 20 min

### Task 4.5: KeyPointsTable.tsx
- DataTable: ID | Statement | Sources | Confidence
- Truncate long statements, expand on click
**Effort:** 25 min

### Task 4.6: TensionCard.tsx
- Two-sided card showing opposing positions
- Sources on each side
**Effort:** 20 min

### Task 4.7: ConfidenceCard.tsx
- ConfidenceBadge (large)
- List of reasoning points
- AlertBox wrapper
**Effort:** 15 min

**Phase 4 Total:** ~2.5 hours

---

## Phase 5: Integration

### Task 5.1: DocumentRenderer.tsx (router)
```tsx
interface Props {
  type: 'source_ledger' | 'jump_start' | 'semantic_brief';
  data: unknown;
}
// Routes to correct component based on type
```
**Effort:** 15 min

### Task 5.2: Update DocumentViewerModal.tsx
- Add toggle: "Raw Markdown" | "Rich View"
- Default to Rich View when data available
- Fall back to markdown for backwards compatibility
**Effort:** 30 min

### Task 5.3: Update JobResults.tsx
- Use DocumentRenderer when inline viewing
- Keep markdown for PDF export
**Effort:** 20 min

### Task 5.4: Update types/documents.ts
- Export all type definitions
- Add to store types if needed
**Effort:** 15 min

**Phase 5 Total:** ~1.5 hours

---

## Phase 6: Testing & Polish

### Task 6.1: Storybook stories (optional)
- One story per shared component
- One story per document type
**Effort:** 1 hour (optional)

### Task 6.2: Manual QA
- Test with real job data
- Test with minimal data (thin output)
- Test with failed sources
- Test mobile responsiveness
**Effort:** 30 min

### Task 6.3: Accessibility audit
- Keyboard navigation
- Screen reader labels
- Color contrast
**Effort:** 30 min

**Phase 6 Total:** ~2 hours

---

## Summary

| Phase | Description | Effort |
|-------|-------------|--------|
| 1 | Shared Components | 2h |
| 2 | Source Ledger (Doc 0) | 2.5h |
| 3 | Jump-Start (Doc 1) | 2h |
| 4 | Semantic Brief (Doc 2) | 2.5h |
| 5 | Integration | 1.5h |
| 6 | Testing & Polish | 2h |
| **Total** | | **12.5h** |

---

## File Checklist

```
[ ] frontend/types/documents.ts
[ ] frontend/components/documents/index.ts
[ ] frontend/components/documents/shared/ConfidenceBadge.tsx
[ ] frontend/components/documents/shared/StatusBadge.tsx
[ ] frontend/components/documents/shared/AlertBox.tsx
[ ] frontend/components/documents/shared/CollapsibleSection.tsx
[ ] frontend/components/documents/shared/DataTable.tsx
[ ] frontend/components/documents/source-ledger/SourceLedger.tsx
[ ] frontend/components/documents/source-ledger/SourceManifest.tsx
[ ] frontend/components/documents/source-ledger/SourceCard.tsx
[ ] frontend/components/documents/source-ledger/TranscriptQuality.tsx
[ ] frontend/components/documents/jump-start/JumpStart.tsx
[ ] frontend/components/documents/jump-start/ScopeLock.tsx
[ ] frontend/components/documents/jump-start/KeyPointsList.tsx
[ ] frontend/components/documents/jump-start/GapCard.tsx
[ ] frontend/components/documents/jump-start/NextSteps.tsx
[ ] frontend/components/documents/semantic-brief/SemanticBrief.tsx
[ ] frontend/components/documents/semantic-brief/SemanticCore.tsx
[ ] frontend/components/documents/semantic-brief/ThemeCard.tsx
[ ] frontend/components/documents/semantic-brief/KeyPointsTable.tsx
[ ] frontend/components/documents/semantic-brief/TensionCard.tsx
[ ] frontend/components/documents/semantic-brief/ConfidenceCard.tsx
[ ] frontend/components/documents/DocumentRenderer.tsx
```

---

## Dependencies

**Required packages (already installed):**
- `framer-motion` - animations
- `tailwindcss` - styling

**Optional packages:**
- `@radix-ui/react-collapsible` - accessible collapsible (or use native `<details>`)

---

## Rollback Plan

Keep markdown rendering as fallback:
1. DocumentViewerModal already has `markdown` prop
2. Toggle allows switching between views
3. If React components fail, markdown still works

---

## Unresolved Questions

1. **Virtual scrolling:** Need for large source lists (>20 sources)?
2. **In-document search:** Add Ctrl+F style search within documents?
3. **Dark mode:** Current dark mode styles apply automatically via Tailwind?
4. **Print CSS:** Need dedicated print stylesheet for PDF export?
