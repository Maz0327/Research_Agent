# Implementation Plan: Full Pipeline Upgrade

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.**
> This plan is **non-authoritative**.

**Created:** 2026-03-11
**Scope:** Everything discussed in the competitive strategy session
**Reference:** `docs/competitive/sandcastles-ux-deep-dive.md` (all sections)

---

## Context: What We Agreed To Change

After live-exploring Sandcastles, running an end-to-end example, analyzing their script output (7.5/10 human, 6.5/10 quality), and identifying their structural weaknesses, we agreed on a strategy:

**Take Sandcastles' presentation instincts. Pair them with our verification engine.**

**ADOPT:** Progressive disclosure flow, narrated loading states, research brief sections (shock scores, contrast moments, analogies, video angles — but grounded in verified claims), hook options as visual cards (generated from claims not templates), "Why It Matters" / personal stakes as mandatory section, inline edit/targeted changes (v2)

**REJECT:** Template-driven hooks, style/format selection, invisible sources, flat prose scripts, volume-first mentality, black box pipeline

**Core promise:** "Everything you say on camera can be cited. Nothing you say will embarrass you."

**Target user:** Weekly creators building reputation, not daily posters chasing volume

The user's 6 requirements before rebuilding search:
1. Clean codebase (no legacy contamination)
2. Keep skip-to-sources option
3. Relevance validation on search results
4. Auto-flow approved sources into pipeline
5. Maintain data quality throughout
6. More polished output

---

## Phase 1: Legacy Code Audit & Cleanup

**Goal:** Clean codebase before building anything new. Requirement #1 of 6.

### 1.1 — Audit deprecated API endpoints
Scan `backend/app/routes/jobs_routes.py` for DEPRECATED endpoints:
- `POST /jobs` (legacy topic research)
- `POST /jobs/{job_id}/iterate` (old iterate)
- `POST /jobs/{job_id}/sources` (legacy add sources)
- `POST /jobs/{job_id}/process-pending` (legacy)
Check if frontend calls any. No callers → archive to `backend/archive/`. Callers exist → document.

### 1.2 — Audit V1/V2 artifact mixing
`job_record.py:125` has `booster_output` (V1) alongside `runs[]` (V2). Check all code that reads `booster_output`. Document V1 vs V2 usage per file. Flag for Phase 5.

### 1.3 — Audit API key issues
- `ADMIN_EMAILS` → add to config.py or document
- `JINA_AI_READER_API_KEY` → add to Settings
- 3 clients using `os.getenv` directly → migrate to Settings
- 2 deprecated Slack keys → remove
- 11 keys with no client → document status

### 1.4 — Build naming reference map (for Phase 5)
Find ALL code references. **DO NOT rename** — just document:
- "Booster" → will become "Deep Dive"
- "Addendum" → will become `expand_sources`
- "Doc 3 = Producer Packet" → will become Doc 4
- Every file, line number, context

### 1.5 — Run full test suite baseline
`pytest backend/tests/ -v` + `cd frontend && npm run build`. Document pre-existing failures.

**Acceptance:** Audit report in PROGRESS.md. No broken tests. No pipeline logic changes.

---

## Phase 2: Read & Validate sandcastles-analysis.md

**Goal:** Ground all competitive claims with objective data research.

### 2.1 — Read every line of `docs/competitive/sandcastles-analysis.md`
Catalog every factual claim about Sandcastles, our system, and the market.

### 2.2 — Research & validate each claim
Web search to verify. Cross-reference with live app observations. Tag each: verified (add source), corrected (fix it), unverifiable (mark it).

### 2.3 — Update the doc
Correct wrong claims. Add sources for verified claims. Mark unverifiable.

**Acceptance:** Every claim tagged. Sources cited. Document updated.

---

## Phase 3: Creator Brief — Schema, Prompt, Stage, Validation

**Goal:** Build new Doc 3 (Creator Brief) end-to-end. The hero document. Requirement #6.

