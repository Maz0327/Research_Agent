# Business Viability Analysis: Research Agent

**Date:** 2026-04-06
**Purpose:** Cost modeling, competitive differentiation, pricing viability

---

## 1. Required APIs & Their Costs

### Core APIs (Must Have)

| API | Purpose | Pricing (April 2026) | Can we survive without it? |
|-----|---------|---------------------|---------------------------|
| **Gemini 2.5 Flash** | Extraction, synthesis, gap analysis | Input: $0.30/1M tokens, Output: $2.50/1M | NO — primary LLM |
| **Gemini 2.5 Pro** | Complex synthesis, multimodal video | Input: $1.25/1M tokens, Output: $10.00/1M | YES — Flash handles 90% of work |
| **Anthropic Sonnet 4.6** | Editorial pass, scripts, blogs | Input: $3.00/1M tokens, Output: $15.00/1M | YES — quality differentiator, not critical path |
| **Supadata** | YouTube transcripts | ~$0.01-0.05/request (est. from free tier 100 req) | NO — primary transcript source |
| **OpenAI Whisper** | Transcript fallback | $0.006/min audio | Fallback only — nice to have |
| **Supabase** | DB, auth, storage | $25/mo Pro tier | NO — core infrastructure |
| **Railway** | Backend hosting, Celery workers | $5-20/mo per service | NO — backend hosting |

### Optional APIs (Phase 2+)

| API | Purpose | Pricing | When needed |
|-----|---------|---------|-------------|
| **OpenAI TTS** | Audio/podcast generation | $15/1M chars | Phase 3 (audio output) |
| **Stripe** | Payments/subscriptions | 2.9% + $0.30/txn | Phase 2 (monetization) |
| **Redis Cloud** | SSE pub/sub, caching | $0-7/mo (free tier) | Phase 1 (streaming) |
| **Vercel** | Frontend hosting | $0-20/mo | Already using or can use |

---

## 2. Cost Per Job (Detailed Breakdown)

### Quick Mode (3 sources, single Gemini call)

| Component | Tokens/Usage | Cost |
|-----------|-------------|------|
| Supadata transcripts (3 videos) | 3 requests | $0.03-0.15 |
| Gemini 2.5 Flash: extract+synthesize | ~40K in, ~5K out | $0.025 |
| Sonnet 4.6: editorial polish | ~8K in, ~3K out | $0.069 |
| Supabase storage | ~50KB JSON | negligible |
| **TOTAL per Quick job** | | **$0.12-0.24** |

### Full Mode (5 sources, per-source isolation)

| Component | Tokens/Usage | Cost |
|-----------|-------------|------|
| Supadata transcripts (3 video + 2 article) | 5 requests | $0.05-0.25 |
| Gemini 2.5 Flash: extraction (5 calls) | ~60K in, ~10K out | $0.043 |
| Gemini 2.5 Flash: gap+synthesis (1 call) | ~15K in, ~3K out | $0.012 |
| Gemini 2.5 Flash: assembly | code only | $0.00 |
| Sonnet 4.6: editorial polish | ~10K in, ~4K out | $0.090 |
| Supabase storage | ~200KB JSON | negligible |
| **TOTAL per Full job** | | **$0.20-0.40** |

### Script Generation Add-on

| Component | Tokens/Usage | Cost |
|-----------|-------------|------|
| Gemini 2.5 Flash: draft script | ~20K in, ~5K out | $0.019 |
| Sonnet 4.6: creative edit pass | ~8K in, ~5K out | $0.099 |
| **TOTAL per Script** | | **$0.12** |

### Blog Generation Add-on

| Component | Tokens/Usage | Cost |
|-----------|-------------|------|
| Gemini 2.5 Flash: draft blog | ~20K in, ~8K out | $0.026 |
| Sonnet 4.6: creative edit pass | ~12K in, ~8K out | $0.156 |
| **TOTAL per Blog** | | **$0.18** |

### Chat with Research (per question)

| Component | Tokens/Usage | Cost |
|-----------|-------------|------|
| Gemini 2.5 Flash: Q&A with context | ~30K in, ~1K out | $0.012 |
| **TOTAL per chat message** | | **$0.012** |

---

## 3. Infrastructure Fixed Costs (Monthly)

