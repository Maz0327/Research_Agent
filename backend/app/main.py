"""FastAPI application main module."""
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# Maximum request body size (10 MB)
MAX_REQUEST_SIZE_BYTES = 10 * 1024 * 1024

settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions with proper CORS headers."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    origin = request.headers.get("origin", "")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )

    if origin and cors_origins and origin in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)
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

# Apply rate limits to routers
@app.on_event("startup")
async def apply_rate_limits():
    """Apply rate limits to route handlers."""
    # Settings routes
    settings_router.routes[1].endpoint = limiter.limit("30/minute")(settings_router.routes[1].endpoint)  # PUT /settings
    settings_router.routes[2].endpoint = limiter.limit("10/minute")(settings_router.routes[2].endpoint)  # POST /validate-folder
    settings_router.routes[3].endpoint = limiter.limit("10/minute")(settings_router.routes[3].endpoint)  # GET /oauth-status
    settings_router.routes[4].endpoint = limiter.limit("30/minute")(settings_router.routes[4].endpoint)  # GET /check-username

    # Jobs routes
    jobs_router.routes[0].endpoint = limiter.limit("10/hour")(jobs_router.routes[0].endpoint)  # POST /jobs
    jobs_router.routes[1].endpoint = limiter.limit("30/minute")(jobs_router.routes[1].endpoint)  # GET /jobs
    jobs_router.routes[2].endpoint = limiter.limit("60/minute")(jobs_router.routes[2].endpoint)  # GET /jobs/{id}
    jobs_router.routes[3].endpoint = limiter.limit("10/minute")(jobs_router.routes[3].endpoint)  # POST /jobs/{id}/cancel

    # Transcripts routes
    transcripts_router.routes[0].endpoint = limiter.limit("5/hour")(transcripts_router.routes[0].endpoint)  # POST /transcripts
    transcripts_router.routes[1].endpoint = limiter.limit("60/minute")(transcripts_router.routes[1].endpoint)  # GET /transcripts/{id}


# Include routers
app.include_router(slack_router)
app.include_router(settings_router)
app.include_router(jobs_router)
app.include_router(transcripts_router)
app.include_router(admin_router)
