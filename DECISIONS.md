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

## Decision 027: the extraction three-way, and what it says about the October migration (2026-08-20)

**Status:** Measured; the lineup change it implies is NOT yet adopted (owner decision pending)

Three extraction models over the same six labyrinth sources, identical
prompts, identical schema, scored on the repaired quote verifier (D-026):

| model | quotes | verified | rate | key points | with numbers | claims | cost | time |
|---|---|---|---|---|---|---|---|---|
| gemini-3.6-flash (lineup default) | 39 | 39 | 100% | 22 | 3 | 35 | $0.030 | 71s |
| gemini-3.1-flash-lite (challenger) | 23 | 22 | 96% | 17 | 0 | 22 | $0.026 | 37s |
| **gemini-2.5-flash (incumbent)** | **294** | **291** | 99% | **52** | **11** | **176** | $0.131 | 580s |

**The incumbent extracts 7.5x more material than the model chosen to replace
it**, at a comparable verified rate. Per verified quote it is also cheaper:
$0.00045 against $0.00077. It is 8x slower, which is the one axis where the
newer model wins.

**This is not a thinking-level artifact.** Raising 3.6-flash from `minimal` to
`high` on the two richest sources produced *fewer* quotes (18 to 13) and took
3x as long, so the density gap is the model.

**Confirmed while testing:** `gemini-3.7-flash` rejects `thinking_level:
minimal` outright ("Thinking level MINIMAL is not supported for this model"),
which is exactly what MODEL-DOSSIER predicted and the reason 3.6 was preferred
over 3.7. The dossier's reasoning was sound; its conclusion rests on a cost
axis that this measurement outweighs.

**Why this matters more than a lineup preference.** The 2.5 line retires
**2026-10-16**. The plan treats that as a migration; on this evidence it is a
capability cliff, and moving to 3.6-flash today would cut extracted material by
roughly 85% before the deadline even arrives. Whatever replaces 2.5-flash has
to be chosen on measured extraction density, not on price per token.

**Not adopted here.** The default stays `gemini-3.6-flash` until the owner
decides, because the choice is a real trade (density against 8x latency, on a
model with eight weeks to live) and because one corpus of six sources is thin
evidence for a lineup change. What this decision fixes is that the question is
now measurable at all: every model slot is env-driven, and the sweep is a
config change.

## Decision 028: gpt-5.6-terra takes the judge slot (2026-08-20)

**Status:** Accepted — decided by local measurement, per EXECUTION-PLAN section 1

`kimi-k2.5` sunsets 2026-08-31 and neither successor has published judge data,
so the slot was decided by running both against constructed ground truth: 40
items from the labyrinth corpus, 20 harvested facts (supported) and 20 of the
same facts altered in one specific way each (unsupported) — a changed figure, a
swapped name from the same corpus, a reversed meaning, or an added specific the
source never gives. Word salad was excluded deliberately; it flatters everyone.

| | **gpt-5.6-terra** | kimi-k2.6 |
|---|---|---|
| Cohen's kappa | **0.900** | 0.550 |
| accuracy | 95% | 78% |
| test-retest (3 runs) | **100%** | 80% |
| position consistency (A/B + B/A) | **100%** (10 pairs) | **0 pairs completed** |
| failed calls | **0 of 120** | 46 of 120 |
| wall clock | 181s | 2,827s |

Both judges caught every corruption type perfectly (figure, attribution,
negation, addition all 1.0). The entire gap is on *supported* items, where
Terra scored 0.90 and kimi-k2.6 scored 0.55.

**An honest caveat on that gap.** A failed call is scored as "unsupported", so
kimi-k2.6's low score on supported items is confounded with its 38% call
failure rate and the two cannot be separated without a rerun that retries.
It does not change the outcome: a judge that cannot return a verdict on
two calls in five is unusable as the audit tier whatever its accuracy would
have been, and it could not complete a single position-bias pair.

**Adopted:** `MODEL_JUDGE=gpt-5.6-terra`. kimi-k2.6 is the documented fallback.
The vendor-pairing rule holds — extraction is Gemini, synthesis is Claude, the
judge is OpenAI — and so does the standing law that the judge is never a Claude
model while Claude does synthesis.