| Service | Tier | Monthly Cost | Notes |
|---------|------|-------------|-------|
| Railway (API server) | Pro | $20 | FastAPI + Celery |
| Railway (worker) | Pro | $10-20 | Scales with job volume |
| Railway (Redis) | Included | $0 | Comes with Railway |
| Supabase | Pro | $25 | DB + Auth + Storage |
| Vercel | Hobby/Pro | $0-20 | Frontend hosting |
| Domain + SSL | - | $1-2 | Annual amortized |
| **TOTAL fixed** | | **$56-87/mo** |

At zero users, you burn **~$60-90/month.** Manageable.

---

## 4. Unit Economics by Tier

### Scenario: 100 Users (Early Stage)

**Tier distribution assumption:** 60 Free, 30 Pro ($19), 10 Studio ($49)

| Tier | Users | Revenue | Avg Jobs/mo | Cost/User/mo | Total Cost | Margin |
|------|-------|---------|-------------|-------------|------------|--------|
| Free | 60 | $0 | 5 Quick | $0.90 | $54 | -$54 |
| Pro | 30 | $570 | 12 Full + 5 Script | $4.40 | $132 | $438 |
| Studio | 10 | $490 | 20 Full + 10 Script + 5 Blog | $10.50 | $105 | $385 |
| **TOTAL** | **100** | **$1,060** | | | **$291 + $75 infra** | **$694/mo** |

**Gross margin: ~65%.** Healthy for AI SaaS (industry avg 50-60%).

### Scenario: 500 Users (Growth Stage)

| Tier | Users | Revenue | Total Cost | Margin |
|------|-------|---------|------------|--------|
| Free | 300 | $0 | $270 | -$270 |
| Pro | 150 | $2,850 | $660 | $2,190 |
| Studio | 50 | $2,450 | $525 | $1,925 |
| **TOTAL** | **500** | **$5,300** | **$1,455 + $150 infra** | **$3,695/mo** |

**Gross margin: ~70%.** Infra scales sublinearly (Railway workers handle more concurrent jobs).

### Breakeven Point

Fixed costs ($75-90/mo) ÷ avg margin per paid user (~$14.60) = **~6 paid users to breakeven.**

That's extremely low. Even with just 6 paying users at $19/mo, you cover infrastructure.

---

## 5. Competitive Differentiation — Are We a Clone?

### Direct Competitor Map

| Tool | What they do | Funding | Pricing | Your edge |
|------|-------------|---------|---------|-----------|
| **NotebookLM** | Upload docs → chat, audio overviews | Google (infinite) | Free | They don't ingest YouTube URLs automatically, no scripts, no gap analysis |
| **Perplexity** | Web search with citations | $500M+ raised | $20/mo Pro | Stateless, no multi-source synthesis, no production outputs |
| **Elicit** | Academic paper discovery | $10M+ | $10/mo | Academic-only, no YouTube/video, no content creation |
| **Saner.AI** | NotebookLM alternative, knowledge mgmt | Early stage | $8-15/mo | General knowledge tool, not creator-focused |
| **Storyflow** | YouTube script planning | Small | $19-49/mo | Template-driven, no actual source research |
| **Jasper** | Marketing copy generation | $125M raised | $39-99/mo | No research layer, no source analysis |

### What Makes You NOT a Clone

**Nobody in this landscape does ALL THREE:**
1. Ingests actual YouTube videos + articles (watches/reads them)
2. Cross-references and finds the untold angle (gap analysis)
3. Produces source-verified scripts/blogs with inline citations

**NotebookLM** does #1 partially (manual upload) and #2 partially (chat). No #3.
**Perplexity** does web search but not deep source analysis. No #2 or #3.
**Storyflow** does script templates. No #1 or #2.
**Jasper** does content generation. No #1 or #2.

### The Clone Risk

You BECOME a clone if you:
- Position as "AI research tool" (NotebookLM territory)
- Position as "AI writing tool" (Jasper/Copy.ai territory)
- Position as "YouTube SEO tool" (VidIQ territory)

You AVOID being a clone by positioning as:
**"Source-to-script pipeline for video creators — with the angle nobody covered."**

---

## 6. What You Need to Charge (Minimum Viable Pricing)

