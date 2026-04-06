# Validation Report: Product Viability Brainstorm

**Date:** 2026-04-06
**Purpose:** Ground-truth check on every proposal in `brainstorm-260405-1617-product-viability-overhaul.md`
**Verdict scale:** GROUNDED / PARTIALLY GROUNDED / FLUFF / WRONG

---

## Claim 1: SSE Streaming from Celery → FastAPI → Next.js

**Verdict: GROUNDED — but architecture needs Redis pub/sub bridge**

**What we said:** Add `GET /jobs/{id}/stream` SSE endpoint, stream sections progressively.

**Reality:**
- Celery workers run in separate processes. They CANNOT directly push SSE events to FastAPI.
- **Required pattern:** Celery worker → publishes events to Redis pub/sub channel → FastAPI SSE endpoint subscribes to that channel → streams to frontend.
- This is a well-documented, production-proven pattern. Multiple tutorials and libraries exist (fastapi-sse-events, manual Redis pub/sub).
- FastAPI has native SSE support via `StreamingResponse` with async generators.
- Next.js `EventSource` API handles SSE natively.

**What we got wrong:**
- We said "Medium effort." It's actually **medium-high** for a solo dev because:
  - Every pipeline stage needs to emit granular events (not just stage-level)
  - Frontend needs progressive rendering components (skeleton → streaming text → final)
  - Error handling for SSE reconnection, missed events
  - Redis pub/sub adds an infra dependency (already have Redis for Celery broker, so manageable)

**Revised estimate:** 2-3 weeks for a solo dev (not "~1 week" as implied).

---

## Claim 2: Gemini Multimodal YouTube Fallback

**Verdict: GROUNDED — Gemini can process YouTube URLs directly via API**

**What we said:** Use Gemini 2.5 Pro multimodal to analyze YouTube videos when Supadata fails. Open question about how Gemini accesses the video.

**Reality:**
- **Gemini 2.5 Pro CAN take a YouTube URL directly in the API call.** No download needed.
- The model "watches" the video (samples ~1 frame/sec, 66 tokens/frame) and processes audio natively.
- Supports up to ~6 hours of video content in a single call.
- This is a documented, supported feature — not a hack.

**What we got wrong:**
- We listed this as an "open question." It's actually solved — direct YouTube URL input works.
- However, **cost concern is real and undersized:**
  - 1 hour video ≈ 3,600 frames × 66 tokens = ~238K tokens input just for video
  - At Gemini 2.5 Pro pricing, that's meaningful cost per video
  - Our "cost guard for videos >X minutes" is essential, not optional

**What's still genuinely open:**
- Quality of multimodal transcript vs. Supadata/Whisper actual transcript. Gemini gives you *understanding* of what was said, not verbatim text. The `MULTIMODAL_INFERRED` confidence tier is the right call.
- Gemini has reported quality degradation on long-context tasks (260K+ tokens). A 2-hour video could hit this threshold.

**Revised recommendation:** Cap multimodal fallback at 60-minute videos. Beyond that, fall through to VIDEO_ONLY.

---

## Claim 3: Sonnet 4.6 Editorial Pass

**Verdict: GROUNDED — multi-model draft→edit is a proven pattern with real quality gains**

**What we said:** Gemini drafts → Sonnet 4.6 edits as creative director. +15-20% quality.

**Reality:**
- Multi-model pipelines (draft model → edit model) show **10-30% speed improvement** and **+15-20% quality improvement** in documented production use cases.
- CrewAI, LangGraph, and other frameworks explicitly support this pattern.
- The "dual model" approach (specialized drafter + specialized editor) is faster and more accurate than single-model self-editing.

**Concrete costs (Sonnet 4.6, April 2026):**
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens
- A 5,000 token script with ~2,000 token edit output = ~$0.045 per edit pass
- With prompt caching (10% input cost on cache hit): even cheaper on repeated patterns
- Batch API available at 50% discount for non-real-time processing

**Hallucination risk:**
- Real but manageable. The prompt constraint ("preserve all facts/quotes/citations, never add info") is the standard mitigation.
- Post-edit fact-preservation validation (diff the factual claims before/after) adds safety net.
- Risk is LOWER than self-editing because Sonnet has no knowledge of the original sources — it can only work with what Gemini provided.

**What we got wrong:**
- Background async delivery ("polished version arrives 15-20s later") is sound architecturally but the UX needs design thought. How does the user know a better version exists? Toast notification? Auto-replace? Version toggle?

