# Brainstorm Report: Research Agent — Product Viability Overhaul

**Date:** 2026-04-05 (updated 2026-04-06)
**Status:** Brainstorm — validated, ready for planning
**Participants:** Maz + Claude
**Context:** Research Agent feels clunky; need middle ground between OpenClaw simplicity and full pipeline depth
**Supporting reports:**
- `researcher-260406-1233-brainstorm-validation.md` — Technical validation of all proposals
- `researcher-260406-1252-business-viability-analysis.md` — Cost modeling, unit economics, competitive analysis
- `researcher-260405-1552-ai-research-product-ux-patterns.md` — UX patterns from successful AI products
- `researcher-260405-1533-multi-model-pipeline-optimization.md` — Multi-model pipeline patterns

---

## Problem Statement

Research Agent has a powerful 8-stage pipeline producing 4-7 documents with per-source isolation, quote verification, and confidence ceilings. But it feels like a prototype, not a product. The OpenClaw version (Gemini research → draft → Sonnet edit) is fast and "mostly accurate" but shallow. Need a middle ground: fast enough to feel polished, deep enough to justify paying for.

## Root Causes of "Clunky"

1. **Zero streaming** — 3-min wait with polling progress bar. Perplexity streams first word in <500ms.
2. **Complex input** — 4-step wizard forces users to learn pipeline's mental model (topic/source/claim/creator analysis)
3. **Output overload** — 4 docs shown by default; users want ONE thing (Research Brief or Script)

---

## Competitive Positioning

### What We're NOT (Don't Compete Here)

| Tool | Their Lane | Why We Lose There |
|------|-----------|-------------------|
| VidIQ / TubeBuddy | SEO keywords, analytics | Years of keyword data we can't replicate |
| NotebookLM | Upload docs → chat, audio overviews | Free, Google-backed, infinite resources |
| Perplexity | Web search with citations | $500M+ funded, search-first |
| ChatGPT | General writing | Generic LLM battle we can't win |
| Jasper / Copy.ai | Marketing copy | $125M+ funded, content-factory approach |

### What Only We Do (Our Moat)

**Nobody does ALL THREE:**
1. **Ingests actual YouTube videos + articles** — watches/reads them with verified transcripts
2. **Finds the untold angle** — gap analysis identifies what no creator has covered
3. **Produces source-cited scripts** — every fact links back to [Creator Name] at [timestamp]

### Positioning Statement

> **"Turn any collection of videos and articles into a verified, source-cited script — with the angle nobody else covered."**

Three differentiating words: **verified**, **source-cited**, **untold angle**.

### Competitive Story

```
VidIQ:           "What should I make a video about?"     (topic discovery)
Perplexity:      "What does the internet say about X?"   (web search)
NotebookLM:      "What do MY documents say about X?"     (doc analysis)
Research Agent:  "Here's what 5 creators said,            (verified synthesis)
                  here's what NOBODY said yet,             (untold angle)
                  and here's your source-cited script."    (production-ready)
```

---

## Validated Ideas

### Idea 1: Gemini Multimodal Fallback (When Supadata Fails)

**Validation: GROUNDED**

- Add Tier 3.5 in transcript fallback chain: Supadata → Whisper → **Gemini multimodal** → YouTube captions → VIDEO_ONLY
- New confidence tier: `MULTIMODAL_INFERRED` (between CAPTION_GROUNDED and VIDEO_ONLY)
- Hard warnings propagated to ALL downstream docs, not just Doc 0
- **RESOLVED:** Gemini 2.5 Pro accepts YouTube URLs directly via API. No download needed. Samples ~1 frame/sec, 66 tokens/frame, supports up to 6 hours of video.
- **Cost guard (essential):** Cap at 60-minute videos. 1hr video ≈ 238K input tokens. Beyond 60min, fall through to VIDEO_ONLY due to Gemini quality degradation at 260K+ tokens.
- OCR fallback for web pages: strong yes, simpler use case

### Idea 2: Sonnet 4.6 Editorial Pass (Creative Editor/Producer)

