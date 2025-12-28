"""Admin API routes."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.admin import is_admin
from backend.state import get_job, update_job
from backend.state.impl.supabase_store import get_supabase_client

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/check")
async def check_admin_status(user: AuthUser = Depends(get_current_user)):
    """Check if the current user is an admin."""
    return {"is_admin": is_admin(user)}


@router.get("/stats")
async def get_admin_stats(user: AuthUser = Depends(require_admin)):
    """Get admin dashboard statistics."""
    try:
        supabase = get_supabase_client()
        today = datetime.utcnow().date().isoformat()

        # Total users
        users_result = supabase.table("user_settings").select("user_id", count="exact").execute()
        total_users = users_result.count or 0

        # Total jobs
        jobs_result = supabase.table("jobs").select("id", count="exact").execute()
        total_jobs = jobs_result.count or 0

        # Jobs today
        jobs_today_result = supabase.table("jobs").select("id", count="exact").gte("created_at", f"{today}T00:00:00").execute()
        jobs_today = jobs_today_result.count or 0

        # Running jobs
        running_result = supabase.table("jobs").select("id", count="exact").eq("status", "running").execute()
        jobs_running = running_result.count or 0

        # Failed jobs today
        failed_today_result = supabase.table("jobs").select("id", count="exact").eq("status", "failed").gte("created_at", f"{today}T00:00:00").execute()
        jobs_failed_today = failed_today_result.count or 0

        # Unresolved errors
        unresolved_errors = 0
        try:
            errors_result = supabase.table("error_logs").select("id", count="exact").eq("resolved", False).execute()
            unresolved_errors = errors_result.count or 0
        except Exception:
            pass

        return {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "jobs_today": jobs_today,
            "jobs_running": jobs_running,
            "jobs_failed_today": jobs_failed_today,
            "unresolved_errors": unresolved_errors,
        }
    except Exception as e:
        logger.error(f"Failed to fetch admin stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/users")
async def list_admin_users(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
):
    """List all users with their statistics."""
    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        result = supabase.table("user_settings").select(
            "user_id, username, created_at, is_banned",
            count="exact"
        ).range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        users = []
        for row in result.data or []:
            job_count_result = supabase.table("jobs").select("id", count="exact").eq("user_id", row["user_id"]).execute()
            admin_check = supabase.table("admin_users").select("user_id").eq("user_id", row["user_id"]).execute()

            users.append({
                "id": row["user_id"],
                "email": row.get("username") or f"user-{row['user_id'][:8]}",
                "created_at": row["created_at"],
                "last_sign_in_at": None,
                "job_count": job_count_result.count or 0,
                "is_admin": len(admin_check.data or []) > 0,
                "is_banned": row.get("is_banned", False),
            })

        return {
            "users": users,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


@router.get("/jobs")
async def list_admin_jobs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """List all jobs with filters."""
    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        query = supabase.table("jobs").select(
            "id, user_id, config_json, status, progress_percent, created_at, warnings",
            count="exact"
        )

        if status:
            query = query.eq("status", status)
        if user_id:
            query = query.eq("user_id", user_id)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        result = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        jobs = []
        for row in result.data or []:
            config = row.get("config_json", {})
            jobs.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "user_email": config.get("user_email", "Unknown"),
                "prompt": config.get("prompt") or config.get("topic", ""),
                "pipeline": config.get("pipeline", "full"),
                "status": row["status"],
                "progress_percent": row["progress_percent"],
                "created_at": row["created_at"],
                "error": row.get("warnings", [])[-1] if row.get("warnings") else None,
            })

        return {
            "jobs": jobs,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch jobs")


@router.post("/jobs/{job_id}/cancel")
async def admin_cancel_job(
    job_id: str,
    user: AuthUser = Depends(require_admin),
):
    """Cancel any job as admin."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{job.status}'")

    try:
        from backend.worker import celery_app
        celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
    except Exception as e:
        logger.warning(f"Failed to revoke Celery task: {e}")

    update_job(job_id, status="cancelled", stage="cancelled")
    logger.info(f"Admin {user.user_id} cancelled job {job_id}")

    return {"message": "Job cancelled successfully", "job_id": job_id}


@router.delete("/jobs/{job_id}")
async def admin_delete_job(
    job_id: str,
    user: AuthUser = Depends(require_admin),
):
    """Delete a job as admin."""
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Cancel if running
    if job.status in ("queued", "running"):
        try:
            from backend.worker import celery_app
            celery_app.control.revoke(job_id, terminate=True, signal='SIGTERM')
        except Exception:
            pass

    try:
        supabase = get_supabase_client()
        supabase.table("jobs").delete().eq("id", job_id).execute()
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")

    logger.info(f"Admin {user.user_id} deleted job {job_id}")
    return {"message": "Job deleted successfully", "job_id": job_id}


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    admin_user: AuthUser = Depends(require_admin),
):
    """Ban a user."""
    if user_id == admin_user.user_id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    try:
        supabase = get_supabase_client()
        supabase.table("user_settings").update({"is_banned": True}).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to ban user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to ban user")

    logger.info(f"Admin {admin_user.user_id} banned user {user_id}")
    return {"message": "User banned successfully", "user_id": user_id}


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    admin_user: AuthUser = Depends(require_admin),
):
    """Unban a user."""
    try:
        supabase = get_supabase_client()
        supabase.table("user_settings").update({"is_banned": False}).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to unban user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unban user")

    logger.info(f"Admin {admin_user.user_id} unbanned user {user_id}")
    return {"message": "User unbanned successfully", "user_id": user_id}


@router.get("/errors")
async def list_error_logs(
    user: AuthUser = Depends(require_admin),
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    resolved: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """List error logs with filters."""
    try:
        supabase = get_supabase_client()
        offset = (page - 1) * page_size

        query = supabase.table("error_logs").select("*", count="exact")

        if category:
            query = query.eq("error_category", category)
        if resolved is not None:
            query = query.eq("resolved", resolved)
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)

        result = query.range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        errors = []
        for row in result.data or []:
            errors.append({
                "id": row["id"],
                "job_id": row.get("job_id"),
                "user_id": row.get("user_id"),
                "user_email": row.get("user_email"),
                "user_message": row["user_message"],
                "error_category": row["error_category"],
                "technical_message": row["technical_message"],
                "stack_trace": row.get("stack_trace"),
                "stage": row.get("stage"),
                "created_at": row["created_at"],
                "resolved": row.get("resolved", False),
            })

        return {
            "errors": errors,
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        if "error_logs" in str(e).lower():
            return {"errors": [], "total": 0, "page": page, "page_size": page_size}
        logger.error(f"Failed to list error logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch error logs")


@router.post("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    user: AuthUser = Depends(require_admin),
):
    """Mark an error as resolved."""
    try:
        supabase = get_supabase_client()
        supabase.table("error_logs").update({
            "resolved": True,
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": user.user_id,
        }).eq("id", error_id).execute()
    except Exception as e:
        logger.error(f"Failed to resolve error {error_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve error")

    logger.info(f"Admin {user.user_id} resolved error {error_id}")
    return {"message": "Error resolved successfully", "error_id": error_id}
