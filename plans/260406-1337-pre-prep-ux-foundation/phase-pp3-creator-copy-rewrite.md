# Phase PP-3: Creator Copy Rewrite

## Overview
- **Priority:** P0
- **Status:** completed
- **Effort:** 2-3 days
- **Description:** Rewrite all user-facing copy from engineer-speak to creator language. Every string should resonate with a YouTube content creator.
- **Completed:** 2026-04-06
- **Commit:** `d51cc18`

## Key Insights
- Current copy: "Semantic Brief", "Iterate", "Deep Dive", "Pipeline", "Source Ledger"
- Target audience: YouTube video essayists, true crime creators, tech reviewers
- Positioning: "Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered."

## Requirements

### Copy Map (Engineer → Creator)

**Document Names:**
| Current | New | Rationale |
|---------|-----|-----------|
| Source Ledger (Doc 0) | Your Sources | What it is |
| Jump-Start Directions (Doc 1) | Research Gaps | What it reveals |
| Semantic Brief (Doc 2) | Key Findings | What the user wants |
| Creator Brief (Doc 3) | Story Angles | What makes it creative |
| Producer Packet (Doc 4) | Producer Guide | Clear enough |
| Script (Doc 5) | Script | Already clear |
| Blog Post (Doc 6) | Blog Post | Already clear |
| Social Kit (Doc 7) | Social Kit | Already clear |

**Pipeline Stages:**
| Current | New |
|---------|-----|
| source_identity | Finding your sources... |
| semantic_extraction | Reading through everything... |
| semantic_validation | Checking the facts... |
| gap_analysis | Finding what nobody covered... |
| semantic_synthesis | Connecting the dots... |
| document_assembly | Building your research... |
| creator_brief | Crafting story angles... |
| completion | Done! |

**Iteration Modes:**
| Current | New | Description |
|---------|-----|-------------|
| Deep Dive | Find What's Missing | "Uncover gaps and new research directions" |
| Expand Sources | Add More Sources | "Add new videos or articles to your research" |
| Go Deeper | Dig Deeper | "Re-analyze sources with more depth" |
| Different Angle | Try a New Angle | "Same research, fresh perspective" |
| Custom | Custom Request | "Tell us exactly what you need" |
| Inline Edit | Edit Section | "Modify a specific part" |

**Dashboard:**
| Current | New |
|---------|-----|
| Dashboard / Your research hub | What's your next video about? |
| Start Your First Research | Drop some links, get a script |
| New Research | New Project |
| Total Jobs | Projects |
| Completed | Completed |
| Running | In Progress |
| API Spend | Remove entirely (or "Credits Used" when credit system exists) |

**Wizard:**
| Current | New |
|---------|-----|
| Step 1: Topic | What are you researching? |
| Step 2: Sources | Paste your links |
| Step 3: Mode (6 options) | How deep? (Quick / Full) |
| Step 4: Preview | Review & start |

## Related Code Files

| File | Type of Copy |
|------|-------------|
| `lib/constants.ts` | STAGE_LABELS, doc type labels |
| `components/dashboard/dashboard-content.tsx` | Dashboard title, empty state |
| `components/dashboard/recent-jobs-list.tsx` | Empty state, column headers |
| `components/dashboard/dashboard-stats.tsx` | Stat card labels |
| `components/dashboard/job-creation-wizard.tsx` | Wizard step labels |
| `components/dashboard/wizard-step-*.tsx` | Step content copy |
| `components/job-detail-v2/document-nav.tsx` | Document names in sidebar |
| `components/job-detail-v2/chat-sheet.tsx` | Iteration mode labels |
| `components/job-detail-v2/job-right-panel.tsx` | Action button labels |
| `components/layout/pipeline-status-bar.tsx` | Stage display labels |
| `components/auth/login-form.tsx` | Login page copy |

## Implementation Steps

### Task PP-3.1: Update constants and label maps
1. `lib/constants.ts` — update STAGE_LABELS with new names + descriptions
2. Any document type label map — update Doc 0-7 names
3. These constants propagate to many components automatically

### Task PP-3.2: Rewrite dashboard copy
1. `dashboard-content.tsx` — title, subtitle
2. `recent-jobs-list.tsx` — empty state, headers
3. `dashboard-stats.tsx` — remove "API Spend" card, rename others
4. `StartInput.tsx` — placeholder text

### Task PP-3.3: Rewrite wizard copy
1. `job-creation-wizard.tsx` — step labels
2. `wizard-step-topic.tsx` — heading, description
3. `wizard-step-sources.tsx` — heading, description, placeholder
4. `wizard-step-mode.tsx` — heading, mode descriptions
5. `wizard-step-preview.tsx` — heading, labels

### Task PP-3.4: Rewrite job detail copy
1. `document-nav.tsx` — document names
2. `chat-sheet.tsx` — iteration mode labels + descriptions
3. `job-right-panel.tsx` — action button labels

### Task PP-3.5: Rewrite auth copy
1. `login-form.tsx` — add positioning statement, creator-focused tagline

### Task PP-3.6: Verify
1. Grep for remaining engineer terms: `grep -rn "Semantic Brief\|Source Ledger\|Jump-Start\|Iterate\|Deep Dive" components/ lib/`
2. Visual walkthrough of every screen
3. `npm run build` passes

## Todo Checklist
- [x] PP-3.1 Update constants and label maps
- [x] PP-3.2 Rewrite dashboard copy
- [x] PP-3.3 Rewrite wizard copy
- [x] PP-3.4 Rewrite job detail copy
- [x] PP-3.5 Rewrite auth/login copy
- [x] PP-3.6 Verify no engineer-speak remaining

## Success Criteria
- Zero instances of "Semantic Brief", "Source Ledger", "Jump-Start", "Iterate" in user-facing copy
- Positioning statement visible on login page
- All pipeline stages have creator-friendly names + descriptions
- Build passes
