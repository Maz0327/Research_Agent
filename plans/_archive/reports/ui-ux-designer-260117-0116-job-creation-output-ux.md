# UX Design: Multi-Source Job Creation & Output Viewing

**Date:** 2026-01-17
**Designer:** UI/UX Designer Agent
**Status:** Complete

---

## Executive Summary

Redesign the Research Agent dashboard to support:
1. **Multi-source job creation** - Queue multiple source types (YouTube URLs, text, screenshots) in a single job
2. **Document-centric output viewing** - Display Doc 0/1/2 with clear hierarchy and download options
3. **Hide legacy Topic Research tab**

---

## 1. Current State Analysis

### Pain Points Identified

| Issue | Severity | Impact |
|-------|----------|--------|
| Three separate tabs create isolated jobs | High | Users cannot combine YouTube + text + screenshots |
| Output viewing buried in expandable cards | Medium | Documents not prominent; users miss key findings |
| Topic Research tab is legacy | Low | Confuses users, clutters UI |
| No source queue visualization | High | Users cannot preview what will be analyzed |

### Current Flow
```
[Tab: Video] --> Submits --> Separate Job
[Tab: Content] --> Submits --> Separate Job
[Tab: Topic] --> Submits --> Separate Job (legacy)
```

### Proposed Flow
```
[Unified Input Area]
    |
    +--> Add YouTube URLs (bulk)
    +--> Add Text Content
    +--> Add Screenshots
    |
    v
[Source Queue Preview] --> [Submit All] --> Single Job
```

---

## 2. Multi-Source Queue UI Design

### 2.1 Layout Architecture

```
+------------------------------------------------------------------+
|  NEW RESEARCH JOB                                    [Submit Job] |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+  +-------------------+  +----------------+ |
|  | + YouTube URLs    |  | + Paste Text      |  | + Screenshot   | |
|  |   (0 added)       |  |   (0 added)       |  |   (0 added)    | |
|  +-------------------+  +-------------------+  +----------------+ |
|                                                                   |
|  SOURCE QUEUE (0 items)                                           |
|  +---------------------------------------------------------------+|
|  |  [Empty state: Add sources above to begin]                    ||
|  +---------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### 2.2 Component: SourceAdder

Three horizontally-aligned buttons that expand into input panels.

```tsx
// Collapsed state (default)
+------------------+
| + YouTube URLs   |  <-- Click to expand
|   (0 added)      |
+------------------+

// Expanded state
+------------------------------------------+
| YOUTUBE URLS                         [x] |
+------------------------------------------+
| Paste URLs (one per line)                |
| +--------------------------------------+ |
| | https://youtube.com/watch?v=...      | |
| | https://youtu.be/...                 | |
| |                                      | |
| +--------------------------------------+ |
| [Add to Queue]                    3 URLs |
+------------------------------------------+
```

### 2.3 Component: SourceQueue

Visual list of queued sources with type indicators and remove actions.

```
SOURCE QUEUE (5 items)
+---------------------------------------------------------------+
|  [YT] Interview with John Doe - Part 1         [x]            |
|  [YT] Interview with John Doe - Part 2         [x]            |
|  [TXT] WSJ Article: Market Analysis            [x]            |
|  [IMG] Twitter thread screenshot               [x]            |
|  [YT] Expert Commentary on Topic               [x]            |
+---------------------------------------------------------------+
```

**Type Icons:**
- `[YT]` - YouTube video (purple)
- `[TXT]` - Pasted text (green)
- `[IMG]` - Screenshot (blue)

### 2.4 Interaction Flow

```
User clicks "+ YouTube URLs"
    |
    v
Expansion panel appears with textarea
    |
User pastes multiple URLs, clicks "Add to Queue"
    |
    v
URLs validated, added to SourceQueue
Panel collapses, badge updates "(3 added)"
    |
User clicks "+ Paste Text"
    |
    v
Text input panel appears
User enters content + metadata
    |
Clicks "Add to Queue"
    |
    v
Text source added to SourceQueue
    |
