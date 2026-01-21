# Audit Remediation Plan

**Created:** 2026-01-18 16:27
**Source:** `plans/reports/audit-260118-1534-full-codebase-review.md`
**Total Issues:** 29 (3 Critical, 8 High, 11 Medium, 7 Low)
**H4 Already Fixed:** ✅ `sources_extracted` → `sources_processed`

---

## Phase 1: Critical Issues (3 items)

### C1: Gemini Client - No Timeout Configuration
- **File:** `backend/integrations/gemini_client.py:550-554`
- **Risk:** Workers blocked indefinitely on long-running LLM calls
- **Fix:** Add timeout from `settings.timeout_api_default` to GenerateContentConfig
- **Effort:** 30m

### C2: OpenAI Client - No Timeout Configuration
- **File:** `backend/integrations/openai_client.py:195-516`
- **Risk:** Job planning blocked indefinitely
- **Fix:** Add `timeout=settings.timeout_api_default` to OpenAI client init
- **Effort:** 30m

### C3: No Circuit Breaker Pattern
- **File:** `backend/utils/rate_limiter.py:236-273`
- **Risk:** Failed services continue receiving retries, wasted quota
- **Fix:** Implement OPEN/CLOSED/HALF_OPEN states with 5-failure threshold, 60s cooldown
- **Effort:** 4h

---

## Phase 2: High Priority Issues (7 remaining)

### H1: Prompt Injection in LLM Calls
- **File:** `backend/pipeline/extraction.py:352-368`
- **Risk:** User content injected into prompts bypasses extraction rules
- **Fix:** Add `sanitize_for_llm_prompt()` to escape injection markers
- **Effort:** 2h

### H2: Optional Email Claim in JWT
- **File:** `backend/auth/__init__.py:69-74`
- **Risk:** Authorization bypass if email assumed present
- **Fix:** Add explicit null check and logging for missing email claims
- **Effort:** 30m

### H3: YouTube URL Validation Missing in Gemini Client
- **File:** `backend/integrations/gemini_client.py:670`
- **Risk:** Malformed URLs cause API errors
- **Fix:** Call `validate_youtube_url()` before creating video Part
- **Effort:** 15m

### H5: Gemini JSON Parse Errors Silent
- **File:** `backend/integrations/gemini_client.py:582-591`
- **Risk:** Empty extractions treated as successful
- **Fix:** Raise RuntimeError instead of returning error dict
- **Effort:** 15m

### H6: Whisper Command Injection Risk
- **File:** `backend/integrations/whisper_client.py:190-241`
- **Risk:** Command injection via malicious video_id
- **Fix:** Add `_validate_video_id()` call at entry point
- **Effort:** 15m

### H7: Perplexity No Response Structure Validation
- **File:** `backend/integrations/perplexity_client.py:90-120`
- **Risk:** Silent failures if API response format changes
- **Fix:** Add Pydantic response models with validation
- **Effort:** 1h

### H8: YouTube 429 Rate Limit Not Handled Differently
- **File:** `backend/integrations/youtube_client.py:200-207`
- **Risk:** Quota exhausted early, all subsequent jobs fail
- **Fix:** Raise `QuotaExceededError` on 429 status
- **Effort:** 30m

### H9: Incomplete DOMPurify Configuration
- **File:** `frontend/components/job-card/DocumentCard.tsx:144`
- **Risk:** XSS if misconfigured
- **Fix:** Add explicit `ALLOWED_TAGS`/`ALLOWED_ATTR` config
- **Effort:** 15m

---

## Phase 3: Medium Priority Issues (11 items)

### Security (M1-M5)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| M1 | Ban check "fail open" on error | `auth/ban_check.py:59-69` | Return 503 or cache ban status |
| M2 | CORS wildcard not rejected | `app/main.py:40-54` | Validate origins, reject `*` |
| M3 | API keys in Gemini video URLs | `gemini_client.py:670` | Strip API key params from URLs |
| M4 | Rate limiting IP spoofable | `rate_limiter.py` | Trust X-Forwarded-For only from proxies |
| M5 | No CSP headers on API | `app/main.py` | Add security headers middleware |

### Integration (M6-M9)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| M6 | Tavily 10% error rate unhandled | `tavily_client.py` | Add health check before batch |
| M7 | Serper no rate limiting | `serper_client.py:36-42` | Add `@with_rate_limit("serper")` |
| M8 | Exa no rate limiting | `exa_client.py:37-106` | Add `@with_rate_limit("exa")` |
| M9 | Reddit no rate limiting | `reddit_client.py:44-114` | Add `@with_rate_limit("reddit")` |

