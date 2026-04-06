# Phase PP-6: Iteration UX Redesign

## Overview
- **Priority:** P1
- **Status:** pending
- **Effort:** 2-3 days
- **Depends on:** PP-1 (tokens), PP-3 (copy)
- **Description:** Replace the ChatSheet dropdown+textarea with visual quick-action cards. Make the power feature feel intuitive for creators.

## Key Insights
- ChatSheet is 320px wide (w-80) — too narrow
- Dropdown with 6 modes (Deep Dive, Expand Sources, etc.) is confusing for creators
- No descriptions on modes — user can't distinguish "Deep Dive" from "Go Deeper"
- No iteration history visible
- "Run Iteration" button sounds like a CLI command

## Requirements

### New Design: Quick-Action Cards

Replace the dropdown+textarea with a card grid:

```
┌─────────────────────────────────────┐
│  What would you like to do?         │
│                                     │
│  ┌───────────────┐ ┌──────────────┐│
│  │ 🔍 Find       │ │ ➕ Add More  ││
│  │ What's Missing│ │ Sources      ││
│  │ Uncover gaps  │ │ Expand your  ││
│  │ and new dirs  │ │ research     ││
│  └───────────────┘ └──────────────┘│
│  ┌───────────────┐ ┌──────────────┐│
│  │ 🔬 Dig Deeper │ │ 🔄 New Angle ││
│  │ Re-analyze    │ │ Fresh take,  ││
│  │ with depth    │ │ same data    ││
│  └───────────────┘ └──────────────┘│
│                                     │
│  [Custom request...]       [Send]   │
│                                     │
│  History:                           │
│  • v2: Added 2 sources (3min ago)  │
│  • v1: Original research           │
└─────────────────────────────────────┘
```

## Related Code Files

| File | Change |
|------|--------|
| `components/job-detail-v2/chat-sheet.tsx` | Redesign internals |
| `components/job-detail-v2/job-right-panel.tsx` | Quick action buttons on right panel |
| `components/job-detail-v2/version-selector.tsx` | Show version history |

## Implementation Steps

### Task PP-6.1: Redesign ChatSheet content
1. Replace mode dropdown with a 2×2 card grid of quick actions
2. Each card: icon (Lucide) + title + one-line description
3. Cards map to iteration modes from PP-3 copy:
   - Find What's Missing → `deep_dive`
   - Add More Sources → `expand_sources`
   - Dig Deeper → `deeper`
   - Try a New Angle → `different_angle`
4. Below cards: text input for custom request (maps to `custom` mode)
5. Widen sheet: `w-80` → `w-96` or `sm:w-[420px]`

### Task PP-6.2: Add iteration history
1. Below the action cards, show previous iterations with:
   - Version number
   - Mode used (in creator language)
   - Timestamp (relative: "3 min ago")
   - Brief summary of what changed (if available from backend)
2. Source this from the job's version metadata

### Task PP-6.3: Add quick-action buttons to right panel
1. On `job-right-panel.tsx`: add 2-3 most common actions as small buttons
2. "Find What's Missing" and "Add Sources" as persistent shortcuts
3. Clicking opens ChatSheet with that mode pre-selected

### Task PP-6.4: Rename submit button
1. "Run Iteration" → "Go" or "Start" (context-dependent)
2. For quick-action cards: clicking the card itself submits (no separate button)
3. For custom text: "Send" button

### Task PP-6.5: Verify
1. Quick-action cards work — clicking triggers correct iteration mode
2. Custom text input works
3. History shows previous versions
4. Sheet is wide enough to be comfortable
5. Build passes

## Todo Checklist
- [ ] PP-6.1 Redesign ChatSheet with quick-action cards
- [ ] PP-6.2 Add iteration history section
- [ ] PP-6.3 Add quick-action buttons to right panel
- [ ] PP-6.4 Rename submit button
- [ ] PP-6.5 Verify all interactions + build

## Success Criteria
- Zero dropdowns for mode selection
- Quick-action cards with descriptions for all iteration modes
- Custom text input for freeform requests
- Version history visible
- Build passes
