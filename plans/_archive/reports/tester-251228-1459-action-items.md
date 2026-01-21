# Integration Testing - Action Items

**Date:** 2025-12-28
**Status:** Ready for Implementation
**Priority:** High (Production Risk)

---

## CRITICAL FIXES - DO IMMEDIATELY

### Issue #1: Tavily Client Wrong Config Pattern
**File:** `backend/integrations/tavily_client.py:50`
**Fix Time:** 5 minutes
**Severity:** CRITICAL

```diff
- api_key = os.getenv("TAVILY_API_KEY")
- if not api_key:
-     raise ValueError("TAVILY_API_KEY environment variable is required")

+ from backend.config import require_tavily, MissingRequiredSettingError
+ try:
+     settings = require_tavily()
+     self.client = TavilySDK(api_key=settings.tavily_api_key)
+ except MissingRequiredSettingError:
+     raise
```

**Test:** Verify exception type when TAVILY_API_KEY not set matches other clients

---

### Issue #2: Serper Client Wrong Config Pattern
**File:** `backend/integrations/serper_client.py:28-34`
**Fix Time:** 10 minutes
**Severity:** CRITICAL

**Steps:**
1. Add `require_serper()` helper in `backend/config.py` (following OpenAI pattern)
2. Update `SerperClient.__init__()` to use it
3. Ensure MissingRequiredSettingError raised (not ValueError)

**Code:**
```python
# In config.py
def require_serper(self) -> str:
    if not self.serper_api_key:
        raise MissingRequiredSettingError("SERPER_API_KEY not configured")
    return self

# In serper_client.py
from backend.config import require_serper, MissingRequiredSettingError

def __init__(self):
    try:
        settings = require_serper()
        self.api_key = settings.serper_api_key
    except MissingRequiredSettingError:
        raise
```

---

### Issue #3: Supadata Client Wrong Config Pattern
**File:** `backend/integrations/supadata_client.py:69-71`
**Fix Time:** 5 minutes
**Severity:** CRITICAL

```diff
- self.api_key = os.getenv("SUPADATA_API_KEY")
- if not self.api_key:
-     raise ValueError("SUPADATA_API_KEY environment variable is required")

+ from backend.config import require_supadata, MissingRequiredSettingError
+ try:
+     settings = require_supadata()
+     self.api_key = settings.supadata_api_key
+ except MissingRequiredSettingError:
+     raise
```

**Add to config.py:**
```python
def require_supadata(self) -> str:
    if not self.supadata_api_key:
        raise MissingRequiredSettingError("SUPADATA_API_KEY not configured")
    return self
```

---

### Issue #4: Exa Client Multiple API Key Names (Security Risk)
**File:** `backend/integrations/exa_client.py:30`
**Fix Time:** 5 minutes
**Severity:** CRITICAL (Security)

```diff
- api_key = os.getenv("EXA_API_KEY") or os.getenv("EXAAI_SECRET_KEY") or os.getenv("EXA.AI_SECRET_KEY")
+ # Use config pattern like other clients
+ from backend.config import get_settings
+ settings = get_settings()
+ api_key = settings.exa_api_key

# Also update config.py to use ONLY EXA_API_KEY (already does, so just use it)
```

**Follow-up:**
- Remove `EXAAI_SECRET_KEY` and `EXA.AI_SECRET_KEY` references from documentation
- Update `.env.example` to show only `EXA_API_KEY`

---

### Issue #5: Transcripts Module - Remove Disabled Function
**File:** `backend/integrations/transcripts.py`
**Fix Time:** 10 minutes
**Severity:** HIGH (Code Clarity)

**Action:**
1. Delete function `_fetch_with_youtube_transcript_api()` (lines 156-197)
2. Delete function `fetch_transcript()` (lines 230-329) - DEPRECATED, use v2
3. Rename `fetch_transcript_v2()` to `fetch_transcript()` (lines 332-446)
4. Update all callers to use new function

**Reason:** Current code confuses developers by keeping disabled methods alive

---

## HIGH-PRIORITY FIXES - DO THIS WEEK

### Issue #6: Add Rate Limiting to Missing Clients
**Fix Time:** 30 minutes total
**Severity:** HIGH