**Method note for anyone re-running this.** Score with kappa, never raw
agreement: on a balanced set, always answering "supported" scores 50% accuracy
and kappa 0.0, and only one of those two numbers says so. Reproducibility is
reported beside kappa and never instead of it, because a judge can be reliably
wrong. Harness: `backend/pipeline/judge_contest.py`, set builder:
`backend/pipeline/faithfulness_set.py`, both covered by tests.

### Addendum to D-027: the Pro tier does not fix it, and chunking does (2026-08-20)

**Status:** Measured. The chunking fix is NOT yet implemented (owner decision pending)

The first three-way only tested the Flash tier, which left the obvious question
open: does paying for Pro restore the extraction density that the 3.x line
lost? Same six sources, same prompts:

| model (thinking) | quotes | verified | key points | with numbers | cost | time |
|---|---|---|---|---|---|---|
| gemini-2.5-flash | **294** | 291 | **52** | 11 | $0.131 | 580s |
| gemini-2.5-pro | 94 | 94 | 32 | 10 | $0.211 | 322s |
| gemini-3.6-flash (minimal) | 39 | 39 | 22 | 3 | $0.030 | 71s |
| gemini-3.7-flash (low) | 33 | 33 | 18 | 3 | $0.028 | 40s |
| gemini-3.6-flash (high) | 28 | 28 | 22 | 6 | $0.024 | 199s |
| **gemini-3.1-pro-preview (low)** | **22** | 22 | 16 | 1 | $0.023 | 137s |

**The Pro tier is the thinnest of all.** 3.1-pro extracted 22 quotes where
2.5-flash extracted 294. Paying more makes it worse, not better, so this is a
generation difference and not a tier one.

**The mechanism, found by shrinking the input.** gemini-3.6-flash on one source
at four input sizes:

| input | words | quotes | quotes per 1,000 words |
|---|---|---|---|
| 40,000 chars | 6,392 | 10 | 1.56 |
| 20,000 chars | 3,495 | 6 | 1.72 |
| 10,000 chars | 1,790 | 5 | 2.79 |
| 5,000 chars | 912 | 6 | 6.58 |
| 2,000 chars | 379 | 4 | 10.55 |

The model returns roughly the same *number* of items whatever it is given. It
is not failing to read the source; it is filling a fixed output quota, and a
longer source simply gets summarized harder. That is why more thinking made it
worse: thinking compresses.

**Which makes the cliff fixable.** Running the same model over the same source
in 5,000-character chunks: **49 verified quotes and 23 key points, $0.026, 70s
serial** (parallelizable), against 10 quotes for the whole-source call and 92
for dying 2.5-flash. Smaller chunks push density higher still. Chunked
extraction costs about the same per source as the incumbent and runs faster.

**What this changes.** The 2026-10-16 retirement is survivable, but not by
swapping a model string: it needs chunked extraction, which is a real change to
the extraction stage and is not implemented here. Until it is, moving to any
3.x model cuts extracted material by 80-90%.

Evidence: `plans/260814-claim-graph-briefing/artifacts/extraction_pro.json`,
`chunk_probe.json`.

## Decision 029: the quota prompt, not a restructure (2026-08-20)

**Status:** Accepted — the prompt fix is adopted; chunked extraction is NOT built

D-027 found that every Gemini 3.x model returns a roughly fixed *number* of
items whatever it is handed, so a long source is summarized harder. Before
restructuring the extraction stage, the cheap counter-test: state the quota in
the prompt, scaled to the source's length, and change nothing else.

**Counter-test, whole source, no chunking:**

| model | source | plain | with quota | change |
|---|---|---|---|---|
| gemini-3.6-flash | SRC_3 (6,392w) | 6 quotes | **40** | 0.94 → 6.26 per 1,000w |
| gemini-3.6-flash | SRC_16 (6,750w) | 4 quotes | **53** | 0.59 → 7.85 per 1,000w |
| gemini-3.1-pro-preview | SRC_3 | 3 quotes | 5 | 0.47 → 0.78 |
| gemini-3.1-pro-preview | SRC_16 | 3 quotes | 2 | 0.44 → 0.30 |

