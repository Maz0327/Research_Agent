# Research Agent — Implementation Initialization

**For: Claude Code**
**Date: 2026-01-13**

---

## FIRST: Read These Documents IN ORDER

Before doing ANY work, read these documents:

### 1. PROGRESS.md
**Location:** Project root
**Contains:** Current phase, current task, what's done, what's next
**Read this FIRST every session**

### 2. CLAUDE.md
**Location:** Project root
**Contains:** Rules, architecture, session workflows

### 3. DECISIONS.md
**Location:** Project root
**Contains:** 12 architectural decisions (these are FINAL)

### 4. IMPLEMENTATION_PLAN.md
**Location:** Project root
**Contains:** Full phase details, code examples, checkpoint criteria

### 5. SPEC_MANIFEST.md
**Location:** Project root
**Contains:** Maps spec documents to implementation phases

### 6. docs/authoritative/INDEX.md
**Location:** docs/authoritative/
**Contains:** Repo constitution — NON-NEGOTIABLE rules

### 7. docs/authoritative/spec/RASS.md
**Location:** docs/authoritative/spec/
**Contains:** Full system specification

---

## SECOND: Read ClaudeKit Rules

### .claude/rules/implementation.md
Contains: Phase discipline, code quality, testing, git rules

### .claude/rules/architecture.md
Contains: Pipeline rules, confidence rules, prompt requirements

---

## THIRD: Know the Commands

### /checkpoint
Run after completing each task. Generates progress report.

### /review-file [path]
Run when reviewing existing code. Compares against spec.

### /phase-status
Run at start of session. Shows current phase/task.

---

## FOURTH: Know the Workflows

### Session Start (EVERY session)
1. Read PROGRESS.md
2. Run /phase-status
3. State session plan
4. Get approval before coding

### Session End (EVERY session)
1. Run /checkpoint
2. Run tests
3. Update PROGRESS.md
4. Commit with message: "Phase X.Y: [description]"
5. Push
6. Output session summary

---

## NOW: Execute Session Start Workflow

Follow the workflow:

1. **Read PROGRESS.md** — You should have done this
2. **Run /phase-status** — Show current state
3. **Identify current task** — What's the next unchecked item?
4. **Check for blockers** — Any issues noted?
5. **State what you will do this session** — Be specific
6. **Wait for approval** — DO NOT START until owner approves

---

## Critical Rules (Memorize These)

### Source Isolation
Each source extracted in SEPARATE LLM call. Sources NEVER see each other during extraction.

### Confidence Ceilings
- transcript_grounded: HIGH
- caption_grounded: MEDIUM
- video_only: LOW (NO quotes)
- text_provided: MEDIUM (NO quotes)
- ocr_extracted: MEDIUM (NO quotes)
- article_fetched: HIGH

### Prompt Requirements (ALL 5 required)
1. Source Identity Lock Block
2. Confidence Ceiling Declaration
3. Empty Output Permission
4. Layered Extraction Instructions
5. Output Schema

### Document Model
- Doc 0: Source Ledger
- Doc 1: Jump-Start
- Doc 2: Semantic Brief
- Doc 3: Producer Packet (optional, gated)

---

## Current State (as of 2026-01-13)

- **Phase 0** is ready to start
- No code has been modified yet
- Setup documents need to be deployed to project
- INDEX.md and RASS.md have been updated with new rules
- Existing semantic code needs review in Phase 0.5

**Start with Phase 0, Task 0.1: Commit untracked semantic code**

---

## Questions?

If anything is unclear:
1. State what's unclear
2. Reference which document you checked
3. Ask specific question
4. Wait for answer before proceeding

Never guess. Always ask.

---

## Session Start Output Template

When starting a session, output:

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

**Specs I will reference:**
- [spec document]

**Questions/Blockers:**
- [Any questions, or "None"]

**Ready to proceed?**
```

---

**BEGIN SESSION START WORKFLOW NOW**
