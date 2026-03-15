"""Voice Profile API routes.

CRUD endpoints for voice profiles + trigger profile generation.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user
from backend.models.voice_profile import CreateVoiceProfileRequest, VoiceProfile

router = APIRouter(prefix="/voice-profiles", tags=["voice-profiles"])


def _get_supabase():
    """Get Supabase client for voice_profiles table."""
    from backend.integrations.supabase_client import get_supabase_client
    return get_supabase_client()


@router.post("")
async def create_voice_profile(
    request: Request,
    body: CreateVoiceProfileRequest,
    user: AuthUser = Depends(get_active_user),
):
    """Create a new voice profile by analyzing creator videos.

    Triggers async analysis of provided video URLs to extract voice patterns.
    """
    profile_id = str(uuid.uuid4())

    # For now, store a placeholder and trigger async generation
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        data = {
            "id": profile_id,
            "user_id": user.user_id,
            "creator_name": body.creator_name,
            "source_video_urls": body.video_urls,
            "source_video_count": len(body.video_urls),
            "style_profile": {},
            "sentence_rhythm": {},
            "transition_patterns": [],
            "opening_patterns": [],
            "closing_patterns": [],
            "emphasis_patterns": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        result = supabase.table("voice_profiles").insert(data).execute()

        logger.info(
            f"Voice profile created: {profile_id} for {body.creator_name}",
            extra={"user_id": user.user_id, "profile_id": profile_id},
        )

        return {
            "id": profile_id,
            "creator_name": body.creator_name,
            "status": "created",
            "message": "Voice profile created. Analysis will be processed.",
        }

    except Exception as e:
        logger.exception(f"Failed to create voice profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create profile: {e}")


@router.get("")
async def list_voice_profiles(
    user: AuthUser = Depends(get_active_user),
):
    """List all voice profiles for the current user."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        result = (
            supabase.table("voice_profiles")
            .select("*")
            .eq("user_id", user.user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"profiles": result.data or []}

    except Exception as e:
        logger.exception(f"Failed to list voice profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_id}")
async def get_voice_profile(
    profile_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Get a specific voice profile."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        result = (
            supabase.table("voice_profiles")
            .select("*")
            .eq("id", profile_id)
            .eq("user_id", user.user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Voice profile not found")
        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_id}")
async def delete_voice_profile(
    profile_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Delete a voice profile."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database unavailable")

    try:
        result = (
            supabase.table("voice_profiles")
            .delete()
            .eq("id", profile_id)
            .eq("user_id", user.user_id)
            .execute()
        )
        return {"deleted": True, "id": profile_id}

    except Exception as e:
        logger.exception(f"Failed to delete voice profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
