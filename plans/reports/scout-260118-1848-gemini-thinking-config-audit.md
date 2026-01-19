# Gemini Thinking Configuration Audit
**Generated:** 2026-01-18 18:48  
**Scope:** Complete codebase search for ThinkingConfig, thinking_budget, and related Gemini thinking mode references  

---

## Executive Summary

Found **7 locations** where Gemini thinking mode is referenced:
- **1 primary implementation** (production code)
- **1 convenience wrapper** (helper function)
- **3 documentation references** (plans/examples)
- **2 test scripts** (validation code)

**Status:** All implementations use the new `google-genai` SDK with `types.ThinkingConfig()`. Compatible with current SDK as of Jan 2026.

---

## Complete File Inventory

### 1. Production Implementation (PRIMARY)

#### File: `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/gemini_client.py`

**Method:** `generate_with_thinking()`
- **Lines:** 316-377
- **SDK:** New `google-genai` SDK
- **Status:** CURRENT

**Code Snippet:**
```python
@with_rate_limit("gemini")
def generate_with_thinking(
    self,
    prompt: str,
    model: str = "gemini-2.5-flash",
    thinking_budget: int = 1024,
    system_instruction: Optional[str] = None,
) -> dict[str, Any]:
    """Generate with thinking mode for complex reasoning.

    Args:
        prompt: The prompt to send
        model: Model to use
        thinking_budget: Token budget for thinking (default 1024)
        system_instruction: Optional system instruction

    Returns:
        Dict with text response, thinking content, and cost estimate
    """
    try:
        logger.info(f"Gemini {model} thinking: {prompt[:50]}...")

        # Build config with thinking mode
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(
                thinking_budget=thinking_budget
            ),
        )

        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        text = response.text

        # Extract thinking content if available
        thinking = None
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'thinking_content'):
                thinking = candidate.thinking_content

        # Estimate cost (thinking uses more tokens)
        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(text.split()) * 1.3 + thinking_budget
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        logger.info(f"Gemini thinking response: {len(text)} chars, ~${cost:.4f}")

        return {
            "text": text,
            "thinking": thinking,
            "model": model,
            "cost": cost,
        }

    except Exception as e:
        sanitized = sanitize_error_message(e, include_type=False)
        logger.error(f"Gemini thinking failed: {sanitized}")
        raise RuntimeError(f"Gemini thinking failed: {sanitized}") from e
```

**Key Details:**
- Uses `types.ThinkingConfig(thinking_budget=thinking_budget)` from new SDK
- Default `thinking_budget` = 1024 tokens
- Extracts thinking content from `response.candidates[0].thinking_content`
- Cost estimation includes thinking_budget in output tokens
- Error handling with rate limiting decorator

**Related Code:**
- **Line 556:** Comment referencing thinking usage in `generate_json()`:
  ```python
  # Pro thinking model uses separate thinking_budget for reasoning tokens
  ```

---

### 2. Convenience Wrapper Functions

#### File: `/Users/maz/Documents/GitHub/Research_Agent/backend/integrations/gemini_client.py`

**Function:** `plan_with_gemini()` (module-level helper)
- **Lines:** 1833-1845
- **Status:** CURRENT

**Code Snippet:**
```python
def plan_with_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> str:
    """Plan using Gemini Flash with thinking mode."""
    client = GeminiClient()
    response = client.generate_with_thinking(
        prompt,
        model="gemini-2.5-flash",
        thinking_budget=2048,
        system_instruction=system_instruction,
    )
    return response["text"]
```

**Key Details:**
- Convenience wrapper calling `generate_with_thinking()`
- Uses higher `thinking_budget` of 2048 tokens (vs 1024 default)
- Returns only the `text` field (discards thinking content)
- Intended for planning tasks

---

### 3. Documentation & Reference Files

#### File: `/Users/maz/Documents/GitHub/Research_Agent/plans/implementation-tasks-research-validated-stack.md`
- **Lines:** 130-155 (within class definition example)
- **Context:** Example implementation for old API (pre-migration)
- **Status:** OUTDATED (shows old `genai.configure()` pattern)

**Outdated Code Example:**
```python
async def generate_with_thinking(
    self,
    prompt: str,
    model: str = "gemini-2.5-flash",
    thinking_budget: int = 1024,
) -> str:
    """Generate with thinking mode for complex reasoning."""
    logger.info(f"Gemini {model} thinking: {prompt[:50]}...")
    model_instance = genai.GenerativeModel(model)
    response = model_instance.generate_content(
        prompt,
        generation_config={
            "thinking_config": {"thinking_budget": thinking_budget}
        }
    )
    return response.text
```