Add `@with_rate_limit(service_name)` decorator to:
- [ ] `backend/integrations/serper_client.py` - search methods (line 36)
- [ ] `backend/integrations/gemini_client.py` - generate methods (line 58)
- [ ] `backend/integrations/youtube_client.py` - search_youtube_videos (line 20)
- [ ] `backend/integrations/exa_client.py` - search methods (line 37)
- [ ] `backend/integrations/supadata_client.py` - get_transcript (line 87)
- [ ] `backend/integrations/whisper_client.py` - transcribe_youtube (line 188)
- [ ] `backend/integrations/jina_reader_client.py` - extract (line 30)
- [ ] `backend/integrations/web_capture.py` - capture_web_content (line 168)

**Example:**
```python
from backend.utils.rate_limiter import with_rate_limit

@with_rate_limit("serper")
async def search(self, query: str, ...):
    # Implementation
```

---

### Issue #7: Fix YouTube Client Error Handling
**File:** `backend/integrations/youtube_client.py:100-111`
**Fix Time:** 5 minutes
**Severity:** HIGH

```diff
+ from backend.utils.error_handling import sanitize_error_message

  except httpx.HTTPStatusError as e:
-     logger.error(f"YouTube API HTTP error: {e.response.status_code} - {e.response.text}")
+     sanitized = sanitize_error_message(e, include_type=False)
+     logger.error(f"YouTube API HTTP error: {e.response.status_code} - {sanitized}")

  except Exception as e:
-     logger.error(f"Unexpected error searching YouTube: {e}")
+     sanitized = sanitize_error_message(e, include_type=False)
+     logger.error(f"YouTube search failed: {sanitized}")
```

---

### Issue #8: Replace Hardcoded Timeouts with Config References
**Files & Lines:**
- [ ] `perplexity_client.py:66` - Use `settings.timeout_api_default` (currently hardcoded 60.0)
- [ ] `serper_client.py:68, 140, 187` - Use `settings.timeout_api_default`
- [ ] `youtube_client.py:67` - Use `settings.timeout_youtube` (already defined)
- [ ] `jina_reader_client.py:27` - Use `settings.timeout_api_default`
- [ ] `slack.py:13-14` - Use `settings.timeout_api_default`

**Fix Time:** 15 minutes
**Severity:** MEDIUM

**Example:**
```python
# Before
with httpx.Client(timeout=30.0) as client:

# After
from backend.config import get_settings
settings = get_settings()
with httpx.Client(timeout=settings.timeout_api_default) as client:
```

---

### Issue #9: Add Cost Tracking to Perplexity
**File:** `backend/integrations/perplexity_client.py`
**Fix Time:** 5 minutes
**Severity:** HIGH

Document in comments:
```python
def _perplexity_search(query: str, model: str = PERPLEXITY_DEFAULT_MODEL) -> dict:
    """
    Make a search request to Perplexity API.

    Cost: ~$0.003-0.01 per search (varies by query length and response)
    NOTE: Exact cost not documented by Perplexity, this is estimate based on token usage.
    """
    # ... rest of function ...
    # Return dict should include cost estimate
    return {
        "results": urls,
        "cost": estimated_cost,  # Add this
    }
```

---

### Issue #10: Fix Jina Reader Base URL Configuration
**File:** `backend/integrations/jina_reader_client.py:21`
**Fix Time:** 5 minutes
**Severity:** MEDIUM

```diff
- BASE_URL = "https://r.jina.ai/"

+ def __init__(self):
+     from backend.config import get_settings
+     settings = get_settings()
+     self.base_url = settings.jina_api_url
```

---

## MEDIUM-PRIORITY FIXES - DO THIS SPRINT

### Issue #11: Create Comprehensive Integration Tests
**Time:** 4 hours
**Severity:** MEDIUM

Create test file for each integration in `backend/tests/test_*.py`:

```python
# backend/tests/test_perplexity_client.py
import pytest
from backend.integrations.perplexity_client import research_map
from backend.models.job_config import JobConfig

def test_research_map_missing_api_key(monkeypatch):
    """Test graceful handling when API key missing."""
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    job = JobConfig(topic="test topic", mode="claims_evidence")
    result = research_map(job)
    assert result["angles"] == ["general"]

def test_research_map_api_error(monkeypatch, httpx_mock):
    """Test error handling for API failures."""
    httpx_mock.add_response(status_code=429)
    # Test rate limit handling
```

**Clients to test (priority order):**
1. ✅ OpenAI (most critical)
2. ✅ Perplexity
3. ✅ Supadata
4. ✅ Whisper
5. Serper
6. Gemini
7. Exa
8. YouTube
9. Reddit
10. Jina
11. Google Drive
12. Slack
13. Web Capture
14. Transcripts

---

### Issue #12: Remove Stub Integration Files
**Files to review:**
- [ ] `backend/integrations/brave_search_client.py` - Complete or delete?
- [ ] `backend/integrations/claimbuster_client.py` - Complete or delete?
- [ ] `backend/integrations/google_factcheck_client.py` - Complete or delete?
- [ ] `backend/integrations/semantic_scholar_client.py` - Complete or delete?
- [ ] `backend/integrations/gdelt_client.py` - Complete or delete?

**Decision:** Determine if these are planned features or dead code
- If planned: Create issues and estimate effort
- If dead code: Delete and update documentation

---

### Issue #13: Verify Slack Signature Verification in All Routes
**Time:** 30 minutes
**Severity:** MEDIUM (Security)

**Action:**
1. Find all Slack webhook routes in FastAPI app
2. Verify each route calls `verify_slack_signature()` BEFORE processing
3. Add type hints and documentation

**Search for:** "response_url" or "slack" in API routes

---

### Issue #14: Document All API Costs
**Files to update:**
- Perplexity: Add cost documentation
- Gemini: Verify costs match docs/CLAUDE.md
- Serper: Document $1/1k
- Tavily: Document credit system
- Supadata: Document credit system

**Update:** Each client should have cost info in docstring and logging

---

## TESTING VERIFICATION

### Pre-commit Checklist

Before committing any integration client changes:

- [ ] All MissingRequiredSettingError exceptions raised (not ValueError)
- [ ] All API calls log sanitized errors
- [ ] Cost tracking included in response dicts
- [ ] Rate limiting decorator applied
- [ ] Docstrings updated with cost information
- [ ] Type hints complete
- [ ] Tests written and passing

### Integration Test Commands

```bash
# Run all integration tests
pytest backend/tests/test_*_client.py -v

# Run with coverage
pytest backend/tests/ --cov=backend.integrations --cov-report=html

# Test specific client
pytest backend/tests/test_openai_client.py -v
```

---

## COMPLETION TRACKING

- [ ] Issue #1 - Tavily config pattern (CRITICAL)
- [ ] Issue #2 - Serper config pattern (CRITICAL)
- [ ] Issue #3 - Supadata config pattern (CRITICAL)
- [ ] Issue #4 - Exa API key standardization (CRITICAL)
- [ ] Issue #5 - Remove disabled transcripts functions (HIGH)
- [ ] Issue #6 - Add rate limiting to 8 clients (HIGH)
- [ ] Issue #7 - Fix YouTube error handling (HIGH)
- [ ] Issue #8 - Replace hardcoded timeouts (MEDIUM)
- [ ] Issue #9 - Add cost tracking to Perplexity (HIGH)
- [ ] Issue #10 - Fix Jina config (MEDIUM)
- [ ] Issue #11 - Create integration tests (MEDIUM)
- [ ] Issue #12 - Clean up stub files (MEDIUM)
- [ ] Issue #13 - Verify Slack security (MEDIUM)
- [ ] Issue #14 - Document API costs (MEDIUM)

---

## ESTIMATED EFFORT

- **Critical Fixes:** 30 minutes
- **High-Priority Fixes:** 2 hours
- **Medium-Priority Fixes:** 6 hours
- **Testing:** 8 hours

**Total:** ~16 hours
**Recommended Allocation:** Split across 3-4 sprints

---

**Report Generated:** 2025-12-28
**Prepared By:** QA Engineer (Haiku 4.5)
