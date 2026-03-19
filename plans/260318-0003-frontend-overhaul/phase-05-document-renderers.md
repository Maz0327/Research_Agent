# Phase 5: Document Renderers — All 7 Document Types

## Context
- Plan: [plan.md](plan.md)
- Depends on: [Phase 4](phase-04-job-detail-hero-page.md) (DocumentViewer dispatcher)
- Current: `components/document/` — 12 renderer files + 10 shared components
- Target: Rebuilt renderers using shadcn/ui Accordion, Card, Badge, Collapsible

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 |
| Status | pending |
| Effort | 6h |
| Description | Migrate all document renderers to shadcn/ui design system with expandable sections |

## Key Insights
- 7 document types, each with unique structure but shared visual components
- Current renderers already well-decomposed — 10 shared components in `document/shared/`
- Key pattern: most documents are lists of collapsible sections (key points, themes, tensions)
- shadcn/ui Accordion replaces custom CollapsibleSection
- ConfidenceBadge → shadcn Badge with color variants mapped to confidence levels
- CitationPill → compact Badge linking to source
- EditableSection → preserved for inline editing feature (Phase 4 already supports this)
- CardWrapper → shadcn Card
- `lib/document-formatters.ts` (16.8KB) contains all formatting logic — preserve entirely

## Requirements
1. All 7 document renderers rebuilt with shadcn/ui components
2. Shared components migrated: ConfidenceBadge, CitationPill, SectionHeader, EditableSection, ProseBlock
3. Accordion for expandable sections (max 5-7 per group)
4. Consistent dark theme styling via CSS variables
5. Preserve all existing data display (no data loss in migration)
6. Inline editing support maintained
7. Markdown rendering preserved (react-markdown + plugins)

## Architecture

### Shared Components
```
components/document/shared/
├── ConfidenceBadge.tsx      # Badge: HIGH=green, MEDIUM=yellow, LOW=red
├── CitationPill.tsx          # Compact source reference, clickable
├── SectionHeader.tsx         # Section title with icon + count badge
├── EditableSection.tsx       # Inline edit mode with save/cancel ('use client')
├── ProseBlock.tsx            # Markdown-rendered text block
├── QuoteBlock.tsx            # Styled quote with source attribution
├── ClaimCard.tsx             # Claim display with confidence + verification status
├── InlineEditBar.tsx         # Edit toolbar (bold, italic, etc.)
└── CardWrapper.tsx           # Thin wrapper around shadcn Card (backward compat)
```

### Document Renderers
```
components/document/
├── SourceLedgerRenderer.tsx  # Doc 0: Table of sources
├── JumpStartRenderer.tsx     # Doc 1: Key points, tensions, gaps
├── SemanticBriefRenderer.tsx  # Doc 2: Themes, SCQA, confidence
├── CreatorBriefRenderer.tsx   # Doc 3: Story core, hooks, angles (hero doc)
├── ScriptRenderer.tsx         # Doc 5: Beat-labeled sections
├── SocialKitRenderer.tsx      # Doc 6: Platform-tabbed social content
├── BlogPostRenderer.tsx       # Doc 7: Blog sections + SEO
└── shared/                    # Shared components above
```

### Component Patterns

