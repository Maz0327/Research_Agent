# Research Agent Troubleshooting Guide

Common issues and their solutions.

---

## Pipeline Issues

### "No transcript available"

**Symptom:** Job completes with `video_only` mode warning.

**Cause:**
- Supadata API failed or unavailable
- Video has no captions
- Whisper fallback not configured

**Solution:**
- System automatically falls back to `video_only` mode (LOW confidence)
- Job still completes with visual analysis
- Check Supadata API key is valid

**Behavior:**
- Quotes not available in `video_only` mode
- Uses `approximate_observations` instead
- Confidence ceiling enforced at LOW

---

### "Confidence ceiling exceeded"

**Symptom:** Warning in job output about confidence clamping.

**Cause:** LLM returned confidence higher than mode allows.

**Solution:**
- Automatic — system auto-corrects to ceiling
- Warning logged for transparency
- No action needed

**Mode Ceilings:**
| Mode | Ceiling |
|------|---------|
| transcript_grounded | HIGH |
| caption_grounded | MEDIUM |
| video_only | LOW |
| text_provided | MEDIUM |
| ocr_extracted | MEDIUM |
| article_fetched | HIGH |

---

### "Quote verification failed"

**Symptom:** Quotes marked as `unverified` in output.

**Cause:** Extracted quote not found in source transcript.

**Solution:**
- Quote included but marked unverified
- Check transcript quality
- Fuzzy matching used (80% threshold)

**Note:** Unverified quotes are not removed, just flagged.

---

### "Producer packet gating failed"

**Symptom:** Cannot generate Doc 3 (Producer Packet).

**Cause:** Job doesn't meet gating requirements.

**Requirements:**
- 4+ sources analyzed
- At least 1 source with HIGH confidence
- Job status = completed

**Solution:** Add more sources using evolving jobs feature.

---

## Infrastructure Issues

### Redis Connection Refused

**Symptom:** `ConnectionRefusedError: [Errno 111] Connection refused`

**Cause:** Redis server not running.

**Solution:**
```bash
# Start Redis
redis-server

# Or on macOS with Homebrew
brew services start redis
```

---

### Celery Worker Not Processing

**Symptom:** Jobs stuck in `pending` status.

**Cause:** Celery worker not running or crashed.

**Solution:**
```bash
# Check if worker is running
ps aux | grep celery

# Restart worker
celery -A backend.worker worker --loglevel=INFO
```

---

### Gemini Rate Limit

**Symptom:** `429 Too Many Requests` or slow processing.

**Cause:** Exceeded Gemini API rate limits.

**Solution:**
- Built-in rate limiting handles this automatically
- 60 requests/minute limit with exponential backoff
- Jobs will slow down but not fail
- Check Gemini quota in Google Cloud Console

---

### Import Errors

**Symptom:** `ModuleNotFoundError` or `ImportError`

**Cause:** Dependencies not installed or venv not activated.

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify imports
python -c "from backend.pipeline.stages import *"
```

---

## API Issues

### 401 Unauthorized

**Symptom:** All API calls return 401.

**Cause:** Missing or invalid JWT token.

**Solution:**
- For development: Check Supabase JWT configuration
- Ensure `Authorization: Bearer <token>` header is set
- Token may be expired

---

### 400 Bad Request

**Symptom:** API returns validation error.

**Common Causes:**
- Invalid URL format
- Content exceeds limits (50k chars for text, 10MB for images)
- Missing required fields

**Check:**
- API documentation: `http://localhost:8000/docs`
- Request body matches expected schema

---

## Test Failures

### Tests Fail After Code Changes

**Solution:**
```bash
# Run full test suite
pytest backend/tests/ -v --tb=short

# Check specific test
pytest backend/tests/test_semantic_models.py -v

# Expected: 948 tests passing
```

### Mock Import Errors

**Symptom:** `AttributeError: module has no attribute`

**Cause:** Mock path doesn't match import location.

**Solution:** Mock at the import location, not module definition.
```python
# Wrong
@patch("backend.integrations.gemini_client.GeminiClient")

# Right (if imported into stages)
@patch("backend.pipeline.stages.semantic_extraction.GeminiClient")
```

---

## Performance Issues

### Jobs Taking Too Long

**Expected Times:**
| Job Type | Sources | Time |
|----------|---------|------|
| Quick | 3 | 1-2 min |
| Standard | 10 | 5-8 min |
| Deep | 25 | 15-25 min |

**Bottlenecks:**
1. Gemini API calls (10-30s per source)
2. Transcript fetching (5-30s per video)
3. Rate limiting pauses

**Solution:**
- Use fewer sources for testing
- Check API quotas
- Monitor worker logs for bottlenecks

---

## Getting Help

1. Check logs: Worker and API both log to stdout
2. Check job warnings: `GET /jobs/{job_id}/warnings`
3. Run diagnostics: `GET /api/v1/status`
4. File issue: Include job_id and relevant logs
