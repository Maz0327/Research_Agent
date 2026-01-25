# React Component Structure for Document Rendering

**Date:** 2026-01-25
**Purpose:** Frontend component hierarchy for rendering Doc 0/1/2 from JSON data

---

## Component Hierarchy

```
frontend/components/documents/
├── index.ts                    # Barrel exports
├── DocumentRenderer.tsx        # Router - picks correct renderer by type
├── shared/
│   ├── ConfidenceBadge.tsx    # 🟢 HIGH / 🟡 MEDIUM / 🔴 LOW
│   ├── StatusBadge.tsx        # ✅ / ⚠️ / ❌ with colors
│   ├── AlertBox.tsx           # Note/Warning/Important/Caution variants
│   ├── CollapsibleSection.tsx # Expandable content
│   ├── DataTable.tsx          # Generic sortable table
│   └── SourceLink.tsx         # Clickable source reference
├── source-ledger/
│   ├── SourceLedger.tsx       # Doc 0 main component
│   ├── SourceManifest.tsx     # Table of all sources
│   ├── SourceCard.tsx         # Individual source entry
│   └── TranscriptQuality.tsx  # Transcript provenance display
├── jump-start/
│   ├── JumpStart.tsx          # Doc 1 main component
│   ├── ScopeLock.tsx          # IN/OUT scope display
│   ├── KeyPointsList.tsx      # Key points with confidence
│   ├── GapsSection.tsx        # Gaps with research directions
│   └── NextSteps.tsx          # Top 3 action items
└── semantic-brief/
    ├── SemanticBrief.tsx      # Doc 2 main component
    ├── SemanticCore.tsx       # Core summary block
    ├── ThemeCard.tsx          # Individual theme
    ├── TensionCard.tsx        # Individual tension
    ├── ConfidenceCard.tsx     # Confidence assessment
    └── SpeculativeSection.tsx # Speculative observations
```

---

## Shared Components

### ConfidenceBadge.tsx
```tsx
interface ConfidenceBadgeProps {
  level: 'high' | 'medium' | 'low';
  size?: 'sm' | 'md' | 'lg';
}

// Renders: 🟢 HIGH with green bg, 🟡 MEDIUM with yellow bg, etc.
```

### StatusBadge.tsx
```tsx
interface StatusBadgeProps {
  status: 'ingested' | 'partial' | 'failed';
}

// Renders: ✅ Ingested, ⚠️ Partial, ❌ Failed with appropriate colors
```

### AlertBox.tsx
```tsx
interface AlertBoxProps {
  type: 'note' | 'tip' | 'important' | 'warning' | 'caution';
  children: React.ReactNode;
}

// Color scheme:
// note: blue, tip: green, important: purple, warning: yellow, caution: red
```

### CollapsibleSection.tsx
```tsx
interface CollapsibleSectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  badge?: React.ReactNode; // e.g., count badge
}

// Uses Radix Collapsible or custom implementation
```

---

## Doc 0: Source Ledger Components

### SourceLedger.tsx
```tsx
interface SourceLedgerProps {
  data: {
    topic: string;
    sources: SourceEntry[];
    created_at: string;
  };
}

export function SourceLedger({ data }: SourceLedgerProps) {
  const stats = useMemo(() => calculateStats(data.sources), [data.sources]);

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <AlertBox type="note">
        <div className="flex gap-4">
          <span>Sources: {stats.total}</span>
          <span>✅ {stats.ingested}</span>
          <span>⚠️ {stats.partial}</span>
          <span>❌ {stats.failed}</span>
        </div>
      </AlertBox>

      {/* Source Manifest Table */}
      <SourceManifest sources={data.sources} />

      {/* Detailed Source Cards */}
      <CollapsibleSection title="Detailed Analysis" defaultOpen>
        {data.sources.map(source => (
          <SourceCard key={source.source_id} source={source} />
        ))}
      </CollapsibleSection>
    </div>
  );
}
```

### SourceCard.tsx
```tsx
interface SourceCardProps {
  source: SourceEntry;
}

// Card with:
// - Header: ID + Title + Type icon + Status badge
// - Metadata table (creator, published, duration)
// - Quick summary bullets
// - Collapsible full text
// - Transcript quality (if video)
```

---

## Doc 1: Jump-Start Components

