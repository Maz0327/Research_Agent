# Frontend UI Exploration Report

**Generated:** 2026-01-23 11:45
**Purpose:** Understand current frontend implementation for job results, documents, boosters, and producer packets

---

## Executive Summary

Frontend uses card-grid → fullscreen modal pattern. Documents displayed via `DocumentCardGrid` component with lazy loading from cloud storage. Booster/producer packet buttons in dedicated "Actions" section below document cards. ID formatting handled by presentation layer (`document-formatters.ts`). No iteration/addendum handling found.

---

## Component Structure

### JobResults Component
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/JobResults.tsx`

**Responsibilities:**
- Main job results display for completed jobs
- Renders document cards grid
- Handles booster/producer packet trigger buttons
- Manages action states (triggering, loading, errors)

**Key Features:**
- Supports both inline data (legacy) and storage paths (new jobs with lazy loading)
- Booster status tracked separately: `boosterStatus`, `boosterError`, `boosterProgressPercent`
- Producer packet button only shown when Doc 3 doesn't exist (`!hasDoc3`)
- Deep Research (booster) button always visible but disabled during execution

**Action Bar Structure (lines 212-280):**
```tsx
<div className="pt-5 sm:pt-6 mt-2 border-t border-gray-800/50">
  <h3>Actions</h3>

  {/* Producer Packet - only if Doc 3 doesn't exist */}
  {!hasDoc3 && (
    <button onClick={handleProducerPacket} disabled={...}>
      Producer Packet
    </button>
  )}

  {/* Deep Research (Booster) - always visible */}
  <button onClick={handleBooster} disabled={...}>
    {boosterStatus === 'running' ? `${boosterProgressPercent}%` : 'Deep Research'}
  </button>
</div>
```

**Button States:**
- Producer Packet: Hidden when Doc 3 exists
- Booster: Shows progress % when running, "Complete" checkmark when done, "Failed" error when failed

---

### DocumentCardGrid Component
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentCardGrid.tsx`

**Responsibilities:**
- Displays document cards in 3-column grid (1 col mobile)
- Handles click-to-open fullscreen modal
- Manages lazy loading from storage paths
- Provides PDF download per document

**Document Configuration:**
```typescript
// Core docs (0, 1, 2)
const coreDocConfigs: DocConfig[] = [
  { key: 'doc_0', docNumber: 0, title: 'Source Ledger', subtitle: 'What was analyzed' },
  { key: 'doc_1', docNumber: 1, title: 'Jump-Start', subtitle: 'Where to go next' },
  { key: 'doc_2', docNumber: 2, title: 'Semantic Brief', subtitle: 'What sources reveal' },
];

// Optional docs
const boosterConfig: DocConfig = {
  key: 'booster', docNumber: 'B', title: 'Deep Research', subtitle: 'Expanded directions'
};

const doc3Config: DocConfig = {
  key: 'doc_3', docNumber: 3, title: 'Producer Packet', subtitle: 'Creative layer output'
};
```

**Availability Logic:**
- Core docs: Check `artifacts.source_ledger` OR `artifacts.doc_0_path` (lines 161-173)
- Doc 3: Check `artifacts.doc_3_path` OR `artifacts.producer_packet` (line 176)
- Booster: Check `boosterMarkdown` OR `artifacts.booster_expansion_md` (line 179)

**Lazy Loading:**
- Checks for storage path OR placeholder content
- Fetches from API: `/jobs/{jobId}/documents/{docKey}`
- API returns signed URL for cloud storage content
- 30-second timeout with abort controller

---

### DocumentAccordion Component
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentAccordion.tsx`

**Status:** Present but NOT used by JobResults (replaced by DocumentCardGrid)

**Features:**
- Collapsible accordion UI
- Color-coded by document type (gray, blue, purple, amber, indigo)
- PDF download button
- Lazy loading support
- Presentation layer formatting applied via `transformMarkdownForDisplay()`

---

### DocumentViewerModal Component
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentViewerModal.tsx`

**Responsibilities:**
- Fullscreen modal for viewing document content
- Renders markdown or JSON
- Mobile-first with swipe-to-close gesture
- Copy-to-clipboard functionality

