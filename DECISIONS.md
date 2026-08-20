# Research Agent — Architectural Decision Records

**Purpose:** Document key architectural decisions and their rationale. These decisions are FINAL unless explicitly changed by the project owner.

---

## ADR-001: Replace Gemini 4-Pass with Semantic Pipeline

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
The existing video analysis pipeline uses a Gemini 4-pass approach:
- Pass 1: Extraction (clips/quotes)
- Pass 2: Structure Analysis (ContentBlueprint)
- Pass 3: Gap Analysis
- Pass 4: Research Starter

This doesn't align with RASS specification which requires:
- Source isolation during extraction
- Verification stage
- 3-document output model

### Decision
**Replace the Gemini 4-pass pipeline with the semantic pipeline.** Remove the old pipeline immediately without a transition period.

### Rationale
1. RASS requires source isolation — 4-pass doesn't enforce it
2. RASS requires verification stage — 4-pass doesn't have one
3. Semantic pipeline provides provenance tracking
4. Maintaining two pipelines is technical debt
5. 4-pass doesn't support multiple source types

### Consequences
- Existing output format changes
- Old `run_gemini_video_job` task removed
- No rollback without code restoration

---

## ADR-002: Six Analysis Modes

**Date:** 2026-01-13
**Status:** ACCEPTED (AMENDED 2026-01-15 — see ADR-013)
**Deciders:** Project Owner

### Context
Different source types have different content availability and verification capabilities.

### Decision
Implement **six analysis modes** with mode-specific extraction and confidence ceilings:

| Mode | Source Type | Confidence Ceiling | Quotes |
|------|-------------|-------------------|--------|
| `transcript_grounded` | YouTube with transcript | HIGH | Yes |
| `caption_grounded` | YouTube with captions | MEDIUM | Yes (approximate) |
| `video_only` | YouTube, no text | LOW | No |
| `text_provided` | User-pasted content | MEDIUM | Yes (unverified)* |
| `ocr_extracted` | Screenshot | MEDIUM | Yes (unverified)* |
| `article_fetched` | Article URL | HIGH | Yes |

> *\*Amended 2026-01-15: See ADR-013 for quote policy update.*

### Rationale
1. Different sources warrant different confidence levels
2. Can't quote from sources without verifiable text
3. Explicit mode prevents wrong assumptions
4. Mode-specific prompts prevent hallucination

### Consequences
- Six prompt templates required
- Mode selector logic required
- Validation must check mode-specific rules

---

## ADR-003: Source Isolation During Extraction

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
When analyzing multiple sources, there's risk of cross-contamination if the LLM sees multiple sources at once.

### Decision
**Each source is extracted in a separate, isolated LLM call.** The model never sees other sources during extraction. Cross-source analysis only happens in synthesis.

### Rationale
1. Prevents cross-source hallucination
2. Guarantees provenance accuracy
3. Makes validation simpler
4. Required by RASS Section 4.3
5. Added to INDEX.md as non-negotiable rule

### Consequences
- More LLM calls (one per source)
- Slightly higher cost
- Cannot identify cross-source patterns during extraction (by design)

---

## ADR-004: Four-Document Output Model

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Users need different types of information: metadata, directions, analysis, and optionally creative interpretation.

### Decision
Produce **three core documents** plus one optional:

| Doc | Name | Purpose |
|-----|------|---------|
| Doc 0 | Source Ledger | What was analyzed, provenance |
| Doc 1 | Jump-Start | Gaps, next steps, search suggestions |
| Doc 2 | Semantic Brief | Themes, key points, tensions |
| Doc 3 | Producer Packet | Creative interpretation (optional) |

### Rationale
1. Separation of concerns
2. Doc 3 is creative layer that doesn't contaminate research
3. Added to INDEX.md and RASS.md

### Consequences
- Three document templates required (plus optional fourth)
- Assembly stage must produce all three
- Storage must accommodate all documents

---

## ADR-005: Producer Packet Gating

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Producer Packet (Doc 3) is creative interpretation and requires sufficient input.

### Decision
Producer Packet requires:
1. 4+ sources in job
2. At least 1 high-confidence source
3. Job status = complete
4. User explicitly requests it

### Rationale
1. Prevents low-quality creative output
2. Ensures sufficient input for meaningful interpretation
3. User opt-in for creative layer

### Consequences
- Gating logic required
- Separate API endpoint
- Cannot auto-generate

---

## ADR-006: Deep Research Booster as Optional Add-On

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
After initial analysis, users may want deeper research directions.

### Decision
Booster is:
1. Optional — user explicitly triggers
2. 4-stage pipeline
3. Appends to Doc 1 only
4. Does not modify Docs 0/2

### Rationale
1. Not everyone needs deep research
2. Separate from core analysis
3. RASS Section 4.7 defines this

### Consequences
- Separate API endpoint
- Separate Celery task
- Results append to existing Doc 1

---

## ADR-007: Evolving Jobs (Addendum Pattern)

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Users may discover new sources after initial analysis.

