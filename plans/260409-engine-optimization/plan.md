---
title: "Engine Optimization — Speed + Quality"
description: "Swap extraction to Flash, defer verification, merge gap+synthesis, add Sonnet editorial pass, wire genre prompts"
status: pending
priority: P0
effort: 1-2d
branch: feature/product-viability-overhaul
tags: [backend, pipeline, speed, quality, models]
created: 2026-04-09
blocks: [260406-1304-product-viability-overhaul]
---

# Engine Optimization — Speed + Quality

**Goal:** Take pipeline from 3-10 min → 30-90 sec, and output from research paper → creator-ready narrative.

**Research basis:** Gemini Flash is 3x faster and 8x cheaper than Pro for extraction tasks. Cross-model rewriting (Gemini draft → Sonnet edit) improves quality 44% vs self-editing. Both validated against benchmarks (Apr 2026).

**Architecture rules respected:**
- Source isolation preserved (Rule 1) — still separate call per source, just on Flash
- Confidence ceilings unchanged (Rule 4-5)
- Prompt guardrails preserved (Rule 7-8)
- Pipeline order preserved (Rule 3) — stages same, just faster and merged where safe

---

## Phase Map

| Phase | Name | Status | Effort | Depends On |
|-------|------|--------|--------|------------|
| E-1 | [Flash Extraction Swap](phase-e1-flash-extraction.md) | pending | 30min | None |
| E-2 | [Deferred Verification](phase-e2-deferred-verification.md) | pending | 3-4h | None |
| E-3 | [Merge Gap+Synthesis](phase-e3-merge-gap-synthesis.md) | pending | 2-3h | None |
| E-4 | [Sonnet Editorial Pass](phase-e4-sonnet-editorial.md) | pending | 3-4h | E-3 |
| E-5 | [Genre Prompts + Untold Angle](phase-e5-genre-untold-angle.md) | pending | 2-3h | E-3 |
| E-6 | [Workers + Lazy Doc 3](phase-e6-workers-lazy-doc3.md) | pending | 30min | None |

**E-1, E-2, E-3, E-6 can run in parallel** (independent changes).
**E-4 and E-5 depend on E-3** (they modify the merged stage's output).

---

## Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| Extraction time (5 sources) | ~60-120s (Pro) | ~20-40s (Flash) |
| Verification blocking | 5-15s per source | 0s (background) |
| Gap + Synthesis calls | 2 sequential Pro calls | 1 Pro call |
| Doc 3 generation | Always (~10s) | On-demand only |
| Workers | Max 3 | Max 5 |
| Output quality | Research paper | Creator-ready (Sonnet polish) |
| Output structure | Generic | Genre-specific narrative |
| "Untold angle" | Buried in gaps tab | Hero section of brief |
| **Total pipeline time** | **3-10 min** | **30-90 sec** |
| **Cost per job (5 src)** | **~$0.50-1.00** | **~$0.25-0.50 + ~$0.05 Sonnet** |

---

## What This Does NOT Change

- Frontend (zero frontend changes)
- Source isolation (still per-source calls)
- Database schema
- API endpoints
- Document structure (Doc 0/1/2/3 still exist)
- Test infrastructure