**Styling by Document Type:**
```typescript
const docStyles = {
  0: { badge: 'bg-gray-700', accent: 'text-gray-400' },      // Source Ledger
  1: { badge: 'bg-blue-900/50', accent: 'text-blue-400' },   // Jump-Start
  2: { badge: 'bg-purple-900/50', accent: 'text-purple-400' }, // Semantic Brief
  3: { badge: 'bg-amber-900/50', accent: 'text-amber-400' },  // Producer Packet
  'B': { badge: 'bg-indigo-900/50', accent: 'text-indigo-400' }, // Booster
};
```

**Breadcrumb Support:**
- Shows job title → "Doc X: Document Title"
- Only rendered when `jobTitle` prop provided

---

## ID Formatting System

### document-formatters.ts
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/lib/document-formatters.ts`

**Presentation Layer Transformation:**
```typescript
const ID_LABEL_MAP = {
  SRC: 'Source',
  KP: 'Key Point',
  CLM: 'Claim',
  QT: 'Quote',
  OBS: 'Observation',
  THEME: 'Theme',
  TEN: 'Tension',
  GAP: 'Open Question',
  REF: 'Reference',
  EV: 'Evidence',
  ANG: 'Angle',
};
```

**Key Functions:**
- `formatInternalId(id)`: Converts `SRC_1` → `"Source 1"`
- `formatIdWithRef(id)`: Converts `SRC_1` → `"Source 1 (SRC_1)"`
- `transformMarkdownForDisplay(markdown)`: Replaces all IDs in markdown content

**URL Protection:**
```typescript
// Pattern matches IDs at word boundaries, not in URLs
const pattern = new RegExp(`(?<![/\\w])${prefix}_(\\d+)(?![\\w])`, 'g');
```

**Heading Normalization:**
- "Key Points" → "Key Takeaways"
- "Research Gaps" → "Open Questions"
- "Cross-Source Themes" → "Common Themes"
- "Source Tensions" → "Conflicting Views"

---

## Store Integration

### jobs.ts Store
**Location:** `/Users/maz/Documents/GitHub/Research_Agent/frontend/store/jobs.ts`

**Booster Trigger:**
```typescript
triggerBooster: async (jobId: string): Promise<BoosterResponse> => {
  // POST /jobs/{jobId}/booster
  // Updates job with status: 'running', stage: 'booster'
}
```

**Producer Packet Trigger:**
```typescript
triggerProducerPacket: async (jobId: string): Promise<ProducerPacketResponse> => {
  // POST /jobs/{jobId}/producer-packet
  // Updates job with status: 'running', stage: 'producer_packet'
}
```

**Job Refresh:**
```typescript
refreshJob: async (jobId: string) => {
  // GET /jobs/{jobId}
  // Updates all job fields including:
  // - booster_status, booster_error, booster_progress_percent
  // - artifacts (doc_0_path, doc_1_path, doc_2_path, doc_3_path)
}
```

---

## Data Flow

### Document Loading Sequence
1. **Initial Load:** JobResults checks `artifacts` for inline data OR storage paths
2. **Card Render:** DocumentCardGrid displays available documents as cards
3. **User Click:** Card clicked → triggers `handleCardClick(config)`
4. **Content Check:**
   - Booster: Use inline `boosterMarkdown` prop
   - Doc 3: Fetch from API `/jobs/{jobId}/documents/doc_3`
   - Core docs (0,1,2): Check inline → if placeholder/missing → fetch from API
5. **API Fetch:** GET `/jobs/{jobId}/documents/{docKey}` → returns signed URL
6. **Storage Fetch:** GET signed URL → returns JSON with `markdown` field
7. **Modal Open:** DocumentViewerModal displays content with formatting

### Placeholder Detection
```typescript
function isPlaceholderContent(content: string | null | undefined): boolean {
  if (!content) return true;
  return (
    content.includes('Document Available via Cloud Storage') ||
    content.includes('inline JSON omitted')
  );
}
```

---

## Current Button Placement

### Producer Packet Button
**Location:** JobResults → Actions section
**Condition:** Only shown when `!hasDoc3` (Doc 3 doesn't exist)
**State:** Disabled when job not completed or already triggering
**Appearance:** Amber border/background (`bg-amber-600/20 border border-amber-600/30`)

**Code Reference (lines 217-240):**
```tsx
{!hasDoc3 && (
  <button
    onClick={handleProducerPacket}
    disabled={!canTriggerActions || isTriggeringProducer}
    className="... bg-amber-600/20 border border-amber-600/30 text-amber-400 ..."
  >
    {isTriggeringProducer ? 'Generating...' : 'Producer Packet'}
  </button>
)}
```

### Deep Research (Booster) Button
**Location:** JobResults → Actions section (always below Producer Packet if both visible)
**Condition:** Always shown
**State:** Disabled when job not completed OR already running
**Appearance:** Indigo border/background (`bg-indigo-600/20 border border-indigo-600/30`)

**Code Reference (lines 243-278):**
```tsx
<button
  onClick={handleBooster}
  disabled={!canTriggerActions || isTriggeringBooster || isBoosterRunning}
  className="... bg-indigo-600/20 border border-indigo-600/30 text-indigo-400 ..."
