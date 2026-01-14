# Implementation Rules

**Priority:** CRITICAL — These rules must be followed for every code change.

---

## Phase Discipline

### Rule 1: Sequential Phases Only
- Work on ONE phase at a time
- Do NOT skip phases
- Do NOT work ahead
- Complete all tasks in current phase before moving on

### Rule 2: Task Completion
- Complete tasks in order within each phase
- Mark task complete in PROGRESS.md before starting next
- Run `/checkpoint` after each task

### Rule 3: Phase Boundaries
- Phase is complete when ALL tasks done AND checkpoint criteria met
- Get explicit approval before starting new phase
- Update PROGRESS.md status when phase completes

---

## Code Quality

### Rule 4: Type Hints Required
All functions must have complete type hints:

```python
# ✅ Good
def extract_source(ctx: PipelineContext, source_id: str) -> PipelineContext:
    pass

# ❌ Bad
def extract_source(ctx, source_id):
    pass
```

### Rule 5: Docstrings Required
All public functions must have docstrings:

```python
# ✅ Good
def extract_source(ctx: PipelineContext, source_id: str) -> PipelineContext:
    """Extract semantic content from a single source.
    
    Args:
        ctx: Pipeline context with source data
        source_id: ID of source to extract
        
    Returns:
        Updated context with extraction results
        
    Raises:
        ExtractionError: If extraction fails after retry
    """
    pass

# ❌ Bad  
def extract_source(ctx: PipelineContext, source_id: str) -> PipelineContext:
    pass  # No docstring
```

### Rule 6: Error Handling
All external calls must have error handling:

```python
# ✅ Good
try:
    result = gemini_client.generate_json(prompt, schema)
except GeminiError as e:
    logger.error(f"Extraction failed for {source_id}: {e}")
    ctx.warnings.append(f"Extraction failed: {e}")
    return ctx

# ❌ Bad
result = gemini_client.generate_json(prompt, schema)  # No error handling
```

---

## Testing

### Rule 7: Test Before Implementation
When possible, write tests first:
1. Define expected behavior
2. Write test
3. Implement code
4. Verify test passes

### Rule 8: Run Tests After Changes
After ANY code change:
```bash
pytest backend/tests/ -v
```

All tests must pass before proceeding.

### Rule 9: No Untested Code
New code must have tests:
- Model validation tests
- Function unit tests
- Integration tests for pipelines

---

## Git Discipline

### Rule 10: Commit After Each Task
- One commit per completed task
- Do NOT batch multiple tasks in one commit

### Rule 11: Commit Message Format
```
Phase X.Y: [description]
```

Examples:
- `Phase 0.1: Commit untracked semantic code`
- `Phase 1.3: Add generate_json() to GeminiClient`
- `Phase 4.2: Implement quote verification`

### Rule 12: No Uncommitted Work
- Commit before ending session
- Push to branch before ending session
- Never leave work uncommitted overnight

---

## File Changes

### Rule 13: Backup Before Major Changes
Before modifying critical files:
```bash
cp file.py file.py.backup
```

### Rule 14: Archive, Don't Delete
Dead code goes to `backend/archive/`, not deleted:
```bash
mv unused_file.py backend/archive/
git add backend/archive/unused_file.py
```

### Rule 15: Document File Changes
In PROGRESS.md, list all files modified each session.

---

## Prohibited Actions

### DO NOT:
- Skip phases or tasks
- Modify architecture without approval
- Add features not in plan
- "Optimize" without asking
- Delete without archiving
- Leave tests failing
- Commit without testing
- End session without updating PROGRESS.md

---

## Checkpoint Requirements

After each task:
1. Code compiles without errors
2. Related tests pass
3. PROGRESS.md updated
4. Commit made with proper message

After each phase:
1. ALL tasks complete
2. ALL tests pass
3. Checkpoint criteria met
4. Owner approval received
