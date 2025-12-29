# Backend Security & Code Quality Audit

**Auditor**: code-reviewer
**Date**: 2025-12-28 18:19
**Scope**: Backend API, authentication, configuration, route handlers

---

## Executive Summary

**Overall Assessment**: GOOD with MEDIUM-PRIORITY issues requiring attention

Backend demonstrates solid security foundations with JWT auth, rate limiting, input validation, ban checks. Found 12 issues across security, error handling, code quality.

**Critical**: 0 | **High**: 3 | **Medium**: 6 | **Low**: 3

---

## Scope

**Files Reviewed** (18 files, ~3,200 LOC):
- `backend/app/main.py` (187 lines)
- `backend/app/routes/*.py` (5 route modules)
- `backend/auth/*.py` (4 auth modules)
- `backend/config.py` (487 lines)
- `backend/app/rate_limiter.py`
- `backend/utils/validators.py`
- `backend/utils/error_handling.py`

**Focus Areas**:
- Authentication/authorization flows
- Input validation & sanitization
- SQL injection vectors
- OWASP Top 10 compliance
- Error handling & information leakage
- Type safety & code quality

---

## Critical Issues

**None found**

---

## High Priority Findings

### H1. Weak JWT Secret Enforcement - Production Risk
**File**: `backend/config.py:195-224`
**Severity**: HIGH
**OWASP**: A02:2021 - Cryptographic Failures

**Issue**:
```python
if len(v) < 64:
    raise ValueError("JWT secret must be at least 64 characters...")
```

Validation enforces 64+ chars BUT allows ANY 64-char string including weak patterns like:
- `"a" * 64` (single char repeated)
- Sequential patterns
- Low-entropy strings

Only checks for 20 unique chars which is insufficient for 512-bit security.

**Impact**: JWT tokens vulnerable to brute force if weak secret used.

**Evidence**: Line 217 checks `unique_chars < 20` but 20/64 = 31% uniqueness still allows weak secrets.

**Recommendation**:
```python
# Raise threshold to 40+ unique chars (62.5% entropy floor)
if unique_chars < 40:
    raise ValueError("JWT secret has insufficient entropy...")

# Add pattern detection for sequential/repeated chars
if re.search(r'(.)\1{5,}', v):  # 6+ repeated chars
    raise ValueError("JWT secret contains repeated patterns...")
```

---

### H2. Admin Email Cache Never Invalidates
**File**: `backend/auth/admin.py:10-30`
**Severity**: HIGH
**OWASP**: A01:2021 - Broken Access Control

**Issue**:
```python
_admin_emails: Optional[Set[str]] = None

def _load_admin_emails() -> Set[str]:
    global _admin_emails
    if _admin_emails is not None:
        return _admin_emails  # CACHED FOREVER
```

Admin list cached on first load, never refreshes. If `ADMIN_EMAILS` env var updated, requires app restart.

**Impact**:
- Cannot revoke admin access without restart (security incident response delay)
- Cannot grant emergency admin without restart
- Production config changes require downtime

**Attack Scenario**:
1. Admin account compromised
2. Remove from `ADMIN_EMAILS`
3. Attacker retains admin access until restart

**Recommendation**:
```python
# Option 1: TTL-based cache (60 seconds)
_admin_cache_time: Optional[datetime] = None
CACHE_TTL = 60  # seconds

def _load_admin_emails() -> Set[str]:
    global _admin_emails, _admin_cache_time
    now = datetime.utcnow()
    if _admin_emails and _admin_cache_time and (now - _admin_cache_time).seconds < CACHE_TTL:
        return _admin_emails
    # Reload...
    _admin_cache_time = now

# Option 2: Database-backed admin table (better for production)
# Use admin_users table from migrations
```

**Current Workaround**: `reload_admin_emails()` exists but never called.

---

### H3. Ban Check Fails Open on Database Error
**File**: `backend/auth/ban_check.py:59-69`
**Severity**: HIGH
**OWASP**: A01:2021 - Broken Access Control

