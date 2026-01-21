# Integration Clients Code Review

**Date:** 2025-12-28 18:19
**Reviewer:** code-reviewer
**Scope:** Backend integration clients quality & reliability audit

---

## Code Review Summary

### Scope
**Files reviewed:**
- `perplexity_client.py` (546 lines)
- `google_drive_docs.py` (519 lines)
- `openai_client.py` (372 lines)
- `gemini_client.py` (354 lines)
- `tavily_client.py` (313 lines)
- `serper_client.py` (255 lines)
- `supadata_client.py` (307 lines)
- `whisper_client.py` (240 lines)
- `jina_reader_client.py` (146 lines)

**Total LOC analyzed:** ~3,052 lines
**Review focus:** Reliability, error handling, cost tracking, DRY violations, modularization opportunities

### Overall Assessment

**Quality:** Medium-High (70/100)

**Strengths:**
- Excellent rate limiting infrastructure (`rate_limiter.py`)
- Consistent error sanitization (`error_handling.py`)
- Good fallback chain documentation
- Cost tracking present in most clients

**Critical gaps:**
- **Inconsistent retry logic** - only 4/9 clients use `@with_rate_limit` decorator
- **No timeout standardization** - 7 different timeout values (15s-60s)
- **Mixed async/sync patterns** causing complexity
- **Files exceeding 200 LOC target** - 3 files need refactoring
- **Missing cost tracking** in several clients
- **No circuit breaker pattern** for cascading failures

---

## Critical Issues

### 1. **Inconsistent Rate Limiting & Retry Logic**
**Severity:** HIGH
**Impact:** Production failures, quota exhaustion, cascading errors

**Problem:**
Only 4/9 clients use the centralized `@with_rate_limit` decorator:
- ✅ `perplexity_client.py:24` - Uses decorator
- ✅ `openai_client.py:164,231` - Uses decorator
- ✅ `tavily_client.py:59,140` - Uses decorator
- ❌ `gemini_client.py` - No rate limiting
- ❌ `google_drive_docs.py` - No rate limiting
- ❌ `serper_client.py` - Manual retry in sync_wrapper only
- ❌ `supadata_client.py` - No retry logic
- ❌ `whisper_client.py` - No retry logic
- ❌ `jina_reader_client.py` - No retry logic

**Impact:**
- Gemini API calls can fail without retry (expensive errors)
- Google Drive operations have no backoff (quota issues)
- Supadata/Whisper failures are not retried (transcript loss)

**Fix:**
```python
# gemini_client.py:58 - Add decorator
@with_rate_limit("gemini")
def generate(self, prompt: str, ...):

# google_drive_docs.py:201 - Add decorator
@with_rate_limit("google_drive")
def create_research_packet(...):

# supadata_client.py:87 - Add decorator
@with_rate_limit("supadata")
def get_transcript(self, url: str, ...):
```

**File references:**
- `backend/integrations/gemini_client.py:58,113,176,244`
- `backend/integrations/google_drive_docs.py:201,385`
- `backend/integrations/supadata_client.py:87`
- `backend/integrations/whisper_client.py:109,188`
- `backend/integrations/jina_reader_client.py:30`

---

### 2. **Timeout Configuration Chaos**
**Severity:** HIGH
**Impact:** Unpredictable failure behavior, resource leaks

**Problem:**
7 different timeout values across integrations:
```
15s: google_factcheck_client.py:25
30s: jina_reader_client.py:27, serper_client.py:68,140, gdelt_client.py:24
60s: perplexity_client.py:18, supadata_client.py:82
None: gemini_client.py (no timeout), openai_client.py (uses SDK defaults)
```

**No timeout classes for operation types:**
- Fast operations (15-30s): Search, fact-check
- Medium operations (30-60s): Web scraping, transcription
- Long operations (60-120s): Video processing, large file uploads

**Fix:**
Create timeout configuration:
```python
# backend/config.py
class TimeoutConfig:
    FAST_OPERATION = 15.0      # Search, fact-check
    MEDIUM_OPERATION = 30.0    # Web scraping
    LONG_OPERATION = 60.0      # Transcription
    VERY_LONG_OPERATION = 120.0 # Video processing

# Usage
with httpx.Client(timeout=TimeoutConfig.FAST_OPERATION) as client:
```

**File references:**
- All integration clients need standardization

---

### 3. **Cost Tracking Incomplete**
**Severity:** MEDIUM
**Impact:** Budget overruns, missing analytics

**Missing cost tracking:**
- ❌ `google_drive_docs.py` - No cost tracking for API calls
- ❌ `serper_client.py:101` - Logs cost but doesn't return in all methods
- ❌ `whisper_client.py:148` - Returns cost but no pipeline integration
- ❌ `jina_reader_client.py:68` - Returns cost=0.0 (correct but not tracked)

