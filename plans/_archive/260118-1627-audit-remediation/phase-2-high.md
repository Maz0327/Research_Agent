# Phase 2: High Priority Issues Implementation

**Priority:** Next Sprint
**Total Effort:** ~4h 45m
**Issues:** H1, H2, H3, H5, H6, H7, H8, H9 (H4 already fixed)

---

## H1: Prompt Injection Sanitization

**File:** `backend/pipeline/extraction.py`
**Lines:** 352-368
**Risk:** User content injected into prompts bypasses extraction rules
**Effort:** 2h

### Implementation Steps

1. Create sanitization utility in `backend/utils/prompt_sanitizer.py`:
   ```python
   """Sanitize user content before embedding in LLM prompts."""

   import re
   from typing import Optional

   # Patterns that could manipulate LLM behavior
   INJECTION_PATTERNS = [
       r"(?i)\bignore\s+(previous|above|all)\s+instructions?\b",
       r"(?i)\bsystem\s*:\s*",
       r"(?i)\b(assistant|user|human)\s*:\s*",
       r"(?i)\[INST\]",
       r"(?i)\[/INST\]",
       r"(?i)<<SYS>>",
       r"(?i)<</SYS>>",
       r"╔|╗|╚|╝|╠|╣|║",  # Box chars used in identity lock
   ]

   def sanitize_for_llm_prompt(
       content: str,
       max_length: Optional[int] = 50000,
   ) -> str:
       """
       Sanitize user-provided content for safe LLM prompt embedding.

       Args:
           content: Raw user content
           max_length: Maximum allowed length (truncate if exceeded)

       Returns:
           Sanitized content safe for prompt embedding
       """
       if not content:
           return ""

       # Truncate if too long
       if max_length and len(content) > max_length:
           content = content[:max_length] + "\n[CONTENT TRUNCATED]"

       # Escape injection patterns
       for pattern in INJECTION_PATTERNS:
           content = re.sub(pattern, "[REDACTED]", content)

       # Escape potential markdown that could confuse parsing
       # But preserve legitimate formatting
       content = content.replace("```", "'''")

       return content.strip()
   ```

2. Apply sanitization in extraction.py before building prompts:
   ```python
   from backend.utils.prompt_sanitizer import sanitize_for_llm_prompt

   # In build_extraction_prompt or equivalent:
   sanitized_content = sanitize_for_llm_prompt(source_content)
   ```

3. Add tests for sanitization

### Tests
- [ ] Test injection patterns are blocked
- [ ] Test legitimate content preserved
- [ ] Test truncation works
- [ ] Integration test with extraction pipeline

---

## H2: JWT Email Null Check

**File:** `backend/auth/__init__.py`
**Lines:** 69-74
**Risk:** Authorization bypass if email assumed present
**Effort:** 30m

### Current Code
```python
email = payload.get("email")
if not email:
    user_metadata = payload.get("user_metadata", {})
    email = user_metadata.get("email")
# email can still be None here
```

### Implementation Steps

1. Add explicit logging for missing email:
   ```python
   email = payload.get("email")
   if not email:
       user_metadata = payload.get("user_metadata", {})
       email = user_metadata.get("email")

   if not email:
       logger.warning(
           f"User {user_id[:8]}... authenticated without email claim"
       )
   ```

2. Document in AuthUser model that email is Optional:
   ```python
   @dataclass
   class AuthUser:
       user_id: str
       email: Optional[str]  # May be None for some auth methods
       role: str
   ```

3. Update any code that assumes email is present:
   ```bash
   grep -rn "\.email" backend/ --include="*.py" | grep -v "Optional"
   ```

### Tests
- [ ] Test auth works with missing email
- [ ] Test logging occurs for missing email
- [ ] Verify no code assumes email is non-None

---

## H3: YouTube URL Validation in Gemini

**File:** `backend/integrations/gemini_client.py`
**Lines:** ~670
**Risk:** Malformed URLs cause API errors
**Effort:** 15m

### Implementation Steps

1. Find the YouTube URL validation function (should exist per audit):
   ```bash
   grep -n "validate_youtube_url\|is_valid_youtube" backend/
   ```

2. Call validation before creating video Part:
   ```python
   from backend.utils.url_validators import validate_youtube_url  # or wherever it is

   def analyze_youtube_video(self, video_url: str, ...):
       # Validate URL first
       if not validate_youtube_url(video_url):
           raise ValueError(f"Invalid YouTube URL: {video_url}")

       # Proceed with video Part creation
       ...
   ```

### Tests
- [ ] Test invalid URLs are rejected
- [ ] Test valid URLs pass through

---

## H5: Gemini JSON Parse Error Handling

**File:** `backend/integrations/gemini_client.py`
**Lines:** 582-591
**Risk:** Empty extractions treated as successful
**Effort:** 15m

### Current Code
```python
except GeminiParseError as e:
    logger.warning(f"JSON parse failed: {e.message}")
    return {
        "data": {},
        "cost": cost,
        "error": f"JSON parse error: {e.message}",
        "raw_response": e.raw_response,
    }
```

### Implementation Steps

1. Raise exception instead of returning error dict:
   ```python
   except GeminiParseError as e:
       logger.error(f"JSON parse failed: {e.message}")
       logger.debug(f"Raw response: {text[:500]}...")
       raise RuntimeError(
           f"Gemini JSON parse failed: {e.message}"
       ) from e
   ```

2. Update callers to handle the exception:
   ```bash
   grep -rn "generate_json" backend/pipeline/
   ```

3. Ensure callers have try/except:
   ```python
   try:
       result = gemini_client.generate_json(prompt, schema)
   except RuntimeError as e:
       ctx.add_warning(f"Extraction failed: {e}")
       return ctx  # Continue with empty extraction
   ```

### Tests
- [ ] Test RuntimeError raised on parse failure
- [ ] Test callers handle exception gracefully

---

## H6: Whisper Video ID Validation

**File:** `backend/integrations/whisper_client.py`
**Lines:** 190-241
**Risk:** Command injection via malicious video_id
**Effort:** 15m

### Implementation Steps

1. Find or create video ID validation:
   ```python
   import re

   def _validate_video_id(video_id: str) -> bool:
       """Validate YouTube video ID format.

       Valid video IDs are 11 characters: alphanumeric, dash, underscore.
       """
       return bool(re.match(r'^[A-Za-z0-9_-]{11}$', video_id))
   ```

2. Add validation at entry point:
   ```python
   def transcribe_youtube(
       self,
       video_id: str,
       max_duration_minutes: float = 60.0,
   ) -> Dict:
       # Validate video ID first
       if not _validate_video_id(video_id):
           raise ValueError(f"Invalid YouTube video ID: {video_id}")

       try:
           audio_path = self.download_audio(video_id)
           ...
   ```

### Tests
- [ ] Test invalid video IDs rejected
- [ ] Test valid video IDs accepted
- [ ] Test command injection attempts blocked

---

## H7: Perplexity Response Validation

**File:** `backend/integrations/perplexity_client.py`
**Lines:** 90-120
**Risk:** Silent failures if API response format changes
**Effort:** 1h

### Implementation Steps

1. Create Pydantic models for response:
   ```python
   from pydantic import BaseModel, Field
   from typing import Optional

   class PerplexityMessage(BaseModel):
       role: str
       content: str

   class PerplexityChoice(BaseModel):
       message: PerplexityMessage
       index: int = 0
       finish_reason: Optional[str] = None

   class PerplexityResponse(BaseModel):
       id: str
       model: str
       choices: list[PerplexityChoice]
       citations: list[str] = Field(default_factory=list)
   ```

2. Validate response before extracting:
   ```python
   def _extract_urls_from_response(response: dict) -> list[dict]:
       """Extract URLs from validated Perplexity response."""
       try:
           validated = PerplexityResponse.model_validate(response)
       except ValidationError as e:
           logger.warning(f"Perplexity response validation failed: {e}")
           return []

       content = validated.choices[0].message.content if validated.choices else ""
       citations = validated.citations
       ...
   ```

### Tests
- [ ] Test valid response parsed correctly
- [ ] Test invalid response returns empty list
- [ ] Test missing fields handled gracefully

---

## H8: YouTube 429 Rate Limit Handling

**File:** `backend/integrations/youtube_client.py`
**Lines:** 200-207
**Risk:** Quota exhausted early, all subsequent jobs fail
**Effort:** 30m

### Implementation Steps

1. Create QuotaExceededError:
   ```python
   class QuotaExceededError(Exception):
       """Raised when API quota is exhausted."""
       pass
   ```

2. Check for 429 status specifically:
   ```python
   try:
       response = client.get(url, params=params)
       response.raise_for_status()
   except httpx.HTTPStatusError as e:
       if e.response.status_code == 429:
           raise QuotaExceededError(
               "YouTube API quota exceeded. Try again later."
           ) from e
       raise
   ```

3. Update callers to handle QuotaExceededError differently:
   - Don't retry on quota errors
   - Log at ERROR level
   - Consider early termination of batch operations

### Tests
- [ ] Test 429 raises QuotaExceededError
- [ ] Test other errors raise normally
- [ ] Test callers handle QuotaExceededError

---

## H9: Harden DOMPurify Configuration

**File:** `frontend/components/job-card/DocumentCard.tsx`
**Lines:** ~144
**Risk:** XSS if misconfigured
**Effort:** 15m

### Current Code
```typescript
const sanitizedContent = DOMPurify.sanitize(rawContent);
```

### Implementation Steps

1. Add explicit configuration:
   ```typescript
   const DOMPURIFY_CONFIG = {
     ALLOWED_TAGS: [
       'p', 'br', 'strong', 'em', 'h1', 'h2', 'h3', 'h4',
       'ul', 'ol', 'li', 'pre', 'code', 'blockquote', 'div', 'span'
     ],
     ALLOWED_ATTR: ['style', 'class'],
     ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
   };

   const sanitizedContent = DOMPurify.sanitize(rawContent, DOMPURIFY_CONFIG);
   ```

2. Apply same config to title and subtitle:
   ```typescript
   const sanitizedTitle = DOMPurify.sanitize(title, DOMPURIFY_CONFIG);
   const sanitizedSubtitle = DOMPurify.sanitize(subtitle, DOMPURIFY_CONFIG);
   ```

### Tests
- [ ] Test malicious scripts stripped
- [ ] Test legitimate HTML preserved
- [ ] Manual XSS testing with payloads

---

## Verification Checklist

After completing Phase 2:
- [ ] `pytest backend/tests/ -v` passes
- [ ] `cd frontend && npm run build && npm run lint` passes
- [ ] No new warnings or errors
- [ ] Commit: `security: Fix prompt injection, auth, and validation issues (H1-H9)`
