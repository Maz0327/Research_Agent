# ClaudeKit Research - Quick Start Guide

**Goal:** Implement ClaudeKit in Research Agent over 3 sprints
**Status:** Ready to execute
**Time Estimate:** 9 hours total (2.5 + 3 + 4)

---

## The Problem We're Solving

```
Current State (Without ClaudeKit):
┌─────────────────┐
│ Claude generates│
│ code manually   │
│ based on prompts│
└────────┬────────┘
         │
         ▼
    CODE DRIFTS:
    • Missing error handling
    • No cost tracking
    • Inconsistent patterns
    • Secrets leak into commits
    • Tests not run before push
    • Common errors repeated
         │
         ▼
    ❌ Production issues

With ClaudeKit:
┌──────────────────────┐
│ CLAUDE.md documents  │◀──── AI reads once per session
│ • Structure          │
│ • Standards          │
│ • Error fixes        │
└──────────────────────┘

┌──────────────────────┐
│ Skills provide rules │◀──── AI auto-applies when relevant
│ • Code review        │
│ • Pipeline patterns  │
│ • API integration    │
└──────────────────────┘

┌──────────────────────┐
│ Hooks guarantee      │◀──── Shell scripts, zero trust
│ • No secrets leak    │
│ • Tests pass         │
│ • Code formatted     │
└──────────────────────┘

         │
         ▼
    ✅ Production ready
```

---

## Three Core Concepts (Learn These)

### 1. CLAUDE.md - The Brain
**What:** One file, read at session start, contains all project context
**Where:** `/Users/maz/Documents/GitHub/Research_Agent/CLAUDE.md`
**Purpose:** Ground truth for standards, patterns, error solutions
**Cost:** ~500-800 tokens per session

**What goes in:**
- Directory structure overview
- Coding standards (PEP 8, type hints, etc.)
- Testing requirements
- Common errors & how to fix them
- Key file locations
- External service configs

---

### 2. Skills - The Standards
**What:** YAML markdown files that Claude auto-activates based on context
**Where:** `.claude/skills/SKILL_NAME/SKILL.md`
**Purpose:** Enforce team-specific standards without manual asking
**Cost:** ~200-400 tokens when loaded (only if relevant)

**Examples:**
- `/reviewing-code` - Code review checklist
- `/testing` - Test patterns
- `/api-client` - API integration pattern

**How it works:**
1. You ask: "Review this code"
2. Claude sees context → activates `reviewing-code` skill
3. Applies 20-item checklist automatically
4. No back-and-forth needed

---

### 3. Hooks - The Guardrails
**What:** Shell scripts that run at specific lifecycle events
**Where:** `.claude/hooks/` + `scripts/hooks/`
**Purpose:** Prevent bad code from being committed. Period.
**Cost:** Free (no tokens)

**Examples:**
- Before `git push` → run tests (fail if any red)
- Before file write → check for secrets (block if found)
- After edit → auto-format with Black

**How it works:**
1. Claude tries to commit bad code
2. Hook checks (e.g., tests must pass)
3. If test fails → hook says "no, try again"
4. Claude fixes code, retries
5. Only after tests pass does code get committed

**Key difference:** Hooks are GUARANTEED. No negotiation. No "maybe I'll skip this."

---

## Phase 1 Checklist (2.5 hours, This Sprint)

### Step 1: Enhance CLAUDE.md (30 min)
**File:** `/Users/maz/Documents/GitHub/Research_Agent/CLAUDE.md`

**Add:**
```markdown
## Common Errors & Recent Fixes

### Error: Missing error handling in external API calls
**Symptoms:** Pipeline fails silently on API errors
**Solution:** Wrap in try/except with `ctx.add_warning()`
**File:** backend/pipeline/stages.py (see stage_name pattern)

### Error: Forgetting cost tracking
**Symptoms:** API budget exceeded unexpectedly
**Solution:** Add `ctx.add_cost("api_name", amount)` in each integration call
**File:** backend/integrations/client_name.py

[Add 5-10 more recent errors]

## Problem Domain Map

### Pipeline Development
**Entry:** backend/pipeline/stages.py
**Pattern:** Use PipelineContext, graceful degradation, cost tracking
**Skill:** /developing-pipeline-stages

### Integrations
**Entry:** backend/integrations/
**Pattern:** Client structure with logging, error handling, rate limiting
**Skill:** /integrating-external-apis

### Frontend
**Entry:** frontend/components/ and frontend/pages/
**Pattern:** React functional components, TypeScript strict mode
**Skill:** /frontend-design (for UI work)
```