Chunked extraction reached 7.67 per 1,000 words on the same source. **The
prompt reaches the same density with no restructuring**, so the quota is
adopted and chunking is not built. The Pro tier ignores the instruction
entirely, which finishes the case against it for extraction.

**Three-way re-run on the winning strategy, plus a harvest-style leg** (six
sources, 21,251 words):

| strategy | quotes | verified | units | density | cost | time |
|---|---|---|---|---|---|---|
| **gemini-3.6-flash + quota** | **182** | 182 (100%) | 32 KPs | **8.56/1,000w** | $0.054 | 141s |
| gemini-2.5-flash + quota | 124 | 124 (100%) | 24 KPs | 5.84/1,000w | $0.092 | 746s |
| gemini-3.1-flash-lite + quota | 94 | 91 (97%) | 22 KPs | 4.42/1,000w | $0.035 | 55s |
| harvest-style gemini-2.5-flash | — | — | 168 facts | 10.33/1,000w | — | 107s |
| harvest-style gemini-3.6-flash | — | — | 156 facts | 9.59/1,000w | — | 34s |

**gemini-3.6-flash with the quota beats the dying incumbent on equal terms**,
at 60% of the cost and a fifth of the wall clock, with every quote verifying.
The October migration is now a config change after all.

**Two things this surfaced, both handled:**

1. **The quota can overflow the output ceiling.** gemini-2.5-flash truncated on
   two of six sources and returned *nothing* for them, which is why its quota
   figure is below its unquoted 294. Extraction now retries a truncated call on
   half the source rather than losing it. This is also why 2.5-flash's raw
   density is not the target to chase: it was already verbose, and the quota
   pushed it over.
2. **The harvest-style call is denser than schema extraction, by a lot** — 156
   to 168 dense facts against 32 key points over the same sources, with roughly
   eight times as many carrying numbers, in a third of the time. That is the
   same result the harvest stage measured on the films corpus, and it is why
   the Briefing's coverage gate reads the harvest rather than the extraction.
   Schema extraction remains what feeds claims, quotes, and the claim graph;
   the two are complementary rather than competing.

Cost figures for the harvest legs are absent because the Gemini adapter does
not yet compute cost. Evidence:
`plans/260814-claim-graph-briefing/artifacts/quota_countertest.json`,
`threeway_quota.json`.

## Decision 030: extraction is gemini-3.6-flash with a length-scaled quota (2026-08-20)

**Status:** Accepted (project owner, in-session, 2026-08-20). This is the
extraction decision; D-027 and D-029 are the evidence behind it.

**`MODEL_EXTRACTION=gemini-3.6-flash`, with the quota prompt on.** The October
16 retirement of the Gemini 2.5 line is a config swap, not a rebuild.

Measured over six labyrinth sources, 21,251 words, identical prompts:

| strategy | quotes | verified | key points | density | cost | time |
|---|---|---|---|---|---|---|
| **gemini-3.6-flash + quota** | **182** | 182 (100%) | 32 | **8.56/1,000w** | $0.054 | 141s |
| gemini-2.5-flash + quota | 124 | 124 (100%) | 24 | 5.84/1,000w | $0.092 | 746s |
| gemini-3.1-flash-lite + quota | 94 | 91 (97%) | 22 | 4.42/1,000w | $0.035 | 55s |
| gemini-2.5-flash, no quota (old default) | 294 | 291 (99%) | 52 | 13.8/1,000w | $0.131 | 580s |
| gemini-3.6-flash, no quota | 39 | 39 (100%) | 22 | 1.84/1,000w | $0.030 | 71s |

The chosen configuration extracts 4.7x what the same model produced without
the quota, beats the dying incumbent on equal terms, and costs 60% as much in
a fifth of the wall clock. The incumbent's unquoted 294 is the one number it
still leads on; it is also the number that cannot survive October, and its
quota run truncated on two of six sources.

