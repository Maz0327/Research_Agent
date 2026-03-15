"""Style guide store — CRUD operations for user style guides via Supabase REST."""

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from loguru import logger

from backend.config import get_settings
from backend.models.style_guide import (
    StyleGuide,
    StyleGuideCreate,
    StyleGuideUpdate,
    StyleGuideOverrides,
    SectionPreference,
    TemplateBase,
)
from backend.utils.error_handling import sanitize_error_message


SUPABASE_API_TIMEOUT = 5.0
TABLE = "style_guides"


def _rest_base_url() -> str:
    """Base URL for Supabase PostgREST."""
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    base_url = str(settings.supabase_url)
    return base_url.rstrip("/") + "/rest/v1"


def _headers(*, prefer: str = "return=representation") -> dict[str, str]:
    """Headers required by Supabase REST."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _row_to_style_guide(row: dict[str, Any]) -> StyleGuide:
    """Convert a database row to a StyleGuide model."""
    overrides_raw = row.get("overrides") or {}
    overrides = StyleGuideOverrides(**overrides_raw) if isinstance(overrides_raw, dict) else StyleGuideOverrides()

    section_prefs_raw = row.get("section_preferences") or []
    section_prefs = []
    if isinstance(section_prefs_raw, list):
        for sp in section_prefs_raw:
            if isinstance(sp, dict):
                section_prefs.append(SectionPreference(**sp))

    return StyleGuide(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        template_base=TemplateBase(row["template_base"]),
        overrides=overrides,
        section_preferences=section_prefs,
        is_default=row.get("is_default", False),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def list_style_guides(user_id: str) -> list[StyleGuide]:
    """List all style guides for a user."""
    try:
        url = f"{_rest_base_url()}/{TABLE}?user_id=eq.{user_id}&order=created_at.asc"
        resp = httpx.get(url, headers=_headers(prefer=""), timeout=SUPABASE_API_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
        return [_row_to_style_guide(r) for r in rows]
    except Exception as e:
        logger.error(f"Failed to list style guides: {sanitize_error_message(e)}")
        return []


def get_style_guide(user_id: str, guide_id: str) -> Optional[StyleGuide]:
    """Get a single style guide by ID, scoped to user."""
    try:
        url = f"{_rest_base_url()}/{TABLE}?id=eq.{guide_id}&user_id=eq.{user_id}"
        resp = httpx.get(url, headers=_headers(prefer=""), timeout=SUPABASE_API_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        return _row_to_style_guide(rows[0])
    except Exception as e:
        logger.error(f"Failed to get style guide {guide_id}: {sanitize_error_message(e)}")
        return None


def create_style_guide(user_id: str, data: StyleGuideCreate) -> Optional[StyleGuide]:
    """Create a new style guide for a user."""
    try:
        now = datetime.now(timezone.utc).isoformat()

        # If this is being set as default, unset other defaults first
        if data.is_default:
            _unset_default(user_id)

        payload = {
            "user_id": user_id,
            "name": data.name,
            "template_base": data.template_base.value,
            "overrides": data.overrides.model_dump(exclude_none=True),
            "section_preferences": [sp.model_dump() for sp in data.section_preferences],
            "is_default": data.is_default,
            "created_at": now,
            "updated_at": now,
        }

        url = f"{_rest_base_url()}/{TABLE}"
        resp = httpx.post(url, headers=_headers(), json=payload, timeout=SUPABASE_API_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        return _row_to_style_guide(rows[0])
    except Exception as e:
        logger.error(f"Failed to create style guide: {sanitize_error_message(e)}")
        return None


def update_style_guide(user_id: str, guide_id: str, data: StyleGuideUpdate) -> Optional[StyleGuide]:
    """Update an existing style guide."""
    try:
        # If setting as default, unset other defaults first
        if data.is_default:
            _unset_default(user_id, exclude_id=guide_id)

        payload: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}

        if data.name is not None:
            payload["name"] = data.name
        if data.template_base is not None:
            payload["template_base"] = data.template_base.value
        if data.overrides is not None:
            payload["overrides"] = data.overrides.model_dump(exclude_none=True)
        if data.section_preferences is not None:
            payload["section_preferences"] = [sp.model_dump() for sp in data.section_preferences]
        if data.is_default is not None:
            payload["is_default"] = data.is_default

        url = f"{_rest_base_url()}/{TABLE}?id=eq.{guide_id}&user_id=eq.{user_id}"
        resp = httpx.patch(url, headers=_headers(), json=payload, timeout=SUPABASE_API_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        return _row_to_style_guide(rows[0])
    except Exception as e:
        logger.error(f"Failed to update style guide {guide_id}: {sanitize_error_message(e)}")
        return None


def delete_style_guide(user_id: str, guide_id: str) -> bool:
    """Delete a style guide."""
    try:
        url = f"{_rest_base_url()}/{TABLE}?id=eq.{guide_id}&user_id=eq.{user_id}"
        resp = httpx.delete(url, headers=_headers(), timeout=SUPABASE_API_TIMEOUT)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to delete style guide {guide_id}: {sanitize_error_message(e)}")
        return False


def _unset_default(user_id: str, exclude_id: Optional[str] = None) -> None:
    """Unset is_default on all user's guides (except optionally one)."""
    try:
        url = f"{_rest_base_url()}/{TABLE}?user_id=eq.{user_id}&is_default=eq.true"
        if exclude_id:
            url += f"&id=neq.{exclude_id}"
        httpx.patch(
            url,
            headers=_headers(prefer="return=minimal"),
            json={"is_default": False},
            timeout=SUPABASE_API_TIMEOUT,
        )
    except Exception as e:
        logger.warning(f"Failed to unset default style guides: {sanitize_error_message(e)}")
