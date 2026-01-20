# Research Agent PRD v6.0

## Research-Validated Product Requirements Document

**Version:** 6.0
**Date:** December 2024
**Status:** Authoritative Specification
**Supersedes:** PRD v4.3, PRD v5.0

---

## Executive Summary

Research Agent is an AI-powered documentary research assistant that replaces human researchers for content creators. It aggregates and analyzes content from multiple sources and produces two outputs:

1. **NotebookLM Packet** - Optimized for AI podcast generation
2. **Documentary Blueprint** - Optimized for video production

**Production Status:** LIVE
- Frontend: https://research-agent-kohl.vercel.app (Vercel)
- Backend API: https://api-production-1c52.up.railway.app (Railway)
- Database: Supabase (PostgreSQL)
- Queue: Redis (Railway)

---

## Part 1: Current Implementation (What's Actually Built)

### 1.1 Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   Celery    │
│   (Vercel)  │◀────│   (Railway) │◀────│   Worker    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  Supabase   │     │    Redis    │
                    │   (Jobs)    │     │   (Queue)   │
                    └─────────────┘     └─────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Backend Framework | FastAPI | 0.127+ |
| Task Queue | Celery | 5.3.4 |
| Message Broker | Redis | 5.0.1 |
| Database | Supabase (PostgreSQL) | - |
| Frontend | Next.js | 14 |
| Styling | Tailwind CSS | - |
| State Management | Zustand | - |
| LLM | OpenAI GPT-4o-mini | - |
| Search | Perplexity, Tavily | - |

### 1.3 Working Features

| Feature | Status | Location |
|---------|--------|----------|
| 11-stage pipeline | ✅ Working | `backend/pipeline/stages.py` |
| 4 documentary modes | ✅ Working | `backend/models/job_config.py` |
| Niche overlay system | ✅ Working | `backend/pipeline/niche_loader.py` |
| Documentary intelligence | ✅ Working | `backend/pipeline/documentary_intelligence.py` |
| Dual output (NotebookLM + Blueprint) | ✅ Working | `backend/pipeline/dual_output.py` |
| Quality Gate module | ⚠️ Exists, not integrated | `backend/pipeline/quality_gate.py` |
| Cost tracking | ❌ Not implemented | - |

---

## Part 2: Documentary Modes

### 2.1 Implemented Modes (4 of 4)

| Mode | Focus | Time Window | Budget | Key Features |
|------|-------|-------------|--------|--------------|
| `breaking_news` | Speed + Recency | 72 hours | $2 | Hourly timeline, minimal verification |
| `investigation` | Deep Verification | No limit | $15 | Full source coverage, entity mapping |
| `profile` | Single Entity | No limit | $8 | Biographical focus, relationship mapping |
| `controversy` | Multiple Perspectives | No limit | $10 | Balanced viewpoints, all sides validated |

### 2.2 Mode Configuration

```python
# backend/models/job_config.py

DocumentaryMode.BREAKING_NEWS: {
    "focus": "recency_and_speed",
    "time_window_hours": 72,
    "sources": {
        "reddit": {"enabled": True, "sort": "new", "limit": 20},
        "perplexity": {"enabled": True, "queries": 3},
        "youtube": {"enabled": False},  # Too slow
    },
    "timeline_precision": "hourly",
    "max_duration_minutes": 10,
    "max_cost_usd": 2.0
}

DocumentaryMode.INVESTIGATION: {
    "focus": "verification_and_connections",
    "time_window_hours": None,
    "sources": {
        "reddit": {"enabled": True, "sort": "top", "limit": 50},
        "perplexity": {"enabled": True, "queries": 15},
        "youtube": {"enabled": True, "max_videos": 30},
    },
    "validation_all_claims": True,
    "entity_relationship_mapping": True,
    "max_duration_minutes": 45,
    "max_cost_usd": 15.0
}

DocumentaryMode.PROFILE: {
    "focus": "single_entity_deep_dive",
    "sources": {
        "youtube": {"enabled": True, "search_entity_name": True},
        "perplexity": {"enabled": True, "entity_focused": True},
        "reddit": {"enabled": True, "search_mentions": True},
    },
    "timeline_type": "biographical",
    "relationship_mapping": True,
    "max_duration_minutes": 30,
    "max_cost_usd": 8.0
}

DocumentaryMode.CONTROVERSY: {
    "focus": "balanced_perspectives",
    "sources": {
        "reddit": {"enabled": True, "include_controversial": True},
        "perplexity": {"enabled": True, "get_all_sides": True},
        "youtube": {"enabled": True, "diverse_channels": True},
    },
    "validate_all_sides": True,
    "max_duration_minutes": 30,
    "max_cost_usd": 10.0
}
```