### JumpStart.tsx
```tsx
interface JumpStartProps {
  data: {
    scope_lock: { in: string[]; out: string[] };
    current_corpus: { source_count: number; perspectives: string[] };
    key_points: KeyPoint[];
    tensions: Tension[];
    gaps: Gap[];
    research_directions: ResearchDirection[];
    next_steps: string[];
    confidence: string;
  };
}

export function JumpStart({ data }: JumpStartProps) {
  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <AlertBox type="note">
        Sources: {data.current_corpus.source_count} |
        Key Points: {data.key_points.length} |
        Gaps: {data.gaps.length}
      </AlertBox>

      <ScopeLock scope={data.scope_lock} />
      <KeyPointsList points={data.key_points} />
      <GapsSection gaps={data.gaps} directions={data.research_directions} />
      <NextSteps steps={data.next_steps} />
    </div>
  );
}
```

### NextSteps.tsx
```tsx
// Prominent card with numbered steps
// Uses AlertBox type="important" styling
```

---

## Doc 2: Semantic Brief Components

### SemanticBrief.tsx
```tsx
interface SemanticBriefProps {
  data: {
    semantic_core: { text: string; based_on: string[] };
    themes: Theme[];
    key_points: KeyPoint[];
    tensions: Tension[];
    gaps: Gap[];
    confidence_assessment: { level: string; reasoning: string[] };
    triage: string;
    warnings: string[];
  };
}

export function SemanticBrief({ data }: SemanticBriefProps) {
  return (
    <div className="space-y-6">
      {/* Quality Banner */}
      {data.triage !== 'ready' && (
        <AlertBox type="warning">
          Quality: {data.triage.toUpperCase()}
        </AlertBox>
      )}

      <SemanticCore core={data.semantic_core} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.themes.map(theme => (
          <ThemeCard key={theme.theme_id} theme={theme} />
        ))}
      </div>

      <DataTable
        data={data.key_points}
        columns={['ID', 'Statement', 'Sources', 'Confidence']}
      />

      <ConfidenceCard assessment={data.confidence_assessment} />
    </div>
  );
}
```

### ThemeCard.tsx
```tsx
// Card showing:
// - Theme label as title
// - Description
// - Related key points (as links/badges)
// - Optional: consensus indicator if multi-source
```

---

## DocumentRenderer (Router)

```tsx
interface DocumentRendererProps {
  type: 'source_ledger' | 'jump_start' | 'semantic_brief';
  data: any;
}

export function DocumentRenderer({ type, data }: DocumentRendererProps) {
  switch (type) {
    case 'source_ledger':
      return <SourceLedger data={data} />;
    case 'jump_start':
      return <JumpStart data={data} />;
    case 'semantic_brief':
      return <SemanticBrief data={data} />;
    default:
      return <div>Unknown document type</div>;
  }
}
```

---

## Styling Approach

Use Tailwind CSS with these design tokens:

```tsx
// Color scheme for confidence
const confidenceColors = {
  high: 'bg-green-100 text-green-800 border-green-300',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  low: 'bg-red-100 text-red-800 border-red-300',
};

// Color scheme for alerts
const alertColors = {
  note: 'bg-blue-50 border-blue-200 text-blue-800',
  tip: 'bg-green-50 border-green-200 text-green-800',
  important: 'bg-purple-50 border-purple-200 text-purple-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  caution: 'bg-red-50 border-red-200 text-red-800',
};
```

---

## Integration with Existing Frontend

1. **In `JobResults.tsx`**: Replace markdown viewer with `DocumentRenderer`
2. **Data source**: Use `job.artifacts.source_ledger` (JSON), not `_md` (markdown)
3. **PDF export**: Keep using markdown version for download

```tsx
// In JobResults.tsx
{activeDoc === 'doc0' && (
  <DocumentRenderer
    type="source_ledger"
    data={job.artifacts?.source_ledger}
  />
)}
```

---

## Implementation Priority

| Priority | Component | Reason |
|----------|-----------|--------|
| 1 | Shared components | Foundation for all docs |
| 2 | SourceLedger | Most complex, highest value |
| 3 | JumpStart | User's primary "what next" view |
| 4 | SemanticBrief | Deep analysis view |

---

## Unresolved Questions

1. **State management**: Use local state or integrate with jobs store?
2. **Virtualization**: Need virtual scrolling for large source lists?
3. **Search**: Add in-document search functionality?
4. **Print styling**: Need separate print CSS for PDF download?
