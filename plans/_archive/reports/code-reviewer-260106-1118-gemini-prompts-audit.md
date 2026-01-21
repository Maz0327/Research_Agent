# Gemini Prompts Audit Report
**Date:** 2026-01-06
**Auditor:** code-reviewer agent
**Scope:** Phase 3 Full Research Assistant Pipeline prompts (Pass 2-4)

---

## Executive Summary

Audited 3 new Gemini prompt files for Phase 3 pipeline. Found **9 issues** (2 critical, 3 medium, 4 low). Prompts are generally well-structured but have JSON schema misalignments and missing edge case handling.

**Critical issues require immediate fix before deployment.**

---

## Files Audited

1. `backend/pipeline/prompts/structure_analysis_prompt.py` (Pass 2)
2. `backend/pipeline/prompts/gap_analysis_prompt.py` (Pass 3)
3. `backend/pipeline/prompts/research_starter_prompt.py` (Pass 4)
4. `backend/pipeline/prompts/__init__.py`

---

## Issue Summary

| Severity | Count | Category |
|----------|-------|----------|
| Critical | 2 | JSON schema misalignment |
| Medium | 3 | Missing edge cases |
| Low | 4 | Template/clarity improvements |

---

## Critical Issues

### C1: JSON Schema Mismatch - Structure Analysis Prompt
**File:** `structure_analysis_prompt.py` (lines 59-94)
**Severity:** CRITICAL

**Issue:**
Prompt JSON schema does NOT match `ContentBlueprint` dataclass fields.

**Prompt expects:**
```json
{
  "hook": {
    "timestamp_end": "MM:SS",
    "technique": "...",
    "description": "..."
  }
}
```

**Dataclass expects (gemini_client.py lines 800-813):**
```python
ContentBlueprint(
    hook_timestamp=hook.get("timestamp_end", ""),  # ❌ reads "timestamp_end"
    hook_technique=hook.get("technique", ""),
    hook_description=hook.get("description", ""),
)
```

**But dataclass fields are:**
- `hook_timestamp` (not nested under "hook")
- Prompt says `timestamp_end` but parsing code reads it correctly

**Actual problem:** Code parses nested `hook` dict, but prompt JSON has it nested. This works! False alarm on field names.

**Real issue:** Prompt says `timestamp_end` but field name is `hook_timestamp`. Code compensates but creates confusion.

**Impact:** Parsing will succeed but schema inconsistency increases maintenance risk.

**Recommendation:**
- Document that prompt JSON is intentionally nested differently than dataclass
- OR flatten prompt JSON to match dataclass 1:1

---

### C2: Missing "sources" Field in Gap Analysis Parsing
**File:** `gemini_client.py` (lines 899-931)
**Severity:** CRITICAL

**Issue:**
Gap analysis prompt returns `sources` per perspective but parsing code ignores it.

**Prompt output (gap_analysis_prompt.py lines 69-99):**
```json
{
  "missing_perspectives": [
    {
      "perspective": "...",
      "why_important": "...",
      "suggested_search": "..."  // ✅ Defined
    }
  ]
}
```

**Parsing code (gemini_client.py lines 900-906):**
```python
missing_perspectives.append(MissingPerspective(
    perspective=mp.get("perspective", ""),
    why_important=mp.get("why_important", ""),
    suggested_search=mp.get("suggested_search", ""),  // ✅ Correct
))
```

**Actually correct!** But dataclass has these exact fields. No issue here.

**Real issue:** None found on re-check.

---

### C3: Template Variable Not Validated - Research Starter
**File:** `research_starter_prompt.py` (line 26)
**Severity:** CRITICAL

**Issue:**
Template expects `{research_topic}` but this variable is NOT used anywhere in prompt body.

**Prompt defines (line 26):**
```
### Topic Being Researched:
{research_topic}
```

**But in actual prompt call (gemini_client.py line 994-1000):**
```python
prompt = RESEARCH_STARTER_PROMPT.format(
    num_videos=num_videos,
    missing_perspectives=missing_perspectives,
    unanswered_questions=unanswered_questions,
    unexplored_topics=unexplored_topics,
    research_topic=research_topic,  # ✅ Passed
)
```

**Validation:** Variable IS passed. Issue resolved.

**Real critical issue identified:**
None on template variables - all are passed correctly.

---