---

## Part 3: Pipeline Architecture

### 3.1 Current Pipeline (11 Stages - Sequential)

```
Stage 1:  Initialize
    ↓
Stage 2:  Planning (OpenAI) → JobConfig, short_title
    ↓
Stage 3:  Research Mapping (Perplexity) → angles, key_terms
    ↓
Stage 4:  Source Discovery (Perplexity) → web_sources
    ↓
Stage 5:  YouTube Enumeration → youtube_videos
    ↓
Stage 6:  Transcript Extraction (Supadata/Whisper) → transcripts
    ↓
Stage 7:  Web Capture (Jina/Trafilatura/Playwright) → content
    ↓
Stage 8:  Reddit Collection (PRAW) → reddit_posts
    ↓
Stage 9:  AI Extraction (OpenAI) → claims, timeline, entities
    ↓
Stage 10: Validation + Analysis (Perplexity/OpenAI) → evidence, angles
    ↓
Stage 11: Output + Upload → folder_url, doc_urls
```

### 3.2 Pipeline Context

All stages share state via `PipelineContext` (`backend/pipeline/context.py`):

```python
@dataclass
class PipelineContext:
    # Input
    job_id: str
    topic: str

    # Stage 2: Planning
    job_config: Optional[JobConfig] = None
    short_title: str = ""
    niche_config: Optional[dict] = None

    # Stage 3-4: Research
    angles: list = field(default_factory=list)
    key_terms: list = field(default_factory=list)
    web_sources: list = field(default_factory=list)

    # Stage 5-8: Collection
    youtube_videos: list = field(default_factory=list)
    transcripts: list = field(default_factory=list)
    reddit_posts: list = field(default_factory=list)

    # Stage 9: Extraction
    claims: list = field(default_factory=list)
    timeline_events: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)

    # Stage 10: Analysis
    evidence_records: list = field(default_factory=list)
    discovered_angles: dict = field(default_factory=dict)
    documentary_analysis: dict = field(default_factory=dict)

    # Stage 11: Output
    folder_url: Optional[str] = None
    doc_urls: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
```

### 3.3 Optimal Pipeline (Research-Based - Future)

```
Phase 1: Planning [Sequential]
  └── 1. Initialize
  └── 2. Planning (Claude Sonnet) → JobConfig

Phase 2: Discovery [PARALLEL - Celery group()]
  ├── 3a. Web Search (Perplexity/Tavily)
  ├── 3b. YouTube Enumeration
  └── 3c. Reddit Discovery

Phase 3: Collection [PARALLEL]
  ├── 4a. Web Capture
  ├── 4b. Transcript Extraction
  └── 4c. Reddit Collection

Phase 4: Quality Gate [Sequential]
  └── 5. Filter & Score Sources

Phase 5: Extraction [PARALLEL]
  ├── 6a. Claim Extraction
  ├── 6b. Timeline Extraction
  └── 6c. Entity Extraction

Phase 6: Synthesis [Sequential]
  └── 7. Validation
  └── 8. Documentary Intelligence
  └── 9. Dual Output Formatting
  └── 10. Drive Upload
```