**The quota is configuration, not a constant.** `EXTRACTION_QUOTES_PER_1000`,
`EXTRACTION_CLAIMS_PER_1000`, and `EXTRACTION_KEY_POINTS_PER_1000` each take a
`"low-high"` rate, defaulting to 8-12, 6-10 and 2-4. The right rate depends on
the corpus and the model, so finding it is a measurement each time rather than
a number enshrined in code. A malformed value falls back to the default rather
than failing a job.

**The empty-output law still wins, and it is tested.** A quota is a standing
instruction to produce more, so the failure it could introduce is a model
filling the number with invention. Measured live (2026-08-20, gemini-3.6-flash):
a 2,015-word boilerplate page carrying two real facts, quota asking for 16 to
24 quotes, returned **8 quotes, 2 key points, 4 claims, all 8 verbatim, zero
flagged**. It under-delivered rather than filling. That check ships as a test
(`TestThinSourceHonesty`), skipped unless `RUN_LIVE_API_TESTS=1`, alongside an
offline test that the permission text is still in the prompt.

### Addendum: gemini-3.1-pro ignores instructions, and it holds MODEL_REASONING

Flagged here against the slot it affects. The same quota instruction that took
gemini-3.6-flash from 6 quotes to 40 moved gemini-3.1-pro from 3 to 5 on one
source and from 3 to **2** on another. It did not partially comply; it
continued as though the instruction were absent.

`MODEL_REASONING=gemini-3.1-pro-preview` **stays for now**, because gap
analysis is wrapped by quote verification and the dossier's case for it
(best-in-class abstention, best long-context reasoning) is about a different
task than extraction. But a model that ignores an explicit, unambiguous
instruction is a poor bet for a stage whose whole output is instruction-shaped,
and this is on the record as a reason to scrutinise it rather than a settled
verdict.

**Scheduled:** at the judge-contest session, A/B the reasoning slot -
`gemini-3.1-pro` against `gpt-5.4-mini` on the fixture's gap analysis, scored
by the quote verifier. Swap only on numbers.

---

## Decision 031: gpt-5.4-mini takes the reasoning slot (2026-08-20)

**Status:** Accepted — decided by the A/B scheduled in D-030, per the owner's
standing instruction to swap only on numbers.

Three runs each of the Hawara fixture's gap analysis, scored by pulling every
hard atom out of the returned gaps — figures, name tokens, quoted spans — and
checking each one against the corpus with the D-026 span verifier.

| | **gpt-5.4-mini** | gemini-3.1-pro | gemini-3.6-flash |
|---|---|---|---|
| gaps returned | **7, 7, 7** | 4, 3, 3 | 4, 3, 4 |
| ungrounded atoms | **0%, 0%, 0%** | 4.3%, 3.6%, 3.0% | 11.4%, 13.3%, 13.7% |
| unverified quotes | 0 | 0 | 0 |
| words returned | 262 median | 97 median | 99 median |
| wall clock | 8s | 15s | 5s |

gpt-5.4-mini found more than twice as many gaps and never once put a fact in
its output that the corpus does not contain. gemini-3.1-pro invented something
in **every** run — small, one atom in roughly thirty, but never clean — and it
was the slowest of the three. This is the same failure the D-030 quota work
found from the other side: 3.1-pro under-produces and drifts from what it is
told to do. Two independent tests, one verdict.

3.6-flash was tested as a third leg specifically to see whether a Gemini model
could hold the slot without breaking the vendor split below. It cannot: it
matched 3.1-pro's thin output and tripled its ungrounded rate.

**Adopted:** `MODEL_REASONING=gpt-5.4-mini`. gemini-3.1-pro is retired from
the slot, and the D-030 flag against it is closed by this measurement.

**The vendor collision, stated plainly.** D-028 records the pairing as
extraction Gemini, synthesis Claude, judge OpenAI. Reasoning now sits on
OpenAI too, alongside the judge — different models (`gpt-5.4-mini` vs
`gpt-5.6-terra`) but one vendor. This does not breach the standing law, which
binds the judge against the *synthesis* model, and the numbers above came from
the code verifier rather than from any model's opinion, so the result itself is
not vendor-graded. It is still a narrowing of independence and is recorded here
so that a later judge-slot decision reckons with it rather than rediscovering
it: if the judge ever needs to audit gap analysis specifically, that audit
should not be an OpenAI model.