**Inconsistent cost field names:**
- `cost` (whisper_client.py:158)
- `cost_credits` (tavily_client.py:123, supadata_client.py:139)
- `cost` (serper_client.py:101)

**Fix:**
Standardize cost tracking:
```python
# All clients should return
return {
    "data": result,
    "cost_usd": 0.006,  # Always in USD
    "cost_credits": 1,   # If credit-based API
    "api": "whisper",
}

# Pipeline context should aggregate
ctx.add_cost("whisper", 0.006)
```

**File references:**
- `backend/integrations/google_drive_docs.py` - Add cost tracking
- `backend/integrations/serper_client.py:101,169,214` - Standardize field names
- `backend/pipeline/context.py` - Verify cost aggregation

---

## High Priority Findings

### 4. **Mixed Async/Sync Patterns Causing Complexity**
**Severity:** MEDIUM
**Impact:** Maintenance burden, potential async runtime errors

**Problem:**
- `serper_client.py` - Has both async (36,113) and sync (177) methods
- `jina_reader_client.py` - Has both sync (30) and async (91) methods
- `gemini_client.py` - All sync despite being I/O bound
- `perplexity_client.py` - All sync (correct for httpx.Client usage)

**Async candidates (I/O bound but sync):**
- `gemini_client.py:58,113,176,244` - All methods are blocking I/O
- `google_drive_docs.py:201,385` - Drive API calls are blocking
- `whisper_client.py:188` - Audio download + transcription is blocking

**Fix:**
Make Gemini client async (saves pipeline blocking time):
```python
# gemini_client.py:58
async def generate(self, prompt: str, ...) -> dict[str, Any]:
    response = await asyncio.to_thread(
        self._client.models.generate_content,
        model=model,
        contents=prompt,
        config=config,
    )
```

**File references:**
- `backend/integrations/gemini_client.py:58,113,176,244`
- `backend/integrations/serper_client.py:177` - Consider removing sync wrapper
- `backend/integrations/jina_reader_client.py:30` - Make primary method async

---

### 5. **Files Exceeding 200 LOC Target**
**Severity:** MEDIUM (per development rules)
**Impact:** Context management, maintainability

**Files needing refactoring:**
1. **perplexity_client.py (546 lines)** - Split into:
   - `perplexity_search.py` (API calls)
   - `perplexity_parsers.py` (URL extraction, classification)
   - `perplexity_formatters.py` (Markdown generation)

2. **google_drive_docs.py (519 lines)** - Split into:
   - `google_drive_client.py` (Core API wrapper)
   - `google_drive_research_packet.py` (Research packet creation)
   - `google_drive_permissions.py` (Sharing logic)

3. **openai_client.py (372 lines)** - Split into:
   - `openai_client.py` (Core API wrapper)
   - `openai_planning.py` (Job planning logic)
   - `openai_parsers.py` (YouTube channel/date extraction)

**File references:**
- `backend/integrations/perplexity_client.py` - Refactor to 3 modules
- `backend/integrations/google_drive_docs.py` - Refactor to 3 modules
- `backend/integrations/openai_client.py` - Refactor to 3 modules

---

### 6. **Error Handling Inconsistencies**
**Severity:** MEDIUM
**Impact:** Debugging difficulty, inconsistent error messages

**Good patterns:**
```python
# perplexity_client.py:70-82 - Excellent error handling
except httpx.HTTPStatusError as e:
    error_detail = f"HTTP {e.response.status_code}"
    try:
        error_body = e.response.json()
        error_msg = error_body.get('error', {}).get('message', '')
    except Exception:
        error_detail += f": {e.response.text[:200]}"
    sanitized_error = sanitize_error_message(RuntimeError(error_detail))
    raise RuntimeError(f"Perplexity API failed: {sanitized_error}") from e
```

**Bad patterns:**
```python
# gemini_client.py:108-111 - Generic exception handling
except Exception as e:
    sanitized = sanitize_error_message(e, include_type=False)
    logger.error(f"Gemini generate failed: {sanitized}")
    raise RuntimeError(f"Gemini generate failed: {sanitized}") from e
```

**Missing specific exception handling:**
- `gemini_client.py:108` - Should catch `google.api_core.exceptions.*`
- `supadata_client.py:116` - Generic exception, should catch `httpx.HTTPError`
- `whisper_client.py:161` - Generic exception, should catch `openai.APIError`

