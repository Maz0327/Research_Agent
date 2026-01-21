# Backend API Routes - Action Items & Code Fixes

**Report:** tester-251228-1458-backend-api-routes.md
**Status:** Ready for implementation
**Priority:** CRITICAL blocker, then P1-P7

---

## CRITICAL - P0: Import Error Fix

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py`
**Lines:** 18

**Current Code (WRONG):**
```python
from backend.state.impl.supabase_store import get_supabase_client
```

**Fixed Code:**
```python
from backend.auth.ban_check import get_supabase_client
```

**Why:** The function exists in `backend/auth/ban_check.py:17`, not in supabase_store.py. The private version `_get_supabase_client()` exists in supabase_store but is not exported.

**Impact:** This blocks the entire application from starting. All 13 job route tests fail with import error.

**Test Verification:**
```bash
# After fix, this should pass:
python -m pytest backend/tests/test_jobs_routes.py -v
```

---

## HIGH - P1: Add page_size Validation to Admin Queries

**Files:**
1. `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py:91-177` (GET /admin/users)
2. `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py:180-234` (GET /admin/jobs)
3. `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py:338-392` (GET /admin/errors)

**Issue:** Users can request unlimited page_size, causing memory exhaustion DoS.

**Current Code (Line 94-95, /admin/users example):**
```python
@router.get("/users")
async def list_admin_users(
    user: AuthUser = Depends(require_admin),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Items per page (max 100)"),
):
```

**Status:** CORRECT in /admin/users (has `le=MAX_PAGE_SIZE`)

**NEEDS FIX - Lines 183-184 (/admin/jobs):**
```python
async def list_admin_jobs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
```

**Fix:**
```python
async def list_admin_jobs(
    user: AuthUser = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
```

**NEEDS FIX - Lines 341-345 (/admin/errors):**
```python
async def list_error_logs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
```

**Fix:**
```python
async def list_error_logs(
    user: AuthUser = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
```

---

## HIGH - P2: Add Date Format Validation to Admin Filters

**Files:**
1. `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py:180-234` (GET /admin/jobs)
2. `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py:338-392` (GET /admin/errors)

**Issue:** Date parameters should validate ISO 8601 format before passing to Supabase.

**Current Code (Lines 187-188, /admin/jobs):**
```python
date_from: Optional[str] = None,
date_to: Optional[str] = None,
```

**Fix - Add validation helper:**
```python
def validate_iso_date(date_str: Optional[str]) -> Optional[str]:
    """Validate ISO 8601 date format."""
    if not date_str:
        return None
    try:
        # Accept ISO 8601 formats
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_str
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date_str}. Use ISO 8601 (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        )
```

**Apply to both endpoints:**

```python
# In list_admin_jobs
if date_from:
    date_from = validate_iso_date(date_from)
if date_to:
    date_to = validate_iso_date(date_to)

# In list_error_logs
if date_from:
    date_from = validate_iso_date(date_from)
if date_to:
    date_to = validate_iso_date(date_to)
```

---

## HIGH - P3: Add Rate Limiting to Admin Routes

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/admin_routes.py`

**Issue:** Admin routes have no rate limiting, vulnerable to admin DoS attacks.

**Fix - Add rate limits in admin_routes.py:**

Update `/Users/maz/Documents/GitHub/Research_Agent/backend/app/rate_limiter.py` first:

```python
# Add to RATE_LIMITS dict:
RATE_LIMITS = {
    # ... existing settings & jobs & transcripts rates ...

    # Admin routes
    "admin_stats": "30/minute",
    "admin_users": "30/minute",
    "admin_jobs": "30/minute",
    "admin_errors": "30/minute",
    "admin_job_cancel": "30/minute",
    "admin_job_delete": "10/minute",
    "admin_user_ban": "10/minute",
    "admin_error_resolve": "30/minute",
}
```

Then add decorators in admin_routes.py:

```python
from backend.app.rate_limiter import limiter, RATE_LIMITS

@router.get("/stats")
@limiter.limit(RATE_LIMITS["admin_stats"])
async def get_admin_stats(request: Request, user: AuthUser = Depends(require_admin)):
    # ... rest of code

@router.get("/users")
@limiter.limit(RATE_LIMITS["admin_users"])
async def list_admin_users(request: Request, user: AuthUser = Depends(require_admin), ...):
    # ... rest of code

@router.get("/jobs")
@limiter.limit(RATE_LIMITS["admin_jobs"])
async def list_admin_jobs(request: Request, user: AuthUser = Depends(require_admin), ...):
    # ... rest of code

@router.post("/jobs/{job_id}/cancel")
@limiter.limit(RATE_LIMITS["admin_job_cancel"])
async def admin_cancel_job(job_id: str, request: Request, user: AuthUser = Depends(require_admin)):
    # ... rest of code

@router.delete("/jobs/{job_id}")
@limiter.limit(RATE_LIMITS["admin_job_delete"])
async def admin_delete_job(job_id: str, request: Request, user: AuthUser = Depends(require_admin)):
    # ... rest of code

@router.get("/errors")
@limiter.limit(RATE_LIMITS["admin_errors"])
async def list_error_logs(request: Request, user: AuthUser = Depends(require_admin), ...):
    # ... rest of code

@router.post("/errors/{error_id}/resolve")
@limiter.limit(RATE_LIMITS["admin_error_resolve"])
async def resolve_error(error_id: str, request: Request, user: AuthUser = Depends(require_admin)):
    # ... rest of code

@router.post("/users/{user_id}/ban")
@limiter.limit(RATE_LIMITS["admin_user_ban"])
async def ban_user(user_id: str, request: Request, admin_user: AuthUser = Depends(require_admin)):
    # ... rest of code

@router.post("/users/{user_id}/unban")
@limiter.limit(RATE_LIMITS["admin_user_ban"])
async def unban_user(user_id: str, request: Request, admin_user: AuthUser = Depends(require_admin)):
    # ... rest of code
```

Note: All admin route handlers need `request: Request` parameter for rate limiter.

---

## HIGH - P3b: Add Rate Limiting to Slack Route

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/slack_routes.py`

**Issue:** Slack endpoint has no rate limiting.

**Current Code (Line 14):**
```python
@router.post("/slack/command")
async def slack_command(
```

**Fix - Add rate limit decorator and request param:**

```python
from backend.app.rate_limiter import limiter

@router.post("/slack/command")
@limiter.limit("10/minute")  # Slack can retry, be generous
async def slack_command(
    request: Request,
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
):
```

---

## MEDIUM - P4: Create Test Suites for Admin/Settings/Transcripts Routes

**Files to create:**
1. `backend/tests/test_admin_routes.py`
2. `backend/tests/test_settings_routes.py`
3. `backend/tests/test_transcripts_routes.py`
4. `backend/tests/test_slack_routes.py`

**Template for admin_routes tests:**

```python
"""Tests for backend/app/routes/admin_routes.py"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def app_client():
    from backend.app.main import app
    return TestClient(app)

@pytest.fixture
def mock_admin_user():
    from backend.auth import AuthUser
    return AuthUser(
        user_id="admin-123",
        email="admin@example.com",
        role="admin"
    )

class TestAdminStats:
    @patch("backend.app.routes.admin_routes.get_supabase_client")
    def test_stats_cached(self, mock_supabase, app_client):
        # Test that stats are cached
        pass

    @patch("backend.app.routes.admin_routes.get_supabase_client")
    def test_stats_requires_admin(self, mock_supabase, app_client):
        # Test auth requirement
        pass

class TestAdminUsers:
    def test_page_size_limited(self, app_client):
        # Test that page_size is capped at MAX_PAGE_SIZE
        pass

    def test_batch_query_optimization(self, app_client):
        # Test that RPC is used for batch query
        pass

# Similar classes for other endpoints
```

---

## MEDIUM - P5: Cache Ban Status Check

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/auth/ban_check.py`

**Issue:** Every authenticated request hits database for ban check.

**Current Code (Lines 25-60):**
```python
async def check_user_banned(user_id: str) -> bool:
    """Check if a user is banned via the user_settings table."""
    client = get_supabase_client()
    if not client:
        logger.debug("Supabase not configured, skipping ban check")
        return False

    try:
        result = client.table("user_settings").select("is_banned").eq(
            "user_id", user_id
        ).execute()
        # ... rest
```

**Fix - Add cache with TTL:**

```python
from functools import lru_cache
from time import time
from typing import Tuple

# Cache with 10 minute TTL
_ban_cache: dict[str, Tuple[bool, float]] = {}
BAN_CACHE_TTL = 600  # 10 minutes

async def check_user_banned(user_id: str) -> bool:
    """Check if a user is banned via the user_settings table (cached)."""
    global _ban_cache

    # Check cache
    if user_id in _ban_cache:
        is_banned, timestamp = _ban_cache[user_id]
        if time() - timestamp < BAN_CACHE_TTL:
            return is_banned
        else:
            del _ban_cache[user_id]  # Expired

    client = get_supabase_client()
    if not client:
        logger.debug("Supabase not configured, skipping ban check")
        return False

    try:
        result = client.table("user_settings").select("is_banned").eq(
            "user_id", user_id
        ).execute()

        if result.data and len(result.data) > 0:
            is_banned = result.data[0].get("is_banned", False)
            # Cache result
            _ban_cache[user_id] = (is_banned, time())
            if is_banned:
                logger.info(
                    "Banned user attempted access",
                    event="ban_check_blocked",
                    user_id=user_id[:8],
                )
            return is_banned

        # Cache that user is not banned
        _ban_cache[user_id] = (False, time())
        return False

    except Exception as e:
        logger.error(f"Error checking ban status: {e}")
        # On error, assume not banned to allow access
        return False
```

---

## MEDIUM - P6: Validate Video URLs in Transcripts

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/transcripts_routes.py`

**Issue:** No validation on video URLs, no limit on count.

**Current Code (Lines 27-39):**
```python
@router.post("")
@limiter.limit(RATE_LIMITS["transcripts_create"])
async def extract_transcripts(
    request: Request,
    transcript_request: TranscriptRequest,
):
    """Extract transcripts from YouTube videos."""
    video_count = len(transcript_request.video_urls)
```

**Fix - Add validation:**

```python
import re

def _validate_youtube_url(url: str) -> str:
    """Validate and normalize YouTube URL."""
    # Accept multiple YouTube URL formats
    patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return url  # Valid

    raise ValueError(f"Invalid YouTube URL: {url}")

MAX_VIDEOS_PER_REQUEST = 50  # Reasonable limit

async def extract_transcripts(
    request: Request,
    transcript_request: TranscriptRequest,
):
    """Extract transcripts from YouTube videos."""
    # Validate video count
    video_count = len(transcript_request.video_urls)
    if video_count == 0:
        raise HTTPException(status_code=400, detail="No videos provided")

    if video_count > MAX_VIDEOS_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_VIDEOS_PER_REQUEST} videos per request"
        )

    # Validate each URL
    try:
        for url in transcript_request.video_urls:
            _validate_youtube_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ... rest of code
```

---

## MEDIUM - P7: Refactor Slack Form Parsing

**File:** `/Users/maz/Documents/GitHub/Research_Agent/backend/app/routes/slack_routes.py`

**Issue:** Manual form parsing is error-prone and doesn't handle standard format.

**Current Code (Lines 48-62):**
```python
# Parse form data from body
form_data = {}
for pair in body.split("&"):
    if "=" in pair:
        key, value = pair.split("=", 1)
        # URL decode
        form_data[urllib.parse.unquote(key)] = urllib.parse.unquote(value)

# Extract required fields
text = form_data.get("text", "").strip()
user_id = form_data.get("user_id", "")
```

**Fix - Use FastAPI Form:**

```python
from fastapi import Form
from typing import Optional

@router.post("/slack/command")
@limiter.limit("10/minute")
async def slack_command(
    request: Request,
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
    text: str = Form(...),
    user_id: str = Form(...),
    user_name: str = Form(...),
    channel_id: str = Form(...),
    channel_name: str = Form(...),
    response_url: str = Form(...),
    team_id: str = Form(...),
):
    """Handle Slack slash command."""
    settings = require_slack()

    # Get raw body for signature verification
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8")

    # Verify signature
    try:
        if not verify_slack_signature(
            signing_secret=settings.slack_signing_secret,
            timestamp=x_slack_request_timestamp,
            body=body,
            signature=x_slack_signature,
        ):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    except ValueError as e:
        logger.warning(f"Signature verification error: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    # Validate topic
    text = text.strip()
    if not text:
        return {
            "response_type": "ephemeral",
            "text": "❌ Please provide a research topic. Usage: /research <topic>",
        }

    # Create job with config_json
    try:
        config_json = {"topic": text}
        job = create_job(config_json=config_json)
    except Exception as e:
        logger.exception(f"Failed to create job: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ Failed to create research job: {str(e)}",
        }

    # Enqueue Celery task with Slack payload
    slack_payload = {
        "user_id": user_id,
        "user_name": user_name,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "response_url": response_url,
        "team_id": team_id,
    }

    logger.info(
        f"Enqueuing research job {job.job_id} from Slack user {user_id} "
        f"for topic: {text}"
    )

    run_research_job.delay(job.job_id, text, slack_payload=slack_payload)

    # Return immediate response
    return {
        "response_type": "ephemeral",
        "text": f"✅ Started research job: `{job.job_id}`\nTopic: {text}",
    }
```

Note: This change requires removing the manual body parsing and relying on FastAPI's form handling.

---

## Testing Strategy After Fixes

### Step 1: Verify Critical P0 Fix
```bash
cd /Users/maz/Documents/GitHub/Research_Agent
source venv/bin/activate

# This should now work (was blocking before)
python -m pytest backend/tests/test_jobs_routes.py::TestCreateJobEndpoint::test_create_job_requires_prompt -v
```

### Step 2: Run All Backend Tests
```bash
python -m pytest backend/tests/ -v --tb=short
```

### Step 3: Manual Route Testing
```bash
# Start API
uvicorn backend.app.main:app --reload

# Test critical routes
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test topic", "pipeline": "full"}'
```

### Step 4: Security Testing
```bash
# Test page_size limits
curl "http://localhost:8000/admin/jobs?page_size=999999"

# Test date format validation
curl "http://localhost:8000/admin/jobs?date_from=invalid"

# Test rate limiting
for i in {1..15}; do curl http://localhost:8000/jobs; done
```

---

## Priority Implementation Order

1. **P0 (CRITICAL):** Fix admin_routes.py import - 5 minutes
2. **P1 (HIGH):** Add page_size validation - 10 minutes
3. **P2 (HIGH):** Add date validation - 15 minutes
4. **P3 (HIGH):** Add rate limits - 20 minutes
5. **P4 (MEDIUM):** Create test suites - 2-3 hours
6. **P5 (MEDIUM):** Cache ban check - 30 minutes
7. **P6 (MEDIUM):** Validate video URLs - 20 minutes
8. **P7 (MEDIUM):** Refactor Slack parsing - 30 minutes

**Total time: ~4-5 hours to complete all fixes**