### Decision
Use **addendum pattern**:
- Original analysis preserved
- New sources extracted normally
- Cross-reference compares new to existing
- Addendum appended with clear marking

### Rationale
1. Original analysis preserved
2. Clear what's new vs original
3. Lower risk than full re-synthesis

### Consequences
- Cross-reference stage required
- Addendum template required
- Docs grow over time

---

## ADR-008: Validation with Quote Verification

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
LLMs can hallucinate quotes that don't exist in source material.

### Decision
For `transcript_grounded` and `article_fetched` modes, **verify extracted quotes exist in source text**.

### Rationale
1. Catches hallucinated quotes
2. No additional LLM call needed
3. High value for research accuracy
4. RASS Section 4.4 requires this

### Consequences
- Must have transcript text available
- Fuzzy matching needed
- Warning (not error) if quote not found

---

## ADR-009: Archive Dead Code, Don't Delete

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Audit found unused integration clients and deprecated code.

### Decision
**Archive to `backend/archive/`** rather than delete.

### Rationale
1. May need reference for future features
2. Git history isn't enough
3. Clear separation from active code

### Consequences
- Archive directory in codebase
- Must not import from archive

---

## ADR-010: Gemini 2.5 Pro as Primary LLM

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Multiple LLM options available.

### Decision
**Gemini 2.5 Pro** is the primary LLM for all pipeline stages.

Configuration:
- Extraction: temperature 0.1
- Synthesis: temperature 0.2
- Booster: temperature 0.4
- Producer: temperature 0.3-0.5

Use JSON mode with response_schema.

### Rationale
1. Already integrated
2. Native JSON mode
3. Good price/performance
4. Direct YouTube video analysis

### Consequences
- All prompts optimized for Gemini
- Must use response_mime_type: application/json

---

## ADR-011: Prompt Requirements (Five Components)

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Prompts need guardrails to prevent hallucination and ensure consistency.

### Decision
All semantic extraction prompts MUST include:
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema

### Rationale
1. Prevents model from guessing identity
2. Enforces confidence limits
3. Allows sparse but accurate output
4. Structures extraction logically
5. Ensures valid JSON output

### Consequences
- All prompts must be audited
- Added to INDEX.md as non-negotiable
- Added to RASS.md Section 6.3

---

## ADR-012: Spec Documents Updated

**Date:** 2026-01-13
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Analysis found INDEX.md and RASS.md were missing critical rules.

### Decision
Update both documents:

**INDEX.md additions:**
- Source Isolation Rule
- Six Analysis Modes table
- Doc 3 definition
- Prompt Requirements section

**RASS.md additions:**
- Source Isolation in Section 4.3
- All 6 modes in Section 4.2
- Prompt requirements in Section 6.3
- Doc 3 in Section 3

### Rationale
1. Constitution must be complete
2. Spec must match implementation requirements
3. Prevents future drift

### Consequences
- New spec documents deployed in Phase 0
- All code must align with updated specs

---

## ADR-013: Quote Policy for User-Provided Content

**Date:** 2026-01-15
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
ADR-002 originally prohibited quotes for `text_provided` and `ocr_extracted` modes, reasoning that user-provided content cannot be independently verified.

However, in practice:
1. Users paste content expecting quotes to be extracted
2. Screenshots contain visible text users want quoted
3. Omitting quotes reduces system utility without clear security benefit
4. System CAN extract quotes — it just can't verify authenticity

### Decision
**Allow quotes for TEXT_PROVIDED and OCR_EXTRACTED modes, marked as unverified.**

Updated rules:
- `text_provided`: Quotes allowed, marked `unverified: true`
- `ocr_extracted`: Quotes allowed, marked `unverified: true`
- All other modes: Unchanged

Quote output includes:
```json
{
  "quote": "...",
  "unverified": true,
  "verification_note": "Quote extracted from user-provided content. Authenticity not verified by system."
}
```

### Rationale
1. Better UX — users expect quotes from pasted content
2. No security impact — system never claimed to verify user content
3. Clear labeling — `unverified` flag prevents false confidence
4. Reversible — can tighten policy later if needed

### Consequences
- Amends ADR-002 quote policy table
- Validation allows quotes for these modes
- All quotes from these modes flagged as unverified
- INDEX.md updated to match
- Mode spec files already aligned (this ADR formalizes the decision)

---

## ADR-014: Legacy Pipeline Removal

**Date:** 2026-01-19
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
The codebase contained unreachable legacy code:
- Topic-based discovery stages (1-6.5) — never called from current pipeline
- Google Drive integration — replaced by Supabase Storage
- Slack integration — no longer supported
- Legacy search clients (Exa, Perplexity, Serper, Tavily, Reddit) — used only by removed stages

### Decision
**Remove all unreachable legacy code. Keep only user-input semantic pipeline.**