---

## Claim 4: Quick Mode — Single Gemini Call for All Sources

**Verdict: PARTIALLY GROUNDED — feasible but quality degradation risk is REAL**

**What we said:** Send all sources in one Gemini call, extract+synthesize together, 30-60s.

**Reality:**
- Gemini 2.5 Pro has 1M token context window (2M coming). 5 YouTube transcripts × 10K tokens = 50K tokens. Easily fits.
- **But quality degrades in long context.** Users report:
  - Performance degradation threshold dropped from 650K-700K to ~260K tokens
  - Model ignores mid-context instructions
  - Defaults to generic, low-effort answers with large contexts
  - Hallucinations increase with document count

**What we got wrong:**
- "30-60 seconds" timing is **optimistic but plausible** for 3-5 short sources. For 5+ sources with long transcripts, it's more like 60-90s.
- The bigger problem: **per-source isolation exists for a reason** (Architecture Rule 1). Without it, cross-source attribution breaks down. The system can't tell which claim came from which source. This isn't just a quality issue — it breaks the provenance chain that Doc 2-7 depend on.

**Revised recommendation:**
- Quick mode should use **source labels in the prompt** ("SOURCE_1: ...", "SOURCE_2: ...") and require the model to tag outputs with source IDs. This is a middle ground — not full isolation, but structured enough to maintain basic attribution.
- Cap at 3-5 sources for Quick mode. Beyond that, force Full mode.
- Quality label should say "Quick Research — citations may be approximate" to set expectations.

---

## Claim 5: Source Caching by URL Hash (7-day TTL)

**Verdict: PARTIALLY GROUNDED — technically sound, but cache hit rate will be LOW**

**What we said:** Cache Source Identity + Semantic Extraction by URL hash. 10 users = 1 fetch + 9 cache hits.

**Reality:**
- **Technically straightforward.** Redis or Supabase can store JSON blobs keyed by URL hash. TTL is trivial.
- **Cache hit rate will be LOW for a research tool.** Unlike search engines where millions query "weather NYC," research queries are highly unique. The chance of two users submitting the same YouTube URL in 7 days is small for a niche tool.
- **Where it DOES help:**
  - Trending/viral content (same video researched by many creators)
  - User re-running their own job with different options (iteration)
  - "Expand sources" iteration reusing already-fetched sources
- **Stale data risk:** YouTube videos can be edited, articles updated, pages taken down. 7-day TTL is reasonable but should include a "force refresh" option.

**What we got wrong:**
- The "10 users = 9 cache hits" framing is misleading for early-stage product. More realistic: caching saves 20-30% of fetches (mostly from user iterations, not cross-user overlap).
- The real win is **self-caching during iterations** — user runs Full mode, then requests a Script. The Script generation shouldn't re-fetch and re-extract the same sources.

