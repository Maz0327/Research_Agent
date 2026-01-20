"""API route modules.

Updated: 2026-01-19 - Removed slack_routes (Slack integration deprecated).
"""
from .settings_routes import router as settings_router
from .jobs_routes import router as jobs_router
from .transcripts_routes import router as transcripts_router
from .admin_routes import router as admin_router
from .export_routes import router as export_router

__all__ = [
    "settings_router",
    "jobs_router",
    "transcripts_router",
    "admin_router",
    "export_router",
]
