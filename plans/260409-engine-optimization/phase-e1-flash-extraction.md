---
phase: E-1
title: "Flash Extraction Swap"
status: pending
effort: 30min
risk: low
---

# E-1: Flash Extraction Swap

**What:** Change semantic extraction from Gemini 2.5 Pro to Gemini 2.5 Flash.
**Why:** Flash is 3x faster and 8x cheaper. Extraction is structured data-out-of-text — not a reasoning task. Flash benchmarks equal to Pro on extraction/OCR.
**Risk:** Low. Source isolation preserved. Same JSON schema. Same prompt guardrails.

## Changes

### 1. `backend/pipeline/stages/semantic_extraction.py` (line ~463)
Pass `model="gemini-2.5-flash"` to the `generate_json()` call:

```python
# Current (line 463):
response = gemini_client.generate_json(
    prompt=prompt,
    system_message=SEMANTIC_EXTRACTION_ROLE,
    response_schema=SemanticExtractionSchema,
)

# New:
response = gemini_client.generate_json(
    prompt=prompt,
    system_message=SEMANTIC_EXTRACTION_ROLE,
    response_schema=SemanticExtractionSchema,
    model="gemini-2.5-flash",
)
```

### 2. `backend/config.py` — add configurable model setting
```python
semantic_extraction_model: str = Field(
    default="gemini-2.5-flash",
    alias="SEMANTIC_EXTRACTION_MODEL",
    description="Model for per-source semantic extraction (flash recommended for speed)"
)
```

Then use `settings.semantic_extraction_model` in the extraction call so it's env-configurable.

### 3. `.env.example` — document the new setting
```
SEMANTIC_EXTRACTION_MODEL=gemini-2.5-flash
```

## What stays on Pro
- Gap analysis + synthesis (cross-source reasoning)
- Creator Brief generation (creative output)
- These still use `generate_json()` default = `gemini-2.5-pro`

## Tests
- Run existing extraction tests — should pass (same schema, different model)
- Verify cost tracking reflects flash pricing

## Success Criteria
- Extraction calls use Flash
- Same extraction quality (same JSON schema validated)
- All existing tests pass
