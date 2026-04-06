# Brainstorm Report: Research Agent — Product Viability Overhaul

**Date:** 2026-04-05
**Status:** Brainstorm (not yet planned)
**Participants:** Maz + Claude
**Context:** Research Agent feels clunky; need middle ground between OpenClaw simplicity and full pipeline depth

---

## Problem Statement

Research Agent has a powerful 8-stage pipeline producing 4-7 documents with per-source isolation, quote verification, and confidence ceilings. But it feels like a prototype, not a product. The OpenClaw version (Gemini research → draft → Sonnet edit) is fast and "mostly accurate" but shallow. Need a middle ground: fast enough to feel polished, deep enough to justify paying for.

## Root Causes of "Clunky"

1. **Zero streaming** — 3-min wait with polling progress bar. Perplexity streams first word in <500ms.
2. **Complex input** — 4-step wizard forces users to learn pipeline's mental model (topic/source/claim/creator analysis)
3. **Output overload** — 4 docs shown by default; users want ONE thing (Research Brief or Script)

---

## Agreed Ideas

### Idea 1: Gemini Multimodal Fallback (When Supadata Fails)

- Add Tier 3.5 in transcript fallback chain: Supadata → Whisper → **Gemini multimodal** → YouTube captions → VIDEO_ONLY
- New confidence tier: `MULTIMODAL_INFERRED` (between CAPTION_GROUNDED and VIDEO_ONLY)
- Hard warnings propagated to ALL downstream docs, not just Doc 0
- Cost guard: skip for videos >X minutes unless user opts in
- **Open question:** How Gemini accesses YouTube video (download vs. grounding API)
- OCR fallback for web pages: strong yes, simpler use case

### Idea 2: Sonnet 4.6 Editorial Pass (Creative Editor/Producer)

- Two-pass pattern: Gemini 2.5 Pro drafts → Sonnet 4.6 edits as creative director
- Apply to: Doc 5 (Script) always, Doc 6 (Blog) always, Doc 7 (Social) optionally
- Skip for: Doc 2-4 (research docs should stay comprehensive, not polished)
- Prompt must enforce: "preserve all facts/quotes/citations, improve flow/readability, never add info"
- Run as background async pass — user gets raw draft immediately, polished version arrives 15-20s later
- Post-edit fact-preservation validation recommended

### Idea 3: Quick Mode (OpenClaw Pattern, Productized)

| | Quick (30-60s) | Full (2-3 min) |
|---|---|---|
| Extraction | Single Gemini call, all sources | Per-source isolation |
| Validation | Skip quote verification | Full verification |
| Synthesis | Merged into extraction call | Separate stage |
| Output | Research Brief only | Brief + on-demand extras |
| Confidence | MEDIUM max | Full ceiling rules |
| LLM calls | 1-2 total | N+2 |

- Quick = free tier / first-time experience
- Full = paid tier value proposition

### Idea 4: Pipeline Simplification (Both Modes)

- **Merge gap analysis + synthesis** into 1 Gemini call (saves ~8s, low risk)
- **Make Creator Brief (Doc 3) on-demand** instead of always-generated (saves ~10s)
- Net: N+2 calls down from N+3 in full mode

---

## Product UX Overhaul

### Single-Screen Input (Kill 4-Step Wizard)

```
[What do you want to research?         ]
[Topic or paste URLs here...            ]

+ Add YouTube video
+ Add article/webpage
+ Add text/notes
+ Upload screenshot

Mode: ○ Quick (30s)  ● Full (3min)

[Start Research]
```

Auto-detect URLs. No intent selection. Pipeline figures it out.

### SSE Streaming + Progressive UI

```
Submit → Sources loading (2s) → Outline forming (15s)
→ Sections streaming (30s) → Full doc (60s)
→ Polished version (background, +30s)
```

- SSE endpoint: `GET /jobs/{id}/stream`
- Source cards appear during ingestion
- Extraction summaries stream per source
- Synthesis streams as it generates

### One Hero Document + Upsells

- Show **Research Brief (Doc 2)** as primary output
- Doc 0 → collapsible "Sources" sidebar
- Doc 1 → "Research Gaps" tab
- Doc 3 → on-demand button
- Script/Blog/Social Kit → "Want more?" action buttons
- Every fact has inline citation links

---

## Scalability Architecture

| Problem | Fix |
|---------|-----|
| Single Celery worker | Horizontal worker scaling |
| No CDN | Supabase CDN or R2 for generated docs |
| No rate limiting | Per-user limits + credit system |
| No caching | Cache transcripts + extractions by URL hash (TTL: 7d) |
| $5 budget hard limit | Credits model |

### Source Caching

Cache Source Identity Package + Semantic Extraction by URL hash. 10 users researching same trending video = 1 fetch + 9 cache hits.

---

## Proposed Product Tiers

| Tier | Price | Credits/mo | Features |
|------|-------|------------|----------|
| Free | $0 | 10 Quick | Quick mode, 3 sources max, no Script/Blog |
| Pro | $19/mo | 50 credits | Full mode, unlimited sources, Script + Blog, Sonnet polish |
| Studio | $49/mo | 200 credits | Everything + Producer Packet, priority queue, API access |

Credit costs: Quick=1, Full=3, Script=2, Blog=2, Social=1, Producer=5

---

## Implementation Priority

| # | Change | Type | Impact | Effort |
|---|--------|------|--------|--------|
| 1 | SSE streaming + progressive UI | UX | Eliminates clunk | Medium |
| 2 | Single-screen input | UX | Reduces friction | Low |
| 3 | One hero doc + upsell buttons | UX | Focuses value | Low |
| 4 | Quick mode | Pipeline + UX | Fast path + free tier | Medium |
| 5 | Sonnet editorial pass | Pipeline | Output quality differentiator | Medium |
| 6 | Gemini multimodal fallback | Pipeline | Resilience | Medium |
| 7 | Merge gap+synthesis, lazy Doc 3 | Pipeline | Speed optimization | Low |
| 8 | Source caching | Infra | Scale without linear cost | Medium |
| 9 | Credit system + tiers | Infra + UX | Monetization | Medium |

Items 1-3 are UX-only (no pipeline changes). Ship in ~1 week for immediate "feels different" impact.

---

## Combined Architecture Vision

```
Sources → [Supadata | Whisper | Gemini Multimodal | Captions] → Doc 0
  → Quick: Single Gemini call (extract+synthesize) → Brief → [Sonnet polish async]
  → Full:  Per-source extraction (parallel) → Validate → Gap+Synthesis (merged)
           → Assembly → Brief → [Sonnet polish async]
  → On-demand: Script/Blog/Social (Gemini draft → Sonnet edit)
  → Stream everything via SSE
```

---

## Unresolved Questions

1. How does Gemini access YouTube video for multimodal fallback? (download vs grounding API vs frame extraction)
2. Sonnet editorial prompt design — needs careful testing to avoid stripping substance
3. Quick mode: how degraded is output quality without per-source isolation? Needs A/B testing
4. Source caching: invalidation strategy for updated videos/articles?
5. Credit pricing: does Quick=1 / Full=3 match actual cost ratios?
6. Should Quick mode skip Doc 0 entirely or generate a minimal version?
7. Voice mimicry in scripts — does Sonnet preserve voice profile during editorial pass?
