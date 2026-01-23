# Pipeline Performance Analysis
**Date:** 2026-01-23
**Investigator:** Debugger
**Scope:** Semantic extraction pipeline performance bottleneck identification

---

## Executive Summary

**Issue:** Semantic extraction pipeline processes sources sequentially, creating significant bottlenecks for multi-source jobs.

**Root Cause:** Sequential for-loop architecture in `stage_semantic_extraction` (line 607) processes one source at a time, blocking on I/O-bound operations (transcript fetching, Gemini API calls, LLM Judge validation).

**Impact:**
- 10-source job: ~5-15 minutes total processing time
- Each source: 30-90s (transcript + extraction + validation)
- No parallelization = linear time scaling

**Solution:** Implement controlled parallel processing with concurrency limits respecting API rate limits.

---

## Technical Analysis

### Current Execution Flow

```
Job Start
  ├─ source_identity (builds packages) - SEQUENTIAL
  ├─ semantic_extraction - SEQUENTIAL ⚠️ BOTTLENECK
  │   └─ For each source (SRC_1, SRC_2, ... SRC_N):
  │       ├─ Transcript acquisition (0-30s) - I/O BOUND
  │       ├─ Gemini extraction (10-45s) - I/O BOUND
  │       ├─ Quote verification (1-5s) - CPU BOUND
  │       ├─ LLM Judge validation (5-20s) - I/O BOUND
  │       └─ RAG grounding (optional, 3-10s) - I/O BOUND
  ├─ semantic_validation - FAST
  ├─ gap_analysis - FAST
  ├─ semantic_synthesis - SINGLE CALL
  └─ document_assembly - FAST
```

### Key Files & Functions

**Main Stage Loop:**
- File: `/Users/maz/Documents/GitHub/Research_Agent/backend/pipeline/stages/semantic_extraction.py`
- Function: `stage_semantic_extraction()` (line 565)
- Bottleneck: Line 607 `for package in packages:` - sequential iteration
- No parallelism, no concurrency control

**Per-Source Processing (60-90s each):**

1. **Transcript Acquisition** (0-30s)
   - File: `backend/pipeline/transcript_acquisition.py`
   - Function: `acquire_transcript()` (line 258)
   - Fallback chain: Supadata → Whisper → YouTube captions
   - I/O bound, blocks on external APIs

2. **Semantic Extraction** (10-45s)
   - Function: `extract_semantic_structure()` (line 389)
   - Gemini API call with retry logic (max 2 retries)
   - I/O bound, waits for LLM response
   - Uses `@with_rate_limit("gemini")` decorator

3. **Quote Verification** (1-5s)
   - Function: `verify_quotes_in_extraction()` (line 308)
   - CPU bound string matching
   - Minimal time impact

4. **LLM Judge Validation** (5-20s, optional)
   - File: `backend/pipeline/llm_judge.py`
   - Enabled by default (`HallucinationConfig.enable_llm_judge = True`)
   - GPT-4o cross-model validation
   - I/O bound, external API call

5. **RAG Grounding** (3-10s, optional)
   - Disabled by default (`HallucinationConfig.enable_rag_grounding = False`)
   - Embedding + vector search when enabled

### Rate Limits

**Current Rate Limiting:**
- File: `backend/utils/rate_limiter.py`
- Decorator: `@with_rate_limit(api_name)`
- Configured limits:
  - Gemini: 60 req/min, 1500 req/hour
  - OpenAI: 60 req/min, 500 req/hour
  - Supadata: 10 req/min, 100 req/hour
  - Whisper: 10 req/min, 50 req/hour

**Safety Features:**
- Exponential backoff on failures
- Automatic retry (3 attempts)
- Per-API state tracking

### Identified Bottlenecks

**1. Sequential Source Processing** (CRITICAL)
- Location: `semantic_extraction.py:607`
- Current: `for package in packages:`
- Time: Linear O(n) where n = source count
- Example: 10 sources × 60s avg = 10 minutes

**2. Transcript Acquisition** (HIGH)
- Fallback chain is sequential (tier 1 → tier 2 → tier 3)
- Each tier blocks before trying next
- No parallel tier testing
- Time: Up to 30s per source

**3. LLM Judge Enabled by Default** (MEDIUM)
- Adds 5-20s per source
- Runs for ALL sources
- Location: `semantic_extraction.py:724` (check enabled)
- Can be disabled via `JobConfig.hallucination.enable_llm_judge = False`

**4. Gemini Retry Logic** (LOW)
- Max 2 retries with validation loop
- Location: `semantic_extraction.py:427`
- Adds time only on validation failures
- Proper retry is needed, but contributes to total time

---

## Configuration Analysis

**Job Configuration Options:**
- File: `backend/models/job_config.py`
- Hallucination config available but not documented for optimization

**Current Defaults:**
```python
HallucinationConfig:
  enable_llm_judge: True      # ← Adds 5-20s per source
  enable_rag_grounding: False # Already optimized
  max_claims_to_rag_verify: 10
```

**Optimization Opportunity:**
Users could disable LLM Judge for faster processing, but:
- No UI toggle
- No documentation of trade-off
- Not exposed in API

---

## Existing Concurrency Patterns

**Found Patterns:**
1. Rate limiter supports async: `async def wait_for_rate_limit()` (line 161)
2. Decorator works for both sync and async functions (line 180)
3. No current usage of `asyncio.gather()` or `ThreadPoolExecutor`

