---
phase: E-3
title: "Merge Gap Analysis + Synthesis"
status: pending
effort: 2-3h
risk: low-medium
---

# E-3: Merge Gap Analysis + Synthesis

**What:** Combine gap analysis and semantic synthesis into a single Gemini Pro call.
**Why:** Both stages consume the same cross-source context (all key points, themes, tensions). Two sequential Pro calls = ~16-30s. One call = ~8-15s.
**Risk:** Low-medium. Prompt needs careful engineering to produce both gap identification AND synthesis in one pass.

## Current Flow (worker.py lines 465-469)

```python
# Two separate stages, two separate Pro calls:
run_stage_with_recovery(stage_gap_analysis, ctx, "gap_analysis")        # ~8-15s
run_stage_with_recovery(stage_semantic_synthesis, ctx, "semantic_synthesis")  # ~8-15s
```

## New Flow

```python
# One merged stage, one Pro call:
run_stage_with_recovery(stage_gap_and_synthesis, ctx, "gap_and_synthesis")  # ~8-15s
```

## Changes

### 1. New file: `backend/pipeline/stages/gap_and_synthesis.py`
Merge the prompts from `gap_analysis.py` and `semantic_synthesis.py` into one stage.

**Prompt structure:**
```
You are analyzing research from multiple sources. Do TWO things:

PART 1 — GAP ANALYSIS:
Identify what's MISSING from this research. What questions remain unanswered?
What perspectives are absent? What contradictions exist?

PART 2 — SYNTHESIS:
Synthesize the findings into a cohesive research brief.
[existing synthesis prompt content]

Return JSON with both sections.
```

**Output schema** combines both:
```json
{
  "gaps": [...],           // from gap analysis
  "semantic_core": "...",  // from synthesis
  "themes": [...],         // from synthesis
  "tensions": [...],       // from synthesis
  "style_violations": []   // from synthesis style check
}
```

### 2. `backend/worker.py` — replace two stage calls with one
```python
# Replace lines 465-469:
update_job(job_id, stage="analysis_and_synthesis", progress_percent=50)
run_stage_with_recovery(stage_gap_and_synthesis, ctx, "gap_and_synthesis")
```

### 3. Keep old files for reference
Archive `gap_analysis.py` and `semantic_synthesis.py` to `backend/archive/` per repo rules (Rule 14: Archive, Don't Delete).

### 4. Preserve style enforcement
The synthesis stage has a style enforcement retry loop (lines 330-369 of semantic_synthesis.py). This MUST be preserved in the merged stage.

### 5. Preserve gap storage
Gap analysis stores results in `ctx.identified_gaps`. The merged stage must still populate this for downstream document assembly.

## Tests
- New tests for merged stage
- Verify gaps are still identified correctly
- Verify synthesis quality matches current
- Verify style enforcement still works

## Success Criteria
- One Pro call instead of two
- Same gap identification quality
- Same synthesis quality
- Style enforcement preserved
- `ctx.identified_gaps` still populated for doc assembly