---

### Step 2: Create 3 Skills (2 hours)

#### Skill 1: Code Review
**Create file:** `.claude/skills/reviewing-research-agent-code/SKILL.md`

```yaml
---
name: reviewing-research-agent-code
description: |
  Review Research Agent code for production readiness.
  Check: Type safety, error handling, API cost tracking,
  graceful degradation, security, testing.
  Use when: Code review requested, PR provided, quality check asked.
allowed_tools: [bash, read, write]
---

# Reviewing Research Agent Code

## Checklist

### Type Safety
- [ ] Python: All functions have type hints (including return)
- [ ] TypeScript: Strict mode enabled
- [ ] No `any` types (TypeScript) without comment
- [ ] Pydantic models for API validation

### Error Handling
- [ ] External API calls wrapped in try/except
- [ ] `ctx.add_warning()` for non-fatal errors
- [ ] Logging with loguru at INFO level minimum
- [ ] Graceful degradation with fallback chains

### API Costs
- [ ] `ctx.add_cost()` called for paid APIs
- [ ] Budget limits respected (JobConfig mode budgets)
- [ ] Cost estimation logged before expensive ops

### Testing
- [ ] New features have test coverage
- [ ] External APIs mocked in tests
- [ ] No real API calls in test suite
- [ ] Edge cases tested, not just happy path

### Security
- [ ] No hardcoded secrets/API keys
- [ ] Input validation for user data
- [ ] Rate limiting on sensitive endpoints

### Database & State
- [ ] Supabase queries use indexes
- [ ] Job state updated after each pipeline stage
- [ ] Soft delete pattern used (status field)

### Documentation
- [ ] Non-obvious code sections have comments
- [ ] Function docstrings present (Python)
- [ ] Complex algorithms explained

## Reference
See: docs/code-standards.md for examples
```

**Save time:** Copy template above, just replace Pydantic comments if needed.

---

#### Skill 2: Pipeline Development
**Create file:** `.claude/skills/developing-pipeline-stages/SKILL.md`

```yaml
---
name: developing-pipeline-stages
description: |
  Develop Research Agent pipeline stages with proper error recovery.
  Follow: PipelineContext pattern, graceful degradation, cost tracking,
  fallback chains, warning collection.
  Use when: Creating new stage, refactoring existing stage, debugging.
allowed_tools: [bash, read, write]
---

# Developing Pipeline Stages

## Pattern: Stage Function

```python
async def stage_name(ctx: PipelineContext) -> None:
    """What this stage does."""
    logger.info(f"Starting {ctx.job_id}")

    try:
        # Stage work here
        result = await do_work(ctx)
        ctx.data["key"] = result

    except SpecificError as e:
        logger.warning(f"Non-fatal: {e}")
        ctx.add_warning(f"Stage failed: {e}")
        result = fallback_strategy()

    except CriticalError as e:
        logger.error(f"Critical: {e}")
        raise

    await update_job(ctx.job_id, {
        "progress": ctx.progress + 10
    })
```

## Checklist
- [ ] Try/except with appropriate fallbacks
- [ ] PipelineContext passed correctly
- [ ] Warnings added for non-fatal issues
- [ ] Costs tracked with ctx.add_cost()
- [ ] Job progress updated after stage
- [ ] All external APIs have fallback chains
- [ ] Logging includes job_id

## Reference
See: backend/pipeline/stages.py for reference
```

---

#### Skill 3: API Integration
**Create file:** `.claude/skills/integrating-external-apis/SKILL.md`

```yaml
---
name: integrating-external-apis
description: |
  Create API clients for Research Agent integrations.
  Follow: Client structure, loguru logging, rate limiting,
  cost tracking, fallback chains, error handling.
  Use when: Adding new external service, refactoring client.
allowed_tools: [bash, read, write]
---

# Integrating External APIs

## Pattern: API Client

```python
from loguru import logger
from backend.config import settings

class ServiceClient:
    def __init__(self):
        self.api_key = settings.require_service()
        self.base_url = "https://api.service.com"

    async def fetch(self, query: str) -> dict:
        logger.info(f"Service request: {query[:50]}...")

        try:
            response = await self._request(query)
            cost = self._estimate_cost(response)
            logger.debug(f"Cost: ${cost:.4f}")
            return response

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}")
            raise

        except ServiceError as e:
            logger.error(f"Service error: {e}")
            raise

    def _estimate_cost(self, response: dict) -> float:
        # Calculate based on response
        pass
