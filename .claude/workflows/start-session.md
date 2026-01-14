# Session Start Workflow

**Execute this workflow at the beginning of EVERY coding session.**

---

## Steps

### Step 1: Read Progress File

```
Read: PROGRESS.md
```

Understand:
- Current phase
- Current task
- What was completed last session
- Any blockers noted

---

### Step 2: Check Phase Status

```
Run: /phase-status
```

Verify:
- Phase number matches PROGRESS.md
- Task matches PROGRESS.md
- No discrepancies

---

### Step 3: Review Last Session

Look at "Current Session" section of PROGRESS.md:
- What tasks were completed?
- What files were modified?
- Any notes or blockers?

---

### Step 4: Identify Today's Work

Based on current phase and task:
1. What specifically needs to be done?
2. What files will be touched?
3. What tests need to run?
4. Any dependencies or prerequisites?

---

### Step 5: Check for Blockers

Review blockers log in PROGRESS.md:
- Any unresolved blockers?
- Any new blockers discovered?
- Need owner input on anything?

---

### Step 6: State Session Plan

Output to owner:

```markdown
## Session Plan

**Current Phase:** [N] — [Name]
**Current Task:** [N.N] — [Description]

**Today I will:**
1. [Specific action]
2. [Specific action]
3. [Specific action]

**Files I expect to modify:**
- [path/to/file.py]
- [path/to/other.py]

**Tests I will run:**
- [test command]

**Questions/Blockers:**
- [Any questions or blockers, or "None"]

**Ready to proceed?**
```

---

### Step 7: Wait for Approval

**DO NOT START CODING** until owner confirms:
- "Approved" or
- "Yes, proceed" or
- Similar confirmation

If owner has corrections or different priorities, adjust plan accordingly.

---

## Quick Version

If resuming immediately after previous session (same day, no context loss):

```
1. /phase-status
2. "Resuming [task N.N]. Continuing from [last stopping point]. Proceed?"
3. Wait for approval
4. Continue work
```

---

## If Session Starts with Confusion

If unclear about state:

```
1. Read PROGRESS.md completely
2. Read last 10 commits: git log --oneline -10
3. /phase-status
4. Ask owner: "I see [X]. Is this correct? Should I proceed with [Y]?"
```

Never guess. Always verify.

---

## Checklist

```
[ ] Read PROGRESS.md
[ ] Run /phase-status
[ ] Identify current task
[ ] Check for blockers
[ ] State session plan
[ ] Get owner approval
[ ] Begin work
```