**Fix:**
```python
# gemini_client.py:108
except google.api_core.exceptions.ResourceExhausted as e:
    # Handle quota errors specifically
except google.api_core.exceptions.GoogleAPIError as e:
    # Handle API errors
except Exception as e:
    # Catch-all
```

**File references:**
- `backend/integrations/gemini_client.py:108,172,239,302`
- `backend/integrations/supadata_client.py:116,238`
- `backend/integrations/whisper_client.py:161,226`

---

## Medium Priority Improvements

### 7. **DRY Violations - URL Validation**
**Severity:** LOW-MEDIUM
**Impact:** Maintenance burden

**Duplicate URL validation logic:**
```python
# perplexity_client.py:123-144 - _is_valid_source_url()
# supadata_client.py:241-264 - detect_platform()
# openai_client.py:29-70 - _extract_youtube_channels()
```

**Fix:**
Create shared URL utilities:
```python
# backend/utils/url_helpers.py
def validate_source_url(url: str) -> bool:
    """Validate URL is not social/search engine."""

def detect_video_platform(url: str) -> Optional[Platform]:
    """Detect video platform from URL."""

def extract_youtube_channels(text: str) -> list[str]:
    """Extract YouTube channel IDs/handles."""
```

**File references:**
- Create `backend/utils/url_helpers.py`
- Refactor `backend/integrations/perplexity_client.py:123`
- Refactor `backend/integrations/supadata_client.py:241`
- Refactor `backend/integrations/openai_client.py:29`

---

### 8. **DRY Violations - Date Parsing**
**Severity:** LOW
**Impact:** Maintenance burden

**Duplicate date parsing:**
```python
# openai_client.py:73-123 - _parse_date_window() (50 lines)
# Similar logic likely needed in other clients
```

**Fix:**
```python
# backend/utils/datetime_utils.py (already exists)
def parse_natural_date_range(text: str) -> tuple[Optional[date], Optional[date]]:
    """Parse natural language date expressions."""
```

**File references:**
- Move `backend/integrations/openai_client.py:73-123` to `backend/utils/datetime_utils.py`

---

### 9. **Missing Circuit Breaker Pattern**
**Severity:** LOW-MEDIUM
**Impact:** Cascading failures

**Problem:**
No circuit breaker for degraded APIs. If Tavily has 10% 502 rate (documented), pipeline should auto-fallback after N failures.

**Current behavior:**
```python
# tavily_client.py:1-6 - Documents 10% 502 rate
# But no circuit breaker to skip Tavily after failures
```

**Desired behavior:**
```python
# backend/utils/circuit_breaker.py
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.state = "closed"  # closed, open, half_open

    def call(self, func):
        if self.state == "open":
            raise CircuitBreakerOpen("API temporarily disabled")
```

**File references:**
- Create `backend/utils/circuit_breaker.py`
- Integrate with `backend/utils/rate_limiter.py`

---

### 10. **Security - Command Injection Prevention**
**Severity:** LOW (already handled)
**Impact:** Security

**Good patterns found:**
```python
# whisper_client.py:35-52 - Excellent video ID validation
@staticmethod
def _validate_video_id(video_id: str) -> str:
    if not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        raise ValueError(f"Invalid YouTube video ID format: {video_id}")
    return video_id

# whisper_client.py:69 - Uses validated video_id
video_id = self._validate_video_id(video_id)
```

**Recommendation:**
Ensure all subprocess calls validate inputs:
- ✅ `whisper_client.py:69,86` - Validated
- ✅ `whisper_client.py:171` - Uses validated path
- Review any other subprocess usage

---

## Low Priority Suggestions

### 11. **Logging Consistency**
**Severity:** LOW
**Impact:** Debugging efficiency

**Inconsistent log formats:**
```python
# Good (structured):
logger.info(f"Perplexity query: {query[:100]}...")  # perplexity_client.py:63

# Bad (unstructured):
logger.info(f"Gemini {model}: {prompt[:50]}...")  # gemini_client.py:79
```

**Recommendation:**
Standardize log format:
```python
logger.info(f"{self.__class__.__name__}: {operation} - {details}")
```

---

### 12. **Type Hints Completeness**
**Severity:** LOW
**Impact:** Developer experience

**Missing return type hints:**
- `google_drive_docs.py:120,125` - `_get_drive_service`, `_get_docs_service`
- `perplexity_client.py:90` - `_extract_urls_from_response` returns `list[dict]` but not typed

**Fix:**
```python
def _get_drive_service(creds: Credentials) -> Resource:
    return build("drive", "v3", credentials=creds)
```

---

## Positive Observations

### Excellent Patterns Found

1. **Rate Limiter Utility** (`backend/utils/rate_limiter.py`)
   - Comprehensive exponential backoff
   - Both async/sync support
   - Per-API configuration
   - Request tracking
   - **Score: 95/100**

