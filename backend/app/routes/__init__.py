"""API route modules."""
from .slack_routes import router
from .settings_routes import router as settings_router
from .jobs_routes import router as jobs_router
from .transcripts_routes import router as transcripts_router
from .admin_routes import router as admin_router

__all__ = [
    "router",  # slack router (legacy name)
    "settings_router",
    "jobs_router",
    "transcripts_router",
    "admin_router",
]