>
  {isBoosterRunning ? `${boosterProgressPercent}%` :
   isBoosterCompleted ? 'Complete ✓' :
   isBoosterFailed ? 'Failed ✗' : 'Deep Research'}
</button>
```

---

## Iteration/Addendum Handling

**Search Results:** No files found containing "iteration" or "addendum" keywords (except package-lock.json)

**Current Implementation:** None

**Implications:**
- No UI for displaying job iterations
- No visual indicator for addendum documents
- No mechanism to show source additions to existing jobs
- No versioning display in document viewer

---

## Testing Patterns

### Test File Location
`/Users/maz/Documents/GitHub/Research_Agent/frontend/__tests__/lib/document-formatters.test.ts`

**Coverage:**
- ID formatting functions
- Timestamp formatting
- Markdown transformation
- Confidence level display
- Source type display

**Example Test Pattern:**
```typescript
describe('formatInternalId', () => {
  it('converts SRC_1 to "Source 1"', () => {
    expect(formatInternalId('SRC_1')).toBe('Source 1');
  });

  it('passes through unknown IDs unchanged', () => {
    expect(formatInternalId('unknown')).toBe('unknown');
  });
});
```

---

## Key Findings

### Strengths
1. **Clean separation:** Presentation layer formatting doesn't modify stored JSON
2. **Lazy loading:** Storage paths enable large document payloads without bloating job list
3. **Mobile-first:** Touch targets (44px), swipe gestures, responsive layouts
4. **Type safety:** TypeScript interfaces for all data structures
5. **Error handling:** Loading states, error messages, retry capability

### Gaps
1. **No iteration support:** Cannot display multiple versions of documents
2. **No addendum handling:** No way to show source additions
3. **No document versioning:** No timestamps or version indicators
4. **Static button placement:** Actions section layout fixed, no dynamic reordering
5. **No document metadata:** Creation time, word count, confidence summary not shown in cards

### Technical Debt
- DocumentAccordion component exists but unused (replaced by DocumentCardGrid)
- Inline data support remains for legacy jobs (could be deprecated)
- No centralized loading state management (per-component state)

---

## Unresolved Questions

1. Should iterations show as separate cards or as versions within a single modal?
2. How should addendum documents be visually distinguished from base documents?
3. Should booster button move into document card grid or remain in actions section?
4. Should producer packet generation be triggered inline with Doc 3 card or kept separate?
5. What happens to UI when job has 10+ iterations/addendums? Pagination? Collapse?

---

## Files Referenced

### Primary Components
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/JobResults.tsx`
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentCardGrid.tsx`
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentAccordion.tsx`
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/components/job-card/DocumentViewerModal.tsx`

### Supporting Libraries
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/lib/document-formatters.ts`
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/store/jobs.ts`

### Tests
- `/Users/maz/Documents/GitHub/Research_Agent/frontend/__tests__/lib/document-formatters.test.ts`

---

**END OF REPORT**
