# QA Action Plan - Research Agent Backend

**Generated:** 2025-12-28 14:45
**Status:** READY FOR IMPLEMENTATION
**Estimated Timeline:** 2-3 weeks

---

## Quick Reference

### Critical (Do First - Risk of Data Loss)
- [ ] Add thread safety to PipelineContext (30 min)
- [ ] Add checkpoints between stages (2 hours)
- [ ] Wrap parallel execution in try-except (20 min)
- [ ] Create test_worker.py with orchestration tests (3 hours)

### Major (Do Next - Risk of Silent Failures)
- [ ] Add defensive checks to all 11 stages (4 days)
- [ ] Create missing test files (5 files) (4 days)
- [ ] Add integration test suite (2 days)
- [ ] Fix Redis/Celery error handling (1 day)

### Minor (Polish & Documentation)
- [ ] Add inline comments to complex functions (1 day)
- [ ] Update error messages to be user-facing (1 day)
- [ ] Performance profiling for parallel execution (1 day)

---

## WEEK 1: Critical Fixes

### Day 1: Thread Safety & Exception Handling

#### Task 1.1: Add Thread Safety to PipelineContext
**File:** `backend/pipeline/context.py`
**Time:** 30 minutes
**Verification:** Run test_parallel_executor.py

```python
# Changes needed:
from threading import Lock

@dataclass
class PipelineContext:
    # ... existing fields ...
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def add_warning(self, warning: str) -> None:
        with self._lock:
            self.warnings.append(warning)

    def set_output(self, key: str, value: str) -> None:
        with self._lock:
            self.outputs[key] = value

    def get_output(self, key: str, default: str = "") -> str:
        with self._lock:
            return self.outputs.get(key, default)
```

**Definition of Done:**
- Thread safety test passes
- Parallel executor tests still pass
- No race condition warnings in logs

---

#### Task 1.2: Wrap Parallel Execution in Try-Except
**File:** `backend/worker.py`
**Time:** 20 minutes
**Changes at:** Lines 150-157, 163-170

```python
# Current (lines 150-157):
if enable_parallel:
    logger.info(f"[{job_id}] Running collection stages in parallel")
    run_collection_stages_parallel(ctx)  # ← Add try-except
else:
    # sequential stages

# Fixed:
if enable_parallel:
    logger.info(f"[{job_id}] Running collection stages in parallel")
    try:
        run_collection_stages_parallel(ctx)
    except Exception as e:
        logger.error(f"[{job_id}] Parallel collection failed: {e}", exc_info=True)
        ctx.add_warning(f"Parallel collection failed, using sequential: {str(e)}")
        # Fallback to sequential
        stage_4_youtube_enumeration(ctx)
        stage_5_transcripts(ctx)
        stage_6_web_capture(ctx)
        stage_6_5_reddit(ctx)
```

**Definition of Done:**
- Parallel failures are caught
- Job falls back to sequential (or fails gracefully)
- Unit test verifies fallback logic

---

### Day 2: Job State Checkpoints

#### Task 2.1: Add Checkpoints After Each Stage
**File:** `backend/worker.py`
**Time:** 2 hours
**Pattern:** After each major stage, add:

```python
update_job(
    ctx.job_id,
    stage="stage_name_complete",
    progress_percent=XX,
    partial_outputs={"key": serialized_value}
)
```

**Stages needing checkpoints:**
1. After stage_1_planning (line ~140)
2. After stage_2_research_mapping (line ~145)
3. After stage_3_source_shortlist (line ~146)
4. After stage_3_5_quality_gate (line ~147)
5. After collection stages (line ~157)
6. After stage_7_extraction (line ~160)
7. After extraction stages (line ~169)

**Definition of Done:**
- Job state is recoverable if worker crashes
- Progress tracking is accurate
- Integration test verifies checkpoints

---

### Day 3: Create test_worker.py

#### Task 3.1: Create Worker Orchestration Tests
**File:** `tests/test_worker.py` (NEW)
**Time:** 3 hours

**Test cases needed:**
1. `test_run_research_job_basic` - Happy path
2. `test_parallel_execution_failure` - Handles parallel crash
3. `test_sequential_fallback` - Falls back when parallel fails
4. `test_error_logging_complete` - Error context captured
5. `test_job_checkpoints_created` - Checkpoints saved

