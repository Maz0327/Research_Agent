# /review-file

Review a file against project specifications.

---

## Usage

```
/review-file [path/to/file.py]
```

---

## What This Command Does

1. Reads the specified file
2. Checks against project specifications
3. Identifies gaps and issues
4. Recommends: keep / modify / rewrite

---

## Review Criteria

### For Pydantic Models

- [ ] All fields have type hints
- [ ] All fields have descriptions/docstrings
- [ ] Field names match spec conventions
- [ ] Required vs optional correct
- [ ] Validators present where needed
- [ ] Matches corresponding spec in IMPLEMENTATION_PLAN.md

### For Pipeline Stages

- [ ] Function has proper signature
- [ ] Takes PipelineContext, returns PipelineContext
- [ ] Has complete docstring
- [ ] Has error handling
- [ ] Follows source isolation rule
- [ ] Updates correct context fields

### For Prompts

- [ ] Has Source Identity Lock block
- [ ] Has Confidence Ceiling declaration
- [ ] Has Empty Output Permission
- [ ] Has Layered Extraction (if extraction prompt)
- [ ] Has Output Schema specification
- [ ] Temperature appropriate for stage
- [ ] No leading questions that imply facts

### For API Routes

- [ ] Proper request/response schemas
- [ ] Error handling present
- [ ] Auth dependency included
- [ ] Rate limiting applied
- [ ] Follows REST conventions

### For Celery Tasks

- [ ] Proper task decorator
- [ ] Retry configuration
- [ ] Error handling
- [ ] State updates
- [ ] Returns expected type

---

## Output Format

```markdown
## File Review: [path/to/file.py]

**File Type:** [Model / Stage / Prompt / Route / Task / Other]
**Review Date:** [timestamp]

---

### Checklist Results

| Check | Status | Notes |
|-------|--------|-------|
| Type hints | ✅/❌ | [notes] |
| Docstrings | ✅/❌ | [notes] |
| Error handling | ✅/❌ | [notes] |
| Spec alignment | ✅/❌ | [notes] |
| [criteria...] | ✅/❌ | [notes] |

---

### Issues Found

1. **[Issue Type]:** [Description]
   - Location: line [N]
   - Severity: High/Medium/Low
   - Fix: [what to do]

2. **[Issue Type]:** [Description]
   - Location: line [N]
   - Severity: High/Medium/Low
   - Fix: [what to do]

---

### Spec Comparison

**Expected (from spec):**
```python
[relevant spec snippet]
```

**Actual (in file):**
```python
[relevant file snippet]
```

**Gaps:**
- [gap 1]
- [gap 2]

---

### Recommendation

**KEEP** — File meets spec, no changes needed.

OR

**MODIFY** — File mostly correct, specific changes needed:
1. [change 1]
2. [change 2]

OR

**REWRITE** — File significantly diverges from spec:
- [reason 1]
- [reason 2]
Recommend starting fresh from spec.

---

### If Modifying, Specific Changes

```python
# Line [N]: Change from
[old code]

# To
[new code]
```
```

---

## When to Use

- Phase 0.5: Reviewing existing semantic code
- Before integrating any existing code
- When unsure if code matches spec
- After major refactoring

---

## Notes

- Be thorough — missing issues cause problems later
- Check against IMPLEMENTATION_PLAN.md models
- Check against architecture rules
- When in doubt, recommend MODIFY over KEEP
