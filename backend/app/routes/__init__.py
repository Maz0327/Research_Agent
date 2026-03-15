"""API route modules.

Updated: 2026-03-15 - Added brainstorm_routes and style_guide_routes.
"""
from .settings_routes import router as settings_router
from .jobs_routes import router as jobs_router
from .transcripts_routes import router as transcripts_router
from .admin_routes import router as admin_router
from .export_routes import router as export_router
from .share_routes import router as share_router
from .search_routes import router as search_router
from .style_guide_routes import router as style_guide_router
from .brainstorm_routes import router as brainstorm_router

__all__ = [
    "settings_router",
    "jobs_router",
    "transcripts_router",
    "admin_router",
    "export_router",
    "share_router",
    "search_router",
    "style_guide_router",
    "brainstorm_router",
]