**Validation: GROUNDED — ~$0.045/pass, proven 15-20% quality gain**

- Two-pass pattern: Gemini 2.5 Flash drafts → Sonnet 4.6 edits as creative director
- Multi-model draft→edit is a documented pattern with 10-30% speed + 15-20% quality improvement
- Apply to: Doc 5 (Script) always, Doc 6 (Blog) always, Doc 7 (Social) optionally
- Apply to: Research Brief (Doc 2) as background polish
- Skip for: Doc 0, 1 (internal artifacts), Doc 3-4 (research docs)
- Prompt must enforce: "preserve all facts/quotes/citations, improve flow/readability, never add info"
- Run as background async pass — user gets raw draft immediately, polished version arrives 15-20s later
- Post-edit fact-preservation validation: diff factual claims before/after
- **Concrete cost:** Sonnet 4.6 — $3/1M input, $15/1M output. ~5K token script edit = ~$0.045
- **Open:** UX for version delivery (toast? auto-replace? version toggle?)
- **Open:** Voice mimicry preservation — Sonnet may normalize voice styling during edit. Needs prompt testing.

### Idea 3: Quick Mode (OpenClaw Pattern, Productized)

**Validation: PARTIALLY GROUNDED — feasible but needs guardrails**

| | Quick (30-60s) | Full (2-3 min) |
|---|---|---|
| Extraction | Single Gemini call, all sources (labeled) | Per-source isolation |
| Validation | Skip quote verification | Full verification |
| Synthesis | Merged into extraction call | Separate stage |
| Output | Research Brief only | Brief + on-demand extras |
| Confidence | MEDIUM max | Full ceiling rules |
| LLM calls | 1-2 total | N+1 (merged gap+synthesis) |
| Source cap | **3-5 sources max** | Unlimited |

- Quick = free tier / first-time experience
- Full = paid tier value proposition
- **Guardrails required:** Source labels in prompt ("SOURCE_1: ...", "SOURCE_2: ...") to maintain basic attribution
- **Hard token cap:** Gemini quality degrades at 260K+ tokens. Cap total input.
- **Quality label:** "Quick Research — citations may be approximate"
- **Gemini 2.5 Flash context:** 1M tokens. 5 transcripts × 10K = 50K. Easily fits. Quality concern is accuracy, not capacity.

### Idea 4: Pipeline Simplification (Both Modes)

**Validation: GROUNDED — low risk, clear benefit**

- **Merge gap analysis + synthesis** into 1 Gemini call (saves ~8s). Same input data, complementary tasks, temperature 0.2. Simple prompt engineering change.
- **Make Creator Brief (Doc 3) on-demand** instead of always-generated (saves ~10s, 1 LLM call)
- Net: N+1 calls in full mode (down from N+3)

---

## Product UX Overhaul

### Single-Screen Input (Kill 4-Step Wizard)

**Validation: GROUNDED — standard UX best practice**

```
┌──────────────────────────────────────┐
│  What do you want to research?       │
│  [Topic or paste URLs here...]       │
│                                      │
│  + Add YouTube video                 │
│  + Add article/webpage               │
│  + Add text/notes                    │
│  + Upload screenshot                 │
│                                      │
│  Mode: ○ Quick (30s)  ● Full (3min) │
│                                      │
│  [Start Research]                    │
└──────────────────────────────────────┘
```

Auto-detect URLs pasted into main field. No intent selection. Pipeline figures it out.

### SSE Streaming + Progressive UI

**Validation: GROUNDED — needs Redis pub/sub bridge between Celery and FastAPI**

```
Submit → Sources loading (2s) → Outline forming (15s)
→ Sections streaming (30s) → Full doc (60s)
→ Polished version (background, +30s)
```

- **Architecture:** Celery worker → Redis pub/sub → FastAPI SSE endpoint → Next.js EventSource
- SSE endpoint: `GET /jobs/{id}/stream`
- Source cards appear during ingestion (titles, thumbnails)
- Extraction summaries stream per source (parallel = things appear fast)
- Synthesis streams as it generates
- **Revised effort:** 2-3 weeks for solo dev (not "~1 week")

