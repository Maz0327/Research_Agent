# Phase 3 Prompt — Copy Everything Below Into a New Claude Code Session

---

## Prompt

I need you to implement Phase 3 of the UX Overhaul plan for my Research Agent project.

**Project location:** `/Users/maz/Documents/github/Research_Agent`
**Branch:** `feature/kimi-visual-analysis-and-optimizations`

### Context Documents to Read First

Before writing any code, read these documents in this exact order:

1. **`docs/PHASE_3_HANDOFF.md`** — Complete handoff document with everything done in Phase 1 & 2, all Phase 3 task specs, architecture rules, technical patterns, file structure, and verification commands. THIS IS YOUR PRIMARY REFERENCE.

2. **`.claude/plans/mellow-inventing-rocket.md`** — The master UX Overhaul plan with full context including Kova/Sandcastles insights, design rationale, and competitive analysis.

3. **`.claude/rules/architecture.md`** — NON-NEGOTIABLE architecture rules (source isolation, confidence ceilings, pipeline order, Gemini JSON mode).

4. **`.claude/rules/implementation.md`** — Implementation discipline (sequential tasks, commit format, testing requirements).

5. **`CLAUDE.md`** — Project entry point and session checklist.

### What to Implement

Phase 3 has 5 tasks (3F is explicitly v2 — do NOT implement it):

**Task 3A: Creator Analysis Mode**
- Accept 3-5 YouTube URLs, run specialized extraction for style analysis
- Output Creator Style Profile document (hook patterns, narrative structure, vocabulary fingerprint, aesthetic keywords, tone descriptors)
- "Save as style guide" button saves to existing `style_guides` table
- Creator analysis intent already detected by `intent-router.ts`

**Task 3B: Content Structure Suggestions (Five-Act Story Arc)**
- Add "Suggested Structure" section to Creator Brief based on topic type
- 4 structure archetypes: Cold Open (investigation), Multiple Perspectives (controversy), Hero's Journey (profile), Discovery (explainer)
- Backend logic in `creator_brief_stage.py`, new `StoryArcCard.tsx` frontend component

**Task 3C: Active Wait with Narrated Loading States**
- Replace generic progress labels with narrated stage descriptions
- Add partial result previews as stages complete (source summary, top claims, themes, hook preview)
- "While you wait" suggestions
- Modify existing `JobProgressPanel.tsx`, create `PartialResultsPreview.tsx`

**Task 3D: Progressive Document Reveal**
- Creator Brief (Doc 3) renders full-width as hero at top of job detail page
- Supporting docs (Doc 2, 1, 0, 4) in collapsed accordion below
- Toggle to switch back to grid view
- Uses existing `CollapsibleSection.tsx` pattern

**Task 3E: Export & Sharing Redesign**
- Persistent export toolbar at top of document viewer
- Section-level copy buttons
- "Share snippet" per section (formatted for social, 280 chars)
- Export/share backend routes already exist (`export_routes.py`, `share_routes.py`)

### Implementation Rules

1. **Work in order:** 3A → 3B → 3C → 3D → 3E
2. **Commit after each task** with format: `Phase 3.X: [description]`
3. **Verify after each task:** `cd frontend && npm run lint && npm run build`
4. **For backend changes also run:** `cd /Users/maz/Documents/github/Research_Agent && source venv/bin/activate && pytest`
5. **Gemini response_schema Pydantic models MUST have NO default values** — Gemini rejects them
6. **GeminiClient usage:** `client.generate_json(prompt, model="gemini-2.0-flash", temperature=0.4, response_schema=Model)` returns `{"data": {...}, "cost": float, "error": str}`
7. **Frontend dev port is 3002**, not 3000
8. **`NEXT_PUBLIC_DISABLE_AUTH=true`** for dev mode auto-authentication

### What NOT to Do

- Do NOT implement 3F (Inline Edit) — it's marked v2
- Do NOT modify pipeline architecture (source isolation, confidence ceilings, stage order)
- Do NOT skip tasks or work out of order
- Do NOT delete files — archive to `backend/archive/` instead
- Do NOT start Phase 4 or any work beyond Phase 3 without asking me first