**Template:**
```python
def test_run_research_job_basic():
    """Test basic research job execution."""
    # Mock all stage functions
    with patch('backend.worker.stage_0_initialize'), \
         patch('backend.worker.stage_1_planning'), \
         # ... mock all stages ...
         patch('backend.state.update_job') as mock_update:

        result = run_research_job("test_job", "test topic")

        # Verify result structure
        assert result["job_id"] == "test_job"
        assert result["status"] == "completed"

        # Verify checkpoints
        update_calls = [call[1] for call in mock_update.call_args_list]
        stages = [call.get('stage') for call in update_calls if 'stage' in call]
        assert "planning" in stages
        assert "quality_gate" in stages
```

**Definition of Done:**
- All test cases pass
- 80%+ code coverage of worker.py
- Parallel/sequential logic verified

---

## WEEK 2: Major Fixes

### Day 4-5: Defensive Checks in All Stages

#### Task 4.1: Add Defensive Checks - Stages 0-3
**Files:** `backend/pipeline/stages.py` (lines 31-235)
**Time:** 4 hours (1 hour per stage)

**For each stage, add:**
1. Input validation
2. Return type validation
3. Exception handling with fallback
4. Logging of issues

**Example pattern:**
```python
def stage_X_name(ctx: PipelineContext) -> None:
    logger.info(f"[{ctx.job_id}] Stage X: ...")
    update_job(ctx.job_id, stage="stage_x", progress_percent=XX)

    # Input validation
    if not ctx.prerequisite_data:
        logger.info(f"No input data for stage X")
        ctx.set_output("doc_key", "# Doc\n\nNo input data.")
        return

    try:
        # Process
        result = process_function(ctx.prerequisite_data)

        # Output validation
        if not result:
            logger.info(f"Stage X returned empty result")
            ctx.set_output("doc_key", "# Doc\n\nNo results.")
            return

        # Store result with type checking
        if not isinstance(result, expected_type):
            raise TypeError(f"Expected {expected_type}, got {type(result)}")

        ctx.data = result

    except Exception as e:
        logger.exception(f"Stage X failed: {e}")
        ctx.add_warning(f"Stage X failed: {str(e)}")
        ctx.set_output("doc_key", f"# Doc\n\n*Error: {str(e)}*")
        ctx.data = []  # Reset to empty
```

**Stages to fix:**
- Stage 1: Planning (lines 46-109)
- Stage 2: Research Mapping (lines 115-134)
- Stage 3: Source Shortlist (lines 140-235)
- Stage 3.5: Quality Gate (lines 241-329)

**Definition of Done:**
- All 4 stages have defensive code
- No unhandled exceptions propagate
- Logging is informative
- Unit tests added for error paths

---

#### Task 4.2: Add Defensive Checks - Stages 4-10
**Files:** `backend/pipeline/stages.py` (lines 335-898)
**Time:** 8 hours (6 stages)

**Stages to fix:**
- Stage 4: YouTube Enumeration (lines 335-355)
- Stage 5: Transcripts (lines 361-403)
- Stage 6: Web Capture (lines 409-490)
- Stage 6.5: Reddit (lines 496-534)
- Stage 7: Extraction (lines 540-565)
- Stage 7.5: Timeline (lines 571-592)
- Stage 7.6: Entities (lines 598-620)
- Stage 8: Validation (lines 626-675)

**Key fixes:**
1. **Stage 4:** Check youtube attribute exists
2. **Stage 5:** Validate video.duration_seconds
3. **Stage 6:** Normalize source types before quality gate
4. **Stage 6.5:** Add return statement after ImportError
5. **Stage 7:** Check memory pressure and stop if critical
6. **Stage 7.5/7.6:** Differentiate empty vs error results
7. **Stage 8:** Handle both v2 and v1 failure paths
8. **Stage 9:** Build doc_contents safely with try-except per doc

**Definition of Done:**
- All 8 stages have defensive code
- Error scenarios tested
- No lost data on API failures

---

### Day 6: Missing Test Files