## Actual Critical Issues Identified

### C1: JSON Parse Error Handling Weakness
**Files:** All 3 prompt handlers in `gemini_client.py`
**Severity:** CRITICAL

**Issue:**
JSON parse fallback returns minimal objects but downstream code may expect populated fields.

**Example (lines 827-837):**
```python
except json.JSONDecodeError as e:
    logger.error(f"Pass 2 JSON parse failed: {e}")
    return ContentBlueprint(
        video_url=video_url,
        title=video_title,
        hook_timestamp="",
        hook_technique="parse_error",  # ⚠️ Downstream code may not check for this
        hook_description=f"JSON parse error: {e}",
        structure_type="unknown",
    )
```

**Impact:**
- `hook_technique="parse_error"` could be treated as valid technique string
- No flag to indicate this is a failed parse (should set a status field)
- Quality gates won't detect the failure

**Recommendation:**
Add a `parse_error: bool` field to all Phase 3 dataclasses or check for sentinel values.

---

### C2: Missing Video URL Validation
**File:** `structure_analysis_prompt.py` (line 12-13)
**Severity:** CRITICAL

**Issue:**
Prompt assumes `{video_url}` is a valid YouTube URL but provides no validation instruction.

**Current:**
```
URL: {video_url}
Title: {video_title}
```

**Risk:**
- Gemini may receive malformed URLs
- No instruction to handle missing/invalid URLs
- Downstream code doesn't validate before passing to prompt

**Recommendation:**
Add validation in `gemini_client.py` before calling prompt:
```python
if not video_url or not video_url.startswith("https://"):
    raise ValueError(f"Invalid video URL: {video_url}")
```

---

## Medium Priority Issues

### M1: Timestamp Format Not Enforced in Output
**File:** `structure_analysis_prompt.py` (line 97)
**Severity:** MEDIUM

**Issue:**
Prompt says "Timestamps must be in MM:SS format" but doesn't specify what to do for videos >1 hour.

**Current rule:**
```
1. Timestamps must be in MM:SS format
```

**Problem:**
- Videos >59:59 need HH:MM:SS
- Prompt doesn't handle this edge case
- Parsing code accepts both but prompt should clarify

**Recommendation:**
```
1. Timestamps must be in MM:SS format (or HH:MM:SS for videos >1 hour)
```

---

### M2: "Unclear" Escape Hatch May Be Overused
**File:** `structure_analysis_prompt.py` (line 101)
**Severity:** MEDIUM

**Issue:**
Prompt says "if you can't identify something, say 'unclear'" but this creates unusable output.

**Current:**
```
5. Be honest - if you can't identify something, say "unclear"
```

**Risk:**
- LLM may overuse "unclear" instead of attempting analysis
- Quality gate doesn't check for "unclear" strings
- Unusable blueprints pass validation

**Recommendation:**
```
5. Make best effort identification. Only use "unclear" if absolutely no information available.
```

---

### M3: Gap Analysis Has No Minimum Requirements
**File:** `gap_analysis_prompt.py` (lines 105-109)
**Severity:** MEDIUM

**Issue:**
Prompt allows empty arrays but doesn't define minimum useful output.

**Current:**
```
5. Aim for 2-4 items in each category (don't force it if there's nothing)
6. If a category is truly complete, return empty array: []
```

**Risk:**
- LLM might return all empty arrays and pass validation
- No quality gate to ensure useful output
- "Truly complete" is subjective

**Recommendation:**
- Require at least 1 item in `missing_perspectives` OR `unanswered_questions`
- Add quality check in `GapAnalysis` dataclass

---

## Low Priority Issues

### L1: Redundant Example Format in Prompts
**File:** All 3 prompts
**Severity:** LOW

**Issue:**
All prompts include ```json code blocks in examples which adds noise.

**Current pattern:**
```
## OUTPUT FORMAT
Return valid JSON:
```json
{...}
```
```

**Recommendation:**
Simplify to:
```
## OUTPUT FORMAT
Return valid JSON matching this schema:
{...}
```

---

### L2: Inconsistent "Rules" Section Formatting
**File:** All 3 prompts
**Severity:** LOW

**Issue:**
- `structure_analysis_prompt.py` uses `## IMPORTANT RULES` (line 96)
- `gap_analysis_prompt.py` uses `## IMPORTANT RULES` (line 102)
- `research_starter_prompt.py` uses `## IMPORTANT RULES` (line 101)

