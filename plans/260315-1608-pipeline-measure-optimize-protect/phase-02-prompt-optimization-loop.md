# Phase 2: Prompt Optimization Loop (Dev Tool)

## Context Links

- [Plan Overview](plan.md)
- [Phase 1: Quality Score](phase-01-composite-quality-score.md) (prerequisite -- score is the metric)
- [Phase 3: Circuit Breakers](phase-03-circuit-breaker-expansion.md) (independent)

## Overview

Offline CLI script implementing Karpathy's autoresearch loop: **modify prompt -> run pipeline -> measure quality score -> keep/revert -> log -> repeat**. This is a developer tool, NOT production code. It lives in `scripts/` and is never imported by the backend.

Scope: extraction prompts only (the highest-leverage prompts in the pipeline).

## Key Insights

- Phase 1's `composite_score` is the objective function; no new metric invention needed
- Extraction prompts live in `backend/pipeline/prompts/semantic_extraction_prompt.py` with mode-specific templates in `backend/pipeline/prompts/modes/`
- Git commit before each experiment gives clean revert path (`git stash` or `git checkout -- file`)
- TSV log format is grep-friendly and version-controllable
- The script does NOT auto-modify prompts -- it runs the pipeline with the current prompt state and logs the result; the developer modifies prompts manually between runs
- ThreadPoolExecutor in semantic_extraction.py means parallel source processing is already handled

## Requirements

1. `scripts/prompt_optimizer.py` -- standalone CLI script
2. Reads quality score from Phase 1 after pipeline execution
3. Logs to `scripts/prompt_experiments.tsv` (append-only)
4. TSV columns: `timestamp`, `variant_name`, `composite_score`, `validation_rate`, `diversity_score`, `provenance_completeness`, `ceiling_compliance`, `cost`, `test_pass_rate`, `notes`
5. Supports `--variant` flag to name the experiment
6. Supports `--job-id` to measure an existing completed job
7. Supports `--run-tests` to run pytest and capture pass rate
8. Git-aware: warns if working tree is dirty, optionally commits before run

## Architecture

```
Developer workflow:
1. Edit prompt in backend/pipeline/prompts/
2. Run: python scripts/prompt_optimizer.py --variant "v3-add-layer-hint" --job-id <id>
3. Script fetches job record, reads quality_score
4. Logs result to TSV
5. Developer compares variants in TSV
6. If worse: git checkout -- backend/pipeline/prompts/
```

### Script Flow

```
prompt_optimizer.py
  |
  +-- parse_args()
  |     --variant: str (required)
  |     --job-id: str (measure existing job)
  |     --run-tests: bool (run pytest, capture pass rate)
  |     --notes: str (freeform notes)
  |
  +-- check_git_status()  # Warn if dirty
  |
  +-- fetch_quality_score(job_id)
  |     Read from job record via backend.state.get_job()
  |     Extract quality_score dict
  |
  +-- [optional] run_tests()
  |     subprocess.run(["pytest", "backend/tests/", "-v", "--tb=short"])
  |     Parse exit code + summary line for pass rate
  |
  +-- append_to_tsv(row)
  |     Append to scripts/prompt_experiments.tsv
  |     Create header row if file doesn't exist
  |
  +-- print_summary()
```

### TSV Format

```
timestamp	variant_name	composite_score	validation_rate	diversity_score	provenance_completeness	ceiling_compliance	cost	test_pass_rate	notes
2026-03-15T16:30:00	baseline	0.82	0.90	0.65	0.95	1.00	0.045	1.00	initial baseline
2026-03-15T17:00:00	v2-add-layer-hint	0.85	0.92	0.65	0.97	1.00	0.048	1.00	added explicit layer instruction
```

## Related Code Files

| File | Role |
|------|------|
| `scripts/prompt_optimizer.py` | NEW: CLI script |
| `scripts/prompt_experiments.tsv` | NEW: experiment log (generated) |
| `backend/pipeline/quality_score.py` | Phase 1: source of quality score |
| `backend/state.py` | `get_job()` to fetch job record |
| `backend/pipeline/prompts/semantic_extraction_prompt.py` | Prompt being optimized (read-only by script) |
| `backend/pipeline/prompts/modes/*.py` | Mode templates (read-only by script) |

## Implementation Steps

### 2.1: Create `scripts/prompt_optimizer.py` skeleton

- argparse with `--variant`, `--job-id`, `--run-tests`, `--notes`
- Import `backend.state.get_job` for reading job records
- Git status check via `subprocess.run(["git", "status", "--porcelain"])`
- Type hints, docstring, `if __name__ == "__main__"` guard

### 2.2: Implement `fetch_quality_score()`

- Call `get_job(job_id)` to get JobRecord
- Extract `quality_score` dict from record
- Validate score exists (error if Phase 1 hasn't run on this job)
- Return structured dict with all component signals

### 2.3: Implement `run_tests()` (optional flag)

- `subprocess.run(["pytest", "backend/tests/", "-v", "--tb=short"], capture_output=True)`
- Parse stdout for pass/fail counts
- Return `pass_rate: float` (passed / total)
- Handle pytest not installed or test errors gracefully

### 2.4: Implement TSV logging

- Define `TSV_PATH = Path("scripts/prompt_experiments.tsv")`
- Create header if file doesn't exist
- Append row with tab-separated values
- Use `datetime.utcnow().isoformat()` for timestamp

### 2.5: Write tests for the script

- Unit test for TSV row formatting
- Unit test for quality score extraction from mock job record
- Test that `--help` works (subprocess call)
- No integration test needed (dev tool, not production)

### 2.6: Verify existing tests pass

- `pytest backend/tests/ -v`

## Todo List

- [ ] 2.1: Create script skeleton with argparse
- [ ] 2.2: Implement quality score fetching from job record
- [ ] 2.3: Implement optional test runner
- [ ] 2.4: Implement TSV append logging
- [ ] 2.5: Write unit tests
- [ ] 2.6: Run full test suite

## Success Criteria

- Script runs with `--variant baseline --job-id <completed_job>` and appends row to TSV
- TSV is human-readable and diff-friendly
- `--run-tests` captures pytest pass rate
- Script warns on dirty git tree
- No backend code modified (script is standalone)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Job record has no quality_score (Phase 1 not run) | Script errors | Clear error message: "Run pipeline with Phase 1 first" |
| `get_job()` requires DB connection | Script fails offline | Document: requires running backend or DB access |
| TSV file locked by editor | Write fails | Use append mode with brief lock; not critical |
| Developer forgets to commit before modifying prompt | Can't revert | Git dirty check + warning at script start |

## Security Considerations

- Script reads job records (read-only); no writes to DB
- TSV contains quality metrics, not secrets
- No API calls; no cost implications
- Script never modifies prompts itself

## Next Steps

After Phase 2:
- Build a simple comparison view (sort TSV by composite_score)
- Future: auto-generate prompt variants via LLM (Phase 2b, out of scope)
- Future: CI integration to run optimizer on PR branches