Removed:
- `backend/integrations/slack.py`
- `backend/integrations/google_drive_docs.py`
- `backend/integrations/exa_client.py`
- `backend/integrations/perplexity_client.py`
- `backend/integrations/serper_client.py`
- `backend/integrations/tavily_client.py`
- `backend/integrations/reddit_client.py`
- `backend/pipeline/stages/planning.py`
- `backend/pipeline/stages/discovery.py`
- `backend/pipeline/stages/youtube.py`
- `backend/pipeline/stages/web_capture.py`
- `backend/pipeline/parallel_executor.py`

Kept:
- All semantic pipeline stages
- Config fields for potential future use (Perplexity, Tavily, etc.)
- Reddit as source type (user can provide Reddit URLs/text)

### Rationale
1. Dead code creates maintenance burden
2. Legacy pipeline was unreachable from any active route
3. Drive/Slack had no active callers
4. Keeping config fields is low-cost future-proofing

### Consequences
- ~1,800 lines of dead code removed
- Deprecated endpoints return 410 Gone
- Tests updated to verify 410 responses
- Compile check passes

---

## ADR-015: Constitution Finalization & Single Authority

**Date:** 2026-01-20
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Multiple documents claimed authority ("authoritative", "single source of truth", "constitution"). This caused documentation drift and confusion for Claude agents about which documents to follow.

### Decision
**Establish `docs/authoritative/INDEX.md` as the SOLE pointer-of-pointers (repo constitution).** All other documents must defer to it or be archived.

Locked decisions in constitution:
1. Semantic-only pipeline (no legacy execution)
2. Storage Strategy Option B (artifacts JSON + Supabase Storage)
3. Transcript chain: Supadata → Whisper → YouTube captions → video_only
4. Quote vs Observation policy per mode (video_only = NO quotes)
5. Document alias mapping (Doc 0/1/2/3 ↔ 20/21/22/3)
6. Failure semantics (graceful degradation, warnings not fatal)
7. Enforcement surfaces (code file paths documented)

Archive structure:
- `docs/_archive_do_not_read/` — Superseded docs with LEGACY banner
- `.claude/rules/authority.md` — Ignore rules for archived folders
- `CLAUDE.md` — Thin pointer only (58 lines)

### Rationale
1. Single source of truth prevents drift
2. Claude agents need clear authority hierarchy
3. Archived docs prevent accidental implementation from old specs
4. Thin CLAUDE.md prevents rule duplication

### Consequences
- INDEX.md is the sole constitution
- CLAUDE.md no longer contains rules (just pointers)
- Context_Handoff.md, Database_Schema.md demoted to reference
- Active Docs/ archived to docs/_archive_do_not_read/
- New Claude sessions must read INDEX.md first

---

## ADR-016: Artifacts Must Use Partial Merge in Atomic Updates

**Date:** 2026-01-21
**Status:** ACCEPTED
**Deciders:** Project Owner + Claude Code

### Context
Job completion (`stage_10_completion`) was calling `update_job()` with both `partial_outputs=` and `artifacts=`. When `partial_outputs` is set, the state layer routes to `_update_job_atomic()` which supports JSONB merges. However, `_update_job_atomic()` only accepts `partial_artifacts=` (merge semantics), not `artifacts=` (full replace). The `artifacts=` parameter was silently dropped, leaving the artifacts JSONB column empty `{}` for all production jobs.

### Decision
**When atomic update path is triggered, use `partial_artifacts=` for artifact data, never `artifacts=`.**

Implementation:
1. `stage_10_completion` now passes `partial_artifacts=artifacts_dict` instead of `artifacts=Artifacts(...)`
2. Guard added in `SupabaseJobStore.update_job()`: if `needs_atomic=True` AND `artifacts!=None`, raise `ValueError`
3. Tests added to prevent regression

### Rationale
1. Atomic path (`_update_job_atomic`) only accepts merge semantics via `partial_*` params
2. Silent data loss is worse than loud failure — guard makes misuse obvious
3. `partial_artifacts` merge is semantically correct for completion stage (additive)
4. No behavior change for callers using `artifacts=` without atomic triggers

### Consequences
- `stage_10_completion` now correctly persists artifacts to database
- Developers will get clear error if they misuse `artifacts=` with atomic path
- Frontend can now discover documents via `artifacts` JSONB column
- No migration needed — future jobs will have correct data

---

## ADR-017: Iteration Loop for Completed Jobs

**Date:** 2026-01-23
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Users often want to refine research after initial completion — more sources, deeper analysis, or different perspectives. Previously, the only option was to create a new job.

### Decision
**Implement Iteration Loop that re-runs semantic pipeline with user-selected mode on completed jobs.**

Iteration modes:
| Mode | Description |
|------|-------------|
| `more_sources` | Add more sources to existing research |
| `deeper` | Deeper analysis of existing content |
| `different_angle` | Explore from different perspective |
| `custom` | User-provided custom prompt |

Each iteration:
1. Creates new `IterationBundle` with unique `iteration_id` (format: `it_XXXX`)
2. Re-runs extraction → synthesis → assembly pipeline
3. Stores outputs in `artifacts.iterations[]` array
4. Does NOT modify baseline documents (Doc 0/1/2)

