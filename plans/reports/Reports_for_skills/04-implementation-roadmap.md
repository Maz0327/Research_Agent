# ClaudeKit Implementation Roadmap for Research Agent

**Created:** January 8, 2026
**Scope:** Adopt ClaudeKit standards to prevent code drift and improve development efficiency
**Target:** Implement in 3 phases (This Sprint → Next Sprint → Q1 2026)

---

## Phase 1: Immediate (This Sprint - Week of Jan 8)

### Action 1.1: Enhance CLAUDE.md
**File:** `/Users/maz/Documents/GitHub/Research_Agent/CLAUDE.md`

**Changes:**
1. Add "Common Errors & Recent Fixes" section listing last 10 bugs with solutions
2. Restructure into problem domains with hyperlinks to detailed docs
3. Add "Verification Checklist" at top for quick reference before commits
4. Add "Extended Thinking Triggers" section with guidance on when to use

**Expected Benefit:** Prevents Claude from repeating same mistakes; saves ~500 tokens of re-explanation per session.

**Time to implement:** 30 minutes

---

### Action 1.2: Create 3 Core Skills
**Location:** `.claude/skills/`

#### Skill 1: Code Review for Research Agent
**File:** `.claude/skills/reviewing-research-agent-code/SKILL.md`

```yaml
---
name: reviewing-research-agent-code
description: |
  Review Research Agent code for production readiness.
  Checks: Type safety, error handling, API cost tracking, graceful degradation,
  database correctness, frontend accessibility, security.
  Trigger: When user provides code for review, asks "is this production-ready?",
  or requests quality assessment before merge.
allowed_tools: [bash, read, edit, write]
---

# Reviewing Research Agent Code

## Checklist

### Type Safety
- [ ] All Python functions have type hints (including return type)
- [ ] All TypeScript has strict mode enabled
- [ ] No `any` types in TypeScript (except justified with comment)
- [ ] Pydantic models used for API validation

### Error Handling & Logging
- [ ] External API calls wrapped in try/except
- [ ] `ctx.add_warning()` used for non-fatal errors
- [ ] All errors logged with `loguru.logger`
- [ ] Graceful degradation with fallback chains where applicable

### API Cost Awareness
- [ ] Cost tracked with `ctx.add_cost()` if using paid APIs
- [ ] Budget limits respected (mode-specific in JobConfig)
- [ ] Cost estimation logged before expensive operations

### Database & State
- [ ] Supabase queries use appropriate indexes
- [ ] Job state updated after each pipeline stage
- [ ] Soft delete pattern used (status field, not deletion)

### Frontend
- [ ] WCAG 2.1 AA accessibility (alt text, labels, keyboard nav)
- [ ] Mobile-first responsive design
- [ ] No hardcoded breakpoints (use Tailwind)
- [ ] Component prop types defined with TypeScript interfaces

### Security
- [ ] No hardcoded secrets or API keys
- [ ] Input validation for user-provided data
- [ ] Rate limiting enforced on sensitive endpoints

### Testing
- [ ] New features have test coverage
- [ ] External APIs mocked in tests
- [ ] No real API calls in test suite
- [ ] Tests cover edge cases, not just happy path

### Documentation
- [ ] Non-obvious code sections have comments
- [ ] Function docstrings present (Python)
- [ ] Complex algorithms explained
- [ ] Architecture decisions noted if not obvious

## Examples

See: `docs/code-standards.md` for implementation examples
```

**Time:** 30 minutes

#### Skill 2: Pipeline Development
**File:** `.claude/skills/developing-pipeline-stages/SKILL.md`

```yaml
---
name: developing-pipeline-stages
description: |
  Develop Research Agent pipeline stages with proper error recovery.
  Must follow: PipelineContext for state passing, graceful degradation,
  cost tracking, fallback chains, warning collection.
  Trigger: When developing new pipeline stage, refactoring existing stage,
  or debugging stage failures.
allowed_tools: [bash, read, edit, write]
---

# Developing Pipeline Stages

## Pattern: Stage Function

```python
async def stage_name(ctx: PipelineContext) -> None:
    """Description of what this stage does."""
    logger.info(f"Starting {ctx.job_id}")

    try:
        # Stage logic here
        result = await do_work(ctx)
        ctx.data["key"] = result

    except SpecificError as e:
        logger.warning(f"Non-fatal error: {e}")
        ctx.add_warning(f"Stage name failed: {e}")
        # Fallback strategy

    except CriticalError as e:
        logger.error(f"Critical error: {e}")
        raise

    await update_job(ctx.job_id, {"progress": ctx.progress + 10})