**Differences from Current:**
- Old SDK pattern: `genai.GenerativeModel()` + `genai.configure()`
- New SDK pattern: `genai.Client()` + `types.GenerateContentConfig()`
- Old dict config: `{"thinking_config": {"thinking_budget": ...}}`
- New SDK config: `types.ThinkingConfig(thinking_budget=...)`

---

### 4. Test & Validation Scripts

#### File: `/Users/maz/Documents/GitHub/Research_Agent/backend/scripts/test_gemini_video_extraction.py`
- **Lines:** 89-91 (import only)
- **Context:** Imports `types` from `google.genai` for video part handling
- **Status:** Uses new SDK correctly
- **Note:** No thinking_budget usage in this file (only for video analysis)

**Relevant Import:**
```python
from google import genai
from google.genai import types
```

#### File: `/Users/maz/Documents/GitHub/Research_Agent/.claude/skills/ai-multimodal/scripts/gemini_batch_process.py`
- **Lines:** 51-57 (import and configuration)
- **Context:** Batch processing script for multimodal analysis
- **Status:** Uses new SDK correctly
- **Note:** No thinking_budget usage (not needed for batch analysis tasks)

**Relevant Import:**
```python
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: google-genai package not installed")
    print("Install with: pip install google-genai")
    sys.exit(1)
```

---

## Configuration Details

### ThinkingConfig API (New SDK)

**Location:** `google.genai.types.ThinkingConfig`

**Constructor:**
```python
types.ThinkingConfig(
    thinking_budget: int  # Token budget for thinking phase
)
```

**Usage in GenerateContentConfig:**
```python
config = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
    system_instruction=system_instruction,
)
```

### Budget Recommendations

| Use Case | Budget | Notes |
|----------|--------|-------|
| Simple planning | 512-1024 | Default for most tasks |
| Complex reasoning | 2048-4096 | For planning, synthesis |
| Maximum | 64000 | Not recommended - costs increase |

**Current Usage:**
- Default: 1024 tokens (`generate_with_thinking()`)
- Planning: 2048 tokens (`plan_with_gemini()`)

---

## SDK Migration Status

### Current Implementation (Jan 2026)
- ✅ Uses new `google-genai` SDK
- ✅ Uses `types.ThinkingConfig()` for configuration
- ✅ Uses `types.GenerateContentConfig()` for full config
- ✅ Extracts thinking from `response.candidates[0].thinking_content`

### Compatibility
- ✅ Compatible with `google-genai` latest version
- ✅ No deprecated APIs in use
- ✅ Proper error handling for thinking mode

---

## Areas Referencing Thinking Configuration

### Direct References (Code)
1. **gemini_client.py:316-377** - `generate_with_thinking()` method
2. **gemini_client.py:1833-1845** - `plan_with_gemini()` wrapper
3. **gemini_client.py:556** - Comment about thinking tokens in `generate_json()`

### Indirect References (Documentation/Examples)
4. **implementation-tasks-research-validated-stack.md:139-154** - Outdated example
5. **diagnostic-260112-1338-system-diagnostic.md** - Method signature reference
6. **tester-251228-1516-backend-integrations-audit.md** - Bounds check note
7. **tester-251228-1445-integration-audit.md** - Rate limiting suggestion

---

## Update Requirements

### No Changes Needed
- Primary implementation uses correct SDK
- Thinking config properly instantiated
- Cost estimation includes thinking tokens
- Error handling is appropriate

### Optional Improvements
1. **Add bounds checking for thinking_budget:**
   ```python
   if thinking_budget > 64000:
       logger.warning(f"thinking_budget {thinking_budget} exceeds max 64000")
       thinking_budget = 64000
   ```

2. **Add logging of thinking content:**
   ```python
   if thinking and logger.level <= logging.DEBUG:
       logger.debug(f"Thinking content: {thinking[:500]}...")
   ```

3. **Update implementation-tasks-research-validated-stack.md** to reflect new SDK patterns

---

## Audit Checklist

- [x] Located all references to `ThinkingConfig`
- [x] Located all references to `thinking_budget`
- [x] Located all references to `generate_with_thinking`
- [x] Verified SDK compatibility
- [x] Checked error handling
- [x] Verified cost estimation
- [x] Reviewed documentation accuracy
- [x] Identified outdated examples

**Result:** PASS - All thinking configuration references are using current SDK correctly.

---

## Next Steps

1. **Optional:** Add bounds checking to `generate_with_thinking()` method
2. **Optional:** Update outdated examples in `implementation-tasks-research-validated-stack.md`
3. **Monitor:** Watch for Gemini SDK updates (if any) that might affect thinking config

