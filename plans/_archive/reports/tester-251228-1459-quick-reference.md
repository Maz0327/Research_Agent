# Pipeline Analysis - Quick Reference
**For:** Fast lookup of issues and fixes
**Date:** 2025-12-28 14:59

---

## CRITICAL ISSUES AT A GLANCE

### 🔴 CRASH RISK (Fix Now)

| Issue | File | Line | Problem | Fix |
|-------|------|------|---------|-----|
| niche_config NoneType | stages.py | 156 | `.get()` on None dict | Check `if ctx.niche_config and isinstance(...)` |
| cost_breakdown NameError | stages.py | 660 | Undefined after exception | Initialize `cost_breakdown = {}` at stage start |
| CostTracker mode wrong | worker.py | 133-143 | $5 budget used instead of actual | Recreate tracker BEFORE Stage 1, not after |
| Quality Gate type error | stages.py | 255-266 | Assumes source has `.text` | Add explicit type checking: `isinstance(source, SourceItem)` |
| Parallel race condition | parallel_executor.py | 50-54 | Shared context mutations | Add `threading.Lock()` or use `copy.deepcopy()` |

### 🟠 DATA LOSS RISK (High Priority)

| Issue | File | Line | Problem | Impact |
|-------|------|------|---------|--------|
| Claim thin content | stages.py | 549 | Extracts from 50 char snippet | Claims from insufficient evidence |
| BM25 array operations | quality_gate.py | 432 | Uses `.max()` on numpy array | TypeError if array type changes |
| GDELT import unchecked | stages.py | 179 | No try/except on import | ImportError crashes pipeline |
| Playwright import unchecked | stages.py | 461 | No try/except on import | ImportError crashes pipeline |
| Source type inconsistent | stages.py | 206 | Mixes dict and SourceItem | Type confusion in extraction |

---

## ISSUE MATRIX

| Stage | Crash | Data Loss | Quality | Tests |
|-------|-------|-----------|---------|-------|
| 0 | — | — | — | ❌ 0 |
| 1 | 🔴 | 🟠 | 🟡 | ❌ 0 |
| 2 | — | 🟡 | 🟡 | ❌ 0 |
| 3 | 🔴 | 🟠 | 🟡 | ❌ 0 |
| 3.5 | 🔴 | 🟠 | 🟠 | ✅ 10 |
| 4 | — | — | 🟡 | ❌ 0 |
| 5 | — | — | 🟡 | ❌ 0 |
| 6 | 🟠 | 🟡 | 🟡 | ❌ 0 |
| 6.5 | — | — | — | ❌ 0 |
| 7 | — | 🟠 | 🟠 | ❌ 0 |
| 8 | 🔴 | 🟠 | 🟠 | ❌ 0 |
| 8.5 | — | — | 🟡 | ❌ 0 |
| 8.6 | — | — | 🟡 | ❌ 0 |
| 9 | — | — | 🟡 | ❌ 0 |
| 10 | — | — | — | ❌ 0 |

**Legend:** 🔴 = Critical | 🟠 = High | 🟡 = Medium | — = None | ✅ = Good

---

## HOTSPOT FILES

### Most Critical (Fix First)
1. **worker.py** - CostTracker initialization timing
2. **stages.py** - 5+ critical issues across multiple stages
3. **context.py** - niche_config initialization
4. **quality_gate.py** - Type safety and BM25

### Untested (Write Tests First)
1. **extraction.py** (811 lines) - 0 tests
2. **dual_output.py** (407 lines) - 0 tests
3. **documentary_intelligence.py** (395 lines) - 0 tests
4. **angle_discovery.py** (406 lines) - 0 tests
5. **validation_v2.py** (194 lines) - 0 tests

---

## FIX COMPLEXITY CHART

```
Easy (5 min)  Medium (15 min)  Hard (30+ min)  Very Hard (1+ hr)
───────────────────────────────────────────────────────────────

cost_breakdown     BM25 handling       Thread safety     Parallel exec
init               Import wrapping     Type validation   refactor

niche_config       Content validation  v1/v2 fallback
check              Source normalization

CostTracker       Quality Gate        Claim extraction
timing             type mismatch       validation

Cost tracker       Documentary        Integration
mode               blueprint           tests
```

---

## TESTING GAPS BY MODULE

| Module | Lines | Tests | Gap | Priority |
|--------|-------|-------|-----|----------|
| extraction.py | 811 | 0 | 100% | CRITICAL |
| validation_v2.py | 194 | 0 | 100% | CRITICAL |
| dual_output.py | 407 | 0 | 100% | HIGH |
| documentary_intelligence.py | 395 | 0 | 100% | MEDIUM |
| angle_discovery.py | 406 | 0 | 100% | MEDIUM |
| timeline.py | 211 | 0 | 100% | MEDIUM |
| entities.py | 209 | 0 | 100% | MEDIUM |
| stages.py | 898 | 0 | 100% | HIGH |
| quality_gate.py | 645 | 10 | 98% | HIGH |
| document_helpers.py | 179 | 4 | 98% | MEDIUM |
| cost_tracker.py | 138 | 12 | 91% | GOOD |
| parallel_executor.py | 131 | 9 | 93% | GOOD |

**Total:** 5,874 LOC, ~21 tests = 99.6% of code untested

---

## ISSUE SEVERITY QUICK LOOKUP

### Will Crash Pipeline (Fix First)
- [ ] niche_config NoneType at stages.py:156
- [ ] cost_breakdown NameError at stages.py:660
- [ ] CostTracker wrong mode at worker.py:143
- [ ] Quality Gate type error at stages.py:259
- [ ] Parallel thread race at parallel_executor.py:50