#### Task 5.1: Create Priority Test Files
**Time:** 4 days (1 per file)

**File 1: tests/test_gdelt_client.py** (1 day)
```python
# Tests needed:
- test_gdelt_integration_breaking_news()
- test_gdelt_handles_malformed_articles()
- test_gdelt_failure_doesnt_crash_job()
- test_gdelt_url_validation()
- test_gdelt_duplicate_articles()
```

**File 2: tests/test_reddit_client.py** (1 day)
```python
# Tests needed:
- test_reddit_integration()
- test_reddit_import_error()
- test_reddit_no_posts_found()
- test_reddit_api_timeout()
```

**File 3: tests/test_stages.py** (2 days)
```python
# Tests needed per stage:
- Stage 1: planning_fallback, niche_loading
- Stage 2: research_map_validation
- Stage 3: source_type_consistency
- Stage 4: youtube_missing_attributes
- Stage 5: budget_enforcement
- Stage 6: web_capture_fallback
- Stage 7: memory_pressure_handling
- Stage 8: dual_validation_failure
- Stage 9: doc_generation_safety
```

**Definition of Done:**
- All 3 files created
- Coverage: 85%+ for each file
- All tests pass with mocked APIs

---

## WEEK 3: Integration & Polish

### Day 8: Integration Tests

#### Task 6.1: Full Pipeline Integration Test
**File:** `tests/test_integration.py` (NEW)
**Time:** 2 days

**Test scenarios:**
1. Happy path: Complete pipeline with mocked APIs
2. Partial failure: One stage fails, others continue
3. Critical stage failure: Planning fails, job fails
4. Out-of-memory: Extraction stops at memory limit
5. Budget limit: Expensive operations stopped
6. Parallel execution: Concurrent stages work correctly

**Template:**
```python
def test_full_pipeline_happy_path():
    """Test complete pipeline execution."""
    with patch('backend.worker.stage_1_planning') as mock_plan, \
         patch('backend.worker.stage_2_research_mapping') as mock_map, \
         # ... mock all 10 stages ...
         patch('backend.state.update_job') as mock_update:

        # Setup stage functions to populate context
        def plan_impl(ctx):
            ctx.job_config = JobConfig(topic="test", mode=ResearchMode.FULL)

        mock_plan.side_effect = plan_impl

        result = run_research_job("test", "test topic")

        assert result["status"] == "completed"
        assert mock_update.call_count >= 10  # At least one update per stage
```

**Definition of Done:**
- 5+ integration tests pass
- Error scenarios handled gracefully
- Performance metrics collected

---

### Day 9: Error Scenarios

#### Task 6.2: Create Error Scenario Tests
**Time:** 1 day

**Error tests needed:**
1. API timeout (Perplexity, OpenAI, YouTube)
2. Network error (web capture)
3. Invalid credentials (Slack, Google Drive)
4. Out of memory (extraction)
5. Rate limiting (all APIs)
6. Invalid response format (all APIs)

**Template:**
```python
def test_perplexity_timeout():
    """Test job continues if Perplexity times out."""
    with patch('backend.integrations.perplexity_client.research_map') as mock_search:
        mock_search.side_effect = TimeoutError("API timeout")

        stage_2_research_mapping(ctx)

        assert len(ctx.warnings) > 0
        assert ctx.outputs.get("research_map_md")  # Has fallback content
```

**Definition of Done:**
- 10+ error scenario tests
- All errors are logged and captured
- Job gracefully degrades on failure

---

## Implementation Checklist

### Critical (Week 1) - 1 Week
- [ ] Thread safety (30 min)
- [ ] Parallel exception handling (20 min)
- [ ] Job checkpoints (2 hours)
- [ ] test_worker.py (3 hours)
- [ ] Subtotal: **6 hours (1 day)**

### Major (Week 2) - 2 Weeks
- [ ] Stage 0-3 defensive checks (4 hours)
- [ ] Stage 4-10 defensive checks (8 hours)
- [ ] test_gdelt_client.py (1 day)
- [ ] test_reddit_client.py (1 day)
- [ ] test_stages.py (2 days)
- [ ] Subtotal: **7 days**

