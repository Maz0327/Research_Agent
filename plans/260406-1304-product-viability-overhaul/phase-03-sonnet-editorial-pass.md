# Phase 03: Sonnet 4.6 Editorial Pass

## Context Links
- [Brainstorm -- Sonnet Editorial](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#idea-2-sonnet-46-editorial-pass-creative-editorproducer)
- [Technical Validation](../../plans/reports/researcher-260406-1233-brainstorm-validation.md#claim-3-sonnet-46-editorial-pass)
- Backend Anthropic integration: `backend/integrations/` (check for existing `anthropic_client.py`)
- Requirements: `anthropic>=0.39.0` already in `requirements.txt`

## Overview
- **Priority:** P1 (MVP -- quality differentiator)
- **Status:** pending
- **Effort:** 3-5 days
- **Depends on:** Phase 00
- **Description:** Add Sonnet 4.6 as editorial pass on Research Brief (Doc 2). Draft by Gemini, polish by Sonnet. Background async -- user gets draft immediately, polished version replaces it ~15-20s later.

## Key Insights
- Multi-model draft->edit is a proven pattern: 10-30% speed improvement, 15-20% quality gain
- Cost: ~$0.045 per editorial pass (5K token script, ~2K output)
- Hallucination risk LOW: Sonnet only sees Gemini's output, can't access original sources
- Key constraint: "preserve all facts/quotes/citations, improve flow/readability, NEVER add information"
- Post-edit fact validation: diff factual claims before/after to catch additions

## Requirements

### Functional
- Sonnet 4.6 editorial pass applied to Doc 2 (Research Brief) after assembly
- Same pattern available for Doc 5 (Script) and Doc 6 (Blog) when generated on-demand
- Background async: user sees Gemini draft immediately, polished version arrives ~15-20s later
- Version toggle in UI: "Draft" / "Polished" (or auto-replace with toast notification)
- Post-edit validation: compare factual claim count before/after, flag if Sonnet added new claims
- Cost tracking: editorial pass cost tracked in `cost_tracker.py`

### Non-Functional
- Editorial pass must NOT block pipeline completion
- If Sonnet call fails, draft version is final (graceful degradation)
- Prompt must enforce fact preservation strictly

## Architecture

### Two-Pass Flow
```
Pipeline completes -> Doc 2 (draft) stored -> User sees draft
                   -> Async Celery task: Sonnet editorial pass
                   -> Polished Doc 2 stored as new version
                   -> Frontend polls/SSE detects new version -> auto-update
```

### Backend Components
1. **AnthropicClient** -- wrapper for Sonnet 4.6 API calls (may already exist)
2. **Editorial prompt** -- strict fact-preservation instructions
3. **Fact validation** -- extract claim count before/after, compare
4. **Async task** -- Celery task triggered after pipeline completion

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/worker.py` | After `stage_10_completion`, dispatch async editorial task |
| `backend/pipeline/cost_tracker.py` | Add Sonnet 4.6 cost tracking (input/output tokens) |
| `backend/config/` or `backend/config.py` | Add `ANTHROPIC_API_KEY` config |
| `backend/pipeline/version_manager.py` | Use to store polished version as v2 of Doc 2 |
| `frontend/components/job-detail-v2/hero-document-view.tsx` | Show version indicator, handle version update |
| `frontend/components/job-detail-v2/version-selector.tsx` | Enable switching between draft/polished |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/integrations/anthropic_client.py` | Sonnet 4.6 API wrapper (if not existing) | ~80 |
| `backend/pipeline/stages/editorial_pass.py` | Sonnet editorial stage logic | ~120 |
| `backend/pipeline/prompts/editorial_prompt.py` | Editorial pass prompt with fact-preservation constraints | ~60 |
| `backend/pipeline/editorial_validator.py` | Pre/post edit fact-count comparison | ~50 |

### Check if exists first
- `backend/integrations/anthropic_client.py` -- may already exist since `anthropic>=0.39.0` is in requirements

## Implementation Steps

### Task 3.1: Create/verify AnthropicClient
1. Check if `backend/integrations/anthropic_client.py` exists
2. If not, create it:
   - `class AnthropicClient` with `generate_text(prompt, system, max_tokens, temperature) -> str`
   - Use `anthropic.Anthropic(api_key=...)` from config
   - Model: `claude-sonnet-4-6-20250514` (or latest Sonnet 4.6 model ID)
   - Error handling: retry once on rate limit, log and return None on failure
3. Add `ANTHROPIC_API_KEY` to `backend/config.py` settings
4. Add cost tracking: input_tokens * $3/1M + output_tokens * $15/1M

### Task 3.2: Create editorial prompt
1. Create `backend/pipeline/prompts/editorial_prompt.py`
2. Build prompt with:
   ```
   ROLE: You are a senior editorial producer reviewing research for a video creator.

   RULES (NON-NEGOTIABLE):
   1. PRESERVE every fact, quote, citation, source reference, and data point exactly as written
   2. PRESERVE all source_ids, timestamps, creator names in citations
   3. NEVER add new information, claims, or facts not in the original
   4. NEVER remove facts or data points
   5. IMPROVE: flow, readability, transitions, section headings, paragraph structure
   6. IMPROVE: clarity of complex explanations
   7. IMPROVE: remove redundancy, tighten language
   8. MAINTAIN: the original voice/tone if a voice profile is provided

   OUTPUT: Return the edited document in the same JSON structure as input.
   ```
3. Include original doc JSON as context
4. Optional: include voice profile from job config if available

### Task 3.3: Create editorial validator
1. Create `backend/pipeline/editorial_validator.py`
2. `validate_editorial_pass(original_doc: dict, edited_doc: dict) -> EditorialValidation`
3. Validation checks:
   - Count key_points before/after -- should be equal
   - Count source_ids referenced before/after -- should be equal
   - Count quotes before/after -- should be equal
   - If edited version has MORE claims than original -> reject, use original
   - If edited version has FEWER source references -> reject, use original
4. Return: `EditorialValidation(valid: bool, warnings: list[str], original_claims: int, edited_claims: int)`

### Task 3.4: Create editorial pass stage
1. Create `backend/pipeline/stages/editorial_pass.py`
2. `async_editorial_pass(job_id: str, doc_type: str, doc_content: dict) -> dict`
3. Flow:
   a. Build editorial prompt with `doc_content`
   b. Call `AnthropicClient.generate_text()` at temperature 0.3
   c. Parse response JSON
   d. Run `validate_editorial_pass(doc_content, edited_content)`
   e. If valid: store as new version via `version_manager`
   f. If invalid: log warning, keep original, store warning in job
   g. Track cost via `cost_tracker`

### Task 3.5: Wire into worker as async Celery task
1. In `backend/worker.py`, create new Celery task:
   ```python
   @app.task(name="editorial_pass", bind=True, max_retries=1)
   def task_editorial_pass(self, job_id: str, doc_type: str):
       ...
   ```
2. After `stage_10_completion` in the main pipeline task, dispatch:
   ```python
   task_editorial_pass.delay(job_id, "doc_2")
   ```
3. This runs AFTER the user already has their draft results
4. On completion, update job metadata: `editorial_status: "polished"`

### Task 3.6: Frontend version handling
1. In `frontend/components/job-detail-v2/hero-document-view.tsx`:
   - Check for latest version of Doc 2 via version_selector
   - If new version arrives (polished), show toast: "Polished version ready"
   - Auto-switch to polished version, or show toggle
2. In `frontend/components/job-detail-v2/version-selector.tsx`:
   - Add "Draft" / "Polished" labels for versions
   - Small badge indicating which version is displayed

### Task 3.7: Test
1. Backend: unit test editorial validator with sample before/after docs
2. Backend: integration test editorial pass with mocked Anthropic response
3. Manual: run full pipeline, verify draft appears immediately, polished version arrives ~15-20s later
4. Manual: verify polished version preserves all citations and facts
5. `pytest backend/tests/ -v`

## Todo Checklist
- [ ] 3.1 Create/verify `AnthropicClient` with Sonnet 4.6
- [ ] 3.2 Create editorial prompt with fact-preservation rules
- [ ] 3.3 Create editorial validator (claim count comparison)
- [ ] 3.4 Create editorial pass stage
- [ ] 3.5 Wire as async Celery task after pipeline completion
- [ ] 3.6 Frontend version handling (toast + auto-update)
- [ ] 3.7 Test: unit, integration, manual

## Success Criteria
- Doc 2 (Research Brief) gets Sonnet editorial pass automatically
- User sees draft immediately, polished version arrives background
- Polished version has SAME facts/citations as draft (validator confirms)
- If Sonnet fails, draft is shown (no error for user)
- Cost per editorial pass tracked: ~$0.045

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Sonnet adds hallucinated facts | MEDIUM | Editorial validator rejects if claim count increases. Strict prompt. |
| Sonnet strips voice styling | MEDIUM | Include voice profile in prompt. Test with varied inputs. |
| Anthropic API latency spikes | LOW | Async task with timeout. Draft is always available. |
| Cost overrun on high-volume | LOW | $0.045/pass is negligible. Track in cost_tracker. |

## Security Considerations
- `ANTHROPIC_API_KEY` stored in environment variables, never committed
- API key validated on startup in config
- No user data sent to Anthropic beyond research content (already public sources)
