# ThinkingConfig & Thinking Mode Configuration Research
**Research Date:** 2026-01-18
**Research Focus:** google-genai Python SDK thinking mode configuration
**Status:** COMPLETE

---

## Executive Summary

The google-genai Python SDK (v0.x+) provides thinking mode configuration via `ThinkingConfig` within `GenerateContentConfig`. The SDK uses **snake_case field names** (`thinking_budget`, `thinking_level`, `include_thoughts`), NOT camelCase. Gemini 2.5 and 3 series have different thinking configuration approaches.

**Critical Finding:** The current SDK implementation has two distinct thinking configuration modes:
- **Gemini 2.5 series:** Use `thinking_budget` (token count, 0-32768 range)
- **Gemini 3 series:** Use `thinking_level` (categorical: low/medium/high/minimal)

---

## ThinkingConfig Field Names (CORRECT)

### Python SDK (snake_case)

| Field | Type | Purpose | Values/Range |
|-------|------|---------|--------------|
| `thinking_budget` | int | Token count for thinking (Gemini 2.5) | 0-32768 (model dependent) |
| `thinking_level` | str | Reasoning depth level (Gemini 3) | "minimal", "low", "medium", "high" |
| `include_thoughts` | bool | Include thought summaries in output | true/false |

**NOT** `budget_tokens` or `budgetTokens` — it is `thinking_budget`.

### Model-Specific Behavior

#### Gemini 2.5 Pro
- **Minimum thinking budget:** 128 tokens
- **Maximum thinking budget:** Model dependent (typically 24576-32768)
- **Can be disabled:** No. Setting to 0 disables thinking but thinking_budget still must be set if using thinking at all
- **Default:** Thinking ON by default
- **Dynamic thinking:** Set `thinking_budget=-1` for automatic token allocation (capped at 8,192)

#### Gemini 2.5 Flash
- **Minimum thinking budget:** 0 tokens (can disable)
- **Maximum thinking budget:** 24,576 tokens
- **Default:** Thinking ON by default
- **Dynamic thinking:** Set `thinking_budget=-1`

#### Gemini 3 Pro
- **Uses:** `thinking_level` parameter
- **Options:** "low", "high"
- **Thinking:** ALWAYS ON, cannot be disabled
- **Dynamic thinking:** Not applicable

#### Gemini 3 Flash
- **Uses:** `thinking_level` parameter
- **Options:** "minimal", "low", "medium", "high"
- **Thinking:** ALWAYS ON

---

## Correct Usage Patterns

### Pattern 1: Gemini 2.5 Pro with Thinking Budget

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=10000,           # Token count
        include_thoughts=True            # Include thought summaries
    ),
    temperature=0.2,
    max_output_tokens=2000
)

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents="Your prompt here",
    config=config
)
```

### Pattern 2: Gemini 3 Pro with Thinking Level

```python
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_level="high",           # Categorical level (NOT budget)
        include_thoughts=True            # Include thought summaries
    ),
    temperature=0.2,
    max_output_tokens=2000
)

response = client.models.generate_content(
    model="gemini-3-pro-preview",
    contents="Your prompt here",
    config=config
)
```

### Pattern 3: Dynamic Thinking (Automatic Budget)

```python
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=-1,              # Dynamic thinking (auto up to 8,192 tokens)
        include_thoughts=True
    )
)
```

### Pattern 4: Disable Thinking on Gemini 2.5 Flash

```python
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=0                # Disables thinking
    )
)
```

---

## Recent SDK Changes & Breaking Changes

### Version-Specific Notes

1. **ThinkingConfig Interface Changes (2025-2026)**
   - Thinking level support added for Gemini 3 models
   - `include_thoughts` parameter added for accessing thought summaries
   - Thought summaries feature added for 2.5 Pro and Flash

2. **Known Issues & Workarounds**
   - **Issue #782:** Thinking models unreliable when `max_output_tokens` set (may ignore thinking budget)
     - Workaround: Set `max_output_tokens` conservatively or omit if possible
   - **Issue #1103:** No thinking budget support in batch request API yet
     - Workaround: Use streaming/non-batch generate_content calls for thinking

3. **Thinking with Constraints**
   - Setting `thinking_level` with Gemini 2.5 models returns error
   - Setting `thinking_budget` with Gemini 3 models may be ignored (use `thinking_level` instead)
   - The `include_thoughts` field works across both 2.5 and 3 series

4. **Recent Additions**
   - Minimal thinking level added for Gemini 3 Flash
   - Dynamic thinking (-1) properly supported for both 2.5 and 3 series
   - Thought summaries now synthesized with headers, relevant details, and tool calls

---

## Configuration Checklist

When setting up thinking mode:

- [ ] Confirm model version (2.5 vs 3)
- [ ] Use `thinking_budget` for Gemini 2.5 series
- [ ] Use `thinking_level` for Gemini 3 series
- [ ] **Do NOT mix** `thinking_budget` and `thinking_level`
- [ ] Set `include_thoughts=True` if thought summaries needed
- [ ] For 2.5 Pro: respect minimum budget of 128 tokens
- [ ] For dynamic thinking: use `thinking_budget=-1`
- [ ] Be aware: `max_output_tokens` may affect thinking budget behavior
- [ ] Avoid batch API for thinking-based requests (use streaming/regular calls)

---

## Unresolved Questions

1. **Exact field name deprecation timeline:** When will camelCase (`thinkingBudget`) be fully deprecated in favor of snake_case (`thinking_budget`)? Current SDK uses snake_case but docs may reference both.

2. **Batch API thinking support:** When will thinking budget be supported in Batch API? Issue #1103 suggests this is planned but timeline unclear.

3. **Max output tokens interaction:** What is the exact behavior when both `thinking_budget` and `max_output_tokens` are set? Documentation suggests potential issues but specifics unclear.

4. **Fallback for unsupported models:** If a model doesn't support thinking mode and user passes ThinkingConfig, does the API gracefully ignore it or error?

---

## Sources

- [Google Gen AI SDK Documentation](https://googleapis.github.io/python-genai/)
- [Gemini API Thinking Documentation](https://ai.google.dev/gemini-api/docs/thinking)
- [Vertex AI Thinking Documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/thinking)
- [python-genai GitHub Releases](https://github.com/googleapis/python-genai/releases)
- [python-genai CHANGELOG](https://github.com/googleapis/python-genai/blob/main/CHANGELOG.md)
- [Issue #782: Thinking Models with max_output_tokens](https://github.com/googleapis/python-genai/issues/782)
- [Issue #1103: No Thinking Budget in Batch API](https://github.com/googleapis/python-genai/issues/1103)
- [Gemini API Release Notes](https://ai.google.dev/gemini-api/docs/changelog)
- [Firebase AI Logic Thinking](https://firebase.google.com/docs/ai-logic/thinking)