```

## Checklist
- [ ] Configuration in backend/config.py
- [ ] All API calls logged (INFO minimum)
- [ ] Specific exception handling (no bare except)
- [ ] Cost estimated and logged
- [ ] Rate limiting respected
- [ ] Fallback chains defined in pipeline
- [ ] Tests mock external calls

## Reference
See: backend/integrations/ for examples
```

---

### Step 3: Test Skills (15 min)
In Claude Code, ask:
```
What skills are available?
```

Expected response: Should list your 3 new skills plus any others.

---

### Step 4: Commit (15 min)
```bash
cd /Users/maz/Documents/GitHub/Research_Agent

git add CLAUDE.md .claude/skills/*/SKILL.md

git commit -m "feat(claudekit): add foundational skills and CLAUDE.md enhancements

- Add Common Errors & Fixes section to CLAUDE.md
- Add Problem Domain Map for code organization
- Create reviewing-research-agent-code skill
- Create developing-pipeline-stages skill
- Create integrating-external-apis skill"
```

---

## Phase 2 Preview (Next Sprint, 3 hours)

### Create Hooks
```bash
mkdir -p .claude/hooks scripts/hooks
```

**Hook 1:** Prevent secrets in commits
**Hook 2:** Auto-format Python files
**Hook 3:** Run tests before push

### Create Slash Commands
**Command 1:** /debug-job
**Command 2:** /add-integration
**Command 3:** /add-pipeline-stage

### Document Problem Domains
Add "Problem Domain Map" to CLAUDE.md with links to detailed docs.

---

## Phase 3 Preview (Q1 2026, 4 hours)

- Extended thinking patterns guidance
- Specialized subagents for parallel work
- Structured outputs for JSON schema compliance
- GitHub Actions integration for automated code review

---

## Success Indicators (Phase 1)

✅ All done when:
1. CLAUDE.md has "Common Errors" section with 5+ documented fixes
2. 3 skills created and visible to Claude
3. When you ask Claude to review code, it applies the skill checklist
4. Code follows the reviewed standards more consistently

---

## Files You'll Create

```
/Users/maz/Documents/GitHub/Research_Agent/
├── CLAUDE.md (MODIFIED)
│   ├── New: Common Errors & Fixes section
│   └── New: Problem Domain Map section
│
└── .claude/
    └── skills/
        ├── reviewing-research-agent-code/
        │   └── SKILL.md (NEW)
        ├── developing-pipeline-stages/
        │   └── SKILL.md (NEW)
        └── integrating-external-apis/
            └── SKILL.md (NEW)
```

---

## Quick Timeline

```
Sprint: Jan 8-15, 2026
├─ Day 1 (Today): Read this guide + Key Findings (30 min)
├─ Day 2-3: Enhance CLAUDE.md + create 3 skills (2 hours)
├─ Day 4: Test skills + commit (30 min)
└─ Day 5: Review results, plan Phase 2

Next Sprint: Jan 15-22, 2026
├─ Phase 2: Hooks + commands (3 hours)
└─ Test automation in action

Q1 2026:
└─ Phase 3: Advanced features (4 hours)
```

---

## ROI Snapshot

| Investment | Return | Payoff |
|-----------|--------|--------|
| 2.5 hours (Phase 1) | Consistent code review | Immediate |
| 3 hours (Phase 2) | Zero secrets in commits, zero test failures | Day 2 |
| 4 hours (Phase 3) | +2x development speed | Week 2 |
| **9 hours total** | **184 hours saved annually** | **20.4x ROI** |

---

## Get Started Now

1. **Open** this file in your editor
2. **Read** Key Findings document (10 min)
3. **Schedule** 2.5 hours this week for Phase 1
4. **Create** first skill as proof of concept (30 min)
5. **Test** with Claude ("What skills are available?")
6. **Done!** Then do remaining 2 skills

---

## Questions?

See the comprehensive documents:
- **For why:** Read `/plans/reports/researcher-260108-1819-key-findings.md`
- **For how:** Read `/plans/reports/researcher-260108-1819-implementation-roadmap.md`
- **For details:** Read `/plans/reports/researcher-260108-1819-claudekit-research-comprehensive.md`
- **For index:** Read `/plans/reports/researcher-260108-1819-RESEARCH-INDEX.md`

---

**You're ready to implement. Start today.**