**Issue**:
```python
except Exception as e:
    logger.error(f"Error checking ban status: {e}")
    # Fail open (allow access) on error to prevent lockout
    return False  # ALLOWS BANNED USERS ON DB ERROR
```

Ban check returns `False` (not banned) on ANY database error, allowing banned users through during outages.

**Impact**:
- Banned users regain access during DB issues
- DDoS on database bypasses ban system
- No fail-secure option

**Attack Scenario**:
1. User gets banned for abuse
2. Attacker causes Supabase timeout (rate limiting, network attack)
3. Ban check fails, returns False
4. Banned user regains full access

**Recommendation**:
```python
# Option 1: Fail-secure mode (strict)
except Exception as e:
    logger.error("Ban check failed - BLOCKING access", user_id=user_id, error=e)
    raise HTTPException(503, "Service temporarily unavailable")

# Option 2: Cache last-known ban status (resilient)
from backend.utils.cache import cache_get, cache_set

async def check_user_banned(user_id: str) -> bool:
    try:
        # Check database...
        cache_set(f"ban:{user_id}", is_banned, ttl_seconds=300)
        return is_banned
    except Exception:
        # Fallback to cache
        cached = cache_get(f"ban:{user_id}")
        if cached is not None:
            return cached
        # Only fail open if no cache available
        logger.critical("Ban check failed with no cache - fail open", user_id=user_id)
        return False
```

Recommend Option 2 with short TTL cache for resilience.

---

## Medium Priority Findings

### M1. CORS Origin Validation - String Matching Risk
**File**: `backend/app/main.py:39-50`
**Severity**: MEDIUM
**OWASP**: A05:2021 - Security Misconfiguration

**Issue**:
```python
cors_origins = [origin.strip() for origin in settings.frontend_origins.split(",")]
```

Manual string splitting without validation. Risk of:
- Trailing slashes causing mismatch (`https://app.com` vs `https://app.com/`)
- Wildcard misuse (if admin sets `*` in env var, it passes through)
- Protocol confusion (http vs https)

**Current State**: No wildcard detected (good), but input not normalized.

**Recommendation**:
```python
def parse_cors_origins(origins_str: str) -> list[str]:
    """Parse and validate CORS origins."""
    origins = []
    for origin in origins_str.split(","):
        origin = origin.strip().rstrip("/")  # Remove trailing slash
        if not origin:
            continue
        if origin == "*":
            logger.warning("CORS wildcard '*' detected - security risk in production")
            # Block in production or require explicit flag
            if settings.environment == "production":
                raise ValueError("CORS wildcard not allowed in production")
        if not origin.startswith(("http://", "https://")):
            raise ValueError(f"Invalid CORS origin (must start with http/https): {origin}")
        origins.append(origin)
    return origins

cors_origins = parse_cors_origins(settings.frontend_origins)
```

---

### M2. Request Size Limit Not Applied to All Routes
**File**: `backend/app/main.py:131-141`
**Severity**: MEDIUM
**OWASP**: A04:2021 - Insecure Design

**Issue**:
Middleware checks `content-length` header for 10MB limit BUT:
1. `content-length` can be omitted (HTTP/1.1 chunked encoding)
2. Slack webhook parses raw body without size check first
3. No streaming body size check

**Affected Endpoints**:
- `/slack/command` (line slack_routes.py:31) - reads full body into memory
- All POST endpoints relying on FastAPI body parsing

**Evidence**:
```python
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:  # ONLY IF HEADER EXISTS
        if int(content_length) > MAX_REQUEST_SIZE_BYTES:
            return JSONResponse(status_code=413, ...)
    return await call_next(request)
```

**Attack Scenario**:
1. Send POST without `Content-Length` header
2. Stream 100MB payload using chunked encoding
3. Backend OOM crash

