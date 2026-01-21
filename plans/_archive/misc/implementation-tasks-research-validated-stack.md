# Implementation Tasks: Research-Validated Stack Upgrades

**Created:** December 25, 2025
**Based On:** Validated API stack and ML optimization research
**Status:** Ready for Implementation

---

## Overview

This document consolidates all implementation tasks derived from research validation of the Research Agent API stack and ML optimization opportunities.

**Total Estimated Effort:** ~20-25 hours
**Monthly Cost Savings:** ~$15-54 (15-20% reduction)
**Quality Improvement:** Significant (Exa 94.9% accuracy, Gemini multimodal)

---

## Tier 1: Quick Wins (Immediate, <1 hour each)

### 1.1 Raise Claim Extraction Threshold
**File:** `backend/pipeline/extraction.py`
**Line:** ~196
**Effort:** 10 minutes
**Impact:** Reduces LLM calls by ~30%

```python
# Change from:
if score >= 3:
# To:
if score >= 4:
```

### 1.2 Install ML Optimization Libraries
**Effort:** 5 minutes

```bash
pip install datasketch rank-bm25
# Add to requirements.txt:
# datasketch>=1.6.0
# rank-bm25>=0.2.2
```

### 1.3 Activate Quality Gate in Pipeline
**File:** `backend/pipeline/stages.py`
**Effort:** 30 minutes
**Impact:** HIGH - Filters low-quality sources before extraction

```python
# Add after stage_source_discovery:
from backend.pipeline.quality_gate import run_quality_gate

async def stage_quality_gate(ctx: PipelineContext) -> None:
    """Filter and score discovered sources (deterministic, no LLM)."""
    result = run_quality_gate(
        sources=ctx.web_sources,
        mode=ctx.job_config.mode.value if ctx.job_config else "full"
    )
    ctx.web_sources = result["approved"]
    ctx.add_warning(f"Quality Gate: {result['stats']['approved_count']} approved, "
                    f"{result['stats']['rejected_count']} rejected")
```

---

## Tier 2: API Stack Upgrades (~12 hours total)

### 2.1 Add Exa Semantic Search Client
**File:** `backend/integrations/exa_client.py` (new)
**Effort:** 2 hours
**Impact:** 94.9% search accuracy (highest)

```python
"""Exa AI semantic search client."""
from exa_py import Exa
from loguru import logger
from backend.config import settings

class ExaClient:
    """Client for Exa semantic search API."""

    def __init__(self):
        api_key = settings.EXA_API_KEY
        if not api_key:
            raise ValueError("EXA_API_KEY not configured")
        self.client = Exa(api_key=api_key)

    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_domains: list[str] = None,
        exclude_domains: list[str] = None,
    ) -> list[dict]:
        """Semantic search with optional domain filtering."""
        logger.info(f"Exa search: {query[:50]}...")
        try:
            result = self.client.search_and_contents(
                query,
                num_results=num_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                text=True,
            )
            return [
                {
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.text[:500] if r.text else "",
                    "score": r.score,
                }
                for r in result.results
            ]
        except Exception as e:
            logger.error(f"Exa search error: {e}")
            raise
```

### 2.2 Add Gemini Client
**File:** `backend/integrations/gemini_client.py` (new)
**Effort:** 3 hours
**Impact:** 1M context, multimodal, thinking mode

```python
"""Google Gemini API client for planning and vision tasks."""
import google.generativeai as genai
from loguru import logger
from backend.config import settings

class GeminiClient:
    """Client for Gemini 2.5 Flash/Pro."""

    def __init__(self):
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        genai.configure(api_key=api_key)

    async def generate_with_thinking(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 1024,
    ) -> str:
        """Generate with thinking mode for complex reasoning."""
        logger.info(f"Gemini {model} thinking: {prompt[:50]}...")
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(
            prompt,
            generation_config={
                "thinking_config": {"thinking_budget": thinking_budget}
            }
        )
        return response.text

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        model: str = "gemini-2.5-pro",
    ) -> str:
        """Analyze image with Gemini Pro vision."""
        logger.info(f"Gemini vision analysis: {prompt[:50]}...")
        model_instance = genai.GenerativeModel(model)
        with open(image_path, "rb") as f:
            image_data = f.read()
        response = model_instance.generate_content([prompt, image_data])
        return response.text
```

### 2.3 Add Serper Client (Backup Search)
**File:** `backend/integrations/serper_client.py` (new)
**Effort:** 1 hour
**Impact:** 93.5% success rate, $1/1k searches

