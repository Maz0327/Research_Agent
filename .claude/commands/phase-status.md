# /phase-status

Show current implementation phase status.

---

## Usage

```
/phase-status
```

---

## What This Command Does

1. Reads PROGRESS.md
2. Displays current phase and task
3. Shows completion percentage
4. Lists any blockers

---

## Output Format

```
═══════════════════════════════════════════════════════════
                    PHASE STATUS
═══════════════════════════════════════════════════════════

Current Phase:  [N] — [Phase Name]
Phase Status:   [⏳ Pending / 🔄 In Progress / ✅ Complete]
Tasks:          [completed]/[total] ([percentage]%)

Current Task:   [N.N] — [Task Description]
Task Status:    [Not Started / In Progress / Blocked]

═══════════════════════════════════════════════════════════

Progress Overview:

Phase 0:   [✅/🔄/⏳] Commit & Stabilize
Phase 0.5: [✅/🔄/⏳] Review Existing Code
Phase 1:   [✅/🔄/⏳] Fix Blocking Issues
Phase 2:   [✅/🔄/⏳] Wire Semantic Pipeline
Phase 3:   [✅/🔄/⏳] Add Analysis Modes
Phase 4:   [✅/🔄/⏳] Add Validation
Phase 5:   [✅/🔄/⏳] Multi-Source Support
Phase 6:   [✅/🔄/⏳] Evolving Jobs
Phase 7:   [✅/🔄/⏳] Booster Pipeline
Phase 8:   [✅/🔄/⏳] Producer Packet
Phase 9:   [✅/🔄/⏳] Tests
Phase 10:  [✅/🔄/⏳] Documentation

═══════════════════════════════════════════════════════════

Blockers: [None / List blockers]

Next Action: [What to do next]

═══════════════════════════════════════════════════════════
```

---

## When to Use

- Start of every session
- When resuming after interruption
- When unsure what to work on
- Before asking owner for guidance

---

## After Running

1. Confirm current task is correct
2. Check for blockers
3. Proceed with current task or address blocker