**Recommendation**:
```python
# Add to middleware
MAX_BODY_READ = 10 * 1024 * 1024

async def limit_request_size(request: Request, call_next):
    # Check header first
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE_BYTES:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})

    # For chunked/no header: wrap body stream with size counter
    if request.method in ("POST", "PUT", "PATCH"):
        from starlette.datastructures import UploadFile
        # FastAPI/Starlette handles this at framework level
        # Set in app config:
        # app.router.lifespan_context.max_upload_size = MAX_REQUEST_SIZE_BYTES
        pass

    return await call_next(request)

# Better: Use Starlette's built-in
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    middleware=[
        Middleware(BaseHTTPMiddleware, max_upload_size=10*1024*1024)
    ]
)
```

**Note**: Starlette/FastAPI has built-in protection, but not explicitly configured. Recommend explicit limit.

---

### M3. Job ID Validation Inconsistent
**File**: Multiple route files
**Severity**: MEDIUM
**OWASP**: A03:2021 - Injection

**Issue**:
UUID validation duplicated in 4 files with try/except pattern:

**jobs_routes.py:236**:
```python
try:
    uuid.UUID(job_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid job ID format")
```

**Duplication**: Same code in:
- `jobs_routes.py:236, 295`
- `admin_routes.py:243, 274`
- `transcripts_routes.py:91`

**Problems**:
1. DRY violation (5 copies)
2. Inconsistent error messages
3. No centralized sanitization
4. validators.py:16 already has `validate_uuid()` function

**Impact**: Maintenance burden, potential for validation bypass if one instance weakened.

**Recommendation**:
```python
# Use existing validate_uuid from utils/validators.py
from backend.utils.validators import validate_uuid

@router.get("/{job_id}")
async def get_job_status(job_id: str, ...):
    job_id = validate_uuid(job_id, field_name="job_id")  # Raises ValidationError
    job = get_job(job_id)
    ...
```

Update all 5 locations to use centralized validator.

---

### M4. Subreddit Validation Mismatch
**File**: `backend/app/routes/jobs_routes.py:24,92`
**Severity**: MEDIUM
**OWASP**: A03:2021 - Injection

**Issue**:
Two different regex patterns for subreddit validation:

**jobs_routes.py:24**:
```python
SUBREDDIT_PATTERN = re.compile(r'^[a-zA-Z0-9_]{2,21}$')  # Allows 2-21 chars
```

**validators.py:221**:
```python
if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):  # Must start with letter, 3-21 chars
```

**Differences**:
1. jobs_routes allows 2 chars, validators requires 3
2. jobs_routes allows starting with digit, validators requires letter
3. Different error messages

**Reddit's Actual Rules** (per Reddit API docs):
- 3-21 characters
- Must start with letter
- Only letters, numbers, underscores

**Impact**: jobs_routes.py accepts invalid subreddits like `"2a"` or `"_x"`.

**Recommendation**:
```python
# Remove SUBREDDIT_PATTERN from jobs_routes.py
# Use validators.validate_subreddit_name() instead

def _validate_subreddits(subreddits: list) -> list[str]:
    if not isinstance(subreddits, list):
        raise ValueError("custom_subreddits must be a list")
    if len(subreddits) > MAX_SUBREDDITS:
        raise ValueError(f"Maximum {MAX_SUBREDDITS} custom subreddits allowed")

    validated = []
    for sr in subreddits:
        if not isinstance(sr, str):
            raise ValueError(f"Invalid subreddit name type: {type(sr).__name__}")
        # Use centralized validator
        validated.append(validate_subreddit_name(sr))
    return validated
```

---

### M5. Admin Self-Ban Not Prevented
**File**: `backend/app/routes/admin_routes.py:301-318`
**Severity**: MEDIUM
**OWASP**: A01:2021 - Broken Access Control

**Issue**:
```python
@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, admin_user: AuthUser = Depends(require_admin)):
    if user_id == admin_user.user_id:
        raise HTTPException(400, "Cannot ban yourself")  # ✓ Good
```

BUT unban endpoint has NO such check:
```python
@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, admin_user: AuthUser = Depends(require_admin)):
    # No self-check - admin can unban themselves if accidentally banned
```

