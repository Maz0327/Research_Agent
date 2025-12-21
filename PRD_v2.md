# Product Requirements Document (PRD) v2.0
## Research Agent - Ultimate Documentary Research System

### Document Purpose
This PRD defines the **REVISED** requirements for the Research Agent system, incorporating a multi-API architecture for superior accuracy, cost efficiency, and reliability. It is specifically written to guide AI implementation (Claude Sonnet) with explicit warnings against common pitfalls.

**CRITICAL FOR SONNET:** This document supersedes PRD_v1.md. Do NOT reference PRD_v1 for implementation details.

---

## 1. What Changed from v1 to v2

### Summary of Major Changes
| Component | v1 Approach | v2 Approach | Reason |
|-----------|-------------|-------------|--------|
| **Primary Search** | Perplexity only | Exa.ai (primary) + Brave (backup) | 94.9% accuracy vs ~80% |
| **Content Extraction** | Playwright + Trafilatura | Jina AI Reader API | 2s response, LLM-ready, free |
| **News Discovery** | Perplexity | GDELT + NewsAPI.ai | Free, massive scale |
| **Fact-Checking** | Perplexity validation | ClaimBuster + Google Fact Check | Specialized, free |
| **Academic Sources** | None | Semantic Scholar API | Free, 200M papers |
| **YouTube Transcripts** | youtube-transcript-api only | 3-tier fallback system | Handles videos without captions |
| **Archives** | None | Wayback Machine API | Free historical data |
| **Cost per job** | $7-15 | $3-8 | 40-60% reduction |

---

## 2. Product Vision & Goals (UNCHANGED from v1)

### Vision Statement
Build a **dual-purpose research and documentary intelligence system** that both gathers comprehensive research for NotebookLM analysis AND transforms it into production-ready documentary blueprints.

### The Hybrid Architecture
```
Multi-API Research Gathering + Documentary Intelligence Layer
                        |
    Dual Output: NotebookLM Packet + Documentary Blueprint
```

### Primary Goals
1. **Comprehensive Research** - Gather all available sources with multiple APIs
2. **Documentary Intelligence** - Transform research into narrative structures
3. **Dual Output System** - Serve both analysis (NotebookLM) and production (video creation)
4. **Cost Optimization** - Use the cheapest effective API for each task

### Success Metrics
- Research completion in <30 minutes
- Both outputs generated (research packet + documentary blueprint)
- <$8 cost per complete package (down from $15)
- 94%+ search accuracy (using Exa.ai)

---

## 3. Multi-API Architecture (NEW IN v2)

### CRITICAL SONNET WARNING
**DO NOT** default to Perplexity for everything. Each API serves a specific purpose. Use the RIGHT tool for each task.

### 3.1 Search APIs - Tiered Approach

#### Tier 1: Exa.ai (PRIMARY SEARCH)
**Purpose:** Neural semantic search with 94.9% accuracy
**Use for:** Main topic research, finding authoritative sources
**Cost:** $0.001-0.002 per search (100 free searches/month)
**When to use:** First-pass research, finding specific claims, source discovery

```python
# SONNET: This is the PRIMARY search. Use it first.
EXA_SEARCH_CONFIG = {
    "model": "exa-search",
    "num_results": 20,
    "use_autoprompt": True,  # Enhances queries automatically
    "include_domains": [],    # Optional filtering
    "exclude_domains": ["reddit.com"],  # Reddit has dedicated API
    "start_crawl_date": None,  # Optional date filtering
    "end_crawl_date": None,
}
```

**SONNET WARNING:** Exa returns URLs. You MUST use Jina AI Reader to extract content.

#### Tier 2: Brave Search (BACKUP + FREE TIER)
**Purpose:** Backup search, privacy-focused, 2,000 free requests/month
**Use for:** Fallback when Exa fails, budget-conscious jobs
**Cost:** FREE for 2,000 req/month, then $0.003/query

```python
BRAVE_SEARCH_CONFIG = {
    "count": 20,
    "search_lang": "en",
    "safesearch": "off",  # Important for controversial research
    "freshness": None,     # Options: pd, pw, pm, py (day/week/month/year)
}
```

#### Tier 3: Perplexity (VALIDATION ONLY)
**Purpose:** Claim validation, fact-checking with citations
**Use for:** Final validation step ONLY - not initial research
**Cost:** $0.20-5.00 per 1M tokens