### One Hero Document + Upsells

**Validation: GROUNDED**

- Show **Research Brief (Doc 2)** as primary output with "Untold Angle" section prominently featured
- Doc 0 → collapsible "Sources" sidebar (not a standalone document)
- Doc 1 → "Research Gaps" tab (secondary)
- Doc 3 → on-demand button
- Script/Blog/Social Kit → "Want more?" action buttons
- **Every fact has inline citation links** — this is the trust moat, make it visible
- **Basic exports:** PDF, Markdown, copy-to-clipboard (low effort, high perceived value)

---

## New Features (From User Research)

### Chat with Your Research (Phase 1 — HIGH PRIORITY)

**Why:** NotebookLM's killer feature is chat-with-sources. Creators don't just want a document dump — they want to ask questions. "What did Source 3 say about X?" "Find contradictions between these two experts."

**Implementation:** Send Doc 0 + Doc 2 as context to Gemini Flash, let user ask free-form questions. Technically simple. Cost: ~$0.012/message.

**Current state:** ChatSheet exists with Iterate modes (deep_dive, expand_sources, etc.) but it's mode-based, not conversational. Extend it.

### Source Discovery — "Find Sources For Me" (Phase 2)

**Why:** Current input requires users to already have URLs. Most creators start with a topic and need to FIND the best videos/articles. Without this, they still need Perplexity first.

**Implementation:** New pipeline mode: topic → Gemini/Perplexity search → suggest top YouTube videos + articles → user picks → run research. Closes the loop so creators never leave the tool.

### Title & Thumbnail Suggestions (Phase 2)

**Why:** Creators care about CTR. Research output that includes "Based on this content, here are 5 title options and thumbnail concepts" is a sticky micro-feature nobody else offers in a research tool.

**Implementation:** Lightweight add-on to Creator Brief or standalone micro-generation. Low cost.

### Research Library — Persistent Per-User Knowledge Base (Phase 3)

**Why:** Creators research the same topics repeatedly. True crime = same case across 10 videos. Tech = same company over months. Currently every job is isolated. A persistent, cumulative knowledge base that gets smarter with every project is the long-term moat.

**Why it's a moat:** NotebookLM is notebook-scoped. Perplexity is stateless. Nobody builds on previous research sessions.

**Implementation:** Cache + index sources across jobs per user. "You've researched this topic across 4 previous projects. Here's what you already know + what's new."

**Decision:** Design data model to support this from day 1 (user_id on source cache), build the feature in Phase 3.

### Audio/Podcast Output (Phase 3)

**Why:** NotebookLM's Audio Overviews went viral. Natural extension: Doc 5 (Script) → TTS → audio.

**Implementation:** ElevenLabs or OpenAI TTS integration. Studio tier feature.

### Collaboration/Sharing (Phase 3)

**Why:** Creators with teams (editors, producers, co-hosts) need shared access. But solo creators are the primary market.

**Decision:** Not now. YAGNI. Keep data model team-aware (shareable links, user_id on jobs).

---

## Financial Model

### API Costs (April 2026)

| API | Pricing | Role |
|-----|---------|------|
| Gemini 2.5 Flash | $0.30/$2.50 per 1M tokens (in/out) | Primary LLM (extraction, synthesis, gap analysis) |
| Gemini 2.5 Pro | $1.25/$10.00 per 1M tokens | Complex tasks, multimodal video fallback |
| Anthropic Sonnet 4.6 | $3.00/$15.00 per 1M tokens | Editorial pass, scripts, blogs |
| Supadata | ~$0.01-0.05/request (est.) | YouTube transcripts |
| OpenAI Whisper | $0.006/min audio | Transcript fallback |

### Cost Per Job

| Job Type | LLM Calls | API Cost | Notes |
|----------|-----------|----------|-------|
| Quick (3 sources) | 1 Gemini + 1 Sonnet | **$0.12-0.24** | Single extraction call |
| Full (5 sources) | 6 Gemini + 1 Sonnet | **$0.20-0.40** | Per-source isolation |
| Script add-on | 1 Gemini + 1 Sonnet | **$0.12** | Draft + editorial pass |
| Blog add-on | 1 Gemini + 1 Sonnet | **$0.18** | Draft + editorial pass |
| Chat message | 1 Gemini | **$0.012** | Q&A with research context |