User reviews queue, reorders if needed
    |
    v
Clicks "Submit Job"
    |
    v
Single job created with all sources
```

### 2.5 Mobile Responsiveness

```
MOBILE (< 768px)
+---------------------------+
| NEW RESEARCH JOB          |
+---------------------------+
| + YouTube URLs            |
| + Paste Text              |
| + Screenshot              |
+---------------------------+
| SOURCE QUEUE (3)          |
| +-------------------------+
| | [YT] Video title... [x] |
| | [TXT] Article...    [x] |
| | [IMG] Screenshot    [x] |
| +-------------------------+
+---------------------------+
| [Submit Job]              |
+---------------------------+
```

Buttons stack vertically on mobile.

---

## 3. Output Viewing Experience

### 3.1 Current Problem

Results are crammed into an expandable card with tabs for clips/quotes. The actual documents (Doc 0/1/2) are not visible.

### 3.2 Proposed Design: Document Cards

When a job completes, show three distinct document cards:

```
JOB COMPLETED: UFO Interview Analysis
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------+  +-------------------+  +----------------+ |
|  | DOC 0             |  | DOC 1             |  | DOC 2          | |
|  | Source Ledger     |  | Jump-Start        |  | Semantic Brief | |
|  |                   |  | Directions        |  |                | |
|  | 5 sources         |  | 12 directions     |  | 8 themes       | |
|  | analyzed          |  | suggested         |  | 15 key points  | |
|  |                   |  |                   |  |                | |
|  | [View] [Download] |  | [View] [Download] |  | [View] [Download]|
|  +-------------------+  +-------------------+  +----------------+ |
|                                                                   |
+------------------------------------------------------------------+
```

### 3.3 Component: DocumentCard

```tsx
interface DocumentCardProps {
  docNumber: 0 | 1 | 2;
  title: string;
  subtitle: string;
  stats: { label: string; value: number }[];
  onView: () => void;
  onDownload: () => void;
}
```

**Visual Design:**
```
+---------------------------+
|  DOC 0                    |  <-- Small badge, muted
|  Source Ledger            |  <-- Bold title
|  What was analyzed        |  <-- Subtitle, gray
|                           |
|  5 sources                |  <-- Stats
|  3 videos, 2 texts        |
|                           |
|  [View]  [Download v]     |  <-- Actions
+---------------------------+

Color coding:
- Doc 0: Gray/neutral (reference)
- Doc 1: Blue (exploration)
- Doc 2: Purple (insights)
```

### 3.4 Document Viewer Modal

When user clicks "View", show full document in a modal/drawer:

```
+------------------------------------------------------------------+
| SOURCE LEDGER (Doc 0)                                      [x]   |
+------------------------------------------------------------------+
|                                                                   |
|  SOURCES ANALYZED                                                 |
|  ---------------------------------------------------------------- |
|                                                                   |
|  1. [YT] Joe Rogan #2123 - Interview with Bob Lazar              |
|     Duration: 2:34:15 | Mode: transcript_grounded                |
|     Confidence ceiling: HIGH                                     |
|                                                                   |
|  2. [YT] Lex Fridman - UFO Disclosure Discussion                 |
|     Duration: 1:45:30 | Mode: transcript_grounded                |
|     Confidence ceiling: HIGH                                     |
|                                                                   |
|  3. [TXT] NYT Article: Pentagon UFO Report                       |
|     Words: 2,340 | Mode: text_provided                           |
|     Confidence ceiling: MEDIUM (unverified)                      |
|                                                                   |
|  ---------------------------------------------------------------- |
|                                                                   |
|  PROCESSING SUMMARY                                               |
|  - Total sources: 3                                              |
|  - Total runtime: 4h 19m 45s                                     |
|  - Extraction cost: $0.47                                        |
|                                                                   |
+------------------------------------------------------------------+
|                                      [Copy] [Download Markdown]  |
+------------------------------------------------------------------+
```

### 3.5 Document Download Options

Dropdown menu on download button:

```
[Download v]
+---------------------------+
| Export to Google Docs     |
| Download Markdown         |
| Copy to Clipboard         |
+---------------------------+
```

---

## 4. Component Hierarchy

```
Dashboard
├── Header
│   └── "Dashboard" title + description
│
├── JobCreator (new)
│   ├── SourceAdders
│   │   ├── YouTubeAdder
│   │   │   ├── ExpandButton
│   │   │   └── ExpandedPanel (textarea, validation, add button)
│   │   ├── TextAdder
│   │   │   ├── ExpandButton
│   │   │   └── ExpandedPanel (content, metadata fields)
│   │   └── ScreenshotAdder
│   │       ├── ExpandButton
│   │       └── ExpandedPanel (file upload, context fields)
│   │
│   ├── SourceQueue
│   │   ├── EmptyState
│   │   └── SourceItem (type icon, title, remove button)
│   │
│   └── SubmitButton
│       └── (disabled until queue has items)
│
├── JobsList
│   ├── StatusFilter
│   ├── BulkActions (edit mode)
│   └── JobCard[] (existing, enhanced)
│       ├── Header (title, status, progress)
│       └── ExpandedContent
│           ├── DocumentCards (new - for completed jobs)
│           │   ├── Doc0Card
│           │   ├── Doc1Card
│           │   └── Doc2Card
│           └── LegacyTabs (clips, quotes, blueprints, gaps)
│
└── DocumentViewerModal (new)
    ├── Header (doc title, close button)
    ├── Content (rendered document)
    └── Actions (copy, download)