**Inconsistency**: Ban prevents self-action, unban doesn't.

**Edge Case**: If admin is banned through database manipulation, they can still authenticate (due to H2 cache issue) and unban themselves.

**Recommendation**:
```python
# Decision: Allow self-unban as escape hatch, but log it
@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, admin_user: AuthUser = Depends(require_admin)):
    if user_id == admin_user.user_id:
        logger.warning(
            "Admin unbanned themselves",
            admin_id=admin_user.user_id,
            event="admin_self_unban"
        )
        # Allow but audit
    # ... rest of logic
```

Alternative: Require different admin to unban (stricter).

---

### M6. Error Log Stack Trace Exposure
**File**: `backend/app/routes/admin_routes.py:376`
**Severity**: MEDIUM
**OWASP**: A05:2021 - Security Misconfiguration

**Issue**:
```python
errors.append({
    ...
    "stack_trace": row.get("stack_trace"),  # Full stack trace in API response
    ...
})
```

Admin endpoint returns full stack traces to frontend, which may contain:
- File paths (reveals server structure)
- Environment details
- Sensitive variable names
- Internal implementation details

**Who Can Access**: Only admins (mitigated by require_admin dependency).

**Risk**: If admin account compromised or frontend XSS, stack traces leak internal details.

**Recommendation**:
```python
# Sanitize stack traces before returning
def sanitize_stack_trace(trace: str) -> str:
    """Remove absolute paths and sensitive details from stack trace."""
    if not trace:
        return trace
    # Replace absolute paths with relative
    trace = re.sub(r'/Users/[^/]+/', '~/', trace)
    trace = re.sub(r'/opt/[^/]+/', '/opt/', trace)
    trace = re.sub(r'/home/[^/]+/', '~/', trace)
    # Redact environment variables
    trace = re.sub(r'API_KEY[^\s]*', '[REDACTED]', trace)
    return trace

errors.append({
    ...
    "stack_trace": sanitize_stack_trace(row.get("stack_trace")),
    ...
})
```

---

## Low Priority Suggestions

### L1. Rate Limit Bypass via Header Spoofing
**File**: `backend/app/rate_limiter.py:10`
**Severity**: LOW
**OWASP**: A05:2021 - Security Misconfiguration

**Issue**:
```python
limiter = Limiter(key_func=get_remote_address)
```

Uses IP from `request.client.host` which can be spoofed via proxy headers (`X-Forwarded-For`, `X-Real-IP`).

**Current Deployment**: Railway/Vercel likely sets trusted proxy headers correctly.

**Risk**: If reverse proxy misconfigured, attacker can rotate IPs to bypass rate limits.

**Recommendation**:
```python
# Verify trusted proxy configuration in Railway
# OR use custom key function with user_id for authenticated endpoints

from slowapi.util import get_ipaddr

def get_identifier(request: Request) -> str:
    """Get rate limit key from user ID (if auth) or IP."""
    # Check if authenticated
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            token = extract_token_from_header(auth_header)
            user = verify_jwt(token)
            return f"user:{user.user_id}"
        except:
            pass
    # Fallback to IP with proxy support
    return get_ipaddr(request)

limiter = Limiter(key_func=get_identifier)
```

---

### L2. Username Regex Inconsistency
**File**: `backend/app/routes/settings_routes.py:199`
**Severity**: LOW
**Code Quality Issue**

**Issue**:
```python
if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
```

Regex allows usernames like `"a"` (1 char) but earlier check requires 3+ chars (line 185).

**Logic Flow**:
1. Line 185: `if len(username) < 3` - reject
2. Line 199: Regex allows 1+ chars

**Not a Bug**: Length check happens first, so safe. But regex misleading.

**Recommendation**:
```python
# Make regex explicit about length (readability)
if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,29}$', username):
    # 3-30 chars: 1 letter + 2-29 more chars
```

---

### L3. Missing Type Hints in Error Handlers
**File**: `backend/app/main.py:56,78`
**Severity**: LOW
**Code Quality Issue**