### Infrastructure (Monthly Fixed)

| Service | Cost |
|---------|------|
| Railway (API + workers) | $30-40 |
| Supabase Pro | $25 |
| Vercel (frontend) | $0-20 |
| Redis (Railway included) | $0 |
| **Total** | **$60-90/mo** |

### Proposed Product Tiers

| Tier | Price | Credits/mo | Features | Cost/User/mo | Margin |
|------|-------|------------|----------|-------------|--------|
| Free | $0 | 3 jobs (then paywall) | Full mode, 3 sources max, no Script/Blog | $0.90 | Loss leader |
| Pro | $19/mo | 50 credits | Full mode, unlimited sources, Script + Blog, Sonnet polish, Chat | $4.40 | **77%** |
| Studio | $49/mo | 200 credits | Everything + Producer Packet, priority queue, API access | $10.50 | **79%** |

Credit costs: Quick=1, Full=3, Script=2, Blog=2, Social=1, Chat=free (included), Producer=5

**Pricing psychology:** Same as Storyflow ($19), cheaper than Jasper ($39), more value than both. $19/mo is well above cost floor.

### Unit Economics

| Scenario | Users | Revenue | Cost (API+Infra) | Gross Margin |
|----------|-------|---------|-------------------|-------------|
| Breakeven | 6 paid | $114/mo | ~$100/mo | ~12% |
| Early (100 users) | 40 paid | $1,060/mo | $366/mo | **65%** |
| Growth (500 users) | 200 paid | $5,300/mo | $1,605/mo | **70%** |

**Target:** LTV:CAC > 3x, payback < 12 months, gross margin > 70% at scale.

---

## Scalability Architecture

| Problem | Fix | Priority |
|---------|-----|----------|
| Single Celery worker | Horizontal worker scaling on Railway | Phase 2 |
| No CDN | Supabase CDN for generated docs | Phase 2 |
| No rate limiting | Per-user limits + credit system | Phase 2 |
| No caching | Per-job source caching for iterations (high value) | Phase 1 |
| No caching | Cross-user URL cache (lower value, 20-30% hit rate) | Phase 2 |
| $5 budget hard limit | Credits model | Phase 2 |

### Source Caching (Revised)

- **Per-job caching (Phase 1):** Reuse sources within same job's iterations. High hit rate, zero stale risk. "Expand sources" reuses already-fetched data.
- **Per-user caching (Phase 2):** Feeds into Research Library. Cache by URL hash, TTL: 7 days, "force refresh" option.
- **Cross-user caching (Phase 3):** Lower priority. Cache hit rate for niche research tool is ~20-30% (mostly trending content).

---

## Risk Assessment

### Financial Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini/Anthropic price increases | MEDIUM | Multi-model flexibility; Flash handles 90% of work |
| Supadata goes down | HIGH | Gemini multimodal fallback ready by Phase 2 |
| Low free-to-paid conversion | HIGH | Free tier: 3 jobs (not credits), visibly limited |
| Studio tier margin erosion | MEDIUM | Usage caps + overage pricing |

### Competitive Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| NotebookLM adds YouTube URL ingestion | HIGH | They won't add scripts/gap analysis — full pipeline is moat |
| New startup copies pipeline | MEDIUM | Research Library (Phase 3) creates switching cost |
| Perplexity adds deep source synthesis | MEDIUM | They're search-first, not creator-workflow-first |

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini quality degradation at 260K+ tokens | HIGH | Pin model versions; cap Quick mode input; test before upgrading |
| Sonnet adds info during edit pass | MEDIUM | Post-edit fact validation; strict prompt constraints |
| SSE reliability at scale | LOW | Redis pub/sub battle-tested; fallback to polling |
| Voice mimicry lost in Sonnet edit | MEDIUM | Prompt engineering; include voice profile in edit instructions |