### 3.1 — Define CreatorBrief Pydantic models
Create `backend/models/creator_brief_models.py`. Sections:

```
CREATOR BRIEF: [Topic]
Generated: [Date] | Sources: [N verified]

HOOK OPTIONS (A/B)
  A) [Hook] — why it works: [1 sentence]
  B) [Hook] — why it works: [1 sentence]

THE SETUP
  [1-2 sentences: what problem you're solving for the viewer]

THE TWIST / CONTRAST MOMENT
  "Most believe X. The reality is Y."

CORE FACTS (verified, cited)
  • [Fact] — say it like: "[phrasing]" | Source: [link]
  (3-5 facts max)

THE ANALOGY
  [One memorable comparison]

WHAT THIS MEANS FOR YOU
  [Personal stakes — ties to viewer's daily life]

CLIFFHANGER / OPEN LOOP
  [Unanswered question or forward-looking tension]

SOURCES (for description box)
  [1] [Title] — [URL] — Verified: [date]

DISPUTED/SPECULATIVE CLAIMS
  ⚠ [Claim] — framing: speculative | speaker: [attribution]
```

Every section model includes grounding:
- `grounded_in: list[str]` — claim_ids from Doc 2
- `source_refs: list[str]` — source_ids from Doc 0

v3 claim enrichment mapping:

| Brief Section | Powered By |
|---|---|
| Hook Options | `significance` — highest significance claims become hooks |
| The Twist | `framing: contradicts` + `related_claims` with CONTRADICTS type |
| Core Facts | `significance` ranking + `speaker` attribution |
| Disputed flags | `framing: disputed` or `framing: speculative` |
| Cliffhanger | `framing: speculative` + gap analysis open questions |
| The Analogy | LLM-generated from highest-significance claims |
| Personal Stakes | LLM-generated "what this means for your life" |

### 3.2 — Define Creator Brief prompt
Create `backend/pipeline/prompts/creator_brief_prompt.py`.

**LLM Input:**
- Key_points from Doc 2 with significance, framing, speaker
- Claim relationships (supports, contradicts, qualifies, extends)
- Themes and tensions from Doc 2
- Source metadata from Doc 0 (titles, URLs, dates)
- Gap summary from Doc 1

**Must include all 5 required prompt components** (Rule 7):
1. Context Lock (multi-source adapted)
2. Confidence Ceiling (minimum across sources)
3. Empty Output Permission (thin research → thin brief)
4. Section instructions (what each section contains, where to find it)
5. Output Schema (CreatorBrief JSON)

**Anti-hallucination:**
- Every fact MUST reference a claim_id/key_point_id
- Twist MUST come from contradicting claims/tensions — not invented
- Hooks from high-significance claims — not templates
- Null analogy/stakes if nothing good — never fabricate

**Temperature:** 0.3

### 3.3 — Build Creator Brief pipeline stage
Create `backend/pipeline/stages/creator_brief_stage.py`.

```python
def stage_creator_brief(ctx: PipelineContext) -> dict:
    """Build Doc 3: Creator Brief.
    Consumes: ctx.semantic_brief, ctx.source_ledger, ctx.jump_start,
              ctx.semantic_extractions, ctx.source_coverage
    Produces: ctx.outputs["creator_brief"], ctx.outputs["creator_brief_md"]
    Progress: 87%
    """
```

Steps: aggregate enriched claims → identify hook/twist candidates → build prompt → call Gemini at 0.3 → parse → validate grounding → generate markdown → store.

### 3.4 — Integrate into worker pipeline
Insert after `stage_document_assembly` (80%), before completion (95%).

```
source_identity (5%) → extraction (20%) → validation (35%) →
gap_analysis (50%) → synthesis (65%) → document_assembly (80%) →
creator_brief (87%) → completion (95%) → done (100%)
```

Upload `creator_brief.json` + `creator_brief.md` to Supabase alongside Doc 0/1/2.

