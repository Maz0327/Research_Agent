"""FastAPI application main module."""
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.rate_limiter import limiter
from backend.app.routes import router as slack_router
from backend.app.routes import (
    settings_router,
    jobs_router,
    transcripts_router,
    admin_router,
)
from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user
from backend.config import get_settings
from backend.utils.validators import ValidationError

# Maximum request body size (10 MB)
MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Research Agent API",
    description="Cloud-based research backend for aggregating content from multiple sources",
    version="0.1.0",
)

# Configure rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS middleware
cors_origins = []
if settings.frontend_origins:
    cors_origins = [origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()]

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    logger.info(f"CORS enabled for origins: {cors_origins}")
else:
    logger.warning("FRONTEND_ORIGINS not set - CORS middleware not configured")


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle ValidationError exceptions with 400 Bad Request.

    This ensures that invalid input (UUIDs, video IDs, etc.) returns
    a proper 400 status code instead of 404 or 500.
    """
    logger.warning(f"Validation error: {exc}", extra={"event": "validation_error"})

    origin = request.headers.get("origin", "")
    response = JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

    if origin and cors_origins and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions with proper CORS headers.

    Security: Error messages are sanitized to prevent leaking sensitive
    information like API keys, file paths, or internal implementation details.
    """
    from backend.utils.error_handling import sanitize_error_message

    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Sanitize error message to prevent information leakage
    sanitized_error = sanitize_error_message(exc, include_type=False)

    origin = request.headers.get("origin", "")
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": sanitized_error,
        },
    )

    if origin and cors_origins and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID for tracing and debugging.

    Request ID is either taken from X-Request-ID header (for tracing
    across services) or generated. It's included in response headers
    and available in logs.
    """
    import uuid

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]

    # Make request_id available to the request for logging
    request.state.request_id = request_id

    with logger.contextualize(request_id=request_id):
        logger.debug(f"{request.method} {request.url.path}")
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request body size to prevent memory exhaustion."""
    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > MAX_REQUEST_SIZE_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"}
            )
    return await call_next(request)


# =============================================================================
# Health Check
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "research-agent-api"
    }


# =============================================================================
# Auth Endpoint
# =============================================================================

@app.get("/auth/me")
async def get_current_user_info(user: AuthUser = Depends(get_current_user)):
    """Get the current authenticated user's information."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
    }


# =============================================================================
# Include Route Modules
# =============================================================================

# NOTE: Rate limits are now applied via decorators directly on route handlers
# in settings_routes.py, jobs_routes.py, and transcripts_routes.py.
# This is more robust than the previous startup hook approach which used
# fragile route indices.

# Include routers
app.include_router(slack_router)
app.include_router(settings_router)
app.include_router(jobs_router)
app.include_router(transcripts_router)
app.include_router(admin_router)
