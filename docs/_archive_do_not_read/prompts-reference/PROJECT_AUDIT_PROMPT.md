# Research Agent — Project Audit Prompt

**For: Claude Code**
**Purpose: Analyze existing project before implementation work begins**

---

# CRITICAL INSTRUCTIONS

1. **DO NOT MODIFY ANY CODE.** This is an audit only.
2. **DO NOT SKIP FILES.** Read everything, even if it looks outdated.
3. **BE THOROUGH.** I need a complete picture to plan next steps.
4. **OUTPUT A STRUCTURED REPORT.** Follow the exact format specified below.

---

# YOUR TASK

Analyze this existing Research Agent project and produce a comprehensive audit report. I will share this report with another assistant who has the full specification for what this system SHOULD be. Together we'll determine what needs to change.

---

# AUDIT STEPS

## Step 1: Project Structure Scan

Map the entire project structure. For each directory and file:
- What is its purpose?
- Is it actively used or orphaned?
- Does it follow a consistent pattern?

Output as a tree with annotations.

---

## Step 2: Read CLAUDE.md and Any Documentation

Read the existing CLAUDE.md file and any other documentation files (README, docs/, etc.).

Report:
- What instructions currently exist for AI assistants?
- What architectural decisions are documented?
- What's outdated or contradicts other parts of the codebase?

---

## Step 3: Database Schema Analysis

Find all database-related code (Supabase client, migrations, schema definitions).

Report:
- What tables exist?
- What columns in each table?
- What relationships?
- Any migrations pending or out of sync?

---

## Step 4: Pydantic Models / Data Structures

Find all Pydantic models or data class definitions.

Report:
- What models exist?
- Where are they defined (scattered or centralized)?
- Are they consistent with each other?
- Are they used consistently throughout the codebase?

---

## Step 5: Pipeline Analysis

Trace the data flow from input to output.

Report:
- What pipeline stages exist?
- How do they connect?
- What's the job/task orchestration pattern?
- Are there multiple implementations of the same thing?

---

## Step 6: External Service Integrations

Find all external API integrations (Gemini, Supadata, YouTube, etc.).

Report:
- What services are integrated?
- Where are the client wrappers?
- What API methods are implemented?
- Are there hardcoded API keys or proper config management?

---

## Step 7: Prompt Templates

Find all LLM prompt templates.

Report:
- Where are prompts stored?
- What prompts exist?
- Are they complete or fragmentary?
- Do they follow a consistent structure?

---

## Step 8: API Endpoints

Find all API route definitions.

Report:
- What endpoints exist?
- What do they do?
- Are they functional or stubs?
- What's the request/response pattern?

---

## Step 9: Celery / Task Queue

Find all Celery task definitions and configuration.

Report:
- What tasks are defined?
- How are they chained/orchestrated?
- What's the retry/error handling?
- Is there a clear job state machine?

---

## Step 10: Tests

Find all test files.

Report:
- What test coverage exists?
- What's tested vs untested?
- Are there test fixtures?
- Do tests pass? (run them if possible)

---

## Step 11: Configuration & Environment

Find all configuration management.

Report:
- What env variables are expected?
- Is there a .env.example?
- How is config loaded?
- Any hardcoded values that should be config?

---

## Step 12: Dead Code & Redundancy

Identify:
- Files that aren't imported anywhere
- Functions that aren't called
- Duplicate implementations
- Commented-out code blocks
- TODO/FIXME comments

---

# OUTPUT FORMAT

Produce your report in this exact structure:

```markdown
# RESEARCH AGENT — PROJECT AUDIT REPORT

**Generated:** [timestamp]
**Audited by:** Claude Code

---

## 1. PROJECT STRUCTURE

### Directory Tree
```
[annotated tree here]
```

### Structure Assessment
- [ ] Consistent organization: Yes/No
- [ ] Clear separation of concerns: Yes/No
- [ ] Follows standard patterns: Yes/No

**Issues Found:**
- [list any structural problems]

---

## 2. EXISTING DOCUMENTATION

### CLAUDE.md Summary
[summarize what it says]

### Other Docs Found
- [list other doc files]

### Documentation Issues
- [what's outdated/missing/contradictory]

---

## 3. DATABASE SCHEMA

### Tables
| Table | Columns | Purpose | Status |
|-------|---------|---------|--------|
| [name] | [columns] | [purpose] | Active/Unused |

### Schema Issues
- [list any problems]

---

## 4. DATA MODELS

### Pydantic Models Found
| Model | Location | Purpose | Used By |
|-------|----------|---------|---------|
| [name] | [path] | [purpose] | [what uses it] |

### Model Issues
- Scattered across files: Yes/No
- Inconsistent definitions: Yes/No
- Missing models needed: [list]

---

## 5. PIPELINE STAGES

### Current Flow
```
[diagram of current pipeline]
```

### Stages Implemented
| Stage | File(s) | Status | Notes |
|-------|---------|--------|-------|
| Ingestion | [path] | Complete/Partial/Stub | [notes] |
| Extraction | [path] | Complete/Partial/Stub | [notes] |
| Validation | [path] | Complete/Partial/Stub | [notes] |
| Synthesis | [path] | Complete/Partial/Stub | [notes] |
| Assembly | [path] | Complete/Partial/Stub | [notes] |

### Pipeline Issues
- [list any problems]

---

## 6. EXTERNAL SERVICES

### Integrations Found
| Service | Client Location | Methods Implemented | Status |
|---------|-----------------|---------------------|--------|
| Gemini | [path] | [methods] | Working/Broken/Partial |
| Supadata | [path] | [methods] | Working/Broken/Partial |
| YouTube | [path] | [methods] | Working/Broken/Partial |
| [other] | [path] | [methods] | Working/Broken/Partial |

### Integration Issues
- [list any problems]

---

## 7. PROMPT TEMPLATES

### Prompts Found
| Prompt | Location | Purpose | Complete? |
|--------|----------|---------|-----------|
| [name] | [path] | [purpose] | Yes/No |

### Prompt Issues
- Consistent structure: Yes/No
- Has guardrails: Yes/No
- Missing prompts: [list]

---

## 8. API ENDPOINTS

### Endpoints Found
| Method | Path | Handler | Status |
|--------|------|---------|--------|
| POST | /jobs | [function] | Working/Stub |
| GET | /jobs/{id} | [function] | Working/Stub |
| [etc] | [etc] | [etc] | [etc] |

### API Issues
- [list any problems]

---

## 9. CELERY TASKS

### Tasks Found
| Task | Location | Purpose | Status |
|------|----------|---------|--------|
| [name] | [path] | [purpose] | Working/Broken/Stub |

### Task Chain/Orchestration
[describe how tasks connect]

### Task Issues
- [list any problems]

---

## 10. TESTS

### Test Files Found
| File | Tests | Passing? |
|------|-------|----------|
| [path] | [count] | Yes/No/Unknown |

### Test Coverage Assessment
- Extraction tested: Yes/No
- Validation tested: Yes/No
- Synthesis tested: Yes/No
- API tested: Yes/No

### Test Issues
- [list any problems]

---

## 11. CONFIGURATION

### Environment Variables Expected
| Variable | Required? | Has Default? | Currently Set? |
|----------|-----------|--------------|----------------|
| [name] | Yes/No | Yes/No | Yes/No/Unknown |

### Config Issues
- [list any problems]

---

## 12. DEAD CODE & REDUNDANCY

### Unused Files
| File | Reason Unused | Recommendation |
|------|---------------|----------------|
| [path] | [why] | Archive/Delete/Review |

### Unused Functions
| Function | Location | Recommendation |
|----------|----------|----------------|
| [name] | [path] | Archive/Delete/Review |

### Duplicate Implementations
| Functionality | Locations | Recommendation |
|---------------|-----------|----------------|
| [what] | [paths] | Keep X, remove Y |

### TODO/FIXME Comments
| Location | Comment | Priority |
|----------|---------|----------|
| [path:line] | [comment] | High/Medium/Low |

---

## 13. SUMMARY

### What's Built and Working
1. [item]
2. [item]

### What's Built but Broken/Incomplete
1. [item] — [what's wrong]
2. [item] — [what's wrong]

### What's Not Built Yet
1. [item]
2. [item]

### What Should Be Archived/Removed
1. [item] — [why]
2. [item] — [why]

### Critical Issues to Address First
1. [issue] — [why it's blocking]
2. [issue] — [why it's blocking]

---

## 14. RECOMMENDED NEXT STEPS

Before implementing new features, I recommend:

1. [step 1]
2. [step 2]
3. [step 3]

---

## 15. QUESTIONS FOR PROJECT OWNER

Things I need clarification on before proceeding:

1. [question]
2. [question]
3. [question]

---

**END OF AUDIT REPORT**
```

---

# IMPORTANT

- Read EVERY file. Don't skip based on names.
- Check imports to find what's actually used.
- Run the code if possible to see what works.
- Note version mismatches in dependencies.
- Flag anything that looks like it was started but abandoned.

This audit will be shared with another assistant who will compare it against the target specification. Be accurate and thorough — incomplete information will cause problems later.

---

# START

Begin the audit now. Take your time. Output the complete report when finished.
