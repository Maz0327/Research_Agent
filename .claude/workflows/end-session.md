# Session End Workflow

**Execute this workflow at the end of EVERY coding session.**

---

## Steps

### Step 1: Run Checkpoint

```
Run: /checkpoint
```

This generates:
- Summary of completed work
- Files modified
- Test status
- Any blockers
- Next steps

---

### Step 2: Run Tests

```bash
pytest backend/tests/ -v
```

Verify:
- All tests pass
- No regressions introduced
- New code has test coverage

If tests fail:
- Fix before ending session if possible
- If not fixable quickly, document as blocker

---

### Step 3: Update PROGRESS.md

Update these sections:

#### Phase Status Table
Update checkboxes for completed tasks:
```markdown
- [x] **1.1** Export semantic stages from `stages/__init__.py`
- [x] **1.2** Add missing PipelineContext fields
- [ ] **1.3** Add `generate_json()` to GeminiClient  ← Next
```

#### Current Session Section
```markdown
## Current Session

**Date:** [today's date]
**Tasks Completed:**
- [x] Task 1.1: [description]
- [x] Task 1.2: [description]

**Files Modified:**
- backend/pipeline/stages/__init__.py
- backend/pipeline/context.py

**Next Session Should:**
1. Complete Task 1.3
2. Then Task 1.4
3. Run Phase 1 checkpoint
```

#### Blockers Log (if any)
```markdown
| Date | Blocker | Status | Resolution |
|------|---------|--------|------------|
| 2026-01-14 | Missing API method | Open | Need owner input |
```

---

### Step 4: Commit Changes

Commit with proper message format:

```bash
git add -A
git commit -m "Phase [X].[Y]: [description]"
```

Examples:
- `Phase 0.1: Commit untracked semantic code`
- `Phase 1.2: Add missing PipelineContext fields`
- `Phase 4: Complete validation stage`

---

### Step 5: Push to Branch

```bash
git push origin [branch-name]
```

Verify push succeeded.

---

### Step 6: Output Session Summary

Provide final summary to owner:

```markdown
## Session Complete

**Phase:** [N] — [Name]
**Tasks Completed:** [list]
**Tests:** ✅ All passing / ❌ [N] failing

**Commits Made:**
- `[commit hash]` — [message]

**Files Changed:** [count]

**Next Session Should:**
1. [task]
2. [task]

**Blockers:** None / [list]

**Session Duration:** ~[X] hours
```

---

## Quick Version

If short session or minor changes:

```
1. /checkpoint
2. pytest backend/tests/
3. Update PROGRESS.md
4. git add -A && git commit -m "Phase X.Y: [desc]"
5. git push
6. "Session complete. Next: [task]. Tests: ✅"
```

---

## If Tests Fail at End of Session

### Option A: Quick Fix (< 15 min)
1. Fix the failing test
2. Re-run tests
3. Continue with normal end-session

### Option B: Document and Leave
1. Document failing test in PROGRESS.md blockers
2. Commit working code only
3. Note: "Tests failing, needs fix next session"
4. Do NOT push broken code to main

---

## If Time Runs Out Mid-Task

1. Commit whatever is stable
2. Use commit message: `Phase X.Y: WIP - [description]`
3. Update PROGRESS.md with exact stopping point
4. Note what's incomplete
5. Do NOT leave uncommitted changes

---

## Checklist

```
[ ] Run /checkpoint
[ ] Run pytest (all pass)
[ ] Update PROGRESS.md
  [ ] Task checkboxes
  [ ] Current session section
  [ ] Blockers (if any)
[ ] Commit with proper message
[ ] Push to branch
[ ] Output session summary
[ ] Verify no uncommitted changes: git status
```

---

## Never End Session With

- Uncommitted code changes
- Failing tests (without documenting)
- PROGRESS.md not updated
- Unclear next steps
