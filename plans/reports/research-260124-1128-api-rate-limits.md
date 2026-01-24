# API Rate Limits Research Report

**Date:** 2026-01-24
**Purpose:** Document rate limits for all external APIs used in Research Agent to prevent lockouts

---

## Executive Summary

| API | Current Config | Actual Limit | Status |
|-----|----------------|--------------|--------|
| **Gemini** | 60 RPM / 1500 RPH | Free: 5-15 RPM, Paid: 150-300 RPM | ⚠️ May need adjustment |
| **OpenAI GPT** | 60 RPM / 500 RPH | Tier-dependent, ~500+ RPM | ✅ Conservative |
| **Whisper** | 10 RPM / 50 RPH | ~50 RPM default | ✅ Safe |
| **YouTube Data API** | 60 RPM / 10000 RPH | 10,000 units/day (search=100 units) | ⚠️ Unit-based, not RPM |
| **Supadata** | 10 RPM / 100 RPH | Plan-dependent, 429 on exceed | ✅ Safe |
| **Jina Reader** | 100 RPM / 2000 RPH | Free: 20 RPM, Paid: 500 RPM | ⚠️ May need reduction |
| **Supabase** | N/A (no limit) | 1200 reads/s, 1000 writes/s | ✅ No concern |

---

## Detailed API Analysis

### 1. Google Gemini API

**Source:** [Google AI Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)

| Tier | RPM | TPM | RPD |
|------|-----|-----|-----|
| Free | 5-15 | 250K | 1,500 |
| Paid Tier 1 | 150-300 | 1M | 10,000 |
| Paid Tier 2 | 1,000+ | 4M | - |

**Current Config:** 60 RPM / 1500 RPH
**Recommendation:** If on free tier, reduce to 10 RPM. If paid, current is safe.

**December 2025 Changes:** Google reduced free tier quotas, causing more 429 errors.

---

### 2. OpenAI GPT-4o / GPT-4o-mini

**Source:** [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)

| Tier | RPM | TPM |
|------|-----|-----|
| Tier 1 | ~500 | 30K-60K |
| Tier 2+ | 1,000+ | 100K+ |

**Current Config:** 60 RPM / 500 RPH
**Status:** ✅ Very conservative, safe for all tiers

---

### 3. OpenAI Whisper (Audio Transcription)

**Source:** [OpenAI Whisper Limits](https://community.openai.com/t/whisper-api-limits-transcriptions/167507)

- Default: ~50 RPM
- Azure: 3 RPM default (can request increase)
- File size: 25 MB max

**Current Config:** 10 RPM / 50 RPH
**Status:** ✅ Very safe, accounts for file upload time

---

### 4. YouTube Data API v3

**Source:** [YouTube API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)

**Quota System (NOT RPM-based):**
- **Default:** 10,000 units/day
- Read (list): 1 unit
- Search: 100 units
- Write: 50 units
- Video upload: 1,600 units

**Important:** 10,000 units ÷ 100 per search = **100 searches/day max**

**Current Config:** 60 RPM / 10000 RPH (misleading - quota is units, not requests)
**Recommendation:** Track units consumed, not just requests. Consider unit-based limiter.

---

### 5. Supadata (YouTube Transcripts)

**Source:** [Supadata Docs](https://docs.supadata.ai)

- Rate limits vary by subscription plan
- Returns 429 when exceeded
- Free tier: 100 requests total (one-time)

**Current Config:** 10 RPM / 100 RPH
**Status:** ✅ Appropriately conservative

---

### 6. Jina AI Reader

**Source:** [Jina Reader API](https://jina.ai/reader/)

| Tier | RPM | TPM | Concurrent |
|------|-----|-----|------------|
| Free (no key) | 20 | - | - |
| Free (with key) | 100 | 100K | 2 |
| Paid | 500 | 2M | 50 |

**Current Config:** 100 RPM / 2000 RPH
**Recommendation:** If using free tier without API key, reduce to 15 RPM.

---

### 7. Supabase

**Source:** [Supabase Rate Limits](https://supabase.com/docs/guides/auth/rate-limits)

- **Database CRUD:** No hard limits, depends on instance
- **Free tier:** ~1200 reads/s, ~1000 writes/s
- **Management API:** 120 requests/minute per project

**Current Config:** Not rate-limited
**Status:** ✅ Safe - Supabase handles its own limits

---

## Recommendations

### Immediate Actions

1. **Gemini:** Confirm your tier. If free, change to:
   ```python
   "gemini": RateLimitConfig(requests_per_minute=10, requests_per_hour=1000)
   ```

2. **Jina Reader:** If no API key, reduce:
   ```python
   "jina": RateLimitConfig(requests_per_minute=15, requests_per_hour=500)
   ```

3. **YouTube:** Consider implementing unit-based tracking instead of RPM

### Code Location

Rate limit config in: `backend/utils/rate_limiter.py:40-55`

### Best Practices

1. **Monitor 429 errors** - Add alerting for rate limit hits
2. **Use exponential backoff** - Already implemented ✅
3. **Cache responses** - Reduce redundant API calls
4. **Batch requests** - YouTube allows batching (5 videos = 1 unit)

---

## Sources

- [Google Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)
- [YouTube API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [Jina AI Reader](https://jina.ai/reader/)
- [Supabase Rate Limits](https://supabase.com/docs/guides/auth/rate-limits)
- [Supadata Docs](https://docs.supadata.ai)

---

## Unresolved Questions

1. Which Gemini tier is the project currently on? (affects limits significantly)
2. Is a Jina API key configured? (affects Jina limits)
3. Should we implement YouTube unit-based tracking instead of RPM?