```

---

## 5. State Management

### 5.1 New State for JobCreator

```typescript
interface SourceQueueItem {
  id: string;  // UUID
  type: 'youtube' | 'text' | 'screenshot';
  title: string;  // Display title
  // Type-specific data
  data: YouTubeSource | TextSource | ScreenshotSource;
}

interface YouTubeSource {
  urls: string[];
}

interface TextSource {
  content: string;
  sourceLabel: string;
  sourceUrl?: string;
  author?: string;
  pubDate?: string;
  platformHint: string;
  contextNote?: string;
}

interface ScreenshotSource {
  file: File;
  topic: string;
  platformHint: string;
  contextNote?: string;
}

// Add to jobs store or create separate store
interface JobCreatorState {
  sourceQueue: SourceQueueItem[];
  expandedPanel: 'youtube' | 'text' | 'screenshot' | null;
  isSubmitting: boolean;

  // Actions
  addYouTubeSource: (urls: string[]) => void;
  addTextSource: (source: TextSource) => void;
  addScreenshotSource: (source: ScreenshotSource) => void;
  removeSource: (id: string) => void;
  reorderSources: (fromIndex: number, toIndex: number) => void;
  clearQueue: () => void;
  submitJob: () => Promise<void>;
}
```

### 5.2 API Changes Required

Backend needs new endpoint to accept multi-source jobs:

```typescript
// POST /jobs/multi-source
interface MultiSourceJobRequest {
  title?: string;
  sources: Array<{
    type: 'youtube' | 'text' | 'screenshot';
    data: YouTubeSourceData | TextSourceData | ScreenshotSourceData;
  }>;
  model?: 'gemini-2.5-flash' | 'gemini-2.5-pro';
}