### Frontend (M10-M11)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| M10 | No token expiry validation | `api-client.ts` | Add proactive refresh before expiry |
| M11 | API URL not validated | `constants.ts:44` | Add domain whitelist validation |

---

## Phase 4: Low Priority Issues (7 items)

| ID | Issue | File | Fix |
|----|-------|------|-----|
| L1 | Missing type hints on helpers | Multiple extraction files | Add return type annotations |
| L2 | Jina hardcoded timeout | `jina_reader_client.py:28` | Use centralized config |
| L3 | Perplexity timeout too long | `perplexity_client.py:18` | Split search/extract timeouts |
| L4 | CSP allows unsafe-inline | `next.config.js:23` | Required by Next.js (defer) |
| L5 | No magic bytes validation | `ScreenshotSourceForm.tsx` | Add client + backend validation |
| L6 | External URL not validated | `ExportButton.tsx:61` | Whitelist Google Docs domain |
| L7 | Duplicate CONFIDENCE_CEILINGS | `semantic_units.py:426` | Refactor to break circular import |

---

## Implementation Checklist

### Phase 1: Critical (Do First)
- [ ] C1: Add Gemini timeout configuration
- [ ] C2: Add OpenAI timeout configuration
- [ ] C3: Implement circuit breaker pattern

### Phase 2: High Priority
- [ ] H1: Add prompt injection sanitization
- [ ] H2: Add JWT email null check
- [ ] H3: Add YouTube URL validation in Gemini
- [ ] H5: Fix Gemini JSON parse error handling
- [ ] H6: Add Whisper video_id validation
- [ ] H7: Add Perplexity response validation
- [ ] H8: Handle YouTube 429 rate limit
- [ ] H9: Harden DOMPurify configuration

### Phase 3: Medium Priority
- [ ] M1: Fix ban check fail-open behavior
- [ ] M2: Validate CORS origins
- [ ] M3: Strip API keys from video URLs
- [ ] M4: Secure rate limiting IP detection
- [ ] M5: Add CSP headers to API
- [ ] M6: Add Tavily health check
- [ ] M7: Add Serper rate limiting
- [ ] M8: Add Exa rate limiting
- [ ] M9: Add Reddit rate limiting
- [ ] M10: Add frontend token expiry validation
- [ ] M11: Add API URL whitelist

### Phase 4: Low Priority
- [ ] L1: Add missing type hints
- [ ] L2: Centralize Jina timeout
- [ ] L3: Split Perplexity timeouts
- [ ] L4: CSP unsafe-inline (defer - Next.js requirement)
- [ ] L5: Add magic bytes validation
- [ ] L6: Whitelist Google Docs URL
- [ ] L7: Refactor CONFIDENCE_CEILINGS

---

## Effort Summary

| Phase | Items | Effort |
|-------|-------|--------|
| Phase 1 (Critical) | 3 | 5h |
| Phase 2 (High) | 7 | 4h 45m |
| Phase 3 (Medium) | 11 | ~3h |
| Phase 4 (Low) | 7 | ~2h |
| **Total** | **28** | **~15h** |

---

## Testing Requirements

After each fix:
1. Run `pytest backend/tests/ -v`
2. Verify no regressions
3. Add specific test for the fix if not covered

---

## Notes

- H4 already fixed by code-reviewer subagent
- L4 deferred - required by Next.js
- Circuit breaker (C3) is most complex item
- Prompt injection (H1) highest security impact

---

## Plan Files

| File | Description |
|------|-------------|
| `phase-1-critical.md` | Detailed implementation for C1-C3 |
| `phase-2-high.md` | Detailed implementation for H1-H9 |
| `phase-3-medium.md` | Detailed implementation for M1-M11 |
| `phase-4-low.md` | Detailed implementation for L1-L7 |
| `appendix-empty-docs-diagnostic.md` | Debugging guide for empty Doc 0/1/2 |

---

## Appendix: Empty Document Debugging

**See:** `appendix-empty-docs-diagnostic.md`

Quick reference for diagnosing why Doc 0/1/2 are empty. Root cause is almost always upstream stages not producing inputs:

```
Discovery → Capture → Identity → Extraction → Synthesis → Assembly
```

Common culprits:
1. Missing `EXA_API_KEY` + `PERPLEXITY_API_KEY` → no sources
2. Missing `SUPADATA_API_KEY` + `GOOGLE_API_KEY` → no video extraction

Check job status via `GET /jobs/{job_id}` and inspect:
- `outputs.source_identity_summary.total_sources`
- `outputs.semantic_extraction_summary.sources_processed`
- `warnings` array