**Accordion Section Pattern** (used in Doc 1, 2, 3):
```
<Accordion type="multiple" defaultValue={[first 3 items]}>
  <AccordionItem value="kp-1">
    <AccordionTrigger>
      <SectionHeader title="Key Point 1" confidence="HIGH" />
    </AccordionTrigger>
    <AccordionContent>
      <ProseBlock text={statement} />
      <QuoteBlock quotes={quotes} />
      <div className="flex gap-1">
        {source_ids.map(id => <CitationPill key={id} sourceId={id} />)}
      </div>
    </AccordionContent>
  </AccordionItem>
</Accordion>
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `components/document/SourceLedgerRenderer.tsx` | Rebuild | Table with source tags |
| `components/document/JumpStartRenderer.tsx` | Rebuild | Key points + tensions + gaps |
| `components/document/SemanticBriefRenderer.tsx` | Rebuild | Themes + SCQA |
| `components/document/CreatorBriefRenderer.tsx` | Rebuild | Story core + hooks — hero doc |
| `components/document/ScriptRenderer.tsx` | Rebuild | Beat labels + directions |
| `components/document/SocialKitRenderer.tsx` | Rebuild | Platform tabs |
| `components/document/BlogPostRenderer.tsx` | Rebuild | Sections + SEO |
| `components/document/shared/*` | Rebuild | 10 shared components |
| `components/document/ExportToolbar.tsx` | Moved to Phase 4 | Now in job-detail |
| `components/document/HookOptionCard.tsx` | Preserve | Used in CreatorBrief |
| `components/document/StoryArcCard.tsx` | Preserve | Used in CreatorBrief |
| `components/document/SectionActions.tsx` | Rebuild | Inline action bar |
| `lib/document-formatters.ts` | Preserve | 16.8KB formatting logic |
| `components/common/MarkdownRenderer.tsx` | Preserve | react-markdown wrapper |

## Implementation Steps

### 5.1 Rebuild shared/ConfidenceBadge
- shadcn Badge with variants:
  - HIGH: `variant="default"` with green styling
  - MEDIUM: `variant="secondary"` with yellow styling
  - LOW: `variant="destructive"` (red)
- Props: `level: 'HIGH' | 'MEDIUM' | 'LOW'`, optional `label`

### 5.2 Rebuild shared/CitationPill
- Compact shadcn Badge, `variant="outline"`
- Shows source ID (e.g., "SRC_1")
- Clickable — scrolls to source in Source Ledger or opens tooltip with source title
- Props: `sourceId`, `sourceTitle?`, `onClick?`

### 5.3 Rebuild shared/SectionHeader
- Flex row: icon + title + count Badge + ConfidenceBadge
- Props: `title`, `icon?`, `count?`, `confidence?`
- Used as AccordionTrigger content

### 5.4 Rebuild shared/EditableSection
- 'use client' component
- View mode: renders ProseBlock
- Edit mode: textarea with InlineEditBar
- Save/cancel buttons
- Props: `content`, `onSave`, `sectionId`, `editable`

### 5.5 Rebuild shared/ProseBlock + QuoteBlock + ClaimCard
- **ProseBlock**: MarkdownRenderer wrapper with prose styling
- **QuoteBlock**: Card with left border accent, quote text, source attribution, `unverified` badge if applicable
- **ClaimCard**: Card with claim statement, confidence badge, verification status icon, source citations

### 5.6 Build SourceLedgerRenderer (Doc 0)
- Table layout (shadcn Table or custom grid)
- Columns: #, Title, Type (tag), Mode (badge), Confidence Ceiling, URL (link)
- Sortable by column (optional, stretch)
- Row click shows source detail tooltip
- Source type tags: transcript, article, video, text, ocr

### 5.7 Build JumpStartRenderer (Doc 1)
- Three Accordion groups:
  1. **Key Points** — AccordionItems with statement, quotes, citations
  2. **Tensions** — Conflicting viewpoints with source references
  3. **Knowledge Gaps** — Identified gaps with search directions
- Each group has SectionHeader with count
- Default: first 3 items open in each group

### 5.8 Build SemanticBriefRenderer (Doc 2)
- Sections:
  1. **Themes** — Accordion with theme name, description, supporting key points
  2. **SCQA** (Situation, Complication, Question, Answer) — Card layout
  3. **Cross-Source Analysis** — Patterns, agreements, disagreements
- CircularGauge for overall confidence score
- ConfidenceBadge per theme

### 5.9 Build CreatorBriefRenderer (Doc 3) — Hero Document
- Most styled document, needs special attention
- Sections:
  1. **Story Core** — narrative foundation (Card)
  2. **Content Hooks** — HookOptionCard grid (3 options)
  3. **Angles** — creative angles with descriptions
  4. **Talking Points** — Accordion with expandable items
  5. **References** — linked citations back to Doc 2 claims
- StoryArcCard for narrative structure visualization

### 5.10 Build ScriptRenderer (Doc 5)
- Sequential sections with beat labels
- Each section: beat label badge, heading, body content, stage directions (italic)
- Timeline-style layout with connecting line between sections
- ProseBlock for body content

### 5.11 Build SocialKitRenderer (Doc 6)
- shadcn Tabs for platform switching: Twitter, LinkedIn, Instagram, TikTok, YouTube
- Per platform: multiple post variants
- Each post: content text, hashtags (tags), character count, image prompt (if applicable)
- Copy button per post

### 5.12 Build BlogPostRenderer (Doc 7)
- Sections with headings (H2, H3)
- ProseBlock for body
- SEO metadata card: title tag, meta description, keywords (tags)
- Word count display
- Table of contents (auto-generated from headings)

### 5.13 Integration test with DocumentViewer
- Test all 7 renderers with sample data
- Verify Accordion expand/collapse
- Verify ConfidenceBadge colors
- Verify CitationPill clicks
- Verify inline editing
- Test with empty/sparse data (empty array handling)

## Todo
- [ ] 5.1 ConfidenceBadge
- [ ] 5.2 CitationPill
- [ ] 5.3 SectionHeader
- [ ] 5.4 EditableSection
- [ ] 5.5 ProseBlock + QuoteBlock + ClaimCard
- [ ] 5.6 SourceLedgerRenderer (Doc 0)
- [ ] 5.7 JumpStartRenderer (Doc 1)
- [ ] 5.8 SemanticBriefRenderer (Doc 2)
- [ ] 5.9 CreatorBriefRenderer (Doc 3)
- [ ] 5.10 ScriptRenderer (Doc 5)
- [ ] 5.11 SocialKitRenderer (Doc 6)
- [ ] 5.12 BlogPostRenderer (Doc 7)
- [ ] 5.13 Integration test with DocumentViewer

## Success Criteria
- All 7 document types render correctly with real job data
- Accordion sections expand/collapse smoothly
- Confidence badges show correct colors
- Citation pills link to correct sources
- Inline editing works (save persists, cancel reverts)
- Empty/sparse data renders gracefully (no crashes, shows "No data" states)
- Markdown content renders correctly (lists, bold, links, code)
- Dark theme consistent across all renderers
- `npm run build` passes

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Data shape mismatch with new renderers | Medium | High | Type-check all props against `types/documents.ts` |
| Formatter logic lost in migration | Low | High | `document-formatters.ts` preserved unchanged |
| Accordion performance with many items | Low | Medium | Use `type="multiple"` with limited defaultValue |
| Inline editing state conflicts with polling | Medium | Medium | Disable polling while editing, re-enable on save/cancel |

## Security Considerations
- All user-generated content rendered via react-markdown with rehype-sanitize
- DOMPurify still used for any raw HTML content
- Quote/claim text displayed as text, not dangerouslySetInnerHTML
- Export preserves sanitization (PDF/DOCX exports use sanitized content)

## Next Steps
Phase 6: Migrate remaining pages (Settings, Usage, Transcripts, Admin, Landing, Login).
