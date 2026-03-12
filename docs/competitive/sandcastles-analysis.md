# Sandcastles.ai — Competitive Analysis + Research Agent Source Discovery Plan
**Date:** 2026-03-11
**Last Updated:** 2026-03-12 (added validation notes from independent fact-check)
**Source:** Network tab reverse-engineering + 10-claim fact-check + independent web research on search APIs
**Purpose:** Understand Sandcastles, define Research Agent's position, and plan the source discovery build

> **Validation Notes (2026-03-12):** Claims in this document were cross-referenced against
> independent sources. Validated claims are marked ✅, corrections are marked ⚠️, and
> unverifiable claims (from network tab observation) are marked 🔍. See inline notes throughout.

---

## 1. What Sandcastles.ai Is

A content creation tool for video creators. ⚠️ **Correction:** Sandcastles positions itself specifically for **short-form video** (Reels, TikTok, YouTube Shorts), not general video creation. Their tagline is "Create viral short-form videos in seconds." Plans range $39-149/month (annual billing). Their workflow:

```
User writes notes/prompt
        ↓
Research (their pipeline, ~36s)
        ↓
Outline (separate step, user-triggered)
        ↓
Script (separate step, user-triggered)
```

Their core entity is a **"story"** (UUID-based) — equivalent to Research Agent's `job`.

---

## 2. Their Tech Stack (Confirmed from Network Tab + Public Site)

> 🔍 **Validation note:** Tech stack claims below are from direct network tab observation during
> a live session. These cannot be independently verified from public sources but are consistent
> with the observed XHR payloads and JS bundles.

| Layer | Technology |
|-------|------------|
| Marketing site | Webflow |
| App frontend | React (confirmed: `index.jsx`, `hook.jsx`, `style.jsx`, Sentry React SDK 8.55.0) |
| API style | REST (plain XHR, no GraphQL) |
| Auth | WorkOS (org-based, B2B multi-tenant) |
| Error tracking | Sentry |
| Analytics | PostHog + Google Analytics |
| Infrastructure | Cloudflare CDN |

---

## 3. Their Data Model (From Actual Response Payload)

```json
{
  "uuid": "8756ecf3-8e37-4958-be36-a7a566b0a59d",
  "topic": "Films Don't Look Like Films",
  "notes": "i want to discuss why films dont look like films anymore using jurassic park as an example",
  "context": "### Executive Summary\n...(entire research output as one flat markdown string)",
  "form": "short",
  "kind": "original",
  "status": "draft",
  "version": 4,
  "outline": null,
  "script": null,
  "style_uuid": null,
  "images": ["https://youtube.com/...", "https://reddit.com/...", "..."],
  "organization_uuid": "c5e027a9-68b2-43af-b53c-ce1341672c1f",
  "should_research": true,
  "deleted": false,
  "created_at": "2026-03-11T16:34:16.550371",
  "updated_at": "2026-03-11T16:34:53.104168"
}
```

**Key observations:**
- `context` = entire research output as a **flat markdown string** — not structured JSON, no typed semantic units
- `images` = source URLs (misnamed — was probably for images originally, repurposed for sources)
- `outline` and `script` are `null` — separate pipeline steps not yet triggered
- `version: 4` — they version stories
- `channel_video_uuid` exists as a field — they can base a story on an existing channel video (unreleased feature or separate mode)

---

## 4. Their API Endpoints (From Network Tab)

```
story/                                          Core entity creation/fetch
story/?story_uuid={uuid}                        Fetch specific story
hooks?story_uuid={uuid}                         Which hook templates applied to this story
hook_frameworks?search=&tags=&page=0            Library of hook templates (21.7 kB, paginated)
style_frameworks?story_uuid={uuid}&page=0       Library of style templates (24.8 kB, paginated)
versions?story_uuid={uuid}                      Version history (called twice — on load + after research)
research?story_uuid={uuid}                      THE RESEARCH CALL — 36 seconds, 9.8 kB response
current_org_usage                               Billing/usage at org level
```

---

## 5. Their Research Output Format (Reverse-Engineered System Prompt Structure)

Every section follows a rigid template enforced by their system prompt. This is 100% prompt engineering:

```
### Executive Summary
[2-3 sentence thesis with strong committed POV — not neutral]

### Key Context
[Background + bullet timeline of key moments]

### Key Facts
[Fact] ▸ [Relatable analogy] (Shock Score X/10)
[Shock Score = how surprising/engaging is this to a general audience]

### Interesting Stats And Findings
[Same format as Key Facts]

### Common Misconceptions Vs Reality
Most people think [X], but actually [Y] (Shock Score X/10)

### Analogies And Simple Comparisons
[Concept] → [Analogy]

### How It Works
[Plain-language explanation, written for a 16-year-old on YouTube]

### Real World Use Cases
[Named examples with commentary]

### Major Trends
[Named trend]: [Explanation]

### Future Implications
Optimistic: / Realistic: / Skeptical:

### Potential Concerns And Downsides
[Named concern]: [Explanation]

### Why It Matters
[Emotional closer]

### Video Angles
[Clickable title] — [Description] (Shock Score X/10)

### Contrast Moments
Most believe [X], the twist is [Y]

### Open Questions
[Comment-bait questions for YouTube audience]
```

---

## 6. How Their Research Actually Works

**Short answer: mostly LLM training data, not real web research.**

### Fact-check results (10 claims, Jurassic Park topic)

> 🔍 **Validation note:** The fact-check below was performed during the original analysis session
> by comparing Sandcastles' output against known facts. The methodology (checking specific numerical
> claims against reliable sources) is sound, but the "actual figures" column is itself unverified
> against primary sources and should be treated as best-effort cross-referencing, not definitive.

A full fact-check of 10 specific claims from their output against real sources:

| Claim | Their output | Actual figure | Verdict | Source type |
|-------|-------------|---------------|---------|-------------|
| CGI runtime | 4 minutes | ~6 minutes | **Wrong** (LLM confabulation) | LLM training data |
| Render time per frame | 12 hours | 2–6 hours | **Wrong** (inflated for drama) | LLM training data |
| 35mm film resolution | 6K–8K | ~4K standard | **Wrong** (inflated) | LLM training data |
| 63 VFX shots | 63 shots | 63 shots | Correct | LLM training data |
| Dinosaur Input Device | accurate description | accurate | Correct | LLM training data |
| T-Rex floor shaking | partly true | real, weight figures unreliable | Partly true | LLM training data |
| Gallimimus = first CGI daylight | partly true | significant, not definitively "first" | Partly true | LLM training data |
| Film = chemical reaction | correct | textbook fact | Correct | LLM training data |
| Flat lighting for VFX | partly true | real practice, oversimplified | Partly true | LLM training data |
| Jurassic World: Rebirth criticism | partly true | criticism exists, framing vague | Partly true | Requires web search |

**9 of 10 claims came from LLM training data alone. No live web search required.**

The errors are all inflated in the direction of "more impressive/shocking" — classic LLM confabulation pattern, not scraping errors.

### The smoking gun: the deleted YouTube video

Their `images` field listed `https://www.youtube.com/watch?v=9S_vE28nBfQ` as a source. That video **no longer exists — deleted**. If they had actually fetched it, their pipeline would have errored. They listed it anyway.

> 🔍 **Validation note:** The deleted video claim was verified during original analysis.
> This is strong evidence that Sandcastles does not deeply fetch/process sources.
> However, this could also mean they cache results and the video was deleted after caching.

**Conclusion:** They find URLs via a light search but never read the content. The `images` field is populated with search result URLs as a plausibility signal, not actually-processed sources.

### Their real pipeline

```
User prompt + notes
        ↓
Light web search (Tavily or Perplexity) → get 3-4 URLs
Store URLs in "images" field (never deeply fetched or read)
        ↓
One large LLM synthesis call:
  - User topic/notes as input
  - URL titles/snippets only (not full content)
  - Massive system prompt defining all sections + Shock Score instructions
        ↓
Output (~9.8 kB flat markdown, ~70% factually accurate)
```

**Total time: ~36 seconds**
- Search API: ~3–5s
- One large LLM call (GPT-4o or Claude): ~30s

---

## 7. What Makes Their Output Feel "More Polished"

The polished feeling is **100% prompt engineering, not research quality.**

Their system prompt enforces:
1. Every fact gets a relatable analogy: `[fact] ▸ [analogy] (Shock Score X/10)`
2. Creator vocabulary throughout (Video Angles, Contrast Moments — not "key points")
3. Strong committed thesis — no academic hedging
4. Casual, accessible language for a general YouTube audience
5. Engagement optimization baked in (Shock Score = how surprising is this?)