**Legacy Code:**
- Worker param `enable_parallel` deprecated (line 57)
- Comment indicates parallel was considered but not implemented

---

## Proposed Solutions

### Option 1: Async Parallel Processing (RECOMMENDED)

**Approach:**
```python
# In stage_semantic_extraction()
async def process_source_async(package):
    # Run transcript, extraction, validation in sequence for ONE source
    # But multiple sources run in parallel
    ...

# Run with concurrency limit
async with Semaphore(max_concurrent=3):
    tasks = [process_source_async(pkg) for pkg in packages]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Benefits:**
- Respects rate limits via semaphore
- 3-5x speedup for multi-source jobs
- Uses existing `@with_rate_limit` decorator
- Graceful per-source error handling

**Risks:**
- Must refactor stage to async
- Need to ensure worker loop supports async stages
- Rate limiter already supports async

**Estimated Time Savings:**
- 10 sources: 10 min → 2-3 min (3x faster)
- 20 sources: 20 min → 5-7 min (3x faster)

### Option 2: ThreadPoolExecutor (SIMPLER)

**Approach:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(process_source, pkg): pkg for pkg in packages}
    for future in as_completed(futures):
        result = future.result()
```

**Benefits:**
- Minimal code changes (sync functions work)
- Python GIL not an issue (I/O bound)
- Simpler to implement

**Risks:**
- Thread overhead
- Less elegant than async

**Estimated Time Savings:** Same as Option 1

### Option 3: Optimize Existing Sequential (PARTIAL)

**Quick wins without parallelization:**

1. **Disable LLM Judge by default**
   - Saves: 5-20s per source
   - Trade-off: Lower hallucination detection
   - Make it opt-in instead of opt-out

2. **Parallel transcript tier testing**
   - Try Supadata + Whisper simultaneously
   - Use first successful result
   - Saves: Up to 15s per source

3. **Batch Gemini calls**
   - Extract multiple sources in one call (violates RASS spec Rule 1)
   - NOT RECOMMENDED - breaks source isolation guarantee

---

## Recommendations

### Immediate Actions (High Impact, Low Risk)

1. **Implement Option 2 (ThreadPoolExecutor)** - Target for implementation
   - Max 3-5 concurrent sources
   - Respects existing rate limits
   - Minimal code refactor
   - Estimated effort: 4-6 hours

2. **Make LLM Judge opt-in** - Configuration change
   - Change default: `enable_llm_judge: False`
   - Add API parameter for users who want it
   - Update docs to explain trade-off
   - Estimated effort: 1-2 hours

3. **Add progress tracking** - UX improvement
   - Update job progress per source completion
   - Show "Processing source 3/10..."
   - Estimated effort: 1 hour

### Long-Term Improvements (Medium Priority)

4. **Async refactor** - Replace Option 2 with Option 1
   - Convert stages to async/await
   - Better resource utilization
   - Estimated effort: 1-2 days

5. **Smart concurrency tuning** - Advanced optimization
   - Auto-adjust concurrency based on rate limit headroom
   - Monitor API response times
   - Back off on 429 errors
   - Estimated effort: 3-4 hours

6. **Transcript caching** - Reduce redundant fetches
   - Store transcripts in Supabase
   - Check cache before acquisition
   - Estimated effort: 2-3 hours

---

## Unresolved Questions

1. **Worker async support:** Does Celery worker loop support async stage functions?
   - Need to test if `run_stage_with_recovery()` can handle async
   - May require wrapper: `asyncio.run(stage_func(ctx))`

2. **Rate limit headroom:** Current limits are conservative. Can we increase?
   - Gemini: 60/min seems low for paid tier
   - Need to verify actual quota in Google Cloud Console

3. **Error handling in parallel:** How to handle partial failures?
   - Current: Individual source failure logged, job continues
   - Parallel: Need to ensure same behavior with `return_exceptions=True`

4. **Progress updates:** How granular should parallel progress be?
   - Update on each source completion?
   - Update every N seconds with "X/Y complete"?

5. **Cost implications:** Does parallelization increase API costs?
   - No - same number of calls, just concurrent
   - May reduce costs if timeouts decrease

---

## Appendix: Code Locations

### Critical Files
- `backend/pipeline/stages/semantic_extraction.py` - Main bottleneck
- `backend/pipeline/transcript_acquisition.py` - Transcript fetching
- `backend/integrations/gemini_client.py` - LLM calls (has rate limiting)
- `backend/pipeline/llm_judge.py` - Optional validation layer
- `backend/utils/rate_limiter.py` - Rate limit enforcement
- `backend/worker.py` - Job orchestration (line 337: semantic_extraction call)

### Key Line Numbers
- Sequential loop: `semantic_extraction.py:607`
- Transcript fetch: `transcript_acquisition.py:258`
- Gemini extract: `semantic_extraction.py:693`
- LLM Judge: `semantic_extraction.py:724`
- Rate limit decorator: `rate_limiter.py:180`

### Configuration
- Job config: `backend/models/job_config.py`
- Rate limits: `backend/utils/rate_limiter.py:40-55`
- Default hallucination settings: Need to check `HallucinationConfig` model

---

**Next Steps:**
1. Verify Celery async stage support
2. Prototype ThreadPoolExecutor implementation
3. Test with 10-source job, measure time improvement
4. Update progress tracking
5. Document LLM Judge toggle in API docs
