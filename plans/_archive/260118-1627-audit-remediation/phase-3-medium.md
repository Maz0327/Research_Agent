# Phase 3: Medium Priority Issues Implementation

**Priority:** Future Sprint
**Total Effort:** ~3h
**Issues:** M1-M11

---

## Security Issues (M1-M5)

### M1: Fix Ban Check Fail-Open Behavior

**File:** `backend/auth/ban_check.py`
**Lines:** 59-69
**Risk:** Banned users may access system if database errors occur

#### Implementation
```python
async def check_ban_status(user_id: str) -> bool:
    """Check if user is banned.

    Returns:
        True if user is allowed, raises on error or ban
    """
    try:
        # Database query for ban status
        result = await db.query_ban_status(user_id)
        if result.is_banned:
            raise BannedUserError(f"User {user_id[:8]}... is banned")
        return True
    except DatabaseError as e:
        # Fail CLOSED - deny access on error
        logger.error(f"Ban check failed for {user_id[:8]}...: {e}")
        raise ServiceUnavailableError(
            "Unable to verify user status. Please try again."
        )
```

---

### M2: Validate CORS Origins

**File:** `backend/app/main.py`
**Lines:** 40-54

#### Implementation
```python
from backend.config import settings

ALLOWED_ORIGINS = [
    settings.frontend_url,  # e.g., https://app.example.com
    "http://localhost:3000",  # Local development
]

if "*" in ALLOWED_ORIGINS:
    raise ValueError("CORS wildcard '*' is not allowed in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### M3: Strip API Keys from Video URLs

**File:** `backend/integrations/gemini_client.py`
**Lines:** ~670

#### Implementation
```python
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def strip_api_key_from_url(url: str) -> str:
    """Remove API key parameters from URL."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Remove common API key parameter names
    for key_param in ['key', 'api_key', 'apikey', 'apiKey', 'token']:
        query_params.pop(key_param, None)

    clean_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=clean_query))
```

---

### M4: Secure Rate Limiting IP Detection

**File:** `backend/utils/rate_limiter.py`

#### Implementation
```python
from fastapi import Request

def get_client_ip(request: Request, trusted_proxies: list[str] = None) -> str:
    """Get client IP, trusting X-Forwarded-For only from known proxies.

    Args:
        request: FastAPI request
        trusted_proxies: List of trusted proxy IPs (e.g., ["10.0.0.1"])

    Returns:
        Client IP address
    """
    trusted_proxies = trusted_proxies or []

    # Get direct connection IP
    client_ip = request.client.host

    # Only trust X-Forwarded-For from known proxies
    if client_ip in trusted_proxies:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first (original client) IP
            client_ip = forwarded.split(",")[0].strip()

    return client_ip
```

---

### M5: Add Security Headers Middleware

**File:** `backend/app/main.py`

#### Implementation
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # CSP for API responses
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "frame-ancestors 'none'"
        )

        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## Integration Issues (M6-M9)

### M6: Add Tavily Health Check

**File:** `backend/integrations/tavily_client.py`

#### Implementation
```python
import httpx
from backend.utils.rate_limiter import get_rate_limit_stats

async def tavily_health_check() -> bool:
    """Check if Tavily API is healthy before batch operations.

    Returns:
        True if healthy, False otherwise
    """
    stats = get_rate_limit_stats("tavily")

    # If recent failure rate > 10%, skip batch
    if stats.get("recent_failure_rate", 0) > 0.10:
        logger.warning("Tavily health check failed: high failure rate")
        return False

    # Optional: Make a lightweight test request
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use a simple test query
            response = await client.post(
                "https://api.tavily.com/search",
                json={"query": "test", "max_results": 1},
                headers={"Authorization": f"Bearer {settings.tavily_api_key}"}
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Tavily health check failed: {e}")
        return False
```

---

### M7: Add Serper Rate Limiting

**File:** `backend/integrations/serper_client.py`
**Lines:** 36-42

#### Implementation
```python
from backend.utils.rate_limiter import with_rate_limit

@with_rate_limit("serper")
async def search_serper(query: str, ...) -> dict:
    """Search with Serper API (rate limited)."""
    ...
```

Add to rate limit config:
```python
"serper": RateLimitConfig(
    requests_per_minute=100,
    max_retries=3,
    base_backoff=1.0,
),
```

---

### M8: Add Exa Rate Limiting

**File:** `backend/integrations/exa_client.py`
**Lines:** 37-106

#### Implementation
```python
from backend.utils.rate_limiter import with_rate_limit

@with_rate_limit("exa")
async def search_exa(query: str, ...) -> list:
    """Search with Exa API (rate limited)."""
    ...
```

Add to rate limit config:
```python
"exa": RateLimitConfig(
    requests_per_minute=60,
    max_retries=3,
    base_backoff=1.0,
),
```

---

### M9: Add Reddit Rate Limiting

**File:** `backend/integrations/reddit_client.py`
**Lines:** 44-114

#### Implementation
```python
from backend.utils.rate_limiter import with_rate_limit

@with_rate_limit("reddit")
async def search_reddit(query: str, ...) -> list:
    """Search Reddit (rate limited)."""
    ...
```

Add to rate limit config:
```python
"reddit": RateLimitConfig(
    requests_per_minute=30,  # Reddit is strict
    max_retries=2,
    base_backoff=2.0,
),
```

---

## Frontend Issues (M10-M11)

### M10: Add Token Expiry Validation

**File:** `frontend/lib/api-client.ts`

#### Implementation
```typescript
import { jwtDecode } from 'jwt-decode';

interface JWTPayload {
  exp: number;
  sub: string;
}

function isTokenExpiringSoon(token: string, bufferSeconds = 60): boolean {
  try {
    const decoded = jwtDecode<JWTPayload>(token);
    const expiresAt = decoded.exp * 1000; // Convert to ms
    const buffer = bufferSeconds * 1000;
    return Date.now() >= (expiresAt - buffer);
  } catch {
    return true; // Treat invalid tokens as expiring
  }
}

async function getValidToken(): Promise<string> {
  const session = await supabase.auth.getSession();
  const token = session?.data?.session?.access_token;

  if (!token || isTokenExpiringSoon(token)) {
    // Proactively refresh
    const { data } = await supabase.auth.refreshSession();
    return data?.session?.access_token ?? '';
  }

  return token;
}
```

---

### M11: Add API URL Whitelist

**File:** `frontend/lib/constants.ts`
**Lines:** ~44

#### Implementation
```typescript
const ALLOWED_API_DOMAINS = [
  'localhost',
  '127.0.0.1',
  'api.researchagent.com',  // Production
  'api-staging.researchagent.com',  // Staging
];

function validateApiUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return ALLOWED_API_DOMAINS.includes(parsed.hostname);
  } catch {
    return false;
  }
}

export const API_BASE_URL = (() => {
  const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (!validateApiUrl(url)) {
    console.error(`Invalid API URL: ${url}`);
    throw new Error('Invalid API URL configuration');
  }
  return url;
})();
```

---

## Verification Checklist

After completing Phase 3:
- [ ] `pytest backend/tests/ -v` passes
- [ ] `cd frontend && npm run build && npm run lint` passes
- [ ] Security headers present in API responses
- [ ] Rate limiting active for Serper/Exa/Reddit
- [ ] Commit: `security: Harden auth, CORS, rate limiting, and frontend validation (M1-M11)`