---

## Implementation Priority (Final, Post-Validation)

### MVP (4-6 weeks) — Validate Demand

| # | Feature | Effort | Differentiator? |
|---|---------|--------|-----------------|
| 1 | Single-screen input | 3-5 days | Table stakes |
| 2 | One hero doc + "Untold Angle" hero section | 3-5 days | **YES — unique** |
| 3 | Inline source citations in all outputs | 2-3 days | **YES — trust moat** |
| 4 | Basic exports (PDF, MD, clipboard) | 1-2 days | Table stakes |
| 5 | Merge gap+synthesis, lazy Doc 3 | 1-2 days | Speed win |
| 6 | Sonnet editorial pass on Research Brief | 3-5 days | Quality differentiator |
| 7 | $19/mo paywall after 3 free jobs | 2-3 days | Revenue validation |

**MVP validates:** Do creators find "untold angle" valuable? Do they come back? Will they pay?

### Phase 1 (Weeks 5-10) — Product Feel

| # | Feature | Effort |
|---|---------|--------|
| 8 | SSE streaming + progressive UI | 2-3 weeks |
| 9 | Chat with your research | 1 week |
| 10 | Quick mode (with source labels, 3-5 source cap) | 1-2 weeks |
| 11 | Per-job source caching | 3-5 days |

### Phase 2 (Weeks 11-16) — Growth

| # | Feature | Effort |
|---|---------|--------|
| 12 | Source discovery ("find sources for me") | 2 weeks |
| 13 | Title/thumbnail suggestions | 3-5 days |
| 14 | Gemini multimodal transcript fallback | 3-5 days |
| 15 | Credit system + Stripe integration | 1-2 weeks |
| 16 | Cross-user source caching | 3-5 days |

### Phase 3 (Weeks 17+) — Moat

| # | Feature | Effort |
|---|---------|--------|
| 17 | Research Library (persistent per-user) | 2-3 weeks |
| 18 | Audio/podcast output | 1-2 weeks |
| 19 | Collaboration/sharing | 2 weeks |
| 20 | Horizontal worker scaling | 1 week |

---

## Combined Architecture Vision (Final)

```
INPUT: Single screen → paste URLs + topic → Quick or Full

PIPELINE:
  Quick: Sources → Single Gemini call (labeled) → Brief → [Sonnet async]
  Full:  Sources → Per-source extraction (parallel) → Validate
         → Gap+Synthesis (merged) → Assembly → Brief → [Sonnet async]

OUTPUT: Hero document (Research Brief) with:
  - "Untold Angle" section (gap analysis, prominently featured)
  - Inline source citations on every fact
  - Collapsible Sources sidebar
  - "Generate Script / Blog / Social" upsell buttons
  - Chat with research (conversational Q&A)
  - Export: PDF, Markdown, clipboard

STREAMING: Celery → Redis pub/sub → FastAPI SSE → Next.js EventSource

ON-DEMAND: Script/Blog/Social (Gemini draft → Sonnet edit → source-cited)
```

---

## Resolved Questions

1. ~~How does Gemini access YouTube video?~~ **Direct YouTube URL input via API. No download.**
2. ~~Credit pricing vs cost ratios?~~ **Quick=$0.12-0.24, Full=$0.20-0.40. Credit pricing gives 77-79% margin.**
3. ~~Source caching strategy?~~ **Per-job first (high value), cross-user later (lower hit rate).**
4. ~~Are we a clone?~~ **No. Nobody does ingestion + untold angle + source-cited scripts.**

## Still Open Questions

1. Sonnet editorial prompt design — needs testing to avoid stripping substance
2. Quick mode quality — Gemini long-context degradation documented. A/B test before shipping.
3. Voice mimicry + Sonnet — may normalize voice during edit. Needs prompt testing.
4. Supadata exact pricing at scale — need to check pricing page or contact sales.
5. Free tier abuse — rate limiting by IP? Auth required?
6. Gemini model version pinning — can we pin to avoid quality regressions?
7. Research Library data model — design schema now for Phase 3 even if not building yet.