**A defect this A/B exposed.** The first two attempts at the gemini leg failed
outright with `400 INVALID_ARGUMENT: Thinking level MINIMAL is not supported`.
`GeminiStructuredClient` sent `thinking_level="minimal"` to every `gemini-3*`
model, but only 3.6-flash accepts it — 3.1-pro and 3.7-flash reject it. The
client now falls back to `"low"` for those models instead of failing the call,
pinned by a test. Worth noting how this presented: a model that looks like it
"scores zero" may simply never have been called. Read the failure string.

---

## Decision 032: the harvest chunks, it does not truncate (2026-08-20)

**Status:** Accepted — owner decision, 2026-08-20: "coverage gate integrity
outranks harvest cost."

The harvest sent `HARVEST_MAX_CHARS` of each source and dropped the rest. On
the Hawara fixture that meant **44,602 characters of source text were never
sent to a model at all**:

| source | length | previously unread | share |
|---|---|---|---|
| SRC_16 | 55,779 chars | 31,779 | **57.0%** |
| SRC_3 | 36,823 chars | 12,823 | 34.8% |

This is worse than a quality problem, because of what it did to the coverage
gate. Gate 13 checks the Briefing against the harvest inventory — so an
inventory built from 43% of a source produced a gate that passed cleanly while
more than half the source went unrepresented. The gate reported full coverage
of a corpus it had only partly read. That is the specific failure the I.25
recall audit was built to find, and it found it: SRC_3's back-of-source recall
was 0.0, which is not a recall miss at all but text that never existed as far
as any model was concerned.

**Adopted:** `harvest_source` chunks any source longer than one call's budget
into overlapping chunks and merges the facts.

- `HARVEST_MAX_CHARS` (24,000) is now characters **per call**, not per source.
- `HARVEST_CHUNK_OVERLAP` (1,500) is repeated between chunks so a fact that
  straddles a boundary is not harvested wrong from both halves.
- Merge dedups with `says_the_same_thing`, the conservative matcher. This is
  the one place in the system where a false match DELETES a fact, so the cost
  of over-eager matching is a real loss rather than a duplicate line.
- The identity lock and confidence ceiling are rebuilt per chunk, so a chunked
  source carries exactly the provenance a single-call source does
  (Architecture Rule 1 is untouched: no chunk ever sees another source).

**Cost delta, measured on the fixture** (16 sources, per the owner's request to
log it): calls **16 to 19**, input characters **214,879 to 263,981, +22.9%**.
Only two sources chunk at all; the other fourteen are one call as before.

**Regression test:** `test_density_stays_flat_as_the_source_grows` runs the
harvest at four input sizes against a client that returns a fixed 20 facts per
call — the D-029 behaviour, reproduced deliberately. Facts per 1,000 words must
stay flat. A truncating harvest scores 20, 10, 5, 2.5 on that test.

**Not adopted:** raising the cap instead. D-029 measured that a bigger window
does not buy more output from a model that returns a roughly fixed number of
items whatever it is handed — the source would have been read and then
summarized, which is the same loss wearing a better number.

---

## Decision 033: the pre-rerun sweep — nothing loses source text silently (2026-08-20)

**Status:** Accepted — owner instruction, 2026-08-20: fix what has surfaced and
confirm nothing else needs fixing *before* the next full run.

D-032 fixed one instance of a family. The sweep found three more. All four are
the same disease: **source text that never reaches a model, or an ask that does
not scale with the input, in a way nothing reports.** Every one produced a
plausible-looking number, which is why none had been caught by reading output.

### 1. The harvest asked for a fixed count (fixed here)

`HARVEST_SYSTEM` said "Extract 10 to 40 facts". Measured on the existing Hawara
harvest, that produced:

| | facts per 1,000 words |
|---|---|
| 5 shortest sources | **40.1** |
| 5 longest sources | **12.0** |

A 3.3x decline that is entirely an artefact of the instruction — the model
returns 40-60 facts whatever it is handed. Chunking (D-032) only partly masks
it, because a 24,000-character chunk still sits in the sparse regime.

