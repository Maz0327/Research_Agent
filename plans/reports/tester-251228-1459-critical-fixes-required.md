# Critical Pipeline Fixes Required
**Date:** 2025-12-28 14:59
**Severity:** All items must be fixed before next release

---

## PRIORITY 0: PIPELINE CRASHES (Do First)

### Fix 1: niche_config NoneType Error
**File:** `backend/pipeline/stages.py:156`
**Current Code:**
```python
expanded_key_terms = list(ctx.key_terms)
if ctx.niche_config:
    query_additions = ctx.niche_config.get("query_additions", [])  # Line 157
```

**Problem:** If Stage 1 niche loading fails (line 81-83), ctx.niche_config remains None. But Stage 3 tries to use it.

**Fix:**
```python
# In Stage 1 (line 74-83)
if ctx.job_config.niche:
    try:
        ctx.niche_config = merge_mode_and_niche(...)
    except Exception as niche_error:
        ctx.niche_config = {}  # Initialize to empty dict instead of leaving None
        ctx.add_warning(...)

# In Stage 3 (line 156-168)
if ctx.niche_config and isinstance(ctx.niche_config, dict):
    query_additions = ctx.niche_config.get("query_additions", [])
```

**Test:** Create test with job_config.niche specified + planning failure → verify no AttributeError

---

### Fix 2: Cost Tracker Mode Mismatch
**File:** `backend/worker.py:133-143`
**Current Code:**
```python
ctx = PipelineContext(
    job_id=job_id,
    topic=topic,
    slack_payload=slack_payload,
    cost_tracker=CostTracker(mode="full"),  # Line 133 - WRONG
)

try:
    stage_0_initialize(ctx)
    stage_1_planning(ctx)

    # Update cost tracker with actual mode after planning
    if ctx.job_config:
        ctx.cost_tracker = CostTracker(mode=ctx.job_config.mode.value)  # Line 143 - TOO LATE
```

**Problem:** Stage 1 costs tracked against $5 budget, but actual mode might be breaking_news ($2). Budget limits not enforced.

**Fix:**
```python
# Initialize with placeholder
ctx = PipelineContext(
    job_id=job_id,
    topic=topic,
    slack_payload=slack_payload,
    cost_tracker=CostTracker(mode="full"),
)

stage_0_initialize(ctx)
stage_1_planning(ctx)

# Recreate tracker IMMEDIATELY after planning completes
if ctx.job_config:
    old_cost = ctx.cost_tracker.total_cost
    ctx.cost_tracker = CostTracker(mode=ctx.job_config.mode.value)
    # Re-add Stage 0-1 costs to new tracker
    ctx.cost_tracker.add_cost("stage_0_1", old_cost)
```

**Test:** Test breaking_news mode with high Stage 1 cost → verify stays within $2 budget

---

### Fix 3: Quality Gate Source Type Mismatch
**File:** `backend/pipeline/stages.py:255-266`
**Current Code:**
```python
for source in ctx.web_sources:
    if isinstance(source, dict):
        source_dicts.append(source)
    elif hasattr(source, 'url'):
        source_dicts.append({
            'url': source.url,
            'title': getattr(source, 'title', ''),
            'snippet': getattr(source, 'text', ''),  # Line 262 - ERROR
            'source_type': getattr(source, 'source_type', 'web'),
        })
```

**Problem:** Assumes source has `.text` attribute, but SourceItem might not. Creates incomplete dicts.

**Fix:**
```python
source_dicts = []
for source in ctx.web_sources:
    if isinstance(source, dict):
        source_dicts.append(source)
    elif isinstance(source, SourceItem):  # Explicit type check
        source_dicts.append({
            'url': source.url,
            'title': source.title or '',
            'snippet': source.text or '',  # Safe access
            'source_type': str(source.source_type) if hasattr(source, 'source_type') else 'web',
        })
    else:  # Fallback for unknown types
        source_dicts.append({'url': str(source)})
```

**Test:** Test Quality Gate with mixed SourceItem/dict sources → verify all processed

---