**SONNET WARNING:** Perplexity is EXPENSIVE. Use it ONLY for:
1. Validating extracted claims
2. Running missing angles analysis
3. Final fact-check pass

**DO NOT USE for:** Initial source discovery, web scraping, general research

### 3.2 News Discovery APIs

#### GDELT (PRIMARY NEWS)
**Purpose:** Real-time news monitoring, global coverage
**Use for:** Breaking news mode, trending topics
**Cost:** FREE (unlimited)
**Scale:** 100,000+ articles/day, 65 languages

```python
GDELT_CONFIG = {
    "mode": "ArtList",  # Get article list
    "maxrecords": 50,   # Per query
    "format": "json",
    "timespan": "24h",  # Options: 15min, 1h, 24h, 7d, 30d
    "domain": None,     # Optional domain filter
}
```

**Integration:** Use GDELT GKG (Global Knowledge Graph) for entity extraction

#### NewsAPI.ai (ENRICHED NEWS)
**Purpose:** Enhanced news with entity extraction, sentiment
**Use for:** Profile mode, controversy mode (need entity linking)
**Cost:** $0.001/article (free tier: 1000 articles/month)

### 3.3 Content Extraction

#### Jina AI Reader (PRIMARY EXTRACTION)
**Purpose:** Convert any URL to LLM-ready markdown
**Use for:** ALL content extraction (replaces Playwright+Trafilatura)
**Cost:** FREE (rate limited), Pro: $0.0001/page
**Speed:** 2-3 seconds per page

```python
# SONNET: This replaces Playwright scraping
JINA_READER_CONFIG = {
    "base_url": "https://r.jina.ai/",  # Prepend to any URL
    "headers": {
        "Accept": "text/markdown",
        "X-Return-Format": "markdown",
    }
}

# Usage: Simply prepend URL
# https://r.jina.ai/https://example.com/article
```

**SONNET WARNING:**
- Jina returns clean markdown, NOT raw HTML
- Include images and formatting
- Handles JavaScript-rendered pages
- Much faster than Playwright (2s vs 10-30s)

**FALLBACK:** If Jina fails, use Trafilatura directly (local, no API)

### 3.4 Fact-Checking Pipeline

#### ClaimBuster (CLAIM DETECTION)
**Purpose:** Identify check-worthy claims in text
**Use for:** Pre-filtering before expensive validation
**Cost:** FREE (academic use)
**Output:** Score 0-1 for claim worthiness

```python
CLAIMBUSTER_CONFIG = {
    "endpoint": "https://idir.uta.edu/claimbuster/api/v2/score/text/",
    "threshold": 0.5,  # Only validate claims scoring above this
}
```

**SONNET:** Use ClaimBuster BEFORE Perplexity validation. Only send high-scoring claims to Perplexity.

#### Google Fact Check API (EXISTING CHECKS)
**Purpose:** Find existing fact-checks for claims
**Use for:** Checking if claim already debunked/verified
**Cost:** FREE (part of Google Cloud)
**Output:** Links to existing fact-check articles

```python
GOOGLE_FACTCHECK_CONFIG = {
    "languageCode": "en",
    "pageSize": 10,
}
```

**Pipeline:**
1. ClaimBuster scores claims (free)
2. Google Fact Check finds existing verdicts (free)
3. Perplexity validates remaining uncertain claims (paid)

### 3.5 Academic Sources

#### Semantic Scholar (ACADEMIC PAPERS)
**Purpose:** Access 200M+ academic papers
**Use for:** Investigation mode, credibility checking, scientific topics
**Cost:** FREE (100 requests/second limit)

```python
SEMANTIC_SCHOLAR_CONFIG = {
    "fields": "title,abstract,year,authors,citationCount,url,openAccessPdf",
    "limit": 20,
}
```

**SONNET:** Include academic sources for:
- Scientific claims
- Expert opinions
- Historical context

### 3.6 Archives

#### Wayback Machine (HISTORICAL DATA)
**Purpose:** Access archived versions of websites
**Use for:** Deleted content, historical research, proof of changes
**Cost:** FREE

```python
WAYBACK_CONFIG = {
    "availability_endpoint": "http://archive.org/wayback/available",
    "snapshot_endpoint": "http://web.archive.org/web/{timestamp}/{url}",
}
```

