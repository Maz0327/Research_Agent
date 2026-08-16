---
title: "Product Viability Overhaul"
description: "Transform Research Agent from prototype to product: cleanup, single-screen UX, hero document, Sonnet editorial, paywall, SSE streaming, chat, quick mode"
status: pending
priority: P1
effort: 10-14w
branch: main
tags: [product, ux, monetization, pipeline, streaming]
created: 2026-04-06
---

# Product Viability Overhaul

**Positioning:** "Turn any collection of videos and articles into a verified, source-cited script -- with the angle nobody else covered."

**Supporting reports:**
- `plans/reports/brainstorm-260405-1617-product-viability-overhaul.md`
- `plans/reports/researcher-260406-1233-brainstorm-validation.md`
- `plans/reports/researcher-260406-1252-business-viability-analysis.md`

---

## Pre-Prep Prerequisite Status

**Pre-Prep UX Foundation plan:** `plans/260406-1337-pre-prep-ux-foundation/`

**Progress:** 3/7 phases complete (42%)
- ✅ PP-1: Design Token Migration — 1464 replacements, zero hardcoded colors
- ✅ PP-2: Font & Type Scale — Inter → Plus Jakarta Sans, type scale defined
- ✅ PP-3: Creator Copy Rewrite — all user-facing strings updated
- ⏳ PP-4: Citation Pills (ready)
- ⏳ PP-5: Progress UX Polish (ready)
- ⏳ PP-6: Iteration UX Redesign (ready)
- ⏳ PP-7: First Impressions (ready)

**Blocks:** Phase 00 (Cleanup & Removals) can start immediately. Phases 01-10 blocked until Pre-Prep complete.

**Blocked by:** `plans/260409-engine-optimization/` — Engine speed + quality fixes must land first (Flash swap, deferred verification, Sonnet editorial, genre prompts).

---

## Phase Map

| Phase | Name | Status | Effort | Blocking |
|-------|------|--------|--------|----------|
| 00 | [Cleanup & Removals](phase-00-cleanup-and-removals.md) | pending | 2-3d | None |
| 01 | [Single-Screen Input](phase-01-single-screen-input.md) | pending | 3-5d | Phase 00 |
| 02 | [Hero Document UX](phase-02-hero-document-ux.md) | pending | 3-5d | Phase 00 |
| 03 | [Sonnet Editorial Pass](phase-03-sonnet-editorial-pass.md) | pending | 3-5d | Phase 00 |
| 04 | [Paywall + Stripe](phase-04-paywall-stripe.md) | pending | 2-3d | Phase 01, 02 |
| 05 | [SSE Streaming](phase-05-sse-streaming.md) | pending | 2-3w | Phase 00 |
| 06 | [Chat with Research](phase-06-chat-with-research.md) | pending | 5-7d | Phase 02 |
| 07 | [Quick Mode](phase-07-quick-mode.md) | pending | 1-2w | Phase 00 |
| 08 | [Source Discovery](phase-08-source-discovery.md) | pending | 2w | Phase 07 |
| 09 | [Gemini Multimodal Fallback](phase-09-gemini-multimodal-fallback.md) | pending | 3-5d | Phase 00 |
| 10 | [Credit System](phase-10-credit-system.md) | pending | 1-2w | Phase 04 |

**Phases 01-04** can run in parallel after Phase 00 (except 04 needs 01+02).
**Phases 05-07** can run in parallel after their deps.

---

## Deferred (Phase 3+ -- no phase files yet)

- Research Library (persistent per-user knowledge base) -- 2-3w
- Audio/podcast output (TTS) -- 1-2w
- Collaboration/sharing -- 2w
- Horizontal worker scaling -- 1w
- Cross-user source caching -- 3-5d
- Title/thumbnail suggestions -- 3-5d

---

## Architecture Invariants (from `docs/authoritative/`)

- Full mode: per-source isolation PRESERVED (Architecture Rule 1)
- Quick mode: single call with source labels (NEW, not isolated)
- Confidence ceilings unchanged
- Prompt guardrails (5 components) unchanged
- Doc numbering: Doc 0-3 core, Doc 4+ optional

---

## Key Decisions

1. Dark-only mode (theme toggle already removed functionally)
2. $19/mo after 3 free jobs (simple paywall before credit system)
3. SSE via Redis pub/sub (Celery -> Redis -> FastAPI -> EventSource)
4. Sonnet 4.6 editorial on Doc 2 (Research Brief) + Doc 5/6 (Script/Blog)
5. Gap analysis + synthesis merged into single LLM call
6. Creator Brief (Doc 3) on-demand only