```python
"""Serper search API client (backup for Exa/Perplexity)."""
import httpx
from loguru import logger
from backend.config import settings

class SerperClient:
    """Client for Serper search API."""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured")

    async def search(self, query: str, num_results: int = 10) -> list[dict]:
        """Perform Google search via Serper."""
        logger.info(f"Serper search: {query[:50]}...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.BASE_URL,
                headers={"X-API-KEY": self.api_key},
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()
            return [
                {
                    "url": r.get("link"),
                    "title": r.get("title"),
                    "snippet": r.get("snippet", ""),
                }
                for r in data.get("organic", [])
            ]
```

### 2.4 Update Config with New API Keys
**File:** `backend/config.py`
**Effort:** 30 minutes

```python
# Add to Settings class:
GOOGLE_API_KEY: Optional[str] = None
EXA_API_KEY: Optional[str] = None
SERPER_API_KEY: Optional[str] = None

def require_gemini(self) -> str:
    if not self.GOOGLE_API_KEY:
        raise MissingRequiredSettingError("GOOGLE_API_KEY")
    return self.GOOGLE_API_KEY

def require_exa(self) -> str:
    if not self.EXA_API_KEY:
        raise MissingRequiredSettingError("EXA_API_KEY")
    return self.EXA_API_KEY

def require_serper(self) -> str:
    if not self.SERPER_API_KEY:
        raise MissingRequiredSettingError("SERPER_API_KEY")
    return self.SERPER_API_KEY
```

### 2.5 Implement Mode-Based Search Routing
**File:** `backend/pipeline/stages.py`
**Effort:** 2 hours
**Impact:** Optimal API selection per mode

```python
async def stage_source_discovery(ctx: PipelineContext) -> None:
    """Discover sources using mode-appropriate APIs."""
    mode = ctx.job_config.mode.value if ctx.job_config else "investigation"

    if mode == "breaking_news":
        # Speed priority: Perplexity only
        sources = await perplexity_search(ctx.topic)
    elif mode in ["investigation", "controversy"]:
        # Accuracy priority: Exa + Perplexity
        exa_sources = await exa_search(ctx.topic)
        perplexity_sources = await perplexity_search(ctx.topic)
        sources = deduplicate_sources(exa_sources + perplexity_sources)
    elif mode == "profile":
        # Entity focus: Exa semantic
        sources = await exa_search(f'"{ctx.topic}" biography profile')
    else:
        sources = await perplexity_search(ctx.topic)

    ctx.web_sources = sources
```

### 2.6 Demote Tavily to Fallback
**File:** `backend/pipeline/stages.py`
**Effort:** 1 hour

```python
async def search_with_fallback(query: str, mode: str) -> list[dict]:
    """Search with cascading fallback."""
    # Tier 1: Primary (mode-based)
    try:
        if mode == "breaking_news":
            return await perplexity_search(query)
        else:
            return await exa_search(query)
    except Exception as e:
        logger.warning(f"Primary search failed: {e}")

    # Tier 2: Serper backup
    try:
        return await serper_search(query)
    except Exception as e:
        logger.warning(f"Serper backup failed: {e}")

    # Tier 3: Tavily (last resort - 10% error rate)
    try:
        return await tavily_search(query)
    except Exception as e:
        logger.error(f"All search APIs failed: {e}")
        return []
```

---

## Tier 3: ML Optimizations (~6 hours total)

### 3.1 MinHash LSH Claim Deduplication
**File:** `backend/pipeline/extraction.py`
**Effort:** 2 hours
**Impact:** O(n) vs O(n²) scaling

```python
from datasketch import MinHash, MinHashLSH

def _dedupe_claims_minhash(claims: list[Claim], threshold: float = 0.7) -> list[Claim]:
    """Deduplicate claims using MinHash LSH (O(n) complexity)."""
    if not claims:
        return []

    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    minhashes = {}

    # Build LSH index
    for i, claim in enumerate(claims):
        m = MinHash(num_perm=128)
        for word in claim.canonical_claim.lower().split():
            m.update(word.encode('utf8'))
        lsh.insert(f"claim_{i}", m)
        minhashes[i] = m

    # Group similar claims
    deduped = []
    processed = set()

    for i in range(len(claims)):
        if i in processed:
            continue
        similar_ids = lsh.query(minhashes[i])
        group = [int(s.split('_')[1]) for s in similar_ids]
        processed.update(group)

        # Merge: keep highest confidence, combine citations
        best_idx = max(group, key=lambda idx: claims[idx].confidence)
        merged = claims[best_idx].model_copy()
        for idx in group:
            if idx != best_idx:
                merged.citations.extend(claims[idx].citations)
        deduped.append(merged)

    logger.info(f"MinHash dedup: {len(claims)} → {len(deduped)} claims")
    return deduped
```

