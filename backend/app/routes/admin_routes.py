"""Admin API routes."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from backend.utils.datetime_utils import utc_now_iso, utc_today_iso
from backend.utils.cache import cache_get, cache_set
from backend.config import get_settings

# Maximum page size to prevent memory issues
MAX_PAGE_SIZE = 100

from backend.auth import AuthUser
from backend.auth.dependencies import get_current_user, require_admin
from backend.auth.admin import is_admin
from backend.state import get_job, update_job
from backend.auth.ban_check import get_supabase_client

router = APIRouter(prefix="/admin", tags=["admin"])


def require_supabase():
    """Dependency to check if Supabase is configured.

    Admin endpoints require Supabase for database queries.
    Returns 501 Not Implemented if using in-memory store.
    """
    settings = get_settings()
    if not settings.supabase_url:
        raise HTTPException(
            status_code=501,
            detail="Admin features require Supabase configuration. Running in-memory mode."
        )
    return True


@router.get("/check")
async def check_admin_status(user: AuthUser = Depends(get_current_user)):
    """Check if the current user is an admin."""
    return {"is_admin": is_admin(user)}


@router.get("/stats")
async def get_admin_stats(
    user: AuthUser = Depends(require_admin),
):
    """Get admin dashboard statistics.

    Performance: Uses Redis caching with 60-second TTL to reduce database load.
    """
    # Try cache first (60 second TTL for admin stats)
    cache_key = "admin:stats"
    cached_stats = cache_get(cache_key)
    if cached_stats:
        logger.debug("Admin stats served from cache")
        return cached_stats

    # Only require Supabase if we actually need to query it (i.e., cache miss)
    require_supabase()

    try:
        supabase = get_supabase_client()
        today = utc_today_iso()

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

        stats = {
            "total_users": total_users,
            "total_jobs": total_jobs,
            "jobs_today": jobs_today,
            "jobs_running": jobs_running,
            "jobs_failed_today": jobs_failed_today,
            "unresolved_errors": unresolved_errors,
        }

        # Cache for 60 seconds
        cache_set(cache_key, stats, ttl_seconds=60)
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch admin stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")


@router.get("/users")
async def list_admin_users(
    user: AuthUser = Depends(require_admin),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Items per page (max 100)"),
):
    """List all users with their statistics.

    Performance: Uses batch queries to avoid N+1 query problem.
    """
    require_supabase()
    try:
        supabase = get_supabase_client()
        # Cap page_size to prevent abuse
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size

        # Get users with pagination
        result = supabase.table("user_settings").select(
            "user_id, username, created_at, is_banned",
            count="exact"
        ).range(offset, offset + page_size - 1).order("created_at", desc=True).execute()

        user_rows = result.data or []
        if not user_rows:
            return {
                "users": [],
                "total": result.count or 0,
                "page": page,
                "page_size": page_size,
            }

        # Extract user IDs for batch queries
        user_ids = [row["user_id"] for row in user_rows]

        # Batch query 1: Get all admin user IDs in one query
        admin_result = supabase.table("admin_users").select(
            "user_id"
        ).in_("user_id", user_ids).execute()
        admin_user_ids = {row["user_id"] for row in (admin_result.data or [])}

        # Batch query 2: Get job counts using RPC function (single query)
        # Uses migration 015's get_job_counts_by_users function
        job_counts: dict[str, int] = {}
        try:
            # Call RPC function to get all job counts in one query
            counts_result = supabase.rpc(
                "get_job_counts_by_users",
                {"user_ids": user_ids}
            ).execute()
            for row in (counts_result.data or []):
                job_counts[row["user_id"]] = row["job_count"]
        except Exception as e:
            # Fallback: individual queries if RPC not available
            logger.warning(f"RPC get_job_counts_by_users failed, using fallback: {e}")
            try:
                for uid in user_ids:
                    job_count_result = supabase.table("jobs").select(
                        "id", count="exact"
                    ).eq("user_id", uid).execute()
                    job_counts[uid] = job_count_result.count or 0
            except Exception as fallback_e:
                logger.warning(f"Fallback job count query failed: {fallback_e}")
                job_counts = {uid: 0 for uid in user_ids}

        # Build response using batched data
        users = []
        for row in user_rows:
            uid = row["user_id"]
            users.append({
                "id": uid,
                "email": row.get("username") or f"user-{uid[:8]}",
                "created_at": row["created_at"],
                "last_sign_in_at": None,
                "job_count": job_counts.get(uid, 0),
                "is_admin": uid in admin_user_ids,
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
    require_supabase()
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
    require_supabase()
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
    require_supabase()
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
    require_supabase()
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
    require_supabase()
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
    require_supabase()
    try:
        supabase = get_supabase_client()
        supabase.table("error_logs").update({
            "resolved": True,
            "resolved_at": utc_now_iso(),
            "resolved_by": user.user_id,
        }).eq("id", error_id).execute()
    except Exception as e:
        logger.error(f"Failed to resolve error {error_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve error")

    logger.info(f"Admin {user.user_id} resolved error {error_id}")
    return {"message": "Error resolved successfully", "error_id": error_id}