2. **Error Sanitization** (`backend/utils/error_handling.py`)
   - Removes API keys from logs
   - Pattern matching for various key formats
   - URL redaction
   - **Score: 90/100**

3. **Cost Awareness** (multiple clients)
   - Gemini client tracks per-model costs (gemini_client.py:39-42)
   - Whisper calculates per-minute costs (whisper_client.py:32)
   - Serper logs cost per search (serper_client.py:24)

4. **Security** (whisper_client.py:35-52)
   - Video ID validation prevents command injection
   - Subprocess timeouts prevent hangs
   - Temp file cleanup

5. **Fallback Chains** (documented in comments)
   - Transcripts: Supadata → Whisper (documented)
   - Web capture: Jina → Trafilatura (documented)
   - Search: Perplexity → Serper (validated stack)

---

## Recommended Actions

### Immediate (Critical)
1. **Add `@with_rate_limit` decorator to all clients** (2 hours)
   - Files: gemini_client.py, google_drive_docs.py, supadata_client.py, whisper_client.py, jina_reader_client.py
   - Impact: Prevents production failures, quota exhaustion

2. **Standardize timeout configurations** (1 hour)
   - Create `TimeoutConfig` class
   - Apply across all clients
   - Impact: Predictable failure behavior

3. **Standardize cost tracking** (1 hour)
   - Use `cost_usd` field consistently
   - Ensure pipeline context aggregation
   - Impact: Accurate budget tracking

### Short-term (High Priority)
4. **Refactor files exceeding 200 LOC** (6 hours)
   - perplexity_client.py → 3 modules
   - google_drive_docs.py → 3 modules
   - openai_client.py → 3 modules
   - Impact: Better maintainability, context efficiency

5. **Migrate I/O bound clients to async** (4 hours)
   - gemini_client.py methods
   - google_drive_docs.py methods
   - Impact: Non-blocking pipeline execution

6. **Improve error handling specificity** (2 hours)
   - Add API-specific exception catching
   - Provide actionable error messages
   - Impact: Faster debugging

### Medium-term (Improvements)
7. **Extract shared utilities** (3 hours)
   - URL validation → url_helpers.py
   - Date parsing → datetime_utils.py
   - Impact: DRY compliance

8. **Implement circuit breaker pattern** (4 hours)
   - Create circuit_breaker.py
   - Integrate with rate limiter
   - Auto-fallback for degraded APIs
   - Impact: Resilience to cascading failures

---

## Metrics

### Code Quality Scores

| Client | LOC | Retry | Timeout | Cost | Async | Score |
|--------|-----|-------|---------|------|-------|-------|
| perplexity_client.py | 546 | ✅ | ✅ | ✅ | ❌ | 75/100 |
| google_drive_docs.py | 519 | ❌ | ❌ | ❌ | ❌ | 50/100 |
| openai_client.py | 372 | ✅ | ✅ | ❌ | ❌ | 70/100 |
| gemini_client.py | 354 | ❌ | ❌ | ✅ | ❌ | 60/100 |
| tavily_client.py | 313 | ✅ | ✅ | ✅ | ✅ | 85/100 |
| serper_client.py | 255 | ⚠️ | ✅ | ✅ | ✅ | 80/100 |
| supadata_client.py | 307 | ❌ | ✅ | ✅ | ❌ | 65/100 |
| whisper_client.py | 240 | ❌ | ✅ | ✅ | ❌ | 70/100 |
| jina_reader_client.py | 146 | ❌ | ✅ | ✅ | ⚠️ | 75/100 |

**Average Score:** 70/100

### Technical Debt

- **Critical issues:** 3 (rate limiting, timeouts, cost tracking)
- **High priority:** 3 (async patterns, file size, error handling)
- **Medium priority:** 4 (DRY violations, circuit breaker)
- **Low priority:** 2 (logging, type hints)

**Estimated refactoring time:** 23 hours

---

## Unresolved Questions

1. **Should all clients be async?** - Current mix of sync/async in pipeline. Need decision on pipeline execution model.

2. **Cost tracking aggregation?** - Verify `PipelineContext.add_cost()` implementation exists and works.

3. **Circuit breaker threshold?** - What failure rate triggers circuit breaker? (Suggest: 30% over 10 requests)

4. **YouTube Data API v3 usage?** - Listed in architecture.md but no client found. Is this deprecated?

5. **Exa client missing?** - Architecture.md mentions Exa (94.9% accuracy) but no `exa_client.py` found. Is this planned?

---

**Review complete.** Prioritize immediate actions for production stability.