**Use cases:**
- Verify deleted tweets/posts
- Show evolution of statements
- Recover removed content

---

## 4. YouTube Transcript Extraction (NEW 3-TIER SYSTEM)

### SONNET WARNING
The current system only uses youtube-transcript-api. This fails for videos without captions. Implement the full 3-tier system.

### Tier 1: Native Captions (youtube-transcript-api)
**Use for:** Videos with existing captions
**Cost:** FREE
**Quality:** High (human-generated) or Medium (auto-generated)

```python
TRANSCRIPT_TIER_1 = {
    "method": "youtube_transcript_api",
    "languages": ["en", "en-GB", "en-US"],  # Preferred order
    "fallback_generated": True,  # Accept auto-generated if manual unavailable
}
```

### Tier 2: Audio Download + Whisper API
**Use for:** Videos without any captions
**Cost:** $0.006/minute
**Quality:** Very High (Whisper large-v3)

```python
TRANSCRIPT_TIER_2 = {
    "method": "yt_dlp_whisper",
    "audio_format": "mp3",
    "whisper_model": "whisper-1",  # OpenAI API
    "max_duration_minutes": 60,    # Cost control
}
```

**Implementation:**
1. Use yt-dlp to download audio only
2. Send to OpenAI Whisper API
3. Return timestamped transcript

### Tier 3: AssemblyAI (Fallback)
**Use for:** When Whisper fails or need speaker diarization
**Cost:** $0.015/minute (includes diarization)
**Quality:** Very High + speaker identification

```python
TRANSCRIPT_TIER_3 = {
    "method": "assemblyai",
    "speaker_labels": True,   # Identify different speakers
    "auto_chapters": True,    # Automatic topic segmentation
    "entity_detection": True, # Named entity extraction
}
```

### Fallback Logic
```python
def get_transcript(video_id: str, max_cost_usd: float = 0.50):
    """
    3-tier transcript extraction with cost control.

    SONNET: Implement this EXACTLY. Do not skip tiers.
    """
    # Tier 1: Try native captions (free)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return {"method": "native", "cost": 0, "transcript": transcript}
    except NoTranscriptFound:
        pass
    except TranscriptsDisabled:
        pass

    # Get video duration for cost estimation
    duration_minutes = get_video_duration(video_id)

    # Tier 2: Whisper API ($0.006/min)
    whisper_cost = duration_minutes * 0.006
    if whisper_cost <= max_cost_usd:
        try:
            audio_path = download_audio(video_id)
            transcript = transcribe_with_whisper(audio_path)
            return {"method": "whisper", "cost": whisper_cost, "transcript": transcript}
        except Exception as e:
            logger.warning(f"Whisper failed: {e}")

    # Tier 3: AssemblyAI ($0.015/min) - only if budget allows
    assemblyai_cost = duration_minutes * 0.015
    if assemblyai_cost <= max_cost_usd:
        try:
            transcript = transcribe_with_assemblyai(video_id)
            return {"method": "assemblyai", "cost": assemblyai_cost, "transcript": transcript}
        except Exception as e:
            logger.warning(f"AssemblyAI failed: {e}")

    # All tiers failed
    return {"method": "none", "cost": 0, "transcript": None, "error": "No transcript available"}
```

---

## 5. Documentary Research Modes (UNCHANGED from v1)

### Mode: `breaking_news`
- **Focus:** Speed and recency over depth
- **Primary APIs:** GDELT (news), Brave Search (backup), Reddit
- **Timeline:** Last 48-72 hours with hourly precision
- **Max Duration:** 10 minutes
- **Max Cost:** $2

### Mode: `investigation`
- **Focus:** Deep verification and hidden connections
- **Primary APIs:** Exa.ai (search), Semantic Scholar (academic), full validation pipeline
- **Timeline:** Complete historical reconstruction
- **Max Duration:** 45 minutes
- **Max Cost:** $15

### Mode: `profile`
- **Focus:** Single person or organization deep dive
- **Primary APIs:** Exa.ai (entity search), YouTube, NewsAPI.ai
- **Timeline:** Biographical/chronological
- **Max Duration:** 30 minutes
- **Max Cost:** $8

