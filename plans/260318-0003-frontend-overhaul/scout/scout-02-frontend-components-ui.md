# Scout: Frontend Components & UI

## Component Directories (27 folders)

| Directory | Files | Purpose |
|-----------|-------|---------|
| `job-card` | 20 | Job list items, preview cards, status |
| `document` | 12 | Doc renderers (Blog, Creator Brief, Semantic Brief, etc.) |
| `job-detail` | 11 | Job detail, source explorer, results panels |
| `settings` | 8 | User settings, preferences, API config |
| `ui` | 9 | Reusable primitives |
| `unified-input` | 4 | Source input forms (YT, URL, text, file) |
| `common` | 4 | DocumentHeader, MarkdownRenderer, CopyButton |
| `dashboard` | 4 | Dashboard layout + overview |
| `document-drawer` | 2 | Doc sidebar, version selector |
| `brainstorm` | 2 | Brainstorm/ideation UI |
| `creator-brief` | 2 | Creator Brief view, claim drill-down |
| `creator-analysis` | 2 | Creator profile analysis |
| `iterate` | 2 | Iteration controls |
| `search` | 2 | Search interface |
| `claim-extractor` | 1 | Claim extraction view |

## UI Primitives (`components/ui/`)

- `AnimatedButton.tsx` — primary/secondary/danger/ghost + sm/md/lg + loading
- `FloatingActionButton.tsx` — FAB
- `GlowCard.tsx` — Glowing card container
- `GradientText.tsx` — Gradient text
- `ProgressRing.tsx` — Circular progress (SVG)
- `Skeleton.tsx` — Loading skeleton
- `Spinner.tsx` — Loading spinner
- `StageIndicator.tsx` — Pipeline stage progress

## Document Shared Components (`document/shared/`)

CardWrapper, CollapsibleSection, ConfidenceBadge, CitationPill, EditableSection, InlineEditBar, InlineActionBar, BoldFirstSentence, ProseBlock, SectionHeader

## Tailwind Config

- Dark mode: `class` strategy
- Custom colors: dark.bg (primary/secondary/tertiary), dark.text (primary/secondary/muted/disabled)
- Accent: blue, purple, green variants
- Animations: shimmer, fade-in, slide-up, scale-in, gradient, pulse-slow, spin-slow
- Glow shadows: glow-blue, glow-purple, glow-green
- No custom CSS files — pure Tailwind