Fixed with the D-030 remedy: a length-scaled quota, `HARVEST_FACTS_PER_1000`
(default 25-40), env-configurable. The empty-output law is restated inside the
quota so a thin source still under-delivers honestly.

### 2. The Read cut every source at 40,000 characters (fixed here)

Section 1 — the only part built to be read top to bottom — silently dropped
15,779 characters of SRC_16, 28% of it, while the call as a whole sat nowhere
near its context limit. The cap was per-source; the real constraint is total.

Replaced with `read_budget`: a total budget (700,000 chars) shared by
water-filling, so nothing is trimmed unless the corpus genuinely overflows, the
cut lands on the longest sources first, and every source keeps a 20,000-char
floor. On the Hawara corpus **nothing is trimmed at all** and SRC_16 now goes
to the Read whole.

### 3. The extraction truncation-retry dropped the back half of the source (fixed here)

On a truncated response the retry did `source_content = source_content[:half]`
and continued — so the back half was never extracted. The comment beside it
read "the remainder is covered by the next half". Nothing covered it.

The diagnosis was wrong, not just the code: a truncated response is an OUTPUT
ceiling problem, so cutting the INPUT treats the wrong end. The retry now keeps
the whole source and halves the *quota* (`quota_scale`), losing density instead
of text. Density is recoverable by the harvest; text that was never read is not.

### 4. The production judge read the first 15,000 characters (fixed here)

`build_judge_prompt` took `source_text[:15000]`. The judge's question is "is
this claim supported by the source", so a claim whose evidence sat at character
30,000 was being marked **unsupported on the strength of text the judge never
saw** — a false negative manufactured by the prompt builder, in the one
component whose whole purpose is checking the others. It is in the live path:
`_run_llm_judge` modifies `extraction.claims`.

Replaced with `relevant_source`: the source is cut into ~500-word windows,
windows sharing content words with the extraction are kept best-first until the
budget is spent, and elisions are marked so the judge never reads two distant
passages as one continuous sentence. Verified on a source with the evidence at
character 44,000 — it survives the cut; the old builder sent 15,000 characters
of filler.

`judge_contest.source_window` had had the correct approach since D-028. Only the
contest harness used it.

### What the sweep cleared

Every other `[:N]` on text in the pipeline is a display truncation (log lines,
social captions, excerpt fields). The only other fixed-count prompt instructions
are in the Producer packet, which is optional and asks for genuinely bounded
lists (2-4 angles), not extraction proportional to input.

**Guard:** `backend/tests/test_no_silent_text_loss.py`, 18 tests, one per
defect with the measured evidence in its docstring. Suite: 1682 passed.

---

## Decision 034: off Anthropic — the harvest and prose slots reassigned (2026-08-20)

**Status:** Accepted — owner constraint, 2026-08-20: Anthropic credits are not
available. Decided by measurement on the Hawara fixture, as D-031 was.

Three slots ran on Anthropic: `MODEL_HARVEST` and `MODEL_DISTILL`
(claude-sonnet-5) and `MODEL_ESCALATION` (claude-opus-5). Three call sites also
built an Anthropic client directly rather than going through the provider
router, so the lineup was not actually env-driven where it mattered. Those now
call `get_structured_client`.

### The harvest: a straight upgrade

Same three sources, same chunked prompt, same length-scaled quota (D-033):

| | SRC_8 (284w) | SRC_1 (3,124w) | SRC_16 (8,924w) |
|---|---|---|---|
| gemini-3.6-flash | 31.7 /1k | 10.2 /1k | **10.8 /1k** |
| **gpt-5.4-mini** | 45.8 /1k | 11.2 /1k | **31.3 /1k** |

gemini-3.6-flash does not honour the quota on a long source — it holds ~10
facts per 1,000 words whatever it is handed, which is the exact defect D-033
was written to remove. gpt-5.4-mini scales. On SRC_16 that is **291 facts
against 111**, and the extra volume is not padding: hard-atom grounding against
the raw source was **0.6% ungrounded for gpt-5.4-mini against 1.2% for
gemini-3.6-flash** (both effectively clean — most flagged atoms are word-splits
on "Synthetic Aperture Radar").