```

## Checklist

- [ ] Stage wrapped in try/except with appropriate fallbacks
- [ ] Context passed correctly (PipelineContext)
- [ ] Warnings added with `ctx.add_warning()` for non-fatal issues
- [ ] Cost tracked with `ctx.add_cost()` for paid APIs
- [ ] Job progress updated after stage
- [ ] All external APIs have fallback chains (see quality_gate.py)
- [ ] Logging includes job_id and descriptive context

## References

See: `backend/pipeline/stages.py` for reference implementations
See: `CLAUDE.md` for fallback chain patterns
```

**Time:** 30 minutes

#### Skill 3: API Integration
**File:** `.claude/skills/integrating-external-apis/SKILL.md`

```yaml
---
name: integrating-external-apis
description: |
  Create API clients for Research Agent integrations.
  Must follow: Client structure pattern, loguru logging, rate limiting,
  cost tracking, fallback chains, error handling.
  Trigger: When adding new external service (Gemini, Perplexity, etc.),
  or refactoring existing client.
allowed_tools: [bash, read, edit, write]
---

# Integrating External APIs

## Pattern: API Client

```python
from loguru import logger
from backend.config import settings

class ServiceClient:
    """Client for Service API."""

    def __init__(self):
        self.api_key = settings.require_service()
        self.base_url = "https://api.service.com"

    async def fetch(self, query: str) -> dict:
        """Fetch data from Service API."""
        logger.info(f"Service request: {query[:50]}...")

        try:
            response = await self._request(query)
            cost = self._estimate_cost(response)
            logger.debug(f"Cost: ${cost:.4f}")
            return response

        except RateLimitError as e:
            logger.warning(f"Rate limited: {e}")
            raise  # Let fallback chain handle

        except ServiceError as e:
            logger.error(f"Service error: {e}")
            raise

    def _estimate_cost(self, response: dict) -> float:
        # Calculate cost based on response size/tokens
        pass
```

## Checklist

- [ ] Configuration added to `backend/config.py` with `require_*()` method
- [ ] All API calls logged with loguru (info level minimum)
- [ ] Error handling: try/except with specific exceptions
- [ ] Cost estimated and logged
- [ ] Rate limiting respected (backoff strategy)
- [ ] Fallback chains defined in pipeline stage
- [ ] Tests mock external API calls

## Configuration Pattern

```python
# backend/config.py

SERVICE_API_KEY: Optional[str] = None

def require_service(self) -> str:
    if not self.SERVICE_API_KEY:
        raise ValueError("SERVICE_API_KEY not configured")
    return self.SERVICE_API_KEY
```

## References

See: `backend/integrations/` for reference implementations
See: `CLAUDE.md` fallback chain patterns
```

**Time:** 30 minutes

**Total Phase 1 Time:** 2 hours

---

## Phase 2: Foundation (Next Sprint - Week of Jan 15)

### Action 2.1: Set Up Hooks for Automation
**Location:** `.claude/hooks/`

#### Hook 1: Prevent Secrets in Git
**File:** `.claude/hooks/claude.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "name": "prevent-secrets-in-commits",
        "matcher": {
          "tool": "Bash",
          "command": "git commit"
        },
        "command": "bash scripts/hooks/check-no-secrets.sh"
      }
    ]
  }
}
```

**Script:** `scripts/hooks/check-no-secrets.sh`
```bash
#!/bin/bash
# Check git staged files for common secret patterns

patterns=(
  "OPENAI_API_KEY"
  "SUPABASE_SERVICE_ROLE_KEY"
  "GOOGLE_API_KEY"
  "password="
  "secret_"
)

git diff --cached | grep -E "$(IFS=|; echo "${patterns[*]}")" && {
  echo "ERROR: Potential secrets detected in commit"
  exit 1
}

exit 0
```

#### Hook 2: Auto-Format Python Files
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "name": "auto-format-python",
        "matcher": {
          "tool": ["Edit", "Write"],
          "path": "**/*.py"
        },
        "command": "black {{file}} --quiet"
      }
    ]
  }
}
```

#### Hook 3: Run Tests Before Push
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "name": "run-tests-before-push",
        "matcher": {
          "tool": "Bash",
          "command": "git push"
        },
        "command": "pytest --tb=short -q"
      }
    ]
  }
}
```