### 3.5 — Code-level validation
**HARD FAIL:** grounded_in claim_id not in Doc 2, source_refs source_id not in Doc 0, ungrounded hook, ungrounded core fact.
**SOFT FAIL:** <2 hooks, no twist, no analogy, generic cliffhanger.
The grounding chain is our differentiator. If it breaks, we're Sandcastles.

### 3.6 — Move Producer Packet Doc 3 → Doc 4
- `producer/gating.py` — doc refs
- `producer_stage.py` — output as doc_4
- `producer_prompt.py` — doc number refs
- `jobs_routes.py` — producer serves Doc 4
- `job.py` / `job_record.py` — artifact fields
- Frontend: `document-formatters.ts`, `ArtifactCardGrid.tsx`

### 3.7 — Update authoritative specs

**Document_Output_Format.md:**
- Add `creator_brief` to document_type enum
- New Section 3: Doc 3 Creator Brief schema
- Rename Doc 3 Producer → Section 5: Doc 4 Producer

**architecture.md:**
- Rule 12: Four Core Documents (Doc 0–3)
- Rule 13: Optional starts at Doc 4
- Rule 16: Creator Brief temperature 0.3

**RASS.md:**
- Section 3: Add DOC 3 CREATOR BRIEF between Semantic Brief and Producer
- Producer: DOC 3 → DOC 4
- Section 4.1: Add Creator Brief Assembly stage
- Section 4.6: Four canonical documents
- Section 1.4: Remove "A script writer" from non-goals (now v2 goal)
- Section 7.1: Reading order — Creator Brief (hero) → Semantic Brief → Jump-Start → Source Ledger

### 3.8 — Frontend: Creator Brief rendering
- `DocumentViewerModal.tsx` — Section-specific styling: hooks as cards, "say it like this" highlighted, disputed with warning icon, facts clickable → Doc 2 claim detail, sources for copy-paste to YouTube description
- `ArtifactCardGrid.tsx` — Creator Brief card with hero badge
- `document-formatters.ts` — Doc 3 = "Creator Brief", Doc 4 = "Producer Packet"

### 3.9 — Frontend: Hero landing
Job completes → user sees Creator Brief, NOT card grid. Three nav buttons: "View Research" (Doc 2), "Go Deeper" (Doc 1), "View Sources" (Doc 0). "Generate Script" greyed for v2. Facts clickable → inline expansion with claim, speaker, framing, significance, related claims, source link.

### 3.10 — Frontend: Document drawer
Collapsible sidebar:
```
CORE (auto-generated)
★ Creator Brief  (Doc 3)  ← hero badge
  Semantic Brief (Doc 2)
  Jump-Start     (Doc 1)
  Source Ledger   (Doc 0)
OPTIONAL
  Producer Packet (Doc 4)  ← greyed if absent
🔒 Script        (Doc 5)  ← locked until v2
```
Not a tab bar. Sidebar list. Hero always fills main content.

### 3.11 — API routes
- `GET /jobs/{id}/documents/creator_brief` → Doc 3
- `GET /jobs/{id}/documents/producer_packet` → Doc 4
- Update JobStatusResponse
- Frontend: `api-client.ts`, `constants.ts`

### 3.12 — Tests
- CreatorBrief model validation
- Prompt output parsing
- Broken claim_id → hard fail
- Broken source_id → hard fail
- Thin brief → soft fail with warnings
- Integration: mock pipeline → Doc 0/1/2/3
- Full suite: no regressions

**Acceptance:** 4 core docs auto-generated. Creator Brief is hero. Provenance validated by code. Producer is Doc 4. Specs updated. All tests pass.

---

## Phase 4: Close Enforcement Gaps

**Goal:** Prompt-only rules → code-enforced guarantees. 6 gaps from Section 16 audit.

### 4.1 — Claim source_id enforcement
Add min_length=1 validator on Claim source_ids in `claims.py`.

### 4.2 — Tension source_ids
Add `source_ids` field to Tension model. Update all 6 extraction prompts, synthesis prompt, validation, and document_assembly provenance chain.