TOCTOU protection:
- `iteration_claim` column with UNIQUE constraint
- Worker claims job atomically before processing
- Prevents duplicate iterations from double-clicks

### Rationale
1. Users shouldn't recreate jobs to refine research
2. Baseline preserved — iterations are additive
3. Version switching allows comparison
4. TOCTOU protection prevents race conditions
5. Aligns with Evolving Jobs pattern (ADR-007)

### Consequences
- New API endpoint: POST `/jobs/{job_id}/iterate`
- New Celery task: `run_iteration_task`
- Frontend iteration selector component
- Database migration for `iteration_claim` column
- Each iteration adds ~same cost as original job

---

## ADR-018: Progressive Disclosure UI Pattern

**Date:** 2026-01-23
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
The dashboard was becoming overloaded with Level 0/1/2 expansion, document accordions, action buttons, and iteration controls all in one place. This created cognitive overload, especially for users with ADHD.

### Decision
**Implement progressive disclosure with dedicated Job Detail Page.**

UI layers:
| Layer | Location | Content |
|-------|----------|---------|
| L0 | Dashboard | Job list, titles, status badges |
| L1 | Dashboard card | Summary, task badges, click to navigate |
| L2 | Job Detail Page | Full artifact grid, document viewing, all actions |

Dashboard simplification:
- Remove document accordions from dashboard
- Remove action buttons from dashboard cards
- Add mini task badges (booster/iteration/producer status)
- Card click navigates to `/jobs/[id]`

Job Detail Page features:
- Full header with back navigation
- Active task banners with progress
- 6-card artifact grid (Doc 0/1/2/3, Booster, Iteration)
- Document viewer modal
- Iteration dialog
- Delete confirmation
- Polling for running tasks

### Rationale
1. Reduces cognitive load on dashboard
2. Provides clear information hierarchy
3. Detail page has space for full controls
4. Better mobile experience (less cramped)
5. Follows progressive disclosure best practices

### Consequences
- New route: `/jobs/[id]`
- New components: ArtifactCardGrid, TaskBadges
- Dashboard cards become simpler navigation targets
- Users must click through to take actions
- Better scalability as features are added

---

## ADR-019: Tier 5 Content Generation — Three User-Triggered Documents

**Date:** 2026-03-15
**Status:** ACCEPTED
**Deciders:** Project Owner

### Context
Tiers 1-4 produce Doc 0-4 (auto + user-triggered). Users need derivative content: blog posts, video scripts, and social media posts — all grounded in the same research data with full provenance.

### Decision
**Add three user-triggered document types following the established Doc N pattern:**
- **Doc 5 (Script):** Spoken-word video script with tone/length controls and optional voice mimicry
- **Doc 6 (Social Kit):** Multi-platform social posts (Twitter 280-char validation, LinkedIn, Instagram, YouTube, TikTok, Newsletter)
- **Doc 7 (Blog Post):** Long-form SEO article with meta description and keyword optimization

All follow the established pattern: POST endpoint → Celery task → LLM stage → version_manager storage.

### Consequences
- 3 new API endpoints, 3 new Celery tasks, 3 new pipeline stages
- version_manager DOC_TYPES expanded to doc_0 through doc_7
- ArtifactCardGrid shows 3 new cards in the UI
- Temperature varies by document type (0.3-0.5)

---

## ADR-020: Voice Mimicry via Profile Analysis

**Date:** 2026-03-15
**Status:** ACCEPTED
**Deciders:** Project Owner

### Decision
**Voice mimicry implemented as persistent Supabase-stored profiles, not inline analysis.** Users create profiles from video URLs, analyzed via LLM. Profiles inject voice instructions into Script Writer prompt and bump temperature from 0.5 to 0.55.

### Consequences
- New `voice_profiles` Supabase table with RLS (migration 027)
- CRUD API at `/voice-profiles`
- `VoiceProfile.to_voice_instructions()` generates the prompt injection block

---

## ADR-021: Inline Edit as Iterate Mode

**Date:** 2026-03-15
**Status:** ACCEPTED
**Deciders:** Project Owner

### Decision
**Inline editing implemented as a new mode (`inline_edit`) in the existing iterate system.** Reuses iterate infrastructure (Celery task, version management, progress tracking) rather than creating a separate API.

### Consequences
- `inline_edit` mode requires `doc_type`, `section_id`, `edit_instruction`
- Section spliced back into full document, stored as new version
- Temperature 0.3 for surgical precision
- Frontend uses EditableSection wrapper around renderer sections

---

## ADR-022: Complete Frontend Overhaul — App Router + shadcn/ui

**Date:** 2026-03-18 (updated 2026-03-19)
**Status:** IMPLEMENTED
**Deciders:** Project Owner

