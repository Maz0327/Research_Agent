# Research Agent — Context Handoff Document

> **Purpose of this document**
>
> This is a **handoff/reference document** for preserving context across chat resets and model sessions.
>
> **For authoritative specifications, see [`docs/authoritative/INDEX.md`](../INDEX.md)** — the Repo Constitution.
>
> This document provides historical context and design rationale. If any content here conflicts with INDEX.md, **INDEX.md wins**.

---

## 1. Core Problem Being Solved

The goal of this project is to build a **semantic-first research assistant** that performs the *heavy lifting* of research so the human can focus on:
- deep understanding
- synthesis
- narrative construction
- creative and strategic thinking

This tool exists specifically to address **ADHD-related cognitive constraints**:
- executive dysfunction when faced with too many unstructured tasks
- working-memory collapse (forgetting details across time)
- difficulty activating on boring or effort-heavy steps (reading transcripts, extracting facts, organizing notes)

The system must:
- externalize memory
- reduce activation energy
- provide structured “triggers” that help the user start thinking
- never hide uncertainty or degradation

This is **not** a summarization tool and **not** a script-writing tool.

---

## 2. What This System Is (and Is Not)

### What it IS
- A **semantic research assistant**
- A system that makes long-form sources *scannable, trustworthy, and cognitively usable*
- A replacement for the *mechanical parts* of a human research assistant
- A handoff system that produces an **~80% finished research brief**

### What it is NOT
- Not a topic discovery engine
- Not a clip generator
- Not a script writer
- Not an opinion engine
- Not a replacement for human judgment

The system deliberately stops short of final creative decisions.

---

## 3. The 3-Document Model (Non-Negotiable)

The entire system is built around a strict **three-document separation**. These documents must never be collapsed.

### Doc 0 — Source Ledger (Canonical Data Layer)

**Purpose:**
- Preserve *full context* of all provided sources
- Act as the canonical evidence layer
- Allow verification, revisiting, and re-reading without re-running jobs

**Contains:**
- Full transcripts / full article text / full thread text (stored in Supabase Storage)
- Skim summaries (short, factual, non-interpretive)
- Source metadata
- Transcript provenance and degradation flags

**Rules:**
- No interpretation
- No synthesis
- No opinions
- This is the ground truth

---

### Doc 1 — Jump-Start Research Directions

**Purpose:**
- Reduce research paralysis
- Point the user toward *what to explore next*
- Expand research *directionally*, not factually

**Contains:**
- Scope lock (what this research is actually about)
- What is known (from Doc 0)
- What is missing
- Research gaps
- Follow-up directions
- Suggested search queries
- Top 3 next steps (mandatory)

**Rules:**
- No new claims
- No resolving contradictions
- Directional only
- This document exists to *activate the human*

---

### Doc 2 — Semantic Research Brief

**Purpose:**
- Deliver an ~80% finished handoff to a creative or strategist
- Surface meaning, themes, tensions, and open questions

**Contains:**
- Key semantic points
- Themes
- Tensions / contradictions
- Gaps
- Confidence assessment
- Clearly labeled speculation (allowed, but constrained)

**Rules:**
- No new facts may be introduced
- All content must trace back to Doc 0
- Uncertainty must be explicit
- Thin output is allowed, but must be labeled

---

## 4. The Meaning of “80% Finished”

“80% finished” does NOT mean:
- polished
- final
- complete

It means:
- the mechanical research labor is done
- the information is structured
- the major themes and tensions are visible
- the human can *immediately* begin thinking creatively

The remaining 20% is intentionally human:
- judgment
- narrative framing
- synthesis across time
- creative risk-taking

---

## 5. Transcript-First, Gemini-Always Policy

This is a **locked decision**.

### Transcript acquisition order (per video source):
1. Supadata transcript (primary, canonical)
2. YouTube captions (fallback)
3. None (degraded mode)

### Gemini behavior:
- Gemini **always runs**, regardless of transcript availability
- Gemini receives:
  - Transcript + YouTube URL when available
  - YouTube URL only when transcript unavailable

### Analysis modes:
- `transcript_grounded`
- `caption_grounded`
- `video_only`

### Degradation rules:
- Transcript failure must NEVER fail the job
- Degradation must ALWAYS be disclosed
- Quotes from degraded sources must be marked unverified

Transparency is mandatory. Trust is more important than completeness.

---

## 6. Semantic-First, Not Clip-First

A key insight of this project:

> Clips are handles to meaning — they are not the meaning itself.

Therefore:
- Early phases prioritize semantic understanding
- Key points, themes, and tensions matter more than timestamps
- Clips may be referenced, but are not the primary unit

This is a research system, not a video editing tool.

---

## 7. Deep Research Booster (Post-Job Only)

Topic-based natural language research **before** ingestion was abandoned because:
- LLMs misunderstood topics
- Outputs were shallow or off-topic

**New approach (locked):**
- Deep research only runs AFTER Doc 0 / 1 / 2 exist
- Input is a **Context Bundle**, not raw topic text
- Output expands Doc 1 only

Deep Research Booster:
- Never adds facts
- Never resolves tensions
- Only expands directions and missing perspectives

Fallback tools already exist:
- Exa
- Brave
- Jina

Booster failure must not block core outputs.

---

## 8. Validation Philosophy

The system must prefer:
- honest thin output
- explicit uncertainty

Over:
- padded summaries
- false confidence

Validation is transcript-aware:
- Stricter rules when transcript exists
- Downgraded confidence when transcript does not exist
- Jobs should complete whenever possible

---

## 9. Technical Stack (Current Understanding)

- Frontend: Vercel
- Backend API: FastAPI (Railway)
- Worker: Celery (Railway)
- Redis: Railway
- Database: Supabase Postgres
- Storage: Supabase Storage (media bucket)

Legacy outputs exist and MUST be preserved:
- producer_packet
- clips
- quotes

New semantic docs are **additive**, not replacements.

---

## 10. Phase Plan (Confirmed)

### Phase 0 — ClaudeKit Foundation (NEW)
- Semantic skill files
- CLAUDE.md enhancements
- Pydantic validation hooks

### Phase 1–7 (Unchanged)
1. Storage Foundation
2. Source Ledger (Doc 0)
3. Jump-Start (Doc 1)
4. Semantic Brief (Doc 2)
5. API & Integration
6. Deep Research Booster
7. Frontend 3-Doc UI

---

## 11. Implementation Rules for Claude

- All changes must be additive
- No files deleted
- No refactors unless explicitly requested
- No layer collapse
- Ask before guessing

Claude should follow written specs exactly.

---

## 12. Current Status / Next Step

- Specs updated with transcript-first policy
- Additive change instructions prepared
- Waiting to review files Claude generates

**Next task:**
- Review Claude-written files against this context
- Identify gaps only
- Do not re-scope

---

**END OF CONTEXT HANDOFF DOCUMENT**