---

## Part 4: Niche Overlay System

### 4.1 Implemented Niches

| Niche | Description | Config File |
|-------|-------------|-------------|
| `downfalls` | Scandal timelines, career decline, public reactions | `backend/config/niches/downfalls.yaml` |
| `mysteries` | Evidence analysis, pro/con theories, timeline gaps | `backend/config/niches/mysteries.yaml` |

### 4.2 Niche Configuration Example

```yaml
# backend/config/niches/downfalls.yaml
name: downfalls
description: Research focused on scandals, controversies, and career declines

mode_overrides:
  investigation:
    focus_areas:
      - public_statements
      - timeline_of_events
      - media_coverage
      - social_media_reactions
    additional_prompts:
      - "Identify the turning point that led to their downfall"
      - "Document the public reaction timeline"
      - "Find contradictory statements"

  controversy:
    focus_areas:
      - accusers_perspective
      - defenders_perspective
      - neutral_analysis
```

### 4.3 Planned Niches

| Niche | Description | Priority |
|-------|-------------|----------|
| `history_religion` | Historical context, theological perspectives | Medium |
| `pop_culture` | Trend analysis, social media reactions | Low |
| `current_affairs` | Political context, policy implications | Low |

---

## Part 5: External Services

### 5.1 Research-Validated API Stack (December 2025)

Based on comprehensive research validation comparing 15+ APIs across accuracy, speed, reliability, and cost.

#### LLM Layer (Task-Based Selection)

| Task | Current | **Recommended** | Rationale |
|------|---------|-----------------|-----------|
| Planning | GPT-4o-mini | **Gemini 2.5 Flash** | 1M context, $0.30/$2.50, "thinking" mode |
| Extraction | GPT-4o-mini | **GPT-4o-mini** | ✅ Already optimal - fast, cheap, structured |
| Vision/PDF | None | **Gemini 2.5 Pro** | 1M context, multimodal-native, $1.25/$10 |
| Synthesis | GPT-4o-mini | **Gemini 2.5 Pro** | Quality-critical final output |
| Speed Mode | None | Gemini 2.0 Flash | 250 tok/s for breaking_news |

**Why NOT Claude Opus for everything?** 50x more expensive ($15/$75) than Gemini Flash for marginal quality gain.
**Why NOT DeepSeek?** V3.2 is labeled "experimental", function calling in Beta.

#### Search Layer (Mode-Based Selection)

| Mode | APIs | Rationale |
|------|------|-----------|
| breaking_news | **Perplexity** | Speed: 358ms (fastest) |
| investigation | **Exa + Perplexity** | Exa: 94.9% accuracy (highest) |
| profile | **Exa** | Semantic entity search |
| controversy | **Exa + Perplexity** | Balanced perspectives |
| fallback | **Serper + Tavily** | Serper $1/1k, Tavily demoted due to 10% 502 error rate |