### Fix 4: Cost Breakdown TypeError
**File:** `backend/pipeline/stages.py:660`
**Current Code:**
```python
try:
    ctx.evidence_records, cost_breakdown = validate_claims_v2(...)
    # ...
except Exception as e:
    ctx.add_warning(...)
    try:
        ctx.evidence_records, evidence_table_md, missing_angles_md = validate_claims(...)
        # ...
    except Exception as e2:
        logger.error(...)
        ctx.set_output(...)

logger.info(f"[{ctx.job_id}] Validated {len(ctx.evidence_records)} claims (cost: ${cost_breakdown.get('total', 0):.2f})")
```

**Problem:** If v2 validation raises exception, cost_breakdown is never defined. Line 660 crashes with NameError.

**Fix:**
```python
cost_breakdown = {}  # Initialize at top of stage

try:
    ctx.evidence_records, cost_breakdown = validate_claims_v2(...)
    ctx.add_cost("perplexity_validation", cost_breakdown.get("perplexity", 0))
    ctx.add_cost("openai_validation", cost_breakdown.get("openai", 0))

    try:
        _, evidence_table_md, missing_angles_md = validate_claims(...)
        ctx.set_output("evidence_table_md", evidence_table_md)
        ctx.set_output("missing_angles_md", missing_angles_md)
    except Exception:
        # Fallback markdown generation
        pass

except Exception as e:
    ctx.add_warning(f"Claim validation v2 failed, using v1: {str(e)}")
    try:
        ctx.evidence_records, evidence_table_md, missing_angles_md = validate_claims(...)
        ctx.set_output("evidence_table_md", evidence_table_md)
        ctx.set_output("missing_angles_md", missing_angles_md)
    except Exception as e2:
        logger.error(f"Both v2 and v1 validation failed: {e2}")

logger.info(f"[...] Validated {len(ctx.evidence_records)} claims (cost: ${cost_breakdown.get('total', 0):.2f})")
```

**Test:** Test Stage 8 with v2 validation failure → verify cost_breakdown gracefully handles

---

## PRIORITY 1: DATA LOSS RISKS

### Fix 5: Parallel Execution Thread Safety
**File:** `backend/pipeline/parallel_executor.py:50-54`
**Current Code:**
```python
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_name = {}
    for stage_func, name in zip(stages, names):
        future = executor.submit(_run_stage_safely, ctx, stage_func, name)
        future_to_name[future] = name
```

**Problem:** Shared context `ctx` modified by multiple threads simultaneously. Race conditions on `ctx.claims`, `ctx.web_sources`, etc.

**Fix Option 1: Add threading.Lock**
```python
import threading

# In worker.py, pass lock through context
ctx.mutation_lock = threading.Lock()

# In each stage that modifies context
with ctx.mutation_lock:
    ctx.claims.append(claim)  # Safe now
```

**Fix Option 2: Copy context for each thread**
```python
def _run_stage_safely(ctx, stage_func, name):
    import copy
    ctx_copy = copy.deepcopy(ctx)  # Each thread gets own copy
    try:
        stage_func(ctx_copy)
        # Merge results back
        merge_context_updates(ctx, ctx_copy)
        return None
    except Exception as e:
        ctx.add_warning(f"{name} failed: {str(e)}")
        return e
```

**Recommended:** Fix Option 1 (lightweight locking)

**Test:** Run parallel stages with high concurrency (10+ workers) → verify no data corruption

---

### Fix 6: Claim Extraction Content Validation
**File:** `backend/pipeline/stages.py:549`
**Current Code:**
```python
if ctx.transcripts or any(s.text for s in ctx.web_sources):
    ctx.claims, quote_bank_md, claims_ledger_md = extract_claims(...)
```

**Problem:** Extracts claims from single short snippet. Could generate claims from 50 char snippet.

**Fix:**
```python
# Calculate total content available
total_content_length = sum(len(t.text or '') for t in ctx.transcripts)
total_content_length += sum(len(s.text or '') for s in ctx.web_sources)

# Require minimum 500 chars of content
min_content = 500
if total_content_length < min_content:
    ctx.add_warning(f"Content too thin ({total_content_length} chars < {min_content}). Claims may be unreliable.")

if total_content_length > 0:
    ctx.claims, quote_bank_md, claims_ledger_md = extract_claims(...)
else:
    ctx.claims = []
    ctx.set_output("quote_bank_md", "# Quote Bank\n\nNo content available.")
```