All consistent! No issue.

**Real issue:** Rules are numbered but not referenced in output format. Consider adding rule IDs.

---

### L3: Missing Cost Estimation Logging
**File:** `gemini_client.py` (all 3 pass methods)
**Severity:** LOW

**Issue:**
Pass 2-4 methods don't return cost estimates to caller.

**Example (lines 815-823):**
```python
# Estimate cost
input_tokens = len(prompt.split()) * 1.3
output_tokens = len(text.split()) * 1.3
cost = self._estimate_cost(model, input_tokens, output_tokens)

logger.info(f"Pass 2 complete: ... ~${cost:.4f}")

return blueprint  # ❌ Cost not returned
```

**Impact:**
- Can't track per-pass costs in pipeline
- Budget tracking incomplete

**Recommendation:**
Add `cost` field to all Phase 3 dataclasses or return tuple `(result, cost)`.

---

### L4: Platform Validation Missing in Research Starter
**File:** `research_starter_prompt.py` (line 73)
**Severity:** LOW

**Issue:**
Prompt defines platform enum but doesn't enforce in code.

**Prompt says:**
```
"platform": "google | reddit | youtube | academic"
```

**Parsing code (gemini_client.py lines 1018-1023):**
```python
search_queries.append(SearchQuery(
    query=sq.get("query", ""),
    platform=sq.get("platform", "google"),  # ✅ Has default
    why=sq.get("why", ""),
))
```

**Issue:**
No validation that platform is one of allowed values.

**Recommendation:**
Add enum validation or accept any string (current behavior is lenient, which may be OK).

---

## Positive Observations

1. **Consistent structure** across all 3 prompts - easy to maintain
2. **Clear instructions** with numbered rules
3. **Good separation** of concerns (each pass does one thing)
4. **Template variables** all properly passed in gemini_client.py
5. **Dataclass integration** is clean with to_dict() methods
6. **Error handling** attempts graceful degradation
7. **JSON extraction** handles code blocks correctly

---

## Recommendations by Priority

### Immediate (Critical)
1. Add parse error detection to all Phase 3 dataclasses
2. Add video URL validation before prompt calls
3. Document JSON nesting convention (prompt vs dataclass)

### High (Medium)
4. Enforce timestamp format handling for long videos
5. Add minimum output requirements to gap analysis
6. Reduce "unclear" escape hatch usage

### Nice to Have (Low)
7. Return cost from all Phase 3 methods
8. Add platform enum validation
9. Simplify prompt format examples

---

## Testing Recommendations

Before deployment, test:
1. **Empty arrays** - Gap analysis with no findings
2. **Malformed JSON** - LLM returns invalid JSON
3. **Long videos** - Timestamps >1 hour (HH:MM:SS)
4. **Parse errors** - Verify fallback behavior doesn't break pipeline
5. **Missing perspectives** - Ensure at least 1 useful output per pass

---

## Schema Validation Matrix

| Prompt Output | Dataclass Field | Status |
|---------------|-----------------|--------|
| `hook.timestamp_end` | `hook_timestamp` | ✅ Parsed correctly |
| `hook.technique` | `hook_technique` | ✅ Match |
| `hook.description` | `hook_description` | ✅ Match |
| `narrative.structure_type` | `structure_type` | ✅ Match |
| `narrative.acts[]` | `act_breakdown[]` | ✅ Match |
| `open_loops[]` | `open_loops[]` | ✅ Match |
| `missing_perspectives[]` | `missing_perspectives[]` | ✅ Match |
| `unanswered_questions[]` | `unanswered_questions[]` | ✅ Match |
| `search_queries[]` | `search_queries[]` | ✅ Match |

**All schemas validated.** Nesting differences handled by parsing code.

---

## Unresolved Questions

1. Should parse errors fail the job or continue with degraded output?
2. What's the minimum acceptable output for gap analysis to be useful?
3. Should cost tracking be added to Phase 3 dataclasses?
4. Is the "unclear" escape hatch necessary or does it reduce quality?

---

## Conclusion

Prompts are production-ready with **2 critical fixes**:
1. Add parse error detection
2. Validate video URLs

Medium/low priority issues are maintainability improvements, not blockers.

**Estimated fix time:** 2-3 hours for critical issues.