### Polish (Week 3) - 1 Week
- [ ] Integration tests (2 days)
- [ ] Error scenario tests (1 day)
- [ ] Code review & fixes (2 days)
- [ ] Subtotal: **5 days**

**Total: 12-15 days with 1 engineer**

---

## Review & Approval Gates

### Gate 1: After Task 1-3 (End of Week 1)
**Criteria:**
- test_worker.py passes 100%
- Parallel execution handles failures
- Job checkpoints verified
- **Approval:** All critical tests pass

### Gate 2: After Task 4-5 (End of Week 2)
**Criteria:**
- 80%+ code coverage in stages.py
- All defensive checks implemented
- test_gdelt_client.py, test_reddit_client.py pass
- test_stages.py passes with 85%+ coverage
- **Approval:** All major tests pass

### Gate 3: After Task 6 (End of Week 3)
**Criteria:**
- Integration tests pass
- Error scenarios tested
- Performance benchmarks acceptable
- Code review approved
- **Approval:** Ready for production

---

## Risk Mitigation

### If Timeline Slips

**Reduce scope to:**
1. Thread safety (MUST FIX)
2. Parallel exception handling (MUST FIX)
3. Job checkpoints (MUST FIX)
4. test_worker.py (MUST TEST)

**Defer to next sprint:**
- Stages 4-10 defensive checks (do incrementally)
- Missing test files (backlog)
- Integration tests (backlog)

### If Issues Found During Testing

**Escalation path:**
1. Create GitHub issue with test reproduction
2. Update test plan
3. Add test to prevent regression
4. Re-run full test suite before merge

---

## Deployment Strategy

### Phase 1: Internal Testing
1. Run full test suite in CI/CD
2. Run on staging backend with test data
3. Monitor logs for errors

### Phase 2: Canary Deployment
1. Deploy to 10% of traffic
2. Monitor error rate, latency
3. Alert on critical errors

### Phase 3: Full Rollout
1. Deploy to 100% of traffic
2. Keep monitoring for 1 week
3. Document any issues

---

## Success Metrics

**Test Coverage:** 85%+ of pipeline code
**Error Handling:** All API failures handled gracefully
**Job State:** No job data lost on worker crash
**Performance:** Parallel execution faster than sequential
**Reliability:** <0.1% test failure rate

---

## Contact & Escalation

**Pipeline Maintainer:** [TBD]
**QA Lead:** [TBD]
**On-call Escalation:** [TBD]

For issues: Create GitHub issue with `qa/` label

---

## Appendix A: File Ownership

### Files to Modify

| File | LOC | Changes | Complexity |
|------|-----|---------|-----------|
| context.py | 98 | Add lock | Low |
| worker.py | 370 | Add checkpoints, error handling | Medium |
| stages.py | 900 | Add defensive checks to 11 stages | High |
| parallel_executor.py | 132 | Result checking | Medium |

### Files to Create

| File | LOC | Type | Effort |
|------|-----|------|--------|
| test_worker.py | 200 | Unit tests | 3 hours |
| test_gdelt_client.py | 150 | Unit tests | 1 day |
| test_reddit_client.py | 150 | Unit tests | 1 day |
| test_stages.py | 300 | Unit tests | 2 days |
| test_integration.py | 200 | Integration | 2 days |

---

## Appendix B: Code Review Checklist

### Before Merge
- [ ] All tests pass
- [ ] Code coverage >85%
- [ ] No new warnings in linting
- [ ] Error messages are user-facing (not stack traces)
- [ ] Logging is appropriate (not spam)
- [ ] No hardcoded values (use config)
- [ ] Thread safety verified (if concurrent)
- [ ] Documentation updated

### Performance Check
- [ ] No N+1 queries
- [ ] Memory usage acceptable
- [ ] Parallel execution faster than sequential
- [ ] No busy-wait loops

### Security Check
- [ ] No credentials in logs
- [ ] Input validation for all APIs
- [ ] Rate limiting respected
- [ ] Error messages don't leak info

---

**Report Status:** READY FOR IMPLEMENTATION
**Last Updated:** 2025-12-28 14:45
**Next Review:** After Week 1 completion