**Test:** Create test with 100 char total content → verify warning added, claims empty

---

## PRIORITY 2: QUALITY ISSUES

### Fix 7: BM25 Dependency Handling
**File:** `backend/pipeline/quality_gate.py:27-31, 432`
**Current Code:**
```python
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank-bm25 not installed...")

# Line 432 - assumes numpy array
normalized_scores = scores / max_score if max_score > 0 else scores
```

**Problem:** If BM25 not installed, quality scoring degraded silently. Also assumes numpy operations work.

**Fix:**
```python
# Add type safety
def _calculate_bm25_scores(sources, query_terms):
    if not BM25_AVAILABLE or not query_terms or not sources:
        return {}

    try:
        corpus = []
        for source in sources:
            text = f"{source.title or ''} {source.snippet or ''}".lower()
            corpus.append(text.split())

        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_terms)

        # Use max() instead of numpy operations
        max_score = max(scores) if scores else 1.0

        # Normalize using Python division
        if max_score > 0:
            normalized_scores = [s / max_score for s in scores]
        else:
            normalized_scores = scores

        result = {}
        for i, source in enumerate(sources):
            result[source.canonical_url] = float(normalized_scores[i])

        logger.debug(f"BM25 scoring: {len(sources)} sources")
        return result

    except Exception as e:
        logger.warning(f"BM25 scoring failed: {e}")
        return {}

# Add warning when BM25 disabled
if not BM25_AVAILABLE:
    logger.warning("BM25 scoring not available. Install rank-bm25 for improved relevance scoring.")
```

**Test:** Test with rank_bm25 installed and not installed → verify graceful degradation

---

### Fix 8: PipelineContext Initialization
**File:** `backend/pipeline/context.py:31, 28`
**Current Code:**
```python
@dataclass
class PipelineContext:
    # ...
    cost_tracker: Optional["CostTracker"] = None
    niche_config: Optional[dict] = None
```

**Problem:** Optional fields start as None. No guarantee they're initialized before use.

**Fix:**
```python
from dataclasses import dataclass, field

@dataclass
class PipelineContext:
    job_id: str
    topic: str
    slack_payload: Optional[dict] = None

    # Configuration
    job_config: Optional[JobConfig] = None
    short_title: str = ""

    # Cost tracking - initialize empty, filled in worker.py
    cost_tracker: Optional["CostTracker"] = None

    # Niche - initialize as empty dict to prevent NoneType errors
    niche_config: dict = field(default_factory=dict)

    # ... rest of fields ...

    def __post_init__(self):
        """Validate initial state."""
        if not self.job_id:
            raise ValueError("job_id required")
        if not self.topic:
            raise ValueError("topic required")
```

**Test:** Create context without niche_config → verify it's empty dict, not None

---

## IMPLEMENTATION CHECKLIST

- [ ] Fix 1: niche_config initialization (stages.py:74-83, stages.py:156)
- [ ] Fix 2: cost_tracker mode (worker.py:133-143)
- [ ] Fix 3: quality_gate source types (stages.py:255-266)
- [ ] Fix 4: cost_breakdown error handling (stages.py:626-675)
- [ ] Fix 5: parallel execution threading (parallel_executor.py + context.py)
- [ ] Fix 6: claim extraction validation (stages.py:549)
- [ ] Fix 7: BM25 dependency safety (quality_gate.py:432)
- [ ] Fix 8: context initialization (context.py:31, 28)
- [ ] Write tests for all fixes
- [ ] Run full pipeline test with sample job
- [ ] Verify no regressions in existing tests

---

## TESTING GUIDE

After implementing fixes, run:

```bash
# Test individual fixes
pytest tests/test_cost_tracker.py -v
pytest tests/test_parallel_executor.py -v
pytest tests/test_quality_gate.py -v

# Test with actual job
python -m backend.worker run_research_job \
  --job-id "test-fix-001" \
  --topic "Test topic" \
  --enable-parallel true

# Monitor for errors
tail -f logs/research_agent.log | grep -i error
```

---

**Report Generated:** 2025-12-28 14:59
**Status:** Awaiting implementation