### Mode: `controversy`
- **Focus:** All sides of a disputed issue
- **Primary APIs:** Exa.ai, Google Fact Check, full validation
- **Timeline:** Event sequence with claim/counter-claim
- **Max Duration:** 30 minutes
- **Max Cost:** $10

---

## 6. Cost Optimization Strategy (NEW)

### API Cost Comparison (Validated January 2025)

| Task | v1 Cost | v2 Cost | Savings |
|------|---------|---------|---------|
| Source Discovery (20 queries) | $4.00 (Perplexity) | $0.02 (Exa) + FREE (Brave backup) | 99% |
| Content Extraction (30 pages) | $0.50 (Playwright compute) | FREE (Jina) | 100% |
| Claim Detection | $1.00 (Perplexity) | FREE (ClaimBuster) | 100% |
| Existing Fact-Checks | $0.50 (Perplexity) | FREE (Google Fact Check) | 100% |
| Claim Validation (10 claims) | $2.00 (Perplexity) | $1.00 (Perplexity, fewer calls) | 50% |
| News Discovery | $1.50 (Perplexity) | FREE (GDELT) | 100% |
| Academic Sources | N/A | FREE (Semantic Scholar) | N/A |
| **TOTAL (investigation mode)** | **~$10-15** | **~$3-8** | **40-60%** |

### Cost-Per-Mode Breakdown (v2)

| Mode | Exa | Jina | GDELT | Perplexity | Whisper | Total |
|------|-----|------|-------|------------|---------|-------|
| breaking_news | $0.01 | FREE | FREE | $0.30 | $0 | **~$0.50** |
| investigation | $0.04 | FREE | FREE | $2.00 | $0.50 | **~$4-6** |
| profile | $0.02 | FREE | FREE | $1.00 | $0.30 | **~$2-3** |
| controversy | $0.03 | FREE | FREE | $1.50 | $0.30 | **~$3-4** |

### Model Selection (Cost Optimization)

```python
# SONNET: Use the RIGHT model for each task
TASK_MODELS = {
    # GPT-4o for complex reasoning ($5/1M input, $15/1M output)
    "job_planning": "gpt-4o",
    "documentary_analysis": "gpt-4o",
    "angle_discovery": "gpt-4o",

    # GPT-4o-mini for simple extraction ($0.15/1M input, $0.60/1M output) - 90% cheaper
    "entity_extraction": "gpt-4o-mini",
    "timeline_extraction": "gpt-4o-mini",
    "claim_formatting": "gpt-4o-mini",
    "summary_generation": "gpt-4o-mini",

    # Perplexity only for validation (expensive)
    "claim_validation": "sonar",  # Not sonar-pro unless needed
    "missing_angles": "sonar",
}
```

---

## 7. Integration Requirements

### 7.1 API Client Priority Matrix

| Task | Primary API | Fallback 1 | Fallback 2 |
|------|-------------|------------|------------|
| Web Search | Exa.ai | Brave Search | Perplexity |
| Content Extraction | Jina Reader | Trafilatura (local) | Playwright |
| News Discovery | GDELT | NewsAPI.ai | Brave News |
| Fact-Checking | ClaimBuster + Google FC | Perplexity | Manual |
| Academic | Semantic Scholar | Google Scholar (scrape) | Skip |
| YouTube Transcripts | youtube-transcript-api | Whisper API | AssemblyAI |
| Archives | Wayback Machine | Google Cache | Skip |

### 7.2 Environment Variables (NEW)

```bash
# Search APIs
EXA_API_KEY=your_exa_key                    # Required
BRAVE_API_KEY=your_brave_key                # Optional (has free tier)

# Content Extraction
JINA_API_KEY=your_jina_key                  # Optional (free tier works)

# News
GDELT_API_KEY=not_required                  # GDELT is free
NEWSAPI_KEY=your_newsapi_key                # Optional

# Fact-Checking
CLAIMBUSTER_API_KEY=your_claimbuster_key    # Free for academic use
GOOGLE_FACTCHECK_API_KEY=your_google_key    # Part of Google Cloud

# Academic
SEMANTIC_SCHOLAR_API_KEY=not_required       # Free, rate-limited

# Transcription (for Tier 2/3)
ASSEMBLYAI_API_KEY=your_assemblyai_key      # Optional, for tier 3

# Existing (unchanged)
OPENAI_API_KEY=required
PERPLEXITY_API_KEY=required                 # Now used only for validation
YOUTUBE_API_KEY=optional
REDDIT_CLIENT_ID=required
REDDIT_CLIENT_SECRET=required
```