The "polish" is a formatting template, not deeper research. Their research quality is actually lower than Research Agent's.

---

## 8. Head-to-Head Comparison

| | Sandcastles.ai | Research Agent |
|---|---|---|
| Research depth | Shallow (LLM + URL titles only) | Deep (content actually fetched + parsed) |
| Fact accuracy | ~70% (several wrong numbers confirmed) | High (quote verification + LLM judge) |
| Source attribution | Fake (cites unread/deleted URLs) | Real `source_ids` on every extracted item |
| Quote verification | None | Verbatim fuzzy matching |
| Output format | Excellent for creators | Built for researchers |
| Research reliability | Consistent (works every time) | **Source discovery was broken** |
| Async architecture | No (36s blocking XHR) | Yes (Celery queue) |
| Template library | Rich (hook + style frameworks) | None |
| Version control | Yes | Not yet |
| Org-based billing | Yes | TBD |

---

## 9. The 2026 Market Reality

⚠️ **Validation note:** The market thesis below is strategic opinion, not independently verified market data.
The named creators (Johnny Harris, etc.) are real long-form YouTube creators, but Sandcastles explicitly
targets **short-form** content (Reels, TikTok, Shorts), which is a different segment than what these
creators primarily produce. The competitive positioning is valid, but the market overlap may be smaller
than implied.

The line between creator and journalist is gone. YouTube creators are doing independent investigative journalism. Journalists are making YouTube videos. Serious creators (Johnny Harris, Patrick Boyle, Legal Eagle, Wendover Productions) have brand reputations entirely dependent on being factually correct. Sandcastles' wrong facts would destroy their credibility in their comment sections.

**Sandcastles serves:** entertainment creators who need fast inspiration, don't fact-check, and are optimizing for views.

**Research Agent's actual market:** serious creators who cannot afford to be wrong on camera, need verified sources for their description box, and want the engaging creator format built on top of accurate research.

This is a distinct and growing segment. It is not the same market as Sandcastles.

---

## 10. Research Agent's Unique Position

```
Sandcastles:    Fast + engaging format  BUT  wrong facts, no real sources
Research Agent: Accurate + attributed   BUT  boring output, source discovery broken

The gap to close: (1) fix source discovery, (2) add creator output format
The core architecture is already correct.
```

What serious creators need that no tool currently provides:
- Creator-friendly framing (Shock Scores, Video Angles, Contrast Moments, Analogies)
- **Plus** facts they can defend on camera
- **Plus** real sources for their YouTube description box

---

## 11. Why Source Discovery Was Breaking (Root Cause Analysis)

The old system had four competing search clients (Tavily, Perplexity, Exa, Serper) feeding into a `planning.py` + `discovery.py` stage. All four were removed in the 2026-01-19 cleanup because the pipeline was unreliable.

**Two documented failure modes:**

**Failure 1 — Irrelevant sources ("Barney problem")**
The system would find 1 relevant source and 3-4 completely irrelevant ones — e.g., confusing Barney the Dinosaur with Barney Stinson even with a specific prompt. This is a **named entity disambiguation** failure, documented in RAG pipeline research. Neither Tavily nor Exa nor any search API solves this at the retrieval layer. The fix is **query context** — generating search queries that carry enough disambiguating information that the search engine cannot confuse them. "Barney Stinson fictional character How I Met Your Mother CBS sitcom" vs. "Barney Stinson."

**Failure 2 — Too many failure points**
Four competing clients + complex orchestration = too many things that could fail. Parallel fetching, timeouts, inconsistent responses all compounded. The fix is one client, sequential execution, hard limits, and skip-on-fail never crash-on-fail.

**Current state of the codebase (as of 2026-03-11):**
- ALL search clients removed: Tavily, Perplexity, Exa, Serper — gone
- YouTube search already exists: `search_youtube_videos()` in `youtube_client.py` ✓
- Content fetching exists: `JinaReaderClient` in `jina_reader_client.py` ✓
- Transcript fetching exists: `supadata_client.py` + `transcripts.py` ✓
- Legacy pipeline code: fully deleted (not archived), not recoverable
- **Missing: any web search client and any autonomous discovery stage**

