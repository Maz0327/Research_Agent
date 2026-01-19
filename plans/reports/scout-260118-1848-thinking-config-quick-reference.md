# Gemini Thinking Config - Quick Reference

## Complete Reference Table

| File | Location | Type | Context | Status | SDK |
|------|----------|------|---------|--------|-----|
| `backend/integrations/gemini_client.py` | Lines 316-377 | Method | `generate_with_thinking()` - Main implementation | CURRENT | new google-genai |
| `backend/integrations/gemini_client.py` | Line 340-341 | Code | `types.ThinkingConfig(thinking_budget=...)` | CURRENT | new google-genai |
| `backend/integrations/gemini_client.py` | Line 556 | Comment | Reference to thinking in `generate_json()` | CURRENT | N/A |
| `backend/integrations/gemini_client.py` | Lines 1833-1845 | Function | `plan_with_gemini()` wrapper | CURRENT | new google-genai |
| `backend/integrations/gemini_client.py` | Line 1842 | Code | `thinking_budget=2048` in wrapper | CURRENT | new google-genai |
| `backend/scripts/test_gemini_video_extraction.py` | Lines 89-91 | Import | `from google.genai import types` | CURRENT | new google-genai |
| `.claude/skills/ai-multimodal/scripts/gemini_batch_process.py` | Lines 51-57 | Import | `from google.genai import types` | CURRENT | new google-genai |
| `plans/implementation-tasks-research-validated-stack.md` | Lines 139-154 | Example | Old SDK pattern example (for reference) | OUTDATED | old genai SDK |

## Budget Usage Matrix

```
generate_with_thinking()
  ├─ Default thinking_budget: 1024 tokens
  ├─ Model: gemini-2.5-flash (specified by caller)
  └─ Returns: dict with text, thinking, model, cost

plan_with_gemini()
  ├─ thinking_budget: 2048 tokens (higher for planning)
  ├─ Model: gemini-2.5-flash (hardcoded)
  └─ Returns: str (text only)
```

## Configuration Patterns

### Current (Production)
```python
config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    thinking_config=types.ThinkingConfig(
        thinking_budget=thinking_budget
    ),
)
```

### Outdated (Do Not Use)
```python
generation_config={
    "thinking_config": {"thinking_budget": thinking_budget}
}
```

## Cost Estimation
Thinking tokens counted in output:
```python
output_tokens = len(text.split()) * 1.3 + thinking_budget
```

## Issues Found
- None - SDK is correctly implemented
- Optional: Add input validation for thinking_budget (max 64000)
- Optional: Update documentation examples to match current SDK