### Context
Current frontend uses Next.js Pages Router with inline Tailwind, no design system, and inconsistent component patterns. Dashboard is overloaded (945-line dashboard.tsx). Job detail page (510 lines) mixes document rendering with controls. No mobile optimization.

Owner found design inspiration in okara.ai's AI CMO dashboard: multi-column layout, left sidebar, center analytics, right feed panel, dark terminal aesthetic.

### Decision
**Complete frontend overhaul with:**

1. **App Router migration** — Replace `pages/` with `app/` directory entirely (big-bang, no incremental)
2. **shadcn/ui** — Copy-paste component library with CSS variable theming
3. **Dark-only theme** — 5 surface levels (`#0a0a0f` → `#2a2a38`), CSS vars structured for future light mode
4. **3-column job detail** — Left (job meta + nav), center (documents), right (activity + chat Sheet)
5. **Multi-step wizard** — Replaces single-page job creation form
6. **TanStack Query** — Replaces manual Zustand polling for data fetching
7. **Zustand retained** — UI state only (drawer open, active tab, etc.)
8. **next-themes** — Replaces custom ThemeContext.tsx
9. **Framer Motion** — Page transitions only; Tailwind for micro-interactions
10. **Document output fidelity** — All Doc 0-7 content rendered at full detail, no simplification

