# Critical Action Items - Backend Pipeline Audit

**Generated:** 2025-12-28
**Priority:** IMMEDIATE

---

## CRITICAL FIXES (Block Production)

### 1. Cost Tracker Model Matching
**File:** `backend/cost_tracker.py` Line 82
**Issue:** Substring match `"gpt-4o-mini" in model` fails for versioned models
**Current Code:**
```python
if "gpt-4o-mini" in model:
    input_cost = (input_tokens / 1000) * API_COSTS["openai_gpt4o_mini_input"]
```
**Fix:** Use explicit model comparison or regex
```python
if model.startswith("gpt-4o-mini"):
    input_cost = (input_tokens / 1000) * API_COSTS["openai_gpt4o_mini_input"]
```
**Impact:** Wrong API costs applied to OpenAI calls
**Timeline:** 1 hour

---

### 2. Quality Gate Scoring Exceeds 1.0
**File:** `backend/pipeline/quality_gate.py` Lines 270-274
**Issue:** Final score weights sum to 1.2, allowing scores > 1.0
**Current Code:**
```python
source.final_score = (
    QUALITY_GATE_CONFIG["relevance_weight"] * source.relevance_score +      # 0.6 * [0, 1]
    QUALITY_GATE_CONFIG["quality_weight"] * source.quality_score +          # 0.4 * [0, 1]
    bm25_bonus                                                               # up to 0.2
)  # Could be up to 1.2
```
**Fix:** Cap final score or adjust weights
```python
source.final_score = min(1.0, (
    QUALITY_GATE_CONFIG["relevance_weight"] * source.relevance_score +
    QUALITY_GATE_CONFIG["quality_weight"] * source.quality_score +
    bm25_bonus
))
```
**Impact:** Quality scoring algorithm broken, source ranking incorrect
**Timeline:** 30 minutes

---

### 3. Cost Tracker Loss During Pipeline
**File:** `backend/worker.py` Lines 141-143
**Issue:** Reinitializing cost_tracker loses planning stage costs
**Current Code:**
```python
ctx = PipelineContext(
    job_id=job_id,
    topic=topic,
    slack_payload=slack_payload,
    cost_tracker=CostTracker(mode="full"),  # Line 133
)
...
stage_1_planning(ctx)  # Adds cost: ctx.add_cost("openai_planning", 0.002)
...
if ctx.job_config:
    ctx.cost_tracker = CostTracker(mode=ctx.job_config.mode.value)  # LINE 143 - LOSES PRIOR COSTS!
```
**Fix:** Update mode of existing tracker
```python
if ctx.job_config and ctx.cost_tracker:
    ctx.cost_tracker.mode = ctx.job_config.mode.value
    ctx.cost_tracker.budget_limit = CostTracker(mode=ctx.job_config.mode.value).budget_limit
```
**Impact:** Final cost tracking inaccurate, budget enforcement broken
**Timeline:** 1 hour

---

### 4. GDELT Timespan Hardcoded
**File:** `backend/pipeline/stages.py` Lines 185-189
**Issue:** GDELT search uses "24h" regardless of pipeline mode
**Current Code:**
```python
gdelt_articles = search_news_gdelt(
    query=ctx.topic,
    timespan="24h",  # HARDCODED - wrong for investigation, profile, etc.
    max_records=20
)
```
**Fix:** Use mode-specific timespan
```python
# In stage_3_source_shortlist()
timespan_by_mode = {
    "breaking_news": "24h",
    "investigation": "30d",
    "profile": "90d",
    "controversy": "60d",
}
timespan = timespan_by_mode.get(ctx.job_config.mode.value, "7d")

gdelt_articles = search_news_gdelt(
    query=ctx.topic,
    timespan=timespan,
    max_records=20
)
```
**Impact:** Non-news modes get wrong date range for research
**Timeline:** 1 hour

---