### Cost Floor (What You Can't Go Below)

| Tier | Min cost/user/mo | Floor price | Proposed | Margin |
|------|-----------------|-------------|----------|--------|
| Free | $0.90 (5 Quick) | $0 (loss leader) | $0 | -100% |
| Pro | $4.40 | $9/mo | $19/mo | 77% |
| Studio | $10.50 | $21/mo | $49/mo | 79% |

**$19/mo Pro is well above cost floor.** Room to offer annual discount ($15/mo billed annually) and still be profitable.

### Pricing Psychology

| Competitor | Price | What you get |
|-----------|-------|-------------|
| Perplexity Pro | $20/mo | Unlimited searches, file upload |
| VidIQ Pro | $7.50/mo | Keywords, analytics |
| Storyflow | $19/mo | Script planning |
| Jasper Creator | $39/mo | AI writing |
| **Research Agent Pro** | **$19/mo** | Research + scripts + citations |

$19/mo positions you as "same as Storyflow but does actual research" and "cheaper than Jasper but source-verified." Good positioning.

---

## 7. Risk Assessment

### Financial Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini/Anthropic price increases | MEDIUM | Multi-model flexibility; can swap Flash for cheaper models |
| Supadata goes down/pricing changes | HIGH | Gemini multimodal fallback; multiple transcript sources |
| Low conversion from free to paid | HIGH | Make Quick mode genuinely useful but visibly limited (no scripts, 3 source cap) |
| Studio tier margin erosion | MEDIUM | Usage caps, overage pricing |

### Competitive Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| NotebookLM adds YouTube URL ingestion | HIGH | They won't add scripts/gap analysis — your full pipeline is the moat |
| Perplexity adds deep source synthesis | MEDIUM | They're search-first, not creator-workflow-first |
| New startup copies your pipeline | MEDIUM | Research Library (Phase 3) creates switching cost |
| Google/OpenAI builds this natively | LOW | They build platforms, not niche creator tools |

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini quality degradation (documented) | HIGH | Pin model versions; test before upgrading; Flash is more stable than Pro |
| Sonnet adds info during edit pass | MEDIUM | Post-edit fact validation; strict prompt constraints |
| SSE reliability at scale | LOW | Redis pub/sub is battle-tested; fallback to polling |

---

## 8. Minimum Viable Product (What to Ship First)

To validate the business before building everything:

**MVP (4-6 weeks):**
- Single-screen input (URLs + topic)
- Full mode only (skip Quick mode initially)
- One hero document (Research Brief) with inline citations
- "Untold Angle" section as hero feature (existing gap analysis, reframed)
- Basic export (copy, markdown)
- Sonnet editorial pass on Research Brief
- $19/mo paywall after 3 free jobs (no credit system yet)

**Cost to run MVP:** ~$75/mo infrastructure + ~$0.30/job API costs

**What this validates:**
- Do creators find "untold angle" valuable?
- Do they come back after first use?
- Will they pay $19/mo?

**What you skip for MVP:**
- Quick mode, streaming, chat, source discovery, credits, tiers
- These are all optimizations on a product people already want

---

## Unresolved Questions

1. Supadata exact pricing at scale — need to check their pricing page directly or contact sales
2. Whisper costs for long videos (>1hr) — could be $0.36+ per video, significant
3. Free tier abuse — rate limiting by IP? Auth required for free tier?
4. Gemini model version pinning — can we pin to stable version to avoid quality regressions?
5. Stripe integration timeline — need Stripe account before monetization (noted in go-live blockers)

---

## Sources

- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini 2.5 Flash Pricing](https://pricepertoken.com/pricing-page/model/google-gemini-2.5-flash)
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Supabase Pricing](https://supabase.com/pricing)
- [Railway Pricing](https://getdeploying.com/railway)
- [AI SaaS Unit Economics 2026](https://www.getmonetizely.com/blogs/the-economics-of-ai-first-b2b-saas-in-2026)
- [AI Pricing Playbook — Bessemer](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook)
- [NotebookLM Alternatives 2026](https://elephas.app/blog/best-notebooklm-alternatives)
- [Micro-SaaS State 2025](https://freemius.com/blog/state-of-micro-saas-2025/)