interface MultiSourceJobResponse {
  job_id: string;
  source_count: number;
  estimated_cost: number;
  warnings: string[];
}
```

---

## 6. Key Interactions

### 6.1 Adding YouTube URLs

1. User clicks "+ YouTube URLs" button
2. Panel expands with textarea
3. User pastes URLs (supports bulk paste)
4. System validates URLs in real-time, shows count
5. User clicks "Add to Queue"
6. URLs appear as individual items in SourceQueue
7. Panel collapses, button shows "(3 added)"

### 6.2 Adding Text Content

1. User clicks "+ Paste Text" button
2. Panel expands with form:
   - Source Label (required)
   - Content textarea (required)
   - Collapsible metadata section (URL, author, date, platform)
3. User fills form, clicks "Add to Queue"
4. Text source appears in SourceQueue with truncated preview
5. Panel collapses

### 6.3 Adding Screenshot

1. User clicks "+ Screenshot" button
2. Panel expands with:
   - Drag-drop zone / file picker
   - Topic field (required)
   - Platform hint dropdown
   - Context note (optional)
3. User uploads file, fills fields
4. Thumbnail preview shown
5. Clicks "Add to Queue"
6. Screenshot appears in SourceQueue with thumbnail

### 6.4 Submitting Job

1. User reviews SourceQueue (can reorder via drag-drop)
2. Clicks "Submit Job"
3. Loading state shown
4. On success: queue clears, new job appears in JobsList
5. On error: error message shown, queue preserved

### 6.5 Viewing Output Documents

1. Job completes, card shows DocumentCards
2. User clicks "View" on Doc 2 (Semantic Brief)
3. DocumentViewerModal opens
4. User reads document, can:
   - Copy to clipboard
   - Download as Markdown
   - Export to Google Docs
5. Closes modal

---

## 7. Visual Design Tokens

```css
/* Colors */
--color-youtube: #a855f7;     /* Purple */
--color-text: #22c55e;        /* Green */
--color-screenshot: #3b82f6;  /* Blue */

--color-doc-0: #6b7280;       /* Gray - Source Ledger */
--color-doc-1: #3b82f6;       /* Blue - Jump-Start */
--color-doc-2: #a855f7;       /* Purple - Semantic Brief */

/* Spacing */
--space-xs: 0.25rem;
--space-sm: 0.5rem;
--space-md: 1rem;
--space-lg: 1.5rem;
--space-xl: 2rem;

/* Border radius */
--radius-sm: 0.375rem;
--radius-md: 0.5rem;
--radius-lg: 0.75rem;
--radius-xl: 1rem;