---

## 12. Validated Architecture: Two-Phase Research Pipeline

### Why two phases?

**OpenAI Deep Research** uses this exact pattern in production (⚠️ **Corrected:** February 2025 release, not December 2025): clarify/discover first → deep process second. ✅ An academic study (HLER, arXiv:2603.07444, March 2026) showed a human review gate between phases improved research question feasibility from **41% → 87%** (⚠️ **Clarification:** this metric is specifically about *research question feasibility in economics*, not general "output feasibility" — the study is "Human-in-the-Loop Economic Research via Multi-Agent Pipelines for Empirical Discovery"). This is not theoretical — it is a documented production pattern.

LangGraph's `interrupt()` function is the standard open-source implementation. The pattern is called "Human-in-the-Loop (HITL)" in the agentic workflow literature.

### The architecture

```
PHASE 1 — Fast Discovery (~$0.01, ~30-40s)
══════════════════════════════════════════════════════════

User submits topic + notes (free-text, any length)
        ↓
Query Generator (Gemini Flash, fast LLM call)
  Generates 3 SPECIFIC, CONTEXT-RICH web search queries
  + 1 YouTube-specific query
  Rule: queries must carry enough context to disambiguate
  Example: NOT "Barney" — YES "Barney Stinson fictional character
           How I Met Your Mother CBS sitcom Neil Patrick Harris"
  Note: Exa has no 400-char query limit (unlike Tavily)
        ↓
Source Finder (parallel):
  → Exa search (auto mode, 10 results)       — web articles
  → search_youtube_videos() [already exists] — video sources
  Total: 10-15 candidate sources
        ↓
Binary Relevance Filter (Gemini Flash, $0.0004)
  NOT a 0-10 score — LLM numeric scores are documented as
  uncalibrated and inconsistent across runs (Voyage AI research)
  Instead: binary "relevant / not relevant" + one sentence why
  Trust Exa's own ranking order; use LLM only to discard clear misses
  Keep: top 5 "relevant" results by Exa ranking
  Drop: anything classified "not relevant"
        ↓
Phase 1 Synthesis (Gemini 2.5 Flash, ~$0.002)
  Light, fast synthesis in creator format (see Section 13)
  Shows user: what was found, why each source is relevant,
  key angles, initial facts
        ↓
SOURCE BRIEF displayed to user
User approves / removes individual sources
(This gate is the fix for the Barney problem propagating into
expensive deep processing)

══════════════════════════════════════════════════════════
PHASE 2 — Deep Pipeline (existing code, zero changes, ~$0.09)
══════════════════════════════════════════════════════════

Takes user-approved sources from Phase 1
↓
Existing pipeline runs unchanged:
source_identity → semantic_extraction → quote_verification
→ llm_judge → semantic_validation → gap_analysis
→ semantic_synthesis → document_assembly
↓
Doc 0 (Source Ledger) + Doc 1 (Jump-Start) + Doc 2 (Semantic Brief)
```

### Why Exa, not Tavily (data-backed)

⚠️ **Validation note:** These benchmarks are widely cited but primarily originate from Exa's own
comparison page (exa.ai/versus/tavily) and a "Fortune 100 enterprise evaluation" cited by Exa.
The DEV Community article and Humai Blog articles also reference these numbers but do not appear
to have run independent benchmarks. Treat as Exa-sourced marketing data, not independent third-party validation.

| | Tavily Advanced | Exa (auto mode) |
|---|---|---|
| Complex retrieval accuracy | 71% | **81%** |
| SimpleQA accuracy | 93.3% | **94.9%** |
| Response time | 1.9–4.5s | **1.2–1.7s** | ⚠️ Exa's own "Fortune 100" benchmark reports p95 of 1.4-1.7s (not 1.2s) for Exa, 3.8-4.5s for Tavily |
| Cost per call (10 results) | $0.016 | **$0.007** |
| Query length limit | **400 characters** ✅ | None documented ✅ |
| Content returned | 500-char chunks (default) | Highlights + Contents API |
| Disambiguation | Neural only | `auto` picks neural OR keyword |
| Full page content | Extra flag required | Separate Contents API ($0.001/page) |

Exa is cheaper, faster, more accurate, AND has no query length limit (critical for the disambiguation fix). The `auto` mode is specifically useful for entity queries — it will switch to keyword mode for highly specific named-entity searches where semantic search underperforms.