**Time:** 1.5 hours

---

### Action 2.2: Create Slash Commands
**Location:** `.claude/commands/`

**Command 1: Debug Job**
**File:** `.claude/commands/debug-job.md`

```markdown
# /debug-job

Debug a failed Research Agent job.

## Process

1. Get job ID from user
2. Query Supabase: `SELECT * FROM jobs WHERE id = ?`
3. Review job status and warnings
4. Identify failing stage from logs
5. Reproduce stage locally with test data
6. Apply systematic debugging from debugging skill

## Checklist

- [ ] Job ID identified
- [ ] Status and last stage reviewed
- [ ] Error message captured
- [ ] Root cause identified (not just symptoms)
- [ ] Fix tested locally
- [ ] Solution documented
```

**Command 2: Add Integration**
**File:** `.claude/commands/add-integration.md`

```markdown
# /add-integration

Add new external API integration to Research Agent.

## Checklist

- [ ] Create client in `backend/integrations/client_name.py`
- [ ] Add configuration to `backend/config.py`
- [ ] Write tests in `backend/tests/integrations/test_client.py`
- [ ] Implement fallback chain in relevant pipeline stage
- [ ] Add to CLAUDE.md external services table
- [ ] Document cost per API call
- [ ] Security review: no hardcoded secrets?

## Reference

Use integrating-external-apis skill for implementation details.
```

**Command 3: Add Pipeline Stage**
**File:** `.claude/commands/add-pipeline-stage.md`

```markdown
# /add-pipeline-stage

Add new pipeline stage to Research Agent.

## Steps

1. Plan stage purpose and inputs/outputs
2. Implement in `backend/pipeline/stages.py`
3. Add fields to `PipelineContext` if needed
4. Register in stage list in `backend/worker.py`
5. Add error recovery strategy
6. Write tests
7. Document in architecture.md

## Reference

Use developing-pipeline-stages skill for implementation details.
```

**Time:** 1 hour

---

### Action 2.3: Document Problem Domains
**File:** `CLAUDE.md` enhancement

Add section:
```markdown
## Problem Domain Map

### Pipeline Development
- **Entry point:** `backend/pipeline/stages.py`
- **Context:** `backend/pipeline/context.py`
- **Error recovery:** `backend/pipeline/stage_runner.py`
- **Quality:** `backend/pipeline/quality_gate.py`
- **Skill:** `/developing-pipeline-stages`

### Integrations
- **Location:** `backend/integrations/`
- **Config:** `backend/config.py`
- **Pattern:** See code-standards.md "Integration Patterns"
- **Skill:** `/integrating-external-apis`

### Frontend
- **Components:** `frontend/components/`
- **Pages:** `frontend/pages/`
- **State:** `frontend/store/jobs.ts`
- **Skill:** `/frontend-design` (if needed)

### Database/State
- **Schema:** Supabase (see docs/database-schema.md)
- **Patterns:** Soft delete, job lifecycle, progress tracking
- **Files:** `backend/state/factory.py`
```

**Time:** 30 minutes

**Total Phase 2 Time:** 3 hours

---

## Phase 3: Maturity (Q1 2026)

### Action 3.1: Extended Thinking Integration
Add to CLAUDE.md:
```markdown
## Extended Thinking Patterns

When to use extended thinking for complex decisions:

- **"think"** (baseline): Algorithm design, error handling strategy
- **"think hard"** (2x): Validation logic, schema design
- **"think harder"** (4x): Major architectural changes, API design refactoring

Example:
"Think hard about how to optimize this Quality Gate scoring—I want to minimize LLM calls while maintaining accuracy."
```

### Action 3.2: Subagent Specialization
Create specialized subagents:
```bash
claude subagent create "Pipeline Specialist" \
  --skill developing-pipeline-stages \
  --skill debugging-research-agent-jobs

claude subagent create "Code Reviewer" \
  --skill reviewing-research-agent-code

claude subagent create "Integration Developer" \
  --skill integrating-external-apis
```

### Action 3.3: Structured Outputs Implementation
Implement guaranteed JSON schema compliance for clips/quotes extraction:

```python
from anthropic import messages
from backend.models import ClipsQuotesSchema

response = messages.create(
    model="claude-opus-4-5-20251101",
    max_tokens=2000,
    structured_output={
        "type": "json_schema",
        "json_schema": ClipsQuotesSchema.model_json_schema()
    }
)
```

Benefits:
- Zero schema validation failures
- Removes retry logic in extraction pipeline
- Faster extraction (no LLM-based repair loop)
- Cost savings (~5-10% fewer LLM calls)

### Action 3.4: Automate Code Review in GitHub Actions
**File:** `.github/workflows/claude-review.yml`

```yaml
name: Claude Code Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: |
          claude "Review this PR using the reviewing-research-agent-code skill. \
          Look at the diff and provide feedback on: type safety, error handling, \
          API costs, tests, security, and documentation."
```

---

## Implementation Priority Matrix

| Action | Priority | Effort | Benefit | Dependencies |
|--------|----------|--------|---------|--------------|
| 1.1 CLAUDE.md | P0 | 30m | High | None |
| 1.2 Skills (3) | P0 | 2h | High | None |
| 2.1 Hooks | P1 | 1.5h | High | None |
| 2.2 Slash Commands | P1 | 1h | Medium | None |
| 2.3 Problem Domains | P1 | 30m | Medium | 1.1 |
| 3.1 Extended Thinking | P2 | 30m | Medium | 1.1 |
| 3.2 Subagents | P2 | 1h | Medium | 1.2 |
| 3.3 Structured Outputs | P2 | 2h | High | Framework update |
| 3.4 GitHub Actions | P2 | 1h | High | 2.1, 2.2 |

---

## Success Metrics

### Before Implementation (Baseline)
- Developer friction: Manual repetition of standards explanations
- Code quality: Occasional missing error handling, type safety gaps
- Development speed: Context reloading between sessions
- Drift: AI generates code that contradicts CLAUDE.md

### After Phase 1 (30 minutes in)
- Context recovery: CLAUDE.md includes common errors
- Standard enforcement: Code review skill available
- Metrics: Track adoption (ask Claude "which skills are active?")

### After Phase 2 (3 hours total)
- Automation: Hooks prevent common mistakes (secrets, unfixed errors)
- Consistency: Slash commands guide workflow
- Metrics: Zero secrets in commits, 100% tests passing before push

### After Phase 3 (Q1 2026)
- Reliability: Structured outputs eliminate schema validation
- Scale: Subagents enable parallel development (e.g., 2 pipeline stages simultaneously)
- Quality: Code review automation catches 95% of issues before human review
- Metrics: PR review time reduced by 50%

---

## Quick Start Checklist

- [ ] Read `/Users/maz/Documents/GitHub/Research_Agent/plans/reports/researcher-260108-1819-claudekit-research-comprehensive.md`
- [ ] Backup current `CLAUDE.md`
- [ ] Implement Action 1.1 (CLAUDE.md enhancement)
- [ ] Create 3 skills (Action 1.2)
- [ ] Test: Ask Claude "What skills are active?" → Should see 3 new skills
- [ ] Set up hooks (Action 2.1)
- [ ] Create slash commands (Action 2.2)
- [ ] Document in CLAUDE.md (Action 2.3)

---

## File Locations Summary

| Item | Location | Priority |
|------|----------|----------|
| Comprehensive Report | `/plans/reports/researcher-260108-1819-claudekit-research-comprehensive.md` | Reference |
| Code Review Skill | `.claude/skills/reviewing-research-agent-code/SKILL.md` | P0 |
| Pipeline Development Skill | `.claude/skills/developing-pipeline-stages/SKILL.md` | P0 |
| API Integration Skill | `.claude/skills/integrating-external-apis/SKILL.md` | P0 |
| Hooks Config | `.claude/hooks/claude.json` | P1 |
| Debug Command | `.claude/commands/debug-job.md` | P1 |
| Add Integration Command | `.claude/commands/add-integration.md` | P1 |
| Add Stage Command | `.claude/commands/add-pipeline-stage.md` | P1 |

---

## Notes

- All CLAUDE.md references in this document assume the existing CLAUDE.md at `/Users/maz/Documents/GitHub/Research_Agent/CLAUDE.md`
- Skills use YAML frontmatter format as per official docs
- Hooks use `.claude/hooks/claude.json` format (version 1.0)
- All bash scripts should be stored in `scripts/hooks/` for organization

