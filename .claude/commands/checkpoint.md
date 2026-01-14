# /checkpoint

Generate a checkpoint report for current progress.

---

## Usage

```
/checkpoint
```

---

## What This Command Does

1. Summarizes work completed in current session
2. Lists files modified
3. Reports test status
4. Identifies any blockers
5. States what should happen next

---

## Output Format

Generate this exact format:

```markdown
## Checkpoint Report

**Timestamp:** [current datetime]
**Phase:** [current phase number and name]
**Task:** [current task ID and description]

---

### Completed This Session

- [x] [Task/item completed]
- [x] [Task/item completed]
- [ ] [Task/item in progress] ← CURRENT

---

### Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| path/to/file.py | Modified | [what changed] |
| path/to/new.py | Created | [what it does] |
| path/to/old.py | Archived | [why] |

---

### Tests

**Status:** ✅ All passing / ❌ [N] failing

```
[paste test output summary if relevant]
```

---

### Blockers

**None** 

OR

- **Blocker:** [description]
  - **Impact:** [what it blocks]
  - **Needs:** [what's needed to resolve]

---

### Next Steps

1. [Next immediate task]
2. [Following task]
3. [etc.]

---

### Notes

[Any additional context, decisions made, questions that arose]
```

---

## When to Run

- After completing each task
- Before ending a session
- When switching context
- When encountering a blocker

---

## After Running

1. Review the output
2. Update PROGRESS.md with completed items
3. Commit changes if checkpoint looks good
4. Proceed to next task or end session