Sources: DEV Community SERP API comparison (dev.to/ritza), Exa internal benchmarks (exa.ai/versus/tavily),
Humai Blog API comparison 2025 (humai.blog). ⚠️ All three sources cite similar numbers likely originating
from Exa's own benchmarks. ✅ Tavily 400-char limit independently confirmed via Tavily Community forums
and API docs. ✅ Exa pricing ($0.007/search with 10 results) confirmed via exa.ai/pricing.

### Why binary relevance filter, not 0-10 LLM score

✅ Research finding (Voyage AI, October 22, 2025 blog post "The Case Against LLMs as Rerankers"; ZeroEntropy analysis "Should You Use LLMs for Reranking?"):
- LLM pointwise scores are "uncalibrated and noisy" — the same document can score 7 in one call and 5 in another
- Positional bias: LLMs score results higher when they appear earlier in the prompt
- ✅ Cross-encoder rerankers are 60x cheaper and 48x faster than LLM scoring (confirmed via Voyage AI X post)
- However: cost of LLM scoring is $0.0006 per call — essentially free — so cost is not the issue

**Recommendation:** Use binary LLM classification ("relevant / not relevant") to discard obvious mismatches. Trust Exa's own ranking order for the kept results. Do not use numeric scores. A dedicated cross-encoder reranker (e.g., Cohere Rerank, Voyage Rerank) could replace this at even lower cost and higher reliability if needed later.

### Why the query context approach fixes the Barney problem

From research literature: named entity disambiguation is a documented, named failure mode in RAG pipelines. **Neither Tavily nor Exa nor any search API solves disambiguation at the retrieval layer.** The fix must happen at the query generation layer.

Evidence:
- Exa documents that pure semantic search underperforms on specific entity lookups and provides `keyword` and `auto` modes for this reason
- GraphRAG addresses this with explicit NER + entity disambiguation before retrieval — standard RAG does not do this
- Query expansion research (arXiv 2025): "when the query is genuinely ambiguous, the LLM will pick one interpretation and narrow search coverage, potentially making things worse" — meaning a vague query passed to search makes the problem worse, not better

The fix: the query generator must be given the **full original prompt** (not just the topic keyword) and instructed to generate queries that include entity context. A prompt like "I want to make a video about why films don't look like films anymore using Jurassic Park as an example" contains enough context for the query generator to produce "Jurassic Park 1993 CGI Steven Spielberg ILM visual effects" rather than just "Jurassic Park."

---

## 13. Creator Output Format (Phase 1 Synthesis)

This is the feature that makes Phase 1 feel like Sandcastles but with real sources underneath. These sections should be generated in Phase 1 and refined/expanded in Phase 2.

**Sections to add to output (all derived from existing semantic units):**
- **Analogy for every key point:** `[fact] ▸ [relatable analogy]`
- **Engagement Score** (equivalent to Shock Score): how surprising/useful is this for a creator (1-10)
- **Video Angles:** 4 titled video concepts with engagement scores
- **Contrast Moments:** "Most people think X / the twist is Y" format
- **Casual language rewrite:** existing semantic brief language is academic; Phase 1 output should be casual and accessible
- **Sources box:** "Here are your verified sources for your description box" — this is the differentiator Sandcastles cannot provide

This is a **new output template** layered over existing semantic units — not a new pipeline. The research quality comes from Phase 2. The creator-friendly format is applied at the output stage.

---

## 14. Validated Cost Structure

> ✅ **Validation note (2026-03-12):** Cost figures checked against current API pricing.
> Gemini 2.5 Pro: $10/M output tokens, $1.25/M input tokens → 8K output ≈ $0.08 + input costs ≈ $0.088. Confirmed.
> Exa search with 10 results + contents: $0.007/call. Confirmed via exa.ai/pricing.
> Gemini 2.5 Flash costs not independently verified but order-of-magnitude reasonable.

Costs per full two-phase pipeline run:

| Step | What you get | Cost |
|---|---|---|
| Exa search (10 results, highlights) | 10 relevant web results with query-aligned excerpts | $0.007 |
| YouTube Data API search | Video results (quota units, not $) | ~free |
| Binary relevance filter (Gemini Flash) | Relevant/not relevant for 10-15 snippets | ~$0.0004 |
| Phase 1 synthesis (Gemini 2.5 Flash, ~2K output) | Source Brief, creator-formatted | ~$0.002 |
| **Phase 1 total** | | **~$0.01** |
| Phase 2 deep pipeline (existing) | Doc 0 + Doc 1 + Doc 2, fully verified | ~$0.09 |
| **Full pipeline total** | | **~$0.10** |

**Key finding:** The Gemini 2.5 Pro synthesis call dominates the cost at ~$0.088 per 8K-output-token call. Every search, filtering, and relevance step combined costs less than $0.01. Optimization effort should focus on the synthesis call (model routing, output length control) not the retrieval steps.

---

## 15. What Needs To Be Built

### New files required

**`backend/integrations/exa_client.py`** (~80 lines)
- Re-add Exa client (was deleted 2026-01-19, API key still in `.env`: `EXA_API_KEY=66bcc3f0-...`)
- Methods: `search(query, num_results, use_autoprompt)`, `get_contents(urls)`
- Use `auto` mode for search type selection
- Follow existing client patterns (loguru, error handling, rate limiting)

**`backend/pipeline/stages/autonomous_discovery.py`** (~200 lines)
- Takes: `topic` (str), `notes` (str), `max_sources` (int, default 5)
- Query generator: calls Gemini Flash with full prompt context → returns 3 web queries + 1 YouTube query
- Source finder: calls Exa + `search_youtube_videos()` in parallel → 10-15 candidates
- Relevance filter: calls Gemini Flash with binary classification → drops irrelevant
- Returns: list of approved candidate sources with metadata (url, title, why_relevant)

**New API endpoint** in `backend/app/routes/jobs_routes.py`
- `POST /jobs/discover` — takes topic + notes, runs Phase 1, returns Source Brief + candidates
- `POST /jobs/discover/{discovery_id}/confirm` — user approves sources, triggers Phase 2

**Frontend (separate session)**
- Source Brief display component
- Per-source approve/remove UI
- "Run deep research on approved sources" button

### Existing files that need changes

**`backend/config.py`**
- Add `EXA_API_KEY` field and `require_exa()` method (key already in `.env`)

**`backend/utils/rate_limiter.py`**
- Add rate limit config for Exa (1,000 req/month free tier, paid tier varies)

### What does NOT need to change

The entire Phase 2 pipeline (worker.py, all stages, all models) is untouched. Phase 1 produces a list of source URLs. Phase 2 already knows how to process a list of source URLs. The bridge is just the confirmed source list.

---

## 16. Build Priority Order

1. **`exa_client.py`** — re-add Exa integration, add to config.py
2. **`autonomous_discovery.py`** — query generation + search + binary relevance filter
3. **New API endpoints** — discover + confirm
4. **Creator output format** — new synthesis output template (Phase 1 brief)
5. **Frontend** — Source Brief UI + approve/remove sources

Do not start frontend until backend endpoints are tested and stable.

---

## 17. Open Questions for Next Session

1. Should Phase 1 synthesis use Gemini 2.5 Flash or 2.5 Pro? Flash is ~10x cheaper but produces shorter output. For a quick Source Brief, Flash is likely sufficient.
2. Should the binary relevance filter be its own LLM call or bundled into the Phase 1 synthesis prompt? Bundling saves a round trip but makes the prompt more complex.
3. Max sources for Phase 2: currently the pipeline handles multiple sources. Is there a documented upper limit on sources that produces diminishing returns on quality?
4. Should Exa's `get_contents()` (full page fetch) replace Jina for article content, or should Jina remain as fallback? Exa Contents API is $0.001/page, Jina is free tier.
5. The Phase 1 Source Brief — does it go into the existing job model or is it a new entity (like a `discovery` record) that a job can be created from?

---

*Last updated: 2026-03-12*
*Analysis based on: network tab observation, response payload inspection, 10-claim fact-check,*
*independent web research on Tavily/Exa/Perplexity benchmarks, RAG pipeline failure mode literature,*
*query disambiguation research, two-phase pipeline production examples (OpenAI Deep Research, HLER study)*
*Validation pass (2026-03-12): cross-referenced against arXiv, Voyage AI blog, Exa/Tavily pricing pages,*
*OpenAI release announcements, Sandcastles public marketing. Corrections applied inline.*