**Issue**:
```python
async def validation_error_handler(request: Request, exc: ValidationError):
    # No return type hint
```

**Impact**: Type checkers cannot verify response type.

**Recommendation**:
```python
from fastapi.responses import JSONResponse

async def validation_error_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    ...
    return response
```

---

## Positive Observations

### Security Strengths
1. **JWT Authentication**: Proper Supabase JWT verification with HS256
2. **Ban System**: Proactive ban checking via `get_active_user` dependency
3. **Rate Limiting**: Comprehensive slowapi integration across all routes
4. **Input Validation**: Centralized validators.py with regex-based sanitization
5. **Error Sanitization**: `sanitize_error_message()` redacts API keys from logs
6. **CORS**: Explicit origin whitelist (no wildcards detected)
7. **Request Size Limit**: 10MB max body size enforced
8. **Admin Authorization**: Dual-factor (JWT role + email whitelist)
9. **Audit Logging**: Comprehensive structured logging with loguru
10. **SQL Injection**: Supabase client uses parameterized queries (ORM-safe)

### Code Quality Strengths
1. **Type Hints**: Consistent use of type annotations (90%+ coverage)
2. **Error Handling**: Try/except blocks with specific exception types
3. **Documentation**: Clear docstrings on public functions
4. **Separation of Concerns**: Auth logic separated into auth/ module
5. **DRY Principles**: Shared rate_limiter, validators modules
6. **Logging**: Structured logging with event names, context

---

## Recommended Actions (Prioritized)

### Immediate (Before Production Deploy)
1. **[H2]** Add TTL-based cache refresh to `admin.py:_load_admin_emails()` (60s TTL)
2. **[H3]** Implement cache fallback for `ban_check.py:check_user_banned()` (fail-secure)
3. **[M3]** Replace UUID validation duplicates with `validate_uuid()` (5 locations)
4. **[M4]** Fix subreddit regex mismatch in `jobs_routes.py:24` (use validators.py)

### Short-Term (This Sprint)
5. **[H1]** Strengthen JWT secret validation (40+ unique chars, pattern detection)
6. **[M1]** Add CORS origin normalization/validation in `main.py:39`
7. **[M5]** Add self-unban audit logging in `admin_routes.py:321`
8. **[M6]** Sanitize stack traces in admin error log endpoint

### Medium-Term (Next Sprint)
9. **[M2]** Explicitly configure request size limit via Starlette middleware
10. **[L1]** Migrate to user-aware rate limiting for authenticated routes
11. **[L2]** Update username regex for clarity (not urgent)
12. **[L3]** Add return type hints to exception handlers

---

## Metrics

- **Type Coverage**: ~90% (estimated, mypy not run successfully)
- **Test Coverage**: Unknown (pytest not found)
- **Linting Issues**: Not run (ruff/pylint not configured)
- **Security Issues**: 3 High, 6 Medium, 3 Low
- **Lines of Code**: ~3,200 (reviewed files only)

---

## Testing Gaps

**Critical Missing Tests**:
1. JWT secret validation edge cases (weak secrets)
2. Admin cache invalidation scenarios
3. Ban check failure modes (DB timeout)
4. CORS origin validation (wildcard, trailing slash)
5. Request size limit with chunked encoding
6. Rate limit bypass via header spoofing

**Recommendation**: Add tests in `backend/tests/test_security.py` covering all H/M issues.

---

## Unresolved Questions

1. **H2**: Does production use `admin_users` table or `ADMIN_EMAILS` env var? (Both exist)
2. **M2**: Does Railway/Vercel reverse proxy enforce size limits upstream?
3. **L1**: Are `X-Forwarded-For` headers validated by Railway ingress?
4. **Testing**: Why is pytest not found? (venv not activated or missing deps?)
5. **Type Checking**: Should mypy be added to CI/CD pipeline?

---

**Report Complete**
Next: Review pipeline/integrations code for API key handling, cost tracking, external service timeouts.