### 7.3 Request Budget Controls

```python
# Per-job API limits
API_BUDGETS = {
    "breaking_news": {
        "exa_searches": 5,
        "brave_searches": 10,
        "jina_extractions": 20,
        "gdelt_queries": 5,
        "perplexity_validations": 3,
        "whisper_minutes": 10,
        "total_cost_limit": 2.0,
    },
    "investigation": {
        "exa_searches": 20,
        "brave_searches": 20,
        "jina_extractions": 50,
        "gdelt_queries": 10,
        "semantic_scholar_queries": 10,
        "perplexity_validations": 15,
        "whisper_minutes": 60,
        "total_cost_limit": 15.0,
    },
    "profile": {
        "exa_searches": 10,
        "brave_searches": 10,
        "jina_extractions": 30,
        "perplexity_validations": 8,
        "whisper_minutes": 30,
        "total_cost_limit": 8.0,
    },
    "controversy": {
        "exa_searches": 15,
        "brave_searches": 15,
        "jina_extractions": 40,
        "perplexity_validations": 10,
        "whisper_minutes": 30,
        "total_cost_limit": 10.0,
    },
}
```

---

## 8. Timeline Extraction (UNCHANGED from v1)

**SONNET WARNING:** This feature does NOT exist. You must CREATE it from scratch.

### Requirements:
1. Extract explicit dates from all sources
2. Order events chronologically
3. Include attribution for each event
4. Handle relative dates ("last week", "two months ago")
5. Confidence scoring for inferred dates

### Output Format:
```json
{
  "timeline": [
    {
      "date": "2024-01-15",
      "date_precision": "exact|inferred|approximate",
      "event": "Congressional hearing on topic",
      "source": "https://...",
      "attribution": "Rep. John Smith",
      "confidence": 0.95
    }
  ]
}
```

---

## 9. Entity Extraction (UNCHANGED from v1)

**SONNET WARNING:** The Claim model has an entities field but NO extraction logic. CREATE the extraction.

### Requirements:
1. Extract people, organizations, locations
2. Track aliases and variations
3. Build relationship graph
4. Role identification

---

## 10. Angle Discovery System (UNCHANGED from v1)

### Purpose
Help creators find fresh perspectives on well-covered topics.

### Angle Types:
- **Untold Perspective:** Stories from ignored participants
- **Process Focus:** Behind-the-scenes
- **Temporal Shift:** Before/after stories
- **System Analysis:** Institutional angles
- **Counter-Narrative:** Challenge dominant narrative
- **Intersectional:** Connect unexpected topics

---

## 11. Dual Output System (UNCHANGED from v1)

### Output 1: NotebookLM Research Packet
- Complete research in single markdown file
- All sources with full text
- All claims with validation
- Timeline and entities

### Output 2: Documentary Blueprint
- Three-act structure
- Opening hook
- Interview suggestions
- B-roll list
- Graphics requirements

---

## 12. Critical Implementation Warnings for Sonnet

### DO NOT:
1. **DO NOT** use Perplexity for initial source discovery - use Exa.ai
2. **DO NOT** use Playwright for content extraction - use Jina Reader
3. **DO NOT** skip the 3-tier transcript system - implement all tiers
4. **DO NOT** send all claims to Perplexity - use ClaimBuster first
5. **DO NOT** hardcode API keys anywhere
6. **DO NOT** skip free APIs (GDELT, Semantic Scholar) to "simplify"
7. **DO NOT** combine the 4 research modes into fewer modes
8. **DO NOT** output multiple files for NotebookLM
9. **DO NOT** skip entity/timeline extraction as "optimization"

### YOU MUST:
1. **MUST** use Exa.ai as primary search (94.9% accuracy)
2. **MUST** use Jina Reader for content extraction (free, fast)
3. **MUST** implement 3-tier transcript extraction
4. **MUST** use ClaimBuster before Perplexity (free filtering)
5. **MUST** implement all 4 research modes exactly as specified
6. **MUST** create timeline extraction from scratch
7. **MUST** create entity extraction from scratch
8. **MUST** track API costs per job
9. **MUST** respect per-mode budget limits
10. **MUST** output single NotebookLM file