**⚠️ Tavily Reliability Warning**: Documented 10% 502 error rate in production ([GitHub #5982](https://github.com/langchain-ai/langchainjs/issues/5982)). Demote to fallback only.

### 5.2 Service Inventory (Updated)

| Service | Purpose | Pricing | Status | Priority |
|---------|---------|---------|--------|----------|
| GPT-4o-mini | Extraction, simple tasks | $0.15/$0.60/1M | ✅ Active | Keep |
| Gemini 2.5 Flash | Planning | $0.30/$2.50/1M | ❌ Add | **HIGH** |
| Gemini 2.5 Pro | Vision, synthesis | $1.25/$10/1M | ❌ Add | **HIGH** |
| Perplexity | Speed search, current events | ~€5/1k | ✅ Active | Keep |
| **Exa** | Semantic search (94.9% accuracy) | $5/1k | ❌ **Add** | **HIGH** |
| Serper | Backup search | $1/1k | ❌ Add | MEDIUM |
| Tavily | RAG search (demoted) | $0.01/search | ⚠️ Demote | Fallback only |
| Jina Reader | Web content extraction | FREE | ✅ Active | Keep |
| GDELT | News events | FREE | ✅ Active | Keep |
| Supadata | YouTube transcripts | ~$0.01/transcript | ✅ Active | Keep |
| Whisper | Audio transcription (fallback) | $0.006/minute | ✅ Active | Keep |
| PRAW | Reddit API | Free | ✅ Active | Keep |

### 5.3 Graceful Degradation Chains (Updated)

| Function | Tier 1 | Tier 2 | Tier 3 | Notes |
|----------|--------|--------|--------|-------|
| Web Capture | Jina Reader | Trafilatura | Playwright | ✅ Optimal |
| Transcripts | Supadata | Whisper | youtube-api* | ✅ Optimal |
| Reddit | PRAW | Tavily site:reddit | - | ✅ Optimal |
| **Search** | **Exa/Perplexity** | **Serper** | Tavily | ⚠️ Updated |
| **LLM** | **Gemini Flash** | GPT-4o-mini | - | ⚠️ Updated |

*Note: youtube-transcript-api fails on cloud IPs (Railway, AWS, GCP)

### 5.4 Cost Estimates Per Mode (Updated)

| Mode | Current Cost | **Optimized Cost** | Budget Limit |
|------|--------------|-------------------|--------------|
| breaking_news | $0.50 - $1.00 | **$1.00 - $1.50** | $2.00 |
| investigation | $5.00 - $8.00 | **$8.00 - $12.00** | $15.00 |
| profile | $3.00 - $5.00 | **$4.00 - $6.00** | $8.00 |
| controversy | $4.00 - $6.00 | **$5.00 - $8.00** | $10.00 |

*Note: Optimized costs slightly higher due to better APIs (Exa, Gemini) but significantly higher quality output.*

---

## Part 6: Dual Output System

### 6.1 NotebookLM Packet

Optimized for Google NotebookLM AI podcast generation.

**Format Requirements:**
- Single markdown document < 500KB
- Clear section headers (H1, H2, H3)
- Inline quotes with attribution
- Timeline as narrative, not table
- No external links (NotebookLM can't fetch)

**Structure:**
```markdown
# {Title}

## Overview
{2-3 sentence summary}

## Key Facts
- {Verified fact 1}
- {Verified fact 2}
...

## Timeline
{Chronological narrative}

## Notable Quotes
> "{Quote}" - {Speaker}

## Controversy (if applicable)
{Summary of controversy}

## Open Questions
- {Unresolved question 1}

## Sources
{Summary of source types}
```

### 6.2 Documentary Blueprint

Optimized for video production planning.

**Structure:**
```markdown
# Documentary Blueprint: {Title}

**Logline:** {One sentence hook}
**Estimated Runtime:** {X minutes}
**Music Tone:** {Tone description}

## Three-Act Structure

### Act 1: Setup
**Hook:** {Opening hook}
**Key Players:** {List}

### Act 2: Investigation
**Revelations:** {List}
**Conflicts:** {List}

### Act 3: Resolution
**Climax:** {Description}
**Verified Conclusions:** {List}

## Interview Subjects
{Priority-ordered list with suggested questions}

## B-Roll Suggestions
{Visual content list}

## Graphics Needed
{Infographic and visual element list}

## Production Notes
{Additional guidance}
```

---

## Part 7: Quality Gate (Exists - Needs Integration)

### 7.1 Current Status

The Quality Gate module exists at `backend/pipeline/quality_gate.py` (565 lines) but is **NOT currently called in the pipeline**.

### 7.2 Implemented Functions

| Function | Purpose |
|----------|---------|
| `canonicalize_url()` | Normalize URLs for deduplication |
| `is_junk_source()` | Filter low-quality sources (ads, paywalls) |
| `score_source()` | Calculate quality score (0-100) |
| `filter_sources()` | Apply mode-specific quality floors |

### 7.3 Integration Plan

Add Quality Gate as Stage 4.5 (after Source Discovery, before YouTube):

```python
# In backend/pipeline/stages.py

async def stage_quality_gate(ctx: PipelineContext) -> None:
    """Filter and score discovered sources."""
    from backend.pipeline.quality_gate import filter_sources

    mode = ctx.job_config.mode if ctx.job_config else DocumentaryMode.INVESTIGATION

    # Apply quality filtering
    ctx.web_sources = filter_sources(
        sources=ctx.web_sources,
        mode=mode,
        min_score=get_mode_floor(mode)
    )

    logger.info(f"Quality Gate: {len(ctx.web_sources)} sources passed")
```

---

## Part 8: Gap Analysis

### 8.1 LLM Configuration Gap

| Aspect | Current | Optimal | Gap |
|--------|---------|---------|-----|
| Planning | GPT-4o-mini | Claude Sonnet 4.5 | Quality |
| Extraction | GPT-4o-mini | GPT-4o-mini | ✅ Optimal |
| Breaking News | GPT-4o-mini | Groq Llama 3 | Speed |
| Cheap Mode | Not available | DeepSeek V3 | Missing |

### 8.2 Search API Gap

| Aspect | Current | Optimal | Gap |
|--------|---------|---------|-----|
| Speed Search | Perplexity | Perplexity | ✅ Optimal |
| RAG Search | Tavily | Tavily | ✅ Optimal |
| Semantic Search | Not available | Exa | Missing |

### 8.3 Architecture Gap

| Aspect | Current | Optimal | Gap |
|--------|---------|---------|-----|
| Pipeline | Sequential | Parallel phases | Performance |
| Context | Full data passing | Compaction | Efficiency |
| Quality Gate | Exists unused | Integrated | Integration |
| Cost Tracking | None | Per-job aggregation | Missing |

### 8.4 ML Optimization Gap (Research-Validated)

Based on comprehensive research comparing LLMs vs traditional ML for specific tasks.

| Component | Current | Optimal | Research Finding |
|-----------|---------|---------|------------------|
| Claim Dedup | O(n²) Jaccard | **MinHash LSH O(n)** | [arXiv LSHBloom](https://arxiv.org/html/2411.04257) |
| Entity Extraction | spaCy en_core_web_sm | **spaCy en_core_web_trf** | +6% F1 accuracy |
| Source Scoring | Domain authority only | **Add BM25 relevance** | [Jina AI](https://jina.ai/news/having-it-both-ways-combining-bm25-with-ai-reranking/) |
| Claim Threshold | score >= 3 | **score >= 4** | Reduces LLM calls by ~30% |

**What's Already Optimal (No Change Needed):**
- Quality Gate is deterministic (no LLM) - ✅ Correct per research
- Entity extraction uses spaCy - ✅ Faster/cheaper than LLM per [Explosion AI](https://explosion.ai/blog/against-llm-maximalism)
- Claim candidate filter uses regex heuristics - ✅ High recall pre-filter pattern

**What Should NOT Use Traditional ML:**
- Planning: Complex reasoning requires LLM
- Claim canonicalization: Semantic normalization requires LLM
- Documentary synthesis: Creative work requires LLM

---

## Part 9: Roadmap

### 9.1 Tier 1: Critical Fixes (Immediate)

| Item | File | Effort | Impact |
|------|------|--------|--------|
| Fix transcription order | `backend/integrations/transcripts.py` | 1 hour | HIGH |
| Activate Quality Gate | `backend/pipeline/stages.py` | 2 hours | HIGH |
| Add Reddit fallback | `backend/integrations/reddit_client.py` | 1 hour | MEDIUM |
| Add cost tracking | `backend/pipeline/cost_tracker.py` | 3 hours | HIGH |
| **Raise claim threshold** | `backend/pipeline/extraction.py` | 10 min | MEDIUM |

**Transcription Order Fix:**
```python
# Current (wrong): Supadata → youtube-api → Whisper
# Correct: Supadata → Whisper → youtube-api
# Reason: youtube-api blocked on cloud IPs
```

**Claim Threshold Fix (Research-Validated):**
```python
# Current: if score >= 3:
# Optimal: if score >= 4:
# Saves ~30% LLM calls
```

### 9.2 Tier 2: API Stack Upgrades (Research-Validated)

| Item | File | Effort | Impact | Priority |
|------|------|--------|--------|----------|
| **Add Exa semantic search** | `backend/integrations/exa_client.py` | 4 hours | HIGH | **P0** |
| **Add Gemini 2.5 Flash for planning** | `backend/integrations/gemini_client.py` | 4 hours | HIGH | **P0** |
| **Add Gemini 2.5 Pro for vision** | `backend/integrations/gemini_client.py` | 2 hours | HIGH | **P0** |
| Add Serper as backup search | `backend/integrations/serper_client.py` | 2 hours | MEDIUM | P1 |
| Demote Tavily to fallback | `backend/pipeline/stages.py` | 1 hour | HIGH | P1 |

**Exa Integration (94.9% Accuracy):**
```python
# backend/integrations/exa_client.py
from exa_py import Exa
exa = Exa(api_key=settings.EXA_API_KEY)
result = exa.search_and_contents(query, num_results=10)
```

### 9.3 Tier 3: ML Optimizations (Research-Validated)

| Item | File | Effort | Impact |
|------|------|--------|--------|
| **MinHash LSH deduplication** | `backend/pipeline/extraction.py` | 2 hours | HIGH |
| **Add BM25 to Quality Gate** | `backend/pipeline/quality_gate.py` | 2 hours | MEDIUM |
| Upgrade spaCy model | `backend/pipeline/entities.py` | 30 min | MEDIUM |

**MinHash Implementation:**
```python
# pip install datasketch
from datasketch import MinHash, MinHashLSH
lsh = MinHashLSH(threshold=0.7, num_perm=128)
# Replaces O(n²) Jaccard with O(n) scaling
```

**BM25 Source Scoring:**
```python
# pip install rank-bm25
from rank_bm25 import BM25Okapi
bm25 = BM25Okapi([source_tokens])
relevance = bm25.get_scores(query_terms)
```

### 9.4 Tier 4: Architecture Improvements

| Item | Effort | Impact |
|------|--------|--------|
| Parallelize discovery stages (Celery group) | 1 day | HIGH |
| Implement context compaction | 1 day | MEDIUM |
| Mode-based search routing | 4 hours | HIGH |

### 9.5 Tier 5: Future Evaluation

| Item | Notes | Decision |
|------|-------|----------|
| Claude Opus 4 for synthesis | 50x more expensive, marginal gain | **SKIP** unless quality gap observed |
| DeepSeek V3 | Labeled "experimental", Beta function calling | **WAIT** for stable release |
| Groq for speed | Consider for breaking_news only | EVALUATE |
| Additional niches | Based on user demand | ON DEMAND |
| Claude Agent SDK | Evaluate migration benefit | EVALUATE |

---

## Part 10: Configuration Reference

### 10.1 Environment Variables

```bash
# Core (Required)
REDIS_URL=redis://...
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# LLM (Required)
OPENAI_API_KEY=sk-...

# Search (Required)
PERPLEXITY_API_KEY=pplx-...
TAVILY_API_KEY=tvly-...

# Optional LLMs (For multi-model strategy)
ANTHROPIC_API_KEY=sk-ant-...    # Claude (not implemented)
DEEPSEEK_API_KEY=sk-...          # DeepSeek (not implemented)
GROQ_API_KEY=gsk_...             # Groq (not implemented)

# Content (Optional)
SUPADATA_API_KEY=...
YOUTUBE_API_KEY=...
EXA_API_KEY=...                  # Not implemented

# Reddit (Optional)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=...

# Google Drive (Optional)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...

# Slack (Optional)
SLACK_SIGNING_SECRET=...
SLACK_BOT_TOKEN=...

# Frontend
FRONTEND_ORIGINS=https://research-agent-kohl.vercel.app
```

### 10.2 Railway Deployment

```bash
# Project ID
railway link -p 9d40e7f3-4b60-4456-8a56-9ade9a9c3321

# Services
# - API: Runs FastAPI (default)
# - Worker: Runs Celery (SERVICE_TYPE=worker)
# - Redis: Internal broker

# Key Commands
railway status
railway logs -n 50
railway service API
railway service Worker
```

---

## Part 11: Research Basis

This PRD was created through comprehensive validation:

### 11.1 Internal Validation

- Line-by-line validation of PRD v4.3 against codebase
- Line-by-line validation of PRD v5.0 against codebase
- Gap analysis between claims and implementation

### 11.2 External Research

| Source | Key Finding |
|--------|-------------|
| Anthropic: Building Effective Agents | Orchestrator-Worker pattern, start simple |
| Anthropic: Multi-Agent Systems | 90.2% success rate with multi-agent |
| Anthropic: Context Engineering | Compaction, note-taking, sub-agents |
| AI Search API Comparison | Perplexity (speed), Exa (accuracy), Tavily (RAG) |
| LLM Benchmarks | Claude for quality, DeepSeek for cost, Groq for speed |
| YouTube Transcript Research | youtube-api blocked on cloud IPs |

### 11.3 Key Corrections from Previous PRDs

| Claim | PRD v4.3 | PRD v5.0 | Reality |
|-------|----------|----------|---------|
| Primary LLM | Claude Sonnet 4.5 | DeepSeek V3 | OpenAI GPT-4o-mini |
| Mode count | 6 modes | 7 modes | 4 modes |
| Quality Gate | Integrated | Not mentioned | Exists, not integrated |
| Cost tracking | budget_guard() | ~$0.30/job | Not implemented |
| Transcription | Supadata→Whisper→youtube-api | Not specified | Supadata→youtube-api→Whisper (wrong order) |

---

## Appendix A: File Reference

### Key Backend Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI endpoints |
| `backend/worker.py` | Celery task definitions |
| `backend/pipeline/stages.py` | Pipeline stage implementations |
| `backend/pipeline/context.py` | Shared pipeline state |
| `backend/pipeline/quality_gate.py` | Source filtering (not integrated) |
| `backend/pipeline/dual_output.py` | NotebookLM + Documentary output |
| `backend/pipeline/documentary_intelligence.py` | Documentary analysis |
| `backend/pipeline/niche_loader.py` | Niche overlay loading |
| `backend/models/job_config.py` | Mode configurations |
| `backend/models/job_record.py` | Job state schema |
| `backend/config.py` | Configuration management |
| `backend/state/factory.py` | Job store abstraction |

### Key Frontend Files

| File | Purpose |
|------|---------|
| `frontend/pages/index.tsx` | Main page |
| `frontend/components/ui/` | UI component library |
| `frontend/stores/` | Zustand state stores |
| `frontend/hooks/useETA.ts` | ETA calculation |

---

## Appendix B: Version History

| Version | Date | Changes |
|---------|------|---------|
| v6.0 | Dec 2024 | Research-validated rewrite, supersedes v4.3 and v5.0 |
| v5.0 | Dec 2024 | NotebookLM-first architecture (partially implemented) |
| v4.3 | Dec 2024 | Quality Gate focus (partially implemented) |

---

*This document is the authoritative specification for Research Agent. Previous versions (v4.3, v5.0) are archived for reference but should not be used for development guidance.*