### 5. Circular Import Risk
**File:** `backend/pipeline/stages.py` Line 656
**Issue:** Imports from worker module inside stages
**Current Code:**
```python
from backend.worker import _generate_evidence_table_md
```
**Fix:** Move helper to shared utility module
```
Create: backend/pipeline/formatting_utils.py
Move: _generate_evidence_table_md() to formatting_utils.py
Update imports in both files
```
**Impact:** Could cause import errors or circular dependency issues
**Timeline:** 2 hours

---

## HIGH PRIORITY FIXES (Next 48 Hours)

### 6. Performance: O(n²) Deduplication
**File:** `backend/pipeline/quality_gate.py` Line 575
**Issue:** `if source not in approved` is linear search, creates O(n²) complexity
**Fix:** Use set tracking
```python
approved_ids = set()  # Track by ID/URL instead
for source in allocated_sources:
    if source.canonical_url not in approved_ids:
        approved.append(source)
        approved_ids.add(source.canonical_url)
```
**Timeline:** 1 hour

---

### 7. BM25 Empty Corpus
**File:** `backend/pipeline/quality_gate.py` Lines 425-445
**Issue:** No check if corpus is empty before BM25Okapi
**Fix:** Add guard
```python
if not sources or all(not s.title and not s.snippet for s in sources):
    return {}  # Empty corpus, skip BM25

try:
    corpus = [...]
    bm25 = BM25Okapi(corpus)
```
**Timeline:** 30 minutes

---

### 8. Type Validation for Timeline Events
**File:** `backend/pipeline/stages.py` Line 582
**Issue:** Assumes event has model_dump() method
**Fix:** Add validation
```python
if ctx.timeline_events:
    timeline_data = []
    for event in ctx.timeline_events:
        if hasattr(event, 'model_dump'):
            timeline_data.append(event.model_dump())
        elif isinstance(event, dict):
            timeline_data.append(event)
        else:
            logger.warning(f"Timeline event missing model_dump: {type(event)}")
    update_job(ctx.job_id, partial_outputs={"timeline_events": timeline_data})
```
**Timeline:** 1 hour

---

## MEDIUM PRIORITY FIXES (This Week)

### 9. Remove Hardcoded Limits in dual_output.py
Create config for limits instead of magic numbers throughout file:
```python
OUTPUT_LIMITS = {
    "notebook_claims": 15,
    "notebook_timeline": 20,
    "notebook_quotes": 10,
    "documentary_interviews": 5,
    "documentary_visuals": 10,
}
```
**Timeline:** 3 hours

### 10. Move Regex Outside Loop
**File:** `backend/pipeline/dual_output.py` Line 263
Move `import re` to top of file, not inside loop

### 11. Add Unit Tests
Create test suite for:
- quality_gate scoring algorithm
- cost_tracker accumulation
- stage_7_extraction with empty input
- parallel_executor with failures

**Timeline:** 4-6 hours

---

## Testing Checklist

Before merging fixes:

- [ ] Cost tracking accumulates correctly from stage 0 to completion
- [ ] Quality gate scores stay in [0, 1] range
- [ ] GDELT searches use correct timespan per mode
- [ ] Parallel stage execution doesn't cause race conditions
- [ ] Empty source list doesn't crash quality gate
- [ ] Timeline events with missing model_dump() are handled
- [ ] Budget enforcement actually works
- [ ] All imports resolve without circular dependencies

---

## Estimated Fix Timeline

| Category | Time | Priority |
|----------|------|----------|
| Critical (5 items) | 4 hours | BLOCK RELEASES |
| High (4 items) | 4 hours | DO BEFORE NEXT SPRINT |
| Medium (5 items) | 8 hours | WITHIN 1 WEEK |
| Testing | 6 hours | CONCURRENT |
| **Total** | **28 hours** | - |

---

## Production Alert

**Current Status:** UNSAFE FOR PRODUCTION USE

- Cost tracking is broken (costs discarded during execution)
- Quality gate scoring exceeds bounds (algorithm incorrect)
- GDELT not using correct date ranges (results invalid for some modes)

**Recommendation:** Do NOT deploy until 5 critical issues are fixed.