### Will Lose Data (Fix Soon)
- [ ] Claim extraction insufficient content validation
- [ ] BM25 array operations fragile
- [ ] GDELT import not wrapped
- [ ] Playwright fallback import not wrapped
- [ ] Source type inconsistency

### Will Degrade Quality (Fix Later)
- [ ] Cost tracking inaccuracy
- [ ] Perplexity response not validated
- [ ] Timeline ordering not enforced
- [ ] spaCy model not optimized
- [ ] Import errors not wrapped

---

## IMPLEMENTATION ORDER

### Phase 1: Critical Fixes (Day 1 - 2 hours)
```
1. Fix cost_breakdown (5 min)
2. Fix CostTracker mode (5 min)
3. Fix niche_config (10 min)
4. Fix Quality Gate types (15 min)
5. Fix claim content validation (10 min)
6. Verify no regressions (20 min)
```

### Phase 2: High Priority Fixes (Day 1 - 3 hours)
```
1. Add import try/except (GDELT, Playwright) (15 min)
2. Fix BM25 operations (10 min)
3. Add thread safety (30 min)
4. Fix context initialization (10 min)
5. Test all fixes (90 min)
```

### Phase 3: Test Suite (Day 2-3 - 8 hours)
```
1. Stage 1 tests (1 hour)
2. Stage 3.5 tests (1 hour)
3. Stage 7 tests (2 hours)
4. Stage 8 tests (1 hour)
5. Integration tests (2 hours)
6. Fix failures (1 hour)
```

---

## VERIFICATION CHECKLIST

### After Implementing Fixes

- [ ] No TypeErrors in Stage 1 planning
- [ ] niche_config initialized (dict, not None)
- [ ] CostTracker respects mode budget
- [ ] Quality Gate processes all source types
- [ ] Parallel execution doesn't corrupt data
- [ ] Stage 8 handles validation v1/v2 failures
- [ ] All imports wrapped in try/except
- [ ] Cost tracking within 5% accuracy
- [ ] No new linting errors
- [ ] All existing tests still pass

### Before Production Deployment

- [ ] 80+ unit tests written
- [ ] Integration tests pass
- [ ] Performance test with 100+ page docs
- [ ] Load test with 10 concurrent jobs
- [ ] All critical issues fixed
- [ ] All high issues fixed
- [ ] Code review approved
- [ ] Security audit passed
- [ ] Documentation updated
- [ ] Rollback plan documented

---

## CODE PATTERNS TO WATCH

### ❌ Anti-Pattern: Unchecked None
```python
# BAD - crashes if config_json is None
user_email = job.config_json.get("user_email")

# GOOD - safe access
user_email = job.config_json.get("user_email") if job.config_json else None
```

### ❌ Anti-Pattern: Type Confusion
```python
# BAD - source could be dict or SourceItem
for source in ctx.web_sources:
    title = source.get("title", "")  # Works if dict, fails if object

# GOOD - explicit type checking
for source in ctx.web_sources:
    if isinstance(source, dict):
        title = source.get("title", "")
    elif isinstance(source, SourceItem):
        title = source.title or ""
```

### ❌ Anti-Pattern: Silent Failures
```python
# BAD - error logged but doesn't affect flow
try:
    load_niche_config()
except Exception as e:
    logger.warning(f"Failed: {e}")  # ctx.niche_config is still None

# GOOD - validate recovery
try:
    ctx.niche_config = load_niche_config()
except Exception as e:
    ctx.niche_config = {}  # Explicitly set fallback
    logger.warning(f"Failed: {e}, using empty config")
```

### ✅ Good Pattern: Validation
```python
# GOOD - explicit validation
if isinstance(source, dict):
    required_keys = {"url", "title"}
    if not all(k in source for k in required_keys):
        logger.warning(f"Source missing required keys: {source}")
        continue
```

---

## REFERENCE LINKS

**Full Reports:**
- Comprehensive Analysis: `plans/reports/tester-251228-1459-pipeline-comprehensive-analysis.md` (2000+ lines)
- Critical Fixes: `plans/reports/tester-251228-1459-critical-fixes-required.md` (300+ lines)
- Executive Summary: `plans/reports/tester-251228-1459-executive-summary.md` (400+ lines)

**Code Files:**
- Pipeline stages: `backend/pipeline/stages.py` (898 lines)
- Context: `backend/pipeline/context.py` (97 lines)
- Worker: `backend/worker.py` (first 150 lines reviewed)
- Quality Gate: `backend/pipeline/quality_gate.py` (645 lines)
- Cost Tracker: `backend/pipeline/cost_tracker.py` (138 lines)
- Parallel Executor: `backend/pipeline/parallel_executor.py` (131 lines)

**Related Docs:**
- CLAUDE.md: Project instructions and API stack
- docs/architecture.md: System design
- docs/code-standards.md: Code guidelines

---

## QUICK DEBUG COMMANDS

```bash
# Check for NoneType errors in Stage 1
grep -n "niche_config" backend/pipeline/stages.py | grep -v "= None"

# List all stages
grep -n "^def stage_" backend/pipeline/stages.py

# Find unchecked imports
grep -n "^from\|^import" backend/pipeline/stages.py | grep -v "try"

# Check for undefined variables
python -m pyflakes backend/pipeline/stages.py

# Run specific test
pytest tests/test_quality_gate.py::test_deduplicate -v

# Check test coverage
pytest --cov=backend.pipeline tests/
```

---

## ESCALATION PATH

**If blocking issue found:**
1. Check this quick reference
2. Read detailed analysis in critical fixes doc
3. Check code comment at line number
4. Implement fix from provided example
5. Run tests: `pytest tests/test_*.py -v`
6. If still broken → escalate with line number + error message

---

**Last Updated:** 2025-12-28 14:59
**Status:** Ready for implementation