**Revised recommendation:**
- Cache per-job (reuse within same job's iterations) — high hit rate, zero stale risk
- Cache per-URL globally — nice to have, lower priority
- Storage: Redis for hot cache (fast), Supabase for cold storage (persistent)

---

## Claim 6: Single-Screen Input (Kill 4-Step Wizard)

**Verdict: GROUNDED — standard UX best practice**

No technical validation needed. Every successful AI product (Perplexity, ChatGPT, NotebookLM) uses single-input UX. The 4-step wizard is objectively worse for user conversion. Auto-detecting URLs from pasted text is trivial (regex).

---

## Claim 7: One Hero Document + Upsells

**Verdict: GROUNDED — standard product design**

No technical validation needed. Showing 4 docs by default is information overload. Focusing on Research Brief with upsell buttons for Script/Blog/Social is standard SaaS pattern. No pipeline changes required — purely frontend.

---

## Claim 8: Product Tiers & Credit Pricing

**Verdict: PARTIALLY GROUNDED — pricing needs cost basis validation**

**What we said:** Free ($0, 10 Quick), Pro ($19, 50 credits), Studio ($49, 200 credits).

**Reality — actual cost per job:**

| Job Type | Gemini Calls | Gemini Cost | Sonnet Cost | Supadata/Whisper | Total |
|----------|-------------|-------------|-------------|------------------|-------|
| Quick (3 sources) | 1 call, ~30K in, ~3K out | ~$0.005 | ~$0.045 (edit) | ~$0.10 | ~$0.15 |
| Full (5 sources) | 7 calls, ~80K in, ~15K out | ~$0.015 | ~$0.045 (edit) | ~$0.25 | ~$0.31 |
| Script add-on | 1 Gemini + 1 Sonnet | ~$0.01 + $0.045 | — | — | ~$0.055 |

**Margin analysis:**
- Quick=1 credit: If 10 free credits/mo → $1.50 cost per free user/mo. Sustainable if conversion >5%.
- Pro=$19/mo, 50 credits: At ~$0.15-0.31/credit → $7.50-15.50 cost → **55-80% margin**. Healthy.
- Studio=$49/mo, 200 credits: At ~$0.15-0.31/credit → $30-62 cost → **margin depends heavily on usage mix**. Could be thin if users hit full mode + scripts on every credit.

**What we got wrong:**
- Credit pricing is roughly right but Studio tier margin is tight if heavy users max out. Need usage caps or overage pricing.
- Free tier cost ($1.50/mo/user) is fine for a waitlist phase but needs monitoring at scale.

---

## Claim 9: Merge Gap Analysis + Synthesis

**Verdict: GROUNDED — low risk, clear benefit**

Gap analysis (what's missing) and synthesis (cross-source themes) both operate on the same aggregated extraction data. Combining them into one prompt is straightforward. The output schema just includes both `gaps` and `synthesized_themes` sections. Temperature can be 0.2 (current synthesis value). Saves 1 LLM round-trip (~8s).

No technical risk. This is a prompt engineering change.

---

## Summary Scorecard

| # | Proposal | Verdict | Notes |
|---|----------|---------|-------|
| 1 | SSE Streaming | **GROUNDED** | Needs Redis pub/sub bridge; 2-3 weeks not 1 |
| 2 | Gemini YouTube Fallback | **GROUNDED** | Direct URL works; cap at 60min; cost is real |
| 3 | Sonnet Editorial Pass | **GROUNDED** | ~$0.045/pass; proven pattern; needs UX for version delivery |
| 4 | Quick Mode | **PARTIALLY** | Feasible but quality/attribution degrades; cap 3-5 sources |
| 5 | Source Caching | **PARTIALLY** | Per-job caching high value; cross-user cache hit rate low |
| 6 | Single-Screen Input | **GROUNDED** | Standard UX, no risk |
| 7 | One Hero Doc | **GROUNDED** | Standard UX, no risk |
| 8 | Credit Pricing | **PARTIALLY** | Margins healthy on Pro; Studio tier needs usage monitoring |
| 9 | Merge Gap+Synthesis | **GROUNDED** | Simple prompt change, no risk |

## Revised Priority (Post-Validation)

| # | Change | Confidence | Revised Effort |
|---|--------|-----------|----------------|
| 1 | Single-screen input | HIGH | 3-5 days |
| 2 | One hero doc + upsells | HIGH | 3-5 days |
| 3 | Merge gap+synthesis, lazy Doc 3 | HIGH | 1-2 days |
| 4 | SSE streaming | HIGH | 2-3 weeks |
| 5 | Sonnet editorial pass | HIGH | 1 week |
| 6 | Quick mode (with source labels) | MEDIUM | 1-2 weeks |
| 7 | Gemini multimodal fallback | HIGH | 3-5 days |
| 8 | Per-job source caching | MEDIUM | 3-5 days |
| 9 | Credit system + tiers | MEDIUM | 1-2 weeks |

**Total realistic timeline for solo dev: 8-12 weeks** (not the implied "ship UX in 1 week" from brainstorm)

---

## Unresolved Questions (Validated)

1. ~~How does Gemini access YouTube video?~~ **RESOLVED:** Direct URL input via API.
2. Sonnet editorial prompt design — still needs testing. Low risk but needs iteration.
3. Quick mode quality — **ELEVATED CONCERN.** Gemini long-context degradation is well-documented. A/B test essential before shipping.
4. Source caching invalidation — per-job caching sidesteps this. Global cache needs "force refresh."
5. Credit pricing vs actual costs — margins look healthy but Studio tier needs usage caps.
6. Quick mode Doc 0 — generate minimal version with source labels only (no full extraction).
7. Voice mimicry + Sonnet — **NEW CONCERN.** If Gemini draft includes voice profile styling, Sonnet edit pass may normalize it out. Need prompt testing.
8. **NEW:** Gemini quality regression — multiple user reports of degradation at 260K+ tokens. Quick mode should hard-cap total input tokens.