/* Shadows */
--shadow-card: 0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-glow-purple: 0 0 20px rgb(168 85 247 / 0.2);
--shadow-glow-green: 0 0 20px rgb(34 197 94 / 0.2);
--shadow-glow-blue: 0 0 20px rgb(59 130 246 / 0.2);
```

---

## 8. Wireframes

### 8.1 Desktop - Job Creator Expanded

```
+------------------------------------------------------------------------+
|  NEW RESEARCH JOB                                                       |
+------------------------------------------------------------------------+
|                                                                         |
|  +--------------------+ +--------------------+ +--------------------+   |
|  | + YouTube URLs (3) | | + Paste Text       | | + Screenshot       |   |
|  | EXPANDED           | |                    | |                    |   |
|  +--------------------+ +--------------------+ +--------------------+   |
|  |                                                                  |   |
|  | Paste YouTube URLs (one per line)                                |   |
|  | +--------------------------------------------------------------+ |   |
|  | | https://youtube.com/watch?v=abc123                           | |   |
|  | | https://youtu.be/xyz789                                      | |   |
|  | | https://youtube.com/watch?v=def456                           | |   |
|  | +--------------------------------------------------------------+ |   |
|  |                                                                  |   |
|  | [Cancel]                                   [Add 3 URLs to Queue] |   |
|  +------------------------------------------------------------------+   |
|                                                                         |
|  SOURCE QUEUE (2 items)                                [Submit Job -->] |
|  +---------------------------------------------------------------------+|
|  | [YT] Interview Pt 1                                             [x] ||
|  | [TXT] Background Article                                        [x] ||
|  +---------------------------------------------------------------------+|
|                                                                         |
+------------------------------------------------------------------------+
```

### 8.2 Desktop - Completed Job with Documents

```
+------------------------------------------------------------------------+
|  UFO Disclosure Analysis                           [Completed] [v]     |
|  video_analysis | Jan 17, 2026 10:30 AM                                |
+------------------------------------------------------------------------+
|                                                                         |
|  +----------------------+ +----------------------+ +-------------------+ |
|  |      DOC 0           | |       DOC 1          | |      DOC 2        | |
|  |   Source Ledger      | |   Jump-Start         | |  Semantic Brief   | |
|  |                      | |   Directions         | |                   | |
|  |   5 sources          | |   12 research        | |   8 themes        | |
|  |   analyzed           | |   directions         | |   23 key points   | |
|  |                      | |                      | |   45 quotes       | |
|  |  [View] [Download v] | |  [View] [Download v] | | [View] [Download v]||
|  +----------------------+ +----------------------+ +-------------------+ |
|                                                                         |
|  +---------------------------------------------------------------------+|
|  | [Clips] [Quotes] [Blueprints] [Gaps] [Research]                    ||
|  +---------------------------------------------------------------------+|
|  | (existing tab content)                                              ||
|  +---------------------------------------------------------------------+|
|                                                                         |
+------------------------------------------------------------------------+
```

### 8.3 Mobile - Source Queue

```
+---------------------------+
| NEW RESEARCH JOB          |
+---------------------------+
|                           |
| [+ YouTube URLs     (2)]  |
| [+ Paste Text          ]  |
| [+ Screenshot          ]  |
|                           |
+---------------------------+
| SOURCE QUEUE              |
+---------------------------+
| [YT] Video 1          [x] |
| [YT] Video 2          [x] |
+---------------------------+
|                           |
| [     Submit Job     -->] |
|                           |
+---------------------------+
```

### 8.4 Document Viewer Modal

```
+------------------------------------------------------------------+
|  SEMANTIC BRIEF (Doc 2)                                     [x]  |
+------------------------------------------------------------------+
|                                                                   |
|  ## Themes                                                        |
|                                                                   |
|  ### 1. Government Secrecy                                        |
|  Sources: SRC_1, SRC_2, SRC_3                                    |
|  Confidence: HIGH                                                 |
|                                                                   |
|  Key evidence suggests a pattern of information suppression...    |
|                                                                   |
|  > "We were told not to discuss what we saw"                     |
|  > -- Bob Lazar, Joe Rogan #2123 @ 45:23                         |
|                                                                   |
|  ### 2. Technological Implications                                |
|  Sources: SRC_1, SRC_4                                           |
|  Confidence: MEDIUM                                               |
|                                                                   |
|  ...                                                             |
|                                                                   |
+------------------------------------------------------------------+
|                            [Copy]  [Download v]  [Export to Docs] |
+------------------------------------------------------------------+
```

---

## 9. Implementation Priority

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| P0 | Hide Topic Research tab | Low | Quick win |
| P1 | SourceQueue + SourceAdders | High | Core feature |
| P1 | Backend multi-source endpoint | Medium | Required for P1 |
| P2 | DocumentCards in JobCard | Medium | Better output UX |
| P2 | DocumentViewerModal | Medium | Improved viewing |
| P3 | Drag-drop reordering | Low | Nice to have |

---

## 10. Accessibility Considerations

- All interactive elements have visible focus states
- SourceQueue items can be navigated/removed via keyboard
- DocumentViewer modal traps focus, closes on Escape
- Color is not the only indicator of source type (icons + labels)
- ARIA labels on all buttons
- Reduced motion preference respected for animations

---

## 11. Open Questions

1. **Backend API:** Does multi-source endpoint exist or need to be built?
2. **Source limits:** Max sources per job? (Suggest: 10 YouTube, 5 text, 5 screenshots)
3. **Error handling:** If one source fails validation, reject all or allow partial?
4. **Document generation:** Are Doc 0/1/2 already being generated? Need to confirm backend support.
5. **Reordering:** Is source order significant for analysis? If not, skip drag-drop.

---

## Summary

This design transforms the dashboard from a tab-based, single-source-per-job model to a unified queue-based, multi-source approach. The output experience shifts focus from raw data (clips/quotes) to the actual research documents (Doc 0/1/2) that users need.

Key changes:
1. Replace tabs with expandable source adders
2. Add visual source queue with preview
3. Create document cards for completed jobs
4. Add document viewer modal for detailed reading
5. Remove legacy Topic Research tab