### 3.2 BM25 Source Scoring in Quality Gate
**File:** `backend/pipeline/quality_gate.py`
**Effort:** 2 hours
**Impact:** Better topic relevance filtering

```python
from rank_bm25 import BM25Okapi

def _calculate_bm25_relevance(
    sources: list[Source],
    query_terms: list[str]
) -> dict[str, float]:
    """Calculate BM25 relevance scores for sources."""
    if not query_terms:
        return {}

    # Tokenize source content
    corpus = []
    for source in sources:
        text = f"{source.title} {source.snippet}".lower()
        corpus.append(text.split())

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_terms)

    return {
        source.canonical_url: scores[i]
        for i, source in enumerate(sources)
    }

# Update _calculate_quality_score to include BM25:
def _calculate_quality_score(
    source: Source,
    bm25_scores: dict[str, float] = None
) -> float:
    score = 0.5  # Base score

    # ... existing domain authority logic ...

    # Add BM25 relevance bonus
    if bm25_scores and source.canonical_url in bm25_scores:
        bm25_score = bm25_scores[source.canonical_url]
        score += min(0.2, bm25_score * 0.1)  # Cap at 0.2 bonus

    return max(0.0, min(1.0, score))
```

### 3.3 Upgrade spaCy Model
**File:** `backend/pipeline/entities.py`
**Effort:** 30 minutes
**Impact:** +6% F1 accuracy

```bash
# Install transformer model
python -m spacy download en_core_web_trf

# Update entities.py:
try:
    nlp = spacy.load("en_core_web_trf")  # 91% F1 vs 85%
except OSError:
    nlp = spacy.load("en_core_web_sm")  # Fallback
```

**Note:** en_core_web_trf is 500MB vs 12MB. Only upgrade if Railway memory permits.

---

## Tier 4: Architecture Improvements (~8 hours)

### 4.1 Parallelize Discovery Stages
**Effort:** 4 hours
**Impact:** 40-60% faster discovery phase

```python
from celery import group

@celery.task
def parallel_discovery(job_id: str, topic: str, mode: str):
    """Run discovery stages in parallel."""
    parallel_tasks = group(
        discover_web_sources.s(topic, mode),
        enumerate_youtube.s(topic),
        discover_reddit.s(topic),
    )
    results = parallel_tasks.apply_async()
    return results.get()
```

### 4.2 Context Compaction
**Effort:** 4 hours
**Impact:** Reduce memory usage, fit larger jobs

---

## Dependencies to Add

```txt
# requirements.txt additions
datasketch>=1.6.0          # MinHash LSH
rank-bm25>=0.2.2           # BM25 scoring
exa-py>=1.0.0              # Exa search
google-generativeai>=0.3.0 # Gemini
```

---

## Environment Variables to Add

```bash
# .env additions
GOOGLE_API_KEY=            # Gemini 2.5 Flash/Pro
EXA_API_KEY=               # Semantic search (94.9% accuracy)
SERPER_API_KEY=            # Backup search ($1/1k)
```

---

## Testing Checklist

- [ ] Claim threshold change doesn't break extraction
- [ ] Quality Gate activation works in pipeline
- [ ] Exa client returns valid results
- [ ] Gemini client generates with thinking mode
- [ ] Serper fallback works when Exa fails
- [ ] MinHash dedup produces same results as Jaccard
- [ ] BM25 scoring improves source relevance
- [ ] spaCy trf model loads (or falls back gracefully)

---

## Rollback Plan

If any integration causes issues:

1. **API Keys**: Simply unset the env var to disable integration
2. **MinHash**: `git revert` the extraction.py changes
3. **BM25**: Quality Gate works without it (graceful)
4. **spaCy trf**: Automatic fallback to sm model

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| LLM calls per job | ~60 | ~40 (-30%) |
| Search accuracy | ~91% (Tavily) | ~94.9% (Exa) |
| Claim dedup time | O(n²) | O(n) |
| Monthly API cost | ~$150-250 | ~$130-200 |