### Common Sonnet Failure Modes:
1. **The "Simplification" Trap:** Combining APIs "for simplicity" - DON'T
2. **The "Skip Free APIs" Trap:** Ignoring free APIs because they're "extra work" - DON'T
3. **The "Perplexity Everything" Trap:** Using Perplexity for all tasks - DON'T
4. **The "One Transcript Method" Trap:** Only implementing Tier 1 - DON'T
5. **The "Combine Modes" Trap:** Merging 4 modes into 2 - DON'T

---

## 13. Acceptance Criteria

### Core Features
- [ ] Exa.ai as primary search with Brave fallback
- [ ] Jina Reader for content extraction
- [ ] GDELT for news discovery
- [ ] ClaimBuster + Google Fact Check pipeline
- [ ] 3-tier YouTube transcript extraction
- [ ] Semantic Scholar for academic sources
- [ ] 4 research modes working with mode-specific APIs
- [ ] Timeline extraction producing chronological events
- [ ] Entity extraction identifying people/orgs/places
- [ ] Angle discovery system finding unique perspectives
- [ ] Single NotebookLM packet file generation

### Cost Tracking
- [ ] Per-API cost tracking
- [ ] Per-job cost totals
- [ ] Budget limit enforcement
- [ ] Cost displayed in job status

### Quality
- [ ] No regression in existing pipeline
- [ ] All stages have error handling and fallbacks
- [ ] Tests for each API integration

---

## 14. Phased Rollout Plan

### Phase 1: New API Integrations (Week 1)
1. Implement Exa.ai client
2. Implement Jina Reader client
3. Implement GDELT client
4. Implement ClaimBuster client
5. Update environment variables

### Phase 2: Replace Existing Integrations (Week 2)
1. Replace Perplexity source discovery with Exa.ai
2. Replace Playwright extraction with Jina Reader
3. Add ClaimBuster pre-filtering to validation
4. Add Semantic Scholar to investigation mode

### Phase 3: YouTube Transcript Enhancement (Week 3)
1. Implement yt-dlp audio download
2. Integrate Whisper API for Tier 2
3. Add AssemblyAI for Tier 3
4. Implement fallback logic

### Phase 4: Testing & Optimization (Week 4)
1. Integration tests for all APIs
2. Cost tracking verification
3. Performance optimization
4. Documentation updates

---

## Appendix A: API Quick Reference

### Exa.ai
```python
from exa_py import Exa
exa = Exa(api_key=EXA_API_KEY)
results = exa.search_and_contents(query, num_results=20, text=True)
```

### Jina Reader
```python
import httpx
url = f"https://r.jina.ai/{target_url}"
response = httpx.get(url, headers={"Accept": "text/markdown"})
markdown = response.text
```

### GDELT
```python
import httpx
url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&format=json"
response = httpx.get(url)
articles = response.json()["articles"]
```

### ClaimBuster
```python
import httpx
url = "https://idir.uta.edu/claimbuster/api/v2/score/text/"
response = httpx.post(url, json={"input_text": claim_text})
score = response.json()["results"][0]["score"]
```

### Semantic Scholar
```python
import httpx
url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}"
response = httpx.get(url)
papers = response.json()["data"]
```

---

## Appendix B: Example Job Configurations (v2)

### Breaking News Mode
```json
{
  "mode": "breaking_news",
  "topic": "OpenAI news today",
  "apis": {
    "primary_search": "brave",
    "news": "gdelt",
    "extraction": "jina",
    "validation": "perplexity_minimal"
  },
  "max_duration_minutes": 10,
  "max_cost_usd": 2
}
```

### Investigation Mode
```json
{
  "mode": "investigation",
  "topic": "Corporate scandal analysis",
  "apis": {
    "primary_search": "exa",
    "backup_search": "brave",
    "news": "gdelt",
    "academic": "semantic_scholar",
    "extraction": "jina",
    "factcheck": ["claimbuster", "google_factcheck", "perplexity"],
    "transcripts": "3tier"
  },
  "sources": {
    "youtube_channels": ["@channel1", "@channel2"],
    "reddit_subreddits": ["r/relevant1", "r/relevant2"],
    "time_window": "2024-01-01 to present"
  },
  "max_duration_minutes": 45,
  "max_cost_usd": 15
}
```

---

*END OF PRD v2 - See TEP_v2.md for technical implementation details*