### Design System
- **Surfaces:** surface-0 (#0a0a0f), surface-1 (#12121a), surface-2 (#1a1a25), surface-3 (#222230), surface-hover (#2a2a38)
- **Accents:** blue (primary), purple (AI/synthesis), green (success/HIGH), orange (warning/MEDIUM), red (error), amber (Creator Brief)
- **Text:** primary (#f5f5f5), secondary (#a1a1aa), muted (#71717a), disabled (#52525b)
- **Font:** Inter (all weights), monospace for entity IDs
- **Icons:** Lucide (outline style), no emojis
- **Borders:** default (#27272a), hover (#3f3f46)

### Mockups
10 interactive HTML mockups at `frontend/public/mockups/`:
01-dashboard, 02-job-detail-3col, 03-job-creation-wizard, 04-document-viewer, 05-login, 06-queue, 07-settings, 08-admin, 09-transcripts-shared, 10-component-library

### Rationale
1. Pages Router limits server-component adoption and layout composition
2. No design system → inconsistent UI across 14 pages
3. Manual polling → stale data, unnecessary re-renders
4. Dashboard overload → progressive disclosure (ADR-018) needs proper 3-column layout
5. Mobile experience poor — sidebar + bottom nav pattern is standard
6. shadcn/ui provides accessible, customizable components without vendor lock-in

### Consequences
- 14 pages migrated to `app/` directory
- 27 component directories refactored
- 6 Zustand stores adapted for client/server boundary
- All existing Tailwind classes remapped to CSS variable tokens
- ~44h estimated effort across 7 phases
- No backend changes required (API stays identical)
- E2E tests deferred to separate effort

---

## Decision Index

| ADR | Title | Status |
|-----|-------|--------|
| 001 | Replace 4-Pass with Semantic Pipeline | Accepted |
| 002 | Six Analysis Modes | Accepted (Amended) |
| 003 | Source Isolation During Extraction | Accepted |
| 004 | Four-Document Output Model | Accepted |
| 005 | Producer Packet Gating | Accepted |
| 006 | Deep Research Booster as Optional | Accepted |
| 007 | Evolving Jobs (Addendum Pattern) | Accepted |
| 008 | Validation with Quote Verification | Accepted |
| 009 | Archive Dead Code, Don't Delete | Accepted |
| 010 | Gemini 2.5 Pro as Primary LLM | Accepted |
| 011 | Prompt Requirements (Five Components) | Accepted |
| 012 | Spec Documents Updated | Accepted |
| 013 | Quote Policy for User-Provided Content | Accepted |
| 014 | Legacy Pipeline Removal | Accepted |
| 015 | Constitution Finalization & Single Authority | Accepted |
| 016 | Artifacts Must Use Partial Merge in Atomic Updates | Accepted |
| 017 | Iteration Loop for Completed Jobs | Accepted |
| 018 | Progressive Disclosure UI Pattern | Accepted |
| 019 | Tier 5 Content Generation — Three User-Triggered Documents | Accepted |
| 020 | Voice Mimicry via Profile Analysis | Accepted |
| 021 | Inline Edit as Iterate Mode | Accepted |
| 022 | Complete Frontend Overhaul — App Router + shadcn/ui | Accepted |

---

**All decisions are FINAL unless explicitly changed by project owner.**

---

## Decision 023: Claim Graph + Briefing Architecture — Owner-Approved Build (2026-08-15)

**Status:** Accepted (project owner, in-session, 2026-08-15)

The active build is the Claim Graph + Research Briefing architecture:
**`plans/260814-claim-graph-briefing/`** (spec.md · EXECUTION-PLAN.md · MODEL-DOSSIER.md ·
KICKOFF-PROMPT.md). For the duration of this build, that folder is the owner-approved phase plan,
superseding the Product Viability Overhaul phase list in PROGRESS.md.

**What this decision explicitly supersedes (owner-approved changes to previously-FINAL rules):**
- **Architecture Rule 12–13 (document structure):** Doc 1 (Jump-Start) and Doc 2 (Semantic Brief)
  merge into the Research Briefing, rendered from a canonical Claim Graph; all other documents
  become projections of the graph. Doc numbering is retired in USER-FACING output (internal IDs remain).
- **Architecture Rule 15–16 (LLM config):** the model lineup and per-stage config now come from
  EXECUTION-PLAN §1 (env-driven; Sonnet 5 distillation; Gemini 3.6-flash extraction with
  thinking_level minimal; judge contest). Note newer models reject temperature entirely — Rule 16's
  temperature table applies only where a model accepts it.
- **research-agent.md cost guidance** ("GPT-4o-mini for extraction") — stale; superseded by the
  MODEL-DOSSIER lineup.

**What REMAINS law and the build must respect:** source isolation (Rule 1–3) · confidence ceilings
(Rule 4–6) · the five prompt guardrail components (Rule 7–8, adapted per model) · provenance chain
(Rule 9–11, 14a — the claim graph STRENGTHENS it) · document versioning (13b) · implementation
rules (phases, tests, commit discipline) · empty-output permission (never invent to fill arrays).

**Authority note:** where `plans/260814-claim-graph-briefing/EXECUTION-PLAN.md` explicitly changes
a rule, this Decision is the owner approval the constitution requires. Everything the plan does not
explicitly change still answers to `docs/authoritative/INDEX.md`.

## Decision 024: Briefing Format v2 — Named Stories, Details Woven In (2026-08-16)

**Status:** Accepted (project owner, in-session, 2026-08-16, at the P2 gate)

Owner read the P2 fixture Briefing and redirected the format. The claim-unit
layout (15 units, repeated field anatomy, argument spine) reads as a research
dissertation and fails the document's two real jobs, which the owner defined:

1. **Teach the topic** well enough to hold a conversation about it.
2. **Enable story-finding** — see the threads, the connections, and the
   openings, WITHOUT the document choosing an angle or hiding anything.

Format decided by mockup comparison (three shapes offered; owner chose B):

- **Named stories, said in place.** Sections whose headers are full sentences
  that carry meaning on their own. Every section self-contained and readable
  in any order.
- **NO cross-references, ever.** Nothing is called "thread 2" or "the claim
  above". When a connection matters it is re-said in plain words where the
  reader is standing. (Owner stopped reading at "Thread 4 sits underneath
  threads 2 and 3" — numbered references are a hard failure.)
- **Details ride inside the explanation.** The concrete example is told in
  full where the claim is made (the owner's example: the Se7en remaster story
  told as a story, not "remasters flatten old films" + a detail parked in a
  list). Never split an abstraction from its example.
- **Connections are first-class.** Things sitting between sources that no
  single source assembles are sections of their own.
- **The document never picks the angle.** It maps what everyone already does
  with the topic and names the unopened doors; choosing is the owner's job.
- Confidence is woven into sentences, not badges. Evidence handling follows
  the earlier voice decision (person telling a person; research register is a
  lint error).

The Claim Graph remains the canonical provenance layer (claims with receipts,
holes, story goods) — projections P4-P7 still consume it. What changes is that
distillation now ALSO produces the telling layer (story sections, noticings,
the landscape read), and the Briefing renders the telling layer.

Supersedes the spec Section 3 rendering (map page → claim units on spine).
Spec Sections 1, 2, 4, 5 stand.

## Decision 025: The Hybrid Briefing — Locked Format (2026-08-18)

**Status:** Accepted (project owner, in-session, 2026-08-18, after two-topic validation)

The Briefing format is now FIXED, validated on two topics (films fixture,
Hawara labyrinth job c5d32615) and iterated through owner review on a live
mockup ("The Hawara Briefing" artifact + "The Hawara Sources" vault). The
owner's verdict on the Section-1 read: approved on the fresh topic — the
format generalizes. This supersedes D-024's rendering as the reading
document; D-024's telling-layer models and the Claim Graph provenance layer
remain underneath.

**The document = 8 sections, in this order:**
1. **The Read** — the argument told once, linear, from RAW source text (never
   claim atoms). Judgment allowed: rank the pile, point at the heat, stage
   the fights. The only section built for top-to-bottom reading.
2. **The Players** — consolidated cast cards, collapsible to name + role.
   RULE: a name mentioned in 2+ sections gets a card (lintable); a one-off is
   introduced inline where it appears ("Eric Uphill, the Middle Kingdom
   specialist, argued…").
3. **The Record** — dated chronology, every entry cited, each with a light
   "More" context dropdown (2–4 sentences).
4. **The Files** — the lossless layer (Human-Research-Brief spec): facts
   merged by SUBJECT, never dropped as "unimportant"; true duplicates merged
   (shingle detector, not model judgment); disagreements stay visible; each
   file opens with evidence-status chips. Coverage enforced MECHANICALLY
   against the harvest inventory — never by the model grading itself.
5. **Disputed & Uncertain** — each dispute: title + one-line holders + status
   chip, opening into "Full case, both sides" with each side's actual
   evidence, cited. Chip vocabulary: established / contested / single source /
   unverifiable / belief migration. Never resolved unless the sources resolve it.
6. **Details & Anecdotes** — the texture bin with per-item Context dropdowns.
   Exists so small material cannot vanish in synthesis.
7. **Info Gaps** — what the corpus does NOT contain, phrased as go-get-it
   instructions; doubles as the expand-pass shopping list.
8. **Source Trail** — every source + its one unique contribution; every SRC id
   links to the raw text in the companion vault.

**Companion: the Source Vault** — full unedited raw texts of every source,
anchor-linked per SRC id, generated 100% BY CODE from doc_0 (no model).

**Locked writing rules** (enforcement lives in lint/repair, never the writer):
- Named citations in prose ("Johanna's video (SRC_4) adds…"), bare IDs only
  in trailing citation tags.
- Staging disclosure: when a source dramatizes/performs a fact, say so and
  name where the underlying fact lives (STORY/THEORY/REALITY doctrine).
- One-hearing clarity: compression that forces a re-read is a defect.
- No cross-references (D-024) except inside Section 1, where linearity
  replaces self-containment.
- The document never picks the owner's angle.

**Output medium:** canonical artifact = structured JSON (sections, players,
disputes-with-both-sides, timeline+context, files, gaps, source refs).
HTML is the primary render — a deterministic code renderer (like the vault
generator), because the format's dropdowns/chips/anchors exceed Markdown.
Markdown/Drive exports are lossy secondary renders when needed. LLM calls
write CONTENT FIELDS only; all assembly, linking, and rendering is code.

**Effect on legacy docs:** the Briefing + Vault replace Doc 1 and Doc 2 as
the reading surface (already merged on paper by D-023) and absorb Doc 0's
reading role (Doc 0 remains the canonical data). Doc 3 (Creator Brief) is
NOT part of the Briefing and conflicts with "the brief informs, never
performs" — its retirement or reshaping is a separate owner decision, not
made here.

### Addendum to D-025: the cast is capped at 14 (2026-08-19)

**Status:** Accepted (project owner, in-session, 2026-08-19)

D-025 says a name mentioned in 2+ sections gets a card in The Players. On the
first end-to-end build (labyrinth job c5d32615, 16 sources, 34,501 words of
generated prose) that rule returned **61 names**. Reading the list showed the
rule was sound and the input was not: it contained places and monuments that
recur without ever acting (Giza Plateau, Great Pyramid, Lake Moeris, Middle
Kingdom, City of Crocodiles), and the same person arriving under several forms
(De Cordier and Louis De Cordier; Ministry of Tourism and Egypt's Ministry of
Tourism; William Brown and Bill Brown). A cast of 61 is an index, not a cast.

**What changes:**

1. **The threshold stands.** 2+ distinct sections still qualifies a name.
2. **Aliases count once**, merged by token containment into the fullest form.
3. **A player has to act.** A name never shown doing something is a place, and
   places belong in the prose, not the cast.
4. **The cast is capped at 14**, selected deterministically: rank by distinct
   section count, tie-break by total mentions across every alias, then by the
   name itself, so the result never depends on dict order or prose chunking.
5. **Every name below the line follows the one-off rule** — introduced inline
   wherever it appears ("Eric Uphill, the Middle Kingdom specialist, argued…")
   so a reader never meets a name cold. This is lint-enforced, alongside the
   existing rule that a name above the line without a card is an error.

Same corpus after the amendment: 14 cards (Hawass, De Cordier, Akers, Boulter,
Grassi, Cayce, Lloyd, Diodorus, Pomponius Mela, Merlin Burrows, Ghent
University, and the three publications). Implementation:
`backend/pipeline/briefing_routing.py` (`rank_players`, `qualifying_players`,
`below_the_line`) and `backend/pipeline/briefing_lint.py`
(`check_player_cards`, `check_inline_introductions`), both of which read the
same ranking so the lint enforces the rule as applied.

## Decision 026: Quote verification is a span question, not a similarity question (2026-08-19)

**Status:** Accepted (project owner, in-session, 2026-08-19)

A quotation is the source's own words in sequence. The verifier scored fuzzy
string similarity instead, which answers a different question, and the gap
between the two let fabrications through.

**Evidence (labyrinth corpus, job c5d32615).** 144 real quotes taken as
contiguous runs from 12 transcripts, and 144 fabrications built by recombining
words from *each source's own vocabulary* — the hardest case, since the
vocabulary matches perfectly:

| | fuzzy verdict (before) | contiguous span |
|---|---|---|
| real quotes | 1.00, all VERIFIED | 1.00 |
| fabrications | avg 0.60, min 0.49 | avg 0.14, **max 0.25** |

The old implementation's verdicts on those 144 fabrications: 87 flagged,
39 UNCERTAIN, and **18 stamped VERIFIED**. One in eight fabrications built from
a source's own words passed as a confirmed quote.

**What changes:**

1. **The span is the verdict.** VERIFIED means the source contains the quote's
   words as a contiguous run.
2. **Fuzzy is the borderline signal only**, consulted after the span check
   fails, to tell a near-miss from an invention. It must be order-sensitive:
   measured against a 260-word window, token-set ratio scores real quotes and
   word-salad fabrications *both* at 1.00, so partial ratio is used at every
   length.
3. **Three verdicts.** VERIFIED (span), UNCERTAIN (no span, high fuzzy),
   FLAGGED (neither). `LIKELY_HALLUCINATED` is retained as an alias so stored
   documents keep working.
4. **Normalization before matching**: case, smart quotes and dashes,
   punctuation, whitespace. Typography never decides a verdict.
5. **Ellipsis policy**: a quotation that elides material is several spans, each
   verified on its own, and the verdict is the weakest fragment's.
6. **Nothing is deleted.** An unverified quote is marked, not removed, and the
   claim's confidence carries the consequence. Deleting a real quote that a
   transcript mangled is its own kind of damage.
7. **Threshold set from measurement, not taste.** Span ≥ 0.60. On 208 real
   extracted quotes the median span is 1.00 and only 7 fall below the line, all
   long quotes joined across an unmarked elision; on 156 fabrications, none
   reach even 0.55.

**Acceptance (208 real extracted quotes, 156 fabrications):**

| population | before | after |
|---|---|---|
| real extracted quotes | 208 VERIFIED (100%) | 201 VERIFIED (97%), 7 UNCERTAIN, 0 FLAGGED |
| fabrications | 18 VERIFIED, 39 UNCERTAIN, 87 flagged | 0 VERIFIED, 3 UNCERTAIN, 153 FLAGGED |

The 7 legitimate quotes that lost VERIFIED status are kept and marked, not
dropped. Both populations are retained as regression suites
(`backend/tests/test_quote_verification_regression.py`, fixture at
`backend/tests/fixtures/quote_verification_cases.json`).

**Found while measuring, fixed here:** claim `supporting_quotes` carried quote
IDs rather than quote text in 211 of 211 cases, so every claim-level
verification was checking the string "QT_1" against a transcript and failing.
IDs are now resolved to their text before verification. This silently degraded
every claim's confidence and corrupted the verification rate the distillation
prompt reports.

**Out of scope, deliberately.** Nothing here reads meaning. A verbatim span
quoted against its own sense ("I do not believe the labyrinth is intact" cited
as "the labyrinth is intact") or attributed to the wrong speaker passes every
check in this module by construction. Those are semantic questions for an
advisory pass, on the same footing as the grounding gate's optional verifier:
code decides, a model advises, and a model never gates.

### Addendum to D-026: expect fixture confidence to LIFT on re-distillation (2026-08-19)

**Status:** Accepted (project owner, in-session, 2026-08-19)

The films fixture distilled at `verification_rate=0` and therefore at
confidence ceiling 4 rather than 5. That was recorded as a property of the
corpus. It was the `QT_1` bug, and the chain is exact rather than probable:

1. Extraction returns `supporting_quotes` as quote IDs, not text (211 of 211
   on the labyrinth corpus).
2. `verify_quotes_in_extraction` verified the literal string `"QT_1"` against
   the transcript, found nothing, and deleted it.
3. Every claim ended with `supporting_quotes == []`.
4. `calculate_verification_rate` counts a claim as verified when
   `claim.supporting_quotes` is non-empty, so the rate was 0.0 by construction.
5. `confidence_ceiling_grade` drops the cap by one when
   `verification_rate <= 0.0`, producing ceiling 4.

Individual claims were also downgraded to LOW by the extraction stage for
having "no verified supporting quotes", for the same reason.

**Therefore: when the fixtures re-distill, confidence grades will rise and the
ceiling will return to 5. That is the correction landing, not a regression.**
Do not "fix" it back. The numbers recorded in the 08-16/17 handoffs
(`verification_rate=0`, ceiling 4, claims at LOW) describe a pipeline bug, not
the films corpus, and any comparison against those figures as a baseline is
comparing against the defect.

### Addendum to D-026: the fuzzy signal is advisory forever (2026-08-19)

**Status:** Accepted (project owner, in-session, 2026-08-19)

The partial-ratio separation measured here (real quotes min 0.77, fabrications
max 0.71) is a 6-point margin, and margins that thin move with corpus, window
size, and transcription quality. It may never become a gate.

**VERIFIED comes from the span match alone.** Fuzzy exists only to sort a
non-verbatim quote into UNCERTAIN rather than FLAGGED, which changes how the
quote is labelled and never whether it counts as verified. A test asserts this
directly: a quote with a perfect fuzzy score and no contiguous run cannot be
VERIFIED at any threshold.