### 4.3 — Confidence ceiling for Themes/Tensions
In `semantic_validation.py`: theme confidence ≤ min(ceiling of supporting sources). Same for tensions.

### 4.4 — Source Identity Lock validation
Compare returned source_id to sent source_id. Hard fail on mismatch.

### 4.5 — Fix V5 quote conflict
Update `Validation_and_Retry_Rules.md` — text_provided/ocr_extracted ALLOW quotes (Owner Decision). Code already correct.

### 4.6 — V1/V2 artifact cleanup
Deprecation logging on V1 access. Helper: V2 takes precedence.

**Acceptance:** 6 gaps closed. Docs updated. Tests pass.

---

## Phase 5: Iterate System Consolidation & Naming

**Goal:** Booster + Addendum + old iterate → one system, 5 modes.

### 5.1 — Code renames
- `booster_prompt.py` → `deep_dive_prompt.py`
- `booster_stage.py` → internal deep_dive references
- `job_record.py`: `more_sources` → `expand_sources`, add `deep_dive`
- Worker: `run_booster_task` → `run_deep_dive_task` (with alias)
- Frontend: "Booster" → "Deep Dive" everywhere

### 5.2 — Consolidated Iterate API
```
POST /jobs/{job_id}/iterate
{ "mode": "deep_dive|expand_sources|deeper|different_angle|custom" }
```

| Mode | What Happens | Docs Affected |
|---|---|---|
| `deep_dive` | Gap analysis → append to Doc 1 | Doc 1 only |
| `expand_sources` | New sources → full re-run | Doc 0,1,2,3 |
| `deeper` | Re-extract deeper from same sources | Doc 0,1,2,3 |
| `different_angle` | Re-synthesize with angle focus | Doc 1,2,3 |
| `custom` | Re-synthesize with user instructions | Doc 1,2,3 |

### 5.3 — Update authoritative docs
RASS, architecture, Operational_Definitions — Iterate system replaces Booster/Addendum.

### 5.4 — Document versioning (4-version rolling window)
Latest + 3 previous per document. Storage: `doc_{type}_v{version}.json`. API: `?version=N`. Frontend: version dropdown per doc. Delete oldest when 5th created.

Version rules by mode:
- `deep_dive` → Doc 1 only
- `expand_sources`, `deeper` → all 4 core docs
- `different_angle`, `custom` → Doc 1,2,3 (Doc 0 unchanged)

### 5.5 — Tests
Renames resolve. Old routes work. 5 modes dispatch correctly. Versioning works.

**Acceptance:** Naming updated. Iterate consolidated. Versioning works. Tests pass.

---

## Phase 6: UI Overhaul Foundations

**Goal:** Progressive disclosure, narrated loading, consistent design.

### 6.1 — Narrated loading states
Real pipeline stages with real counts:
```
⬤ Extracting claims from 4 sources... 23 claims found
⬤ Validating quotes... 18/20 verified
⬤ Detecting relationships... 12 mapped
⬤ Synthesizing themes...
⬤ Building your Creator Brief...
```

### 6.2 — Consistent document headers
All docs: type badge, topic, date, source count, version, confidence. Same typography and emphasis patterns everywhere.

### 6.3 — Card-based source approval (prep for search)
Source cards: URL, title, quality score, type icon. Approve/reject per source. Batch approve. Component ready for Entry Point A.

### 6.4 — Progressive disclosure rendering
One document at a time. Creator Brief default. Click fact → inline expansion. "View Research" → Doc 2. "Go Deeper" → Doc 1. "View Sources" → Doc 0. Back → Brief. No tab bar.

### 6.5 — User never sees internals
No "Doc 0/1/2/3" labels. No raw JSON. No claim IDs. Human names and formatted labels only.

### 6.6 — Tests
Loading narration. Header consistency. Hero landing. Navigation. Back button.

**Acceptance:** Narrated loading. Consistent headers. Progressive disclosure. Source cards. Tests pass.

---

## Out of Scope (v2+ — Fully Designed, Not Built)