Note this does NOT contradict D-030, where 3.6-flash responded well to a quota:
that was the extraction prompt at extraction rates. Quota compliance is per
prompt and per rate, not a property of the model.

**Adopted:** `MODEL_HARVEST=gpt-5.4-mini`.

### The prose: a real quality loss, and the vendor split decides it

Three runs each of the full Read pass, scored by the I.30 cold-reader
instrument and the grounding gate:

| | coverage (median) | ungrounded (median) | words |
|---|---|---|---|
| gemini-3.6-flash | 0.785 | 5.8% | 481-875 |
| gpt-5.4-mini | 0.785 | 4.9% | 1,063-1,227 |
| *claude-sonnet-5 (incumbent)* | *0.893* | *0.0%* | *848* |

**Coverage is a tie.** Neither substitute is chosen on quality, because on
quality neither wins.

**An honest caveat on the incumbent's number.** Sonnet's 0.893 is measured
against a player list extracted from a Briefing built on that same Read, so it
has home-field advantage and is not directly comparable. The gemini-vs-gpt
comparison is clean; the Sonnet column is indicative only.

**What is not a tie:** grounding drops from 0% to roughly 5% either way. That
is the price of leaving Anthropic and it should not be presented as anything
else. The grounding gate still strips ungrounded short fields and reports the
rest, and the cold-reader instrument now tracks it per run, so the loss is
visible rather than silent — but it is a loss.

The slot is decided on **vendor independence**, not quality. With the harvest
moving to OpenAI, `MODEL_REASONING` and `MODEL_JUDGE` already on OpenAI, putting
prose there too would leave extraction as the only non-OpenAI stage and would
have an OpenAI judge auditing OpenAI-written prose. That is the self-grading
D-028's law exists to prevent. gpt-5.4-mini also overran the Read's stated
700-1,100 word band on all three runs.

**Adopted:** `MODEL_DISTILL=gemini-3.6-flash`, `MODEL_ESCALATION=gpt-5.4-mini`
(escalation crosses vendors from distill on purpose).

### Resulting lineup

```
harvest      gpt-5.4-mini        openai
distill      gemini-3.6-flash    google
escalation   gpt-5.4-mini        openai
extraction   gemini-3.6-flash    google
reasoning    gpt-5.4-mini        openai
judge        gpt-5.6-terra       openai
vision       gemini-2.5-pro      google
```

**Reversible by env var.** If credits return, `MODEL_DISTILL=claude-sonnet-5`
restores the better Read with no code change. Suite: 1682 passed.

---

## Decision 035: the Claude Code bridge — built, measured, and NOT enabled (2026-08-20)

**Status:** Accepted. The bridge ships as an available provider; it is off by
default, because the measurement that justified it did not survive being redone.

### The idea

The Anthropic API has no credits; the Claude Code subscription does, and
`claude -p` runs the same models headlessly. `ClaudeCodeClient` makes that a
provider like any other, so a slot reading `claude-code:sonnet` routes through
the local CLI and the pipeline neither knows nor cares.

It works. Verified end to end on the real 42,000-word Hawara corpus.

Two traps found building it, both worth keeping written down:

- **`ANTHROPIC_API_KEY` in the environment kills the call.** The CLI prefers an
  API key over the subscription login, and this pipeline loads that key from
  `.env` for its own use. The subprocess env is now scrubbed of it — using the
  API key is the exact thing the bridge exists to avoid. Same family as the
  stale-`GOOGLE_API_KEY` trap from 08-17.
- **`--bare` cannot be used.** It would cut the session tax, and it forces
  API-key auth and never reads the subscription.

### Why it is not enabled

**A correction to D-034, which was wrong.** That decision reported the Read's
grounding falling "from 0% to ~5%" when leaving Anthropic. The 0% was the COLD
READER'S ANSWERS about the Sonnet Read; the ~5% was the substitutes' own atoms.
Two different measurements, put in one column. Scored consistently — every Read
by its own hard atoms against the corpus:

| | coverage | ungrounded |
|---|---|---|
| gemini-3.6-flash | 0.785 | 5.8% |
| gpt-5.4-mini | 0.785 | 4.9% |
| claude-code:sonnet (fresh) | 0.785 | 4.0% |
| claude-sonnet-5 (the published Read, re-scored) | — | **4.1%** |

**There is no measurable Anthropic advantage on the Read.** Coverage is
identical across all four. Grounding sits between 4% and 6% for everything,
including Sonnet. D-034's central caveat — "the Read gets worse and that should
not be dressed up" — was an artefact of comparing two different metrics, and
the honest version is that the substitution costs nothing measurable.

Against that, the bridge costs a great deal:

| | wall clock | notional cost |
|---|---|---|
| gemini-3.6-flash / gpt-5.4-mini | 14-20s | cents |
| claude-code:sonnet | **179s** | **$1.25** |

Plus a fixed session tax that does not amortize — measured at ~45,000 tokens
and ~$0.10 per invocation, on three consecutive trivial calls.

**Adopted:** `MODEL_READ` defaults to empty, meaning the Read uses
`MODEL_DISTILL` like every other pass. Setting `MODEL_READ=claude-code:sonnet`
enables the bridge for that one call, and the stage falls back to
`MODEL_DISTILL` if the CLI cannot be reached.

**The lesson, which is the durable part.** A model swap was justified on a
number that compared two different measurements. It survived being written into
a decision record and would have justified 179-second calls indefinitely. When
a comparison decides something, every column has to come from the same
instrument — and the way that error surfaced was building the thing the number
justified and watching it not reproduce.

---

## Decision 036: the grounding gate repairs, it does not only report (2026-08-20)

**Status:** Accepted — owner instruction, 2026-08-20: "it solves a problem for
us now."

The grounding gate finds every hard atom the Briefing asserts and the corpus
does not contain. In short fields it deleted the offending sentence; in long
prose it stopped at reporting, because cutting a sentence out of an argument
does its own damage. So an invented figure in the Read reached the reader with a
flag on it rather than being fixed.

Measured across the writer bake-off, a Read carries roughly 3 to 8 invented
atoms depending on the model — 3 for gemini-3.6-flash, 7 for gpt-5.6-luna.

`repair_grounding` closes it with the same shape as the D-025 introduction
repair: one narrow question per atom, the answer spliced in by code, the model
never handed the document back (D-024).

### The defect that nearly shipped

The first working version **deleted true statements**, and the run that proved
the pass worked was the run that exposed it:

| atom | what happened |
|---|---|
| `Tutankhamun` | corpus says "the Tomb of the Pharaoh **King Tut**" — same fact, different name. The gate flagged it; the repair cut it. |
| `Rosae` | corpus spells it `Rosæ`. A character difference read as an invented fact. |

The gate matches text, so it raises false alarms on name variants and spelling.
A repair pass that trusts those findings blindly is strictly worse than
reporting them, because it converts a false alarm into lost content.

**The fix:** a third action. The model is handed the source window and may
answer `keep` — the checker was wrong, the fact is genuinely there. Re-run on
the same Briefing: `Tutankhamun` kept twice, `Commentator` kept, `Rosae`
corrected to `Rosæ`, nothing true deleted.

The prompt is explicit that `keep` is the safe answer under uncertainty, for
the same reason the empty-output law exists: a wrongly deleted true fact costs
more than a flagged one.

**A `keep` does not clear the gate.** The finding still appears in the report,
now annotated as model-judged false alarm. D-026's rule holds unchanged: code
decides, a model advises, and a model never gates.

**One round.** An atom the round cannot resolve stays flagged. A failed call
leaves the document untouched.

**Out of scope, and stated so nobody mistakes the coverage.** This repairs facts
the corpus does not contain. A fact the corpus DOES contain, attached to the
wrong person or with its meaning reversed, passes untouched — "Petrie described
the labyrinth" where the source says Herodotus did. That is a reading problem,
and it belongs to the semantic check, which D-026 deferred and which has never
been given a work-order item. Filing it is owed.

Guard: `backend/tests/test_grounding_repair.py`, 10 tests. Suite: 1692 passed.
