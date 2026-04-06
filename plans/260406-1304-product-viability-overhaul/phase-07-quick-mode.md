# Phase 07: Quick Mode

## Context Links
- [Brainstorm -- Quick Mode](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#idea-3-quick-mode-openclaw-pattern-productized)
- [Technical Validation](../../plans/reports/researcher-260406-1233-brainstorm-validation.md#claim-4-quick-mode--single-gemini-call-for-all-sources)
- [Architecture Rules](../../.claude/rules/architecture.md) -- Rule 1: Source Isolation (Full mode only)
- Worker: `backend/worker.py`
- Quick brief stage exists: `backend/pipeline/stages/quick_brief_stage.py`

## Overview
- **Priority:** P2 (Phase 1 -- Product Feel)
- **Status:** pending
- **Effort:** 1-2 weeks
- **Depends on:** Phase 00
- **Description:** Add Quick mode -- single Gemini call with source labels, 30-60s turnaround, 3-5 source cap. Produces Research Brief only (no per-source isolation). Free tier default. Architecture Rule 1 (source isolation) applies ONLY to Full mode.

## Key Insights
- Quick = free tier / first-time experience. Full = paid tier value.
- `quick_brief_stage.py` already exists -- may contain partial implementation
- Source labels ("SOURCE_1: ...", "SOURCE_2: ...") maintain basic attribution without isolation
- Gemini Flash 1M context easily fits 5 transcripts x 10K tokens = 50K tokens
- Quality degrades at 260K+ tokens. Hard cap total input.
- Confidence ceiling for Quick mode: MEDIUM max (never HIGH)
- Output: Research Brief only. No Doc 0/1/3 in Quick mode.
- Quality label: "Quick Research -- citations may be approximate"

## Requirements

### Functional
- New pipeline path: Quick mode selected at job creation
- Single Gemini Flash call with all sources labeled in prompt
- Source cap: 3-5 sources max. Error if more provided.
- Output: Research Brief (Doc 2 equivalent) with source labels
- Inline citations use source labels: `[Source 1 - Creator Name]`
- "Untold Angle" section included (gap identification in same call)
- Sonnet editorial pass applied (same as Full mode)
- Completion time: 30-60 seconds
- Quality label visible: "Quick Research -- citations approximate"

### Non-Functional
- Total input token cap: 200K tokens (prevent quality degradation)
- Confidence: MEDIUM max for all key points
- No quote verification (skip validation stage)

## Architecture

### Quick Mode Pipeline
```
Input (topic + 3-5 URLs)
  -> Source acquisition (parallel transcript/article fetch)
  -> Single Gemini Flash call:
     - Labeled sources in prompt
     - Extract key points, themes, gaps in ONE response
     - Source attribution via labels
  -> Document assembly (Brief only)
  -> Sonnet editorial pass (async)
  -> Done
```

### Prompt Structure (Single Call)
```
You are a research analyst. Analyze these sources and produce a research brief.

=== SOURCE_1: "Video Title" by Creator Name ===
[transcript text]

=== SOURCE_2: "Article Title" from Website ===
[article text]

=== SOURCE_3: ... ===

INSTRUCTIONS:
1. For each key point, cite the source: [SOURCE_1], [SOURCE_2], etc.
2. Identify themes across sources
3. Identify what's MISSING (the untold angle)
4. Maximum confidence: MEDIUM (sources not independently verified)

OUTPUT SCHEMA: { key_points: [...], themes: [...], gaps: [...], semantic_core: "..." }
```

### Differences from Full Mode
| Aspect | Quick | Full |
|--------|-------|------|
| LLM calls | 1 (+ 1 Sonnet) | N+1 (+ 1 Sonnet) |
| Source isolation | No (labeled in single call) | Yes (separate calls) |
| Validation | Skip | Full verification |
| Confidence max | MEDIUM | Per-mode ceiling |
| Documents | Brief only | Brief + Doc 0/1/3 |
| Source cap | 3-5 | Unlimited |
| Quality label | "Quick -- approximate" | Full confidence |

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/worker.py` | Add Quick mode pipeline path (separate from mixed-input flow) |
| `backend/pipeline/stages/quick_brief_stage.py` | Verify/update existing implementation |
| `backend/pipeline/context.py` | Add `is_quick_mode` flag to `PipelineContext` |
| `backend/app/routes/jobs_routes.py` | Accept `mode: "quick"` in create job payload |
| `backend/models/` | Add Quick mode schemas if needed |
| `frontend/components/dashboard/single-screen-input.tsx` | Mode toggle (Quick/Full) |
| `frontend/components/job-detail-v2/hero-document-view.tsx` | Show quality label for Quick mode |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/pipeline/stages/quick_extraction.py` | Single-call extraction with source labels | ~120 |
| `backend/pipeline/prompts/quick_mode_prompt.py` | Labeled-source prompt builder | ~80 |
| `frontend/components/common/quality-label.tsx` | "Quick Research" badge/banner | ~30 |

### Check first
- `backend/pipeline/stages/quick_brief_stage.py` -- what's already implemented?

## Implementation Steps

### Task 7.1: Audit existing quick_brief_stage.py
1. Read `backend/pipeline/stages/quick_brief_stage.py` thoroughly
2. Determine what's already implemented vs what's needed
3. Decide: extend existing or create new `quick_extraction.py`

### Task 7.2: Create Quick mode prompt
1. Create `backend/pipeline/prompts/quick_mode_prompt.py`
2. `build_quick_mode_prompt(sources: list[SourceData], topic: str) -> str`
3. Format each source with label: `=== SOURCE_{N}: "{title}" by {creator} ===`
4. Include all 5 prompt guardrail components (Architecture Rule 7):
   - Source Identity Lock (adapted for multi-source)
   - Confidence ceiling: MEDIUM
   - Empty output permission
   - Extraction instructions (simplified, no layered extraction)
   - Output schema (key_points, themes, gaps, semantic_core)
5. Total input token estimation: log warning if > 200K

### Task 7.3: Create Quick extraction stage
1. Create `backend/pipeline/stages/quick_extraction.py`
2. `stage_quick_extraction(ctx: PipelineContext) -> PipelineContext`:
   - Validate source count <= 5
   - Build prompt with `build_quick_mode_prompt()`
   - Single Gemini Flash call at temperature 0.2
   - Parse response into ctx fields: `key_points`, `themes`, `identified_gaps`, `semantic_core`
   - All key points get confidence capped at MEDIUM
   - Map SOURCE_N labels to actual source_ids
3. Skip: validation stage, per-source extraction

### Task 7.4: Create Quick mode pipeline in worker
1. In `backend/worker.py`, add new pipeline function:
   ```python
   def _run_quick_mode_job(job_id: str, config: dict, user_id: str):
       ctx = PipelineContext(job_id=job_id, is_quick_mode=True)
       # 1. Source acquisition (parallel)
       # 2. Quick extraction (single call)
       # 3. Document assembly (Brief only)
       # 4. Completion
       # 5. Dispatch editorial pass (async)
   ```
2. In main task dispatch, check `config.pipeline == "quick"` and route accordingly
3. Add progress updates with appropriate stage names

### Task 7.5: Update job creation API
1. In `backend/app/routes/jobs_routes.py`, `create_job_endpoint()`:
   - Accept `pipeline: "quick" | "full"` (default "full")
   - If quick: validate source count <= 5
   - Store pipeline mode in job config
2. Frontend already has mode toggle from Phase 01

### Task 7.6: Frontend Quick mode handling
1. In `frontend/components/dashboard/single-screen-input.tsx`:
   - Mode toggle already created in Phase 01
   - If Quick mode selected and > 5 sources, show error
2. Create `frontend/components/common/quality-label.tsx`:
   - "Quick Research -- citations may be approximate" badge
   - Shown on hero doc when `job.pipeline === "quick"`
3. In `frontend/components/job-detail-v2/hero-document-view.tsx`:
   - Show quality label at top for Quick mode jobs
   - Hide "Generate Script/Blog" buttons for Quick mode (Brief only)

### Task 7.7: Test
1. Backend: unit test Quick prompt builder with 3 sources
2. Backend: unit test source label parsing in response
3. Backend: integration test Quick pipeline end-to-end
4. Manual: create Quick mode job with 3 YouTube URLs, verify < 60s completion
5. Manual: verify citations use source labels correctly
6. Manual: verify MEDIUM confidence cap on all outputs
7. `pytest backend/tests/ -v` && `npm run build`

## Todo Checklist
- [ ] 7.1 Audit existing `quick_brief_stage.py`
- [ ] 7.2 Create Quick mode prompt with source labels
- [ ] 7.3 Create Quick extraction stage (single Gemini call)
- [ ] 7.4 Create Quick mode pipeline path in worker
- [ ] 7.5 Update job creation API to accept pipeline mode
- [ ] 7.6 Frontend: quality label, source count validation
- [ ] 7.7 Test: unit, integration, manual timing

## Success Criteria
- Quick mode completes in 30-60 seconds (vs 2-3 minutes Full)
- Output includes key points with source labels
- "Untold Angle" section present
- Confidence never exceeds MEDIUM
- Source count capped at 5
- Quality label clearly visible

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Gemini cross-source attribution errors | HIGH | Source labels in prompt. Test with diverse sources. Accept "approximate." |
| Quality too low vs Full mode | MEDIUM | A/B test before shipping. Quality label sets expectations. |
| Users bypass 5-source cap | LOW | Backend validation. Frontend validation. |
| Quick mode cannibalizes Full mode usage | LOW | Quick = Free tier only. Full = Pro value prop. |

## Security Considerations
- Same input validation as Full mode
- Source count limit enforced server-side (not just client)
- Token count validated server-side to prevent abuse
