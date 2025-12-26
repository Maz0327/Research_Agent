# Validated API Stack Recommendations
## Research Agent - Quality-Optimized Within Reasonable Cost

**Date**: December 25, 2025
**Analysis Method**: Cross-validated claims from multiple recommendation sources against current research

---

## Executive Summary

After validating claims from both recommendation documents against current research data (December 2025), here are the **verified best recommendations** that optimize for quality within reasonable cost.

**Key Finding**: Recommendation 1 (strongest setup) overengineered for cost; Recommendation 2 (budget-focused) missed some quality opportunities. The optimal stack is between them.

---

## Validated Findings

### 1. Tavily Reliability Issues: ✅ CONFIRMED

**Claim**: "About 1/10 of requests return error 502"

**Validation**: Multiple sources confirm significant reliability issues:
- [GitHub Issue #5982](https://github.com/langchain-ai/langchainjs/issues/5982): "tavily search api is not reliable"
- [Tavily Community Forum](https://community.tavily.com/t/frequent-502-responses/57): ~10% 502 error rate documented July 2024
- [March 2025 Report](https://community.tavily.com/t/502-bad-gateway-when-searching-for-a-long-name/683): Long query timeouts
- [July 2025 Report](https://community.tavily.com/t/are-the-tavily-servers-currently-unstable/921): Still experiencing 502 errors

**Verdict**: ⚠️ **DO NOT use Tavily as primary search API for production**. Keep as fallback only.

---

### 2. Search API Comparison: VALIDATED

| API | Accuracy | Speed | Cost | Production Ready |
|-----|----------|-------|------|------------------|
| **Exa** | 94.9% (highest) | 1.2s | $5/1k searches | ✅ |
| **Perplexity** | ~92% | 358ms (fastest) | ~€5/1k | ✅ |
| **Serper** | 93.5% | <2s | $1/1k | ✅ |
| **Tavily** | ~91% | 800ms | $0.01/search | ⚠️ Reliability issues |

**Source**: [Humai Blog Comparison](https://www.humai.blog/tavily-vs-exa-vs-perplexity-vs-you-com-the-complete-ai-search-api-comparison-2025/), [WebSearchAPI Analysis](https://websearchapi.ai/blog/tavily-alternatives)

---

### 3. LLM Pricing & Benchmarks: VALIDATED

| Model | Input/1M | Output/1M | Strengths | Best For |
|-------|----------|-----------|-----------|----------|
| **Claude Opus 4** | $15 | $75 | Creative, safety-critical, human-like | Final synthesis, documentary narrative |
| **GPT-4o** | $1.25 | $10 | Balanced, fast | Extraction, structured data |
| **Gemini 2.5 Pro** | $1.25 | $10 | 1M context, multimodal, PDF | Vision, large documents |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | Speed, 1M context | General tasks, cost-efficient |
| **GPT-4o mini** | $0.15 | $0.60 | Cheapest quality | Simple extraction |
| **DeepSeek V3.2** | $0.028 | $0.42 | 95% cheaper | Cost-sensitive, non-critical |

**Source**: [VentureBeat](https://venturebeat.com/ai/deepseeks-new-v3-2-exp-model-cuts-api-pricing-in-half-to-less-than-3-cents), [LLM-Stats](https://llm-stats.com/models/compare/gemini-2.5-flash-vs-gpt-4o-mini-2024-07-18)

---

### 4. Gemini for Vision: ✅ CONFIRMED ADD

**Claim**: "Gemini 2.5 Pro excels at images, PDFs, multimodal"

**Validation**: Strong evidence supports this:
- 1M token context vs GPT-4o's 128K (8x larger)
- "Multimodal from the ground up" vs GPT-4o's "added on" approach
- Faster for document tasks, better PDF analysis
- Supports video (GPT-4o doesn't natively)

**Source**: [G2 Comparison](https://learn.g2.com/gemini-vs-chatgpt), [Creole Studios](https://www.creolestudios.com/gemini-2-5-vs-gpt-4o-comparison/)

**Verdict**: ✅ **ADD Gemini 2.5 Pro for vision/PDF tasks**

---

### 5. DeepSeek V3.2: ⚠️ USE WITH CAUTION

**Verified Pricing**: $0.028/M input (cache hit), $0.42/M output - 95% cheaper than competitors

**Caveats**:
- V3.2-Exp labeled "experimental" - not V3.1-Terminus stable
- Function calling still in Beta
- Geopolitical considerations (data on Chinese servers)
- "Mission-critical stacks may stay on V3.1-Terminus until V3.2-Exp stabilizes"

**Source**: [DeepSeek API Docs](https://api-docs.deepseek.com/quick_start/pricing)

**Verdict**: ⚠️ Good for **non-critical, high-volume tasks only**

---

## Final Recommended Stack

### Tier System by Research Mode

```
┌────────────────────────────────────────────────────────────────────┐
│              VALIDATED RESEARCH AGENT STACK                        │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  SEARCH LAYER (Mode-Dependent)                                     │
│  ┌──────────────────┬──────────────────┬──────────────────┐       │
│  │ breaking_news    │ investigation    │ profile/         │       │
│  │                  │                  │ controversy      │       │
│  ├──────────────────┼──────────────────┼──────────────────┤       │
│  │ Perplexity       │ Exa + Perplexity │ Exa (primary)    │       │
│  │ (speed: 358ms)   │ (accuracy: 94.9%)│ Perplexity       │       │
│  │                  │ + Serper backup  │ (fallback)       │       │
│  └──────────────────┴──────────────────┴──────────────────┘       │
│                                                                    │
│  LLM LAYER (Task-Dependent)                                        │
│  ┌──────────────────┬──────────────────┬──────────────────┐       │
│  │ Planning &       │ Extraction &     │ Vision & PDF     │       │
│  │ Synthesis        │ Fast Tasks       │ Analysis         │       │
│  ├──────────────────┼──────────────────┼──────────────────┤       │
│  │ Gemini 2.5 Flash │ GPT-4o mini      │ Gemini 2.5 Pro   │       │
│  │ $0.30/$2.50      │ $0.15/$0.60      │ $1.25/$10        │       │
│  │ (replaces Opus   │ (simple tasks)   │ (when needed)    │       │
│  │  for 90% of      │                  │                  │       │
│  │  planning)       │                  │                  │       │
│  └──────────────────┴──────────────────┴──────────────────┘       │
│                                                                    │
│  EXTRACTION LAYER (KEEP AS-IS)                                     │
│  ┌──────────────────┬──────────────────┬──────────────────┐       │
│  │ Jina Reader      │ Supadata         │ PRAW             │       │
│  │ FREE             │ $17/month        │ FREE             │       │
│  │ Web content      │ Transcripts      │ Reddit           │       │
│  └──────────────────┴──────────────────┴──────────────────┘       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Recommendations

### SEARCH APIs

| Keep | Add | Drop | Demote |
|------|-----|------|--------|
| Perplexity ✅ | Exa (for investigation) | - | Tavily → backup only |

**Rationale**:
- **Perplexity**: Speed leader (358ms), great for breaking_news
- **Exa**: 94.9% accuracy, best for semantic/entity search (investigation, profile)
- **Serper**: $1/1k, 93.5% success - excellent backup if Exa/Perplexity fail
- **Tavily**: Documented reliability issues - demote to fallback only

**Cost Impact**: +~$20-30/month for Exa (investigation mode only)

---

### LLM Selection

| Task | Recommended Model | Why |
|------|-------------------|-----|
| **Planning** | Gemini 2.5 Flash | 1M context, $0.30/$2.50, "thinking" mode |
| **Query Generation** | GPT-4o mini | $0.15/$0.60, fast, sufficient quality |
| **Extraction** | GPT-4o mini | Structured output, cheap |
| **Claim Validation** | Gemini 2.5 Flash | Reasoning capabilities |
| **Vision/PDF** | Gemini 2.5 Pro | Best multimodal, 1M context |
| **Documentary Synthesis** | Gemini 2.5 Pro OR Claude Opus 4 | Quality-critical final output |

**Why NOT Claude Opus for everything?**
- $15/$75 per M tokens is **50x more expensive** than Gemini Flash
- Gemini Flash benchmarks comparably for most tasks
- Reserve Opus for **final documentary narrative only** (if needed)

**Why NOT DeepSeek for everything?**
- V3.2-Exp is labeled "experimental"
- Function calling in Beta
- Geopolitical data concerns
- Use for high-volume, non-critical tasks only

---

### KEEP (No Changes Needed)

| Component | Status | Notes |
|-----------|--------|-------|
| Jina Reader | ✅ KEEP | FREE, reliable, Tier 1 |
| Supadata | ✅ KEEP | $17/month, handles cloud IP blocking |
| PRAW | ✅ KEEP | FREE, official Reddit API |
| YouTube Data API | ✅ KEEP | FREE quota sufficient |

---

## Cost Estimates by Mode

### Breaking News (~$1.50/job)
- Perplexity: ~$0.50 (10 searches)
- GPT-4o mini: ~$0.20 (extraction)
- Gemini Flash: ~$0.30 (planning)
- Jina Reader: FREE
- Supadata: ~$0.50 (5 transcripts)

### Investigation (~$8-12/job)
- Exa: ~$2.50 (50 searches)
- Perplexity: ~$1.00 (20 searches)
- Gemini 2.5 Pro: ~$3.00 (vision/PDFs)
- GPT-4o mini: ~$0.50 (extraction)
- Gemini Flash: ~$1.00 (planning + validation)
- Supadata: ~$1.50 (15 transcripts)

### Profile (~$4-6/job)
- Exa: ~$2.00 (40 searches, entity-focused)
- Gemini Flash: ~$1.00 (planning)
- GPT-4o mini: ~$0.30 (extraction)
- Supadata: ~$1.00 (10 transcripts)

### Controversy (~$5-8/job)
- Exa + Perplexity: ~$2.50 (balanced perspectives)
- Gemini Flash: ~$1.50 (multi-perspective analysis)
- GPT-4o mini: ~$0.50 (extraction)
- Supadata: ~$1.00 (10 transcripts)

---

## Monthly Cost Projection (60 jobs)

| Mode Mix | Estimated Monthly Cost |
|----------|----------------------|
| 40 breaking_news + 10 investigation + 10 profile | ~$130-150 |
| 20 breaking_news + 20 investigation + 20 controversy | ~$200-250 |
| Heavy investigation focus | ~$300-400 |

**vs Original Recommendations**:
- Rec 1 "Strongest" ($4-6/job): ~$240-360/month ❌ Overbudget
- Rec 2 "Budget" ($20-35/month): Quality compromises ❌
- **This recommendation**: ~$130-250/month ✅ Best balance

---

## Implementation Priority

### Phase 1: Immediate Changes
1. **Demote Tavily** to fallback only (reliability issues confirmed)
2. **Add Exa** for investigation/profile modes
3. **Add Gemini 2.5 Pro** for vision/PDF analysis
4. **Switch planning to Gemini 2.5 Flash** (from GPT-4o-mini)

### Phase 2: Optimization
1. Implement mode-based search routing
2. Add Serper as secondary fallback (cheaper than Tavily)
3. Configure Gemini Flash "thinking" mode for complex planning

### Phase 3: Quality Enhancement (Optional)
1. Add Claude Opus 4 for final documentary synthesis (if quality gap observed)
2. Evaluate DeepSeek for high-volume extraction (cost savings)

---

## Summary Table: What Changed

| Component | Rec 1 (Strongest) | Rec 2 (Budget) | **Final (Validated)** |
|-----------|-------------------|----------------|----------------------|
| Primary Search | Exa + Perplexity + Tavily | Serper | **Exa + Perplexity** (mode-based) |
| Fallback Search | - | - | **Serper + Tavily** |
| Planning LLM | Claude Opus 4 | DeepSeek/Gemini Flash | **Gemini 2.5 Flash** |
| Extraction LLM | GPT-4o | GPT-3.5/Groq | **GPT-4o mini** |
| Vision LLM | Gemini 2.5 Pro | "Only if needed" | **Gemini 2.5 Pro** (add) |
| Synthesis LLM | Claude Opus 4 | Gemini Flash | **Gemini 2.5 Pro** (Opus optional) |
| Web Extraction | Jina (keep) | Diffbot/Jina | **Jina Reader** (keep) |
| Transcripts | Supadata (keep) | Supadata | **Supadata** (keep) |
| Monthly Cost | ~$240-360 | ~$22-48 | **~$130-250** |

---

## Sources

- [Tavily Reliability Issues - GitHub](https://github.com/langchain-ai/langchainjs/issues/5982)
- [Tavily Community - 502 Errors](https://community.tavily.com/t/frequent-502-responses/57)
- [Search API Comparison - Humai Blog](https://www.humai.blog/tavily-vs-exa-vs-perplexity-vs-you-com-the-complete-ai-search-api-comparison-2025/)
- [WebSearchAPI - Tavily Alternatives](https://websearchapi.ai/blog/tavily-alternatives)
- [DeepSeek Pricing](https://venturebeat.com/ai/deepseeks-new-v3-2-exp-model-cuts-api-pricing-in-half-to-less-than-3-cents)
- [LLM Pricing Comparison](https://llm-stats.com/models/compare/gemini-2.5-flash-vs-gpt-4o-mini-2024-07-18)
- [Gemini vs GPT-4o Vision](https://learn.g2.com/gemini-vs-chatgpt)
- [Serper API Analysis](https://medium.com/@darshankhandelwal12/serpapi-vs-serper-vs-scrapingdog-we-tested-all-three-so-you-dont-have-to-c7d5ff0f3079)

---

## Unresolved Questions

1. **Exa's $49/month minimum** - Need to confirm if pay-as-you-go is available or if minimum applies
2. **Gemini 2.5 Pro context caching** - Could reduce costs significantly if frequently reusing context
3. **DeepSeek V3.2 stability timeline** - When will it graduate from "experimental"?
4. **Perplexity API availability** - Some reports of limited availability in certain regions
