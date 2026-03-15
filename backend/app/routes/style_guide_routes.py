"""Style guide CRUD API routes.

Provides endpoints for managing personal creator style guides:
- GET /style-guides — list user's guides
- GET /style-guides/templates — list default templates (static)
- POST /style-guides — create a new guide
- PUT /style-guides/{id} — update a guide
- DELETE /style-guides/{id} — delete a guide
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter, RATE_LIMITS
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.models.style_guide import (
    StyleGuideCreate,
    StyleGuideUpdate,
    StyleGuideResponse,
    DEFAULT_TEMPLATES,
)
from backend.state.style_guide_store import (
    list_style_guides,
    get_style_guide,
    create_style_guide,
    update_style_guide,
    delete_style_guide,
)


router = APIRouter(prefix="/style-guides", tags=["style-guides"])


@router.get("/templates")
async def get_templates():
    """Get the three default style guide templates (static data, no auth required)."""
    return {"templates": DEFAULT_TEMPLATES}


@router.get("", response_model=list[StyleGuideResponse])
async def list_guides(user: AuthUser = Depends(get_active_user)):
    """List all style guides for the current user."""
    guides = list_style_guides(user.user_id)
    return [StyleGuideResponse.from_style_guide(g) for g in guides]


@router.post("", response_model=StyleGuideResponse, status_code=201)
@limiter.limit(RATE_LIMITS.get("settings_update", "10/minute"))
async def create_guide(
    request: Request,
    data: StyleGuideCreate,
    user: AuthUser = Depends(get_active_user),
):
    """Create a new style guide."""
    # Limit to 10 guides per user
    existing = list_style_guides(user.user_id)
    if len(existing) >= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 style guides per user. Delete an existing guide first.",
        )

    guide = create_style_guide(user.user_id, data)
    if not guide:
        raise HTTPException(status_code=500, detail="Failed to create style guide")

    logger.info(
        "Style guide created",
        extra={
            "user_id": user.user_id,
            "guide_id": guide.id,
            "template_base": data.template_base.value,
            "event": "style_guide_created",
        },
    )
    return StyleGuideResponse.from_style_guide(guide)


@router.put("/{guide_id}", response_model=StyleGuideResponse)
@limiter.limit(RATE_LIMITS.get("settings_update", "10/minute"))
async def update_guide(
    request: Request,
    guide_id: str,
    data: StyleGuideUpdate,
    user: AuthUser = Depends(get_active_user),
):
    """Update an existing style guide."""
    existing = get_style_guide(user.user_id, guide_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Style guide not found")

    updated = update_style_guide(user.user_id, guide_id, data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update style guide")

    logger.info(
        "Style guide updated",
        extra={
            "user_id": user.user_id,
            "guide_id": guide_id,
            "event": "style_guide_updated",
        },
    )
    return StyleGuideResponse.from_style_guide(updated)


@router.delete("/{guide_id}", status_code=204)
@limiter.limit(RATE_LIMITS.get("settings_update", "10/minute"))
async def delete_guide(
    request: Request,
    guide_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Delete a style guide."""
    existing = get_style_guide(user.user_id, guide_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Style guide not found")

    success = delete_style_guide(user.user_id, guide_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete style guide")

    logger.info(
        "Style guide deleted",
        extra={
            "user_id": user.user_id,
            "guide_id": guide_id,
            "event": "style_guide_deleted",
        },
    )