### Script Writer (Doc 5) — v2
Spoken-word FROM Creator Brief. Controls: Tone, Length, Style. Every sentence traces Script → Brief → Doc 2 → Doc 0. Full design: deep-dive Section 12.

### Voice Mimicry — v2+
Analyze 3-5 creator videos → voice profile (sentence length, vocab, transitions, rhetoric, data density). Saveable, reusable. Blend mode. Full design: deep-dive Section 12.4.

### Topic Search / Source Discovery — Todos 4-5
Entry Point A: topic → search → approval → pipeline. Relevance validation, auto-flow. Full design: deep-dive Sections 11.0.2, 13.

### Inline Edit — v2
Highlight lines → targeted changes. Brief first, then Script.

---

## Dependency Graph

```
Phase 1 (Legacy Audit) ─────────┐
                                 ├── Parallel
Phase 2 (Validate Analysis) ────┘
                                 ▼
Phase 3 (Creator Brief) ──────── Requires Phase 1
                                 │
Phase 4 (Enforcement Gaps) ───── Can overlap Phase 3
                                 ▼
Phase 5 (Iterate + Naming) ───── Requires Phase 3+4
                                 ▼
Phase 6 (UI Overhaul) ────────── Requires Phase 3+5
```

---

## File Registry

### Created
| File | Phase |
|---|---|
| `backend/models/creator_brief_models.py` | 3.1 |
| `backend/pipeline/prompts/creator_brief_prompt.py` | 3.2 |
| `backend/pipeline/stages/creator_brief_stage.py` | 3.3 |
| `backend/pipeline/creator_brief_validation.py` | 3.5 |
| `backend/tests/test_creator_brief.py` | 3.12 |

### Modified
| File | Phase |
|---|---|
| `backend/worker.py` | 3.4 |
| `backend/pipeline/stages/document_assembly.py` | 3.5, 4.2 |
| `backend/pipeline/semantic_validation.py` | 4.1-4.4 |
| `backend/models/claims.py` | 4.1 |
| `backend/models/semantic_units.py` | 4.2 |
| `backend/models/job.py` | 3.11 |
| `backend/models/job_record.py` | 5.1, 5.4 |
| `backend/pipeline/producer/gating.py` | 3.6 |
| `backend/pipeline/stages/producer_stage.py` | 3.6 |
| `backend/pipeline/prompts/producer_prompt.py` | 3.6 |
| `backend/pipeline/stages/booster_stage.py` | 5.1 |
| `backend/pipeline/prompts/booster_prompt.py` | 5.1 |
| `backend/pipeline/prompts/modes/*.py` | 4.2 |
| `backend/pipeline/prompts/semantic_synthesis_prompt.py` | 4.2 |
| `backend/pipeline/stages/semantic_validation_stage.py` | 4.4 |
| `backend/app/routes/jobs_routes.py` | 3.11, 5.2 |
| `frontend/lib/document-formatters.ts` | 3.8 |
| `frontend/lib/constants.ts` | 3.11, 6.1 |
| `frontend/components/job-detail/ArtifactCardGrid.tsx` | 3.8, 5.1 |
| `frontend/components/job-card/DocumentViewerModal.tsx` | 3.8 |
| `frontend/pages/jobs/[id].tsx` | 3.9, 6.1, 6.4 |
| `frontend/store/jobs.ts` | 3.11, 5.4 |
| `frontend/lib/api-client.ts` | 3.11, 5.2 |
| `docs/authoritative/spec/RASS.md` | 3.7, 5.3 |
| `docs/authoritative/spec/Document_Output_Format.md` | 3.7 |
| `docs/authoritative/spec/Validation_and_Retry_Rules.md` | 4.5 |
| `docs/authoritative/spec/Operational_Definitions.md` | 5.3 |
| `.claude/rules/architecture.md` | 3.7, 5.3 |

---

*Covers all 6 todos and everything discussed. v2 features preserved in `sandcastles-ux-deep-dive.md`.*
