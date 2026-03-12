"""Share API routes for document sharing."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from backend.app.rate_limiter import limiter
from backend.auth import AuthUser
from backend.auth.ban_check import get_active_user, get_supabase_client
from backend.config import get_settings
from backend.state import get_job
from backend.models.share import (
    CreateShareRequest,
    CreateShareResponse,
    ListSharesResponse,
    RevokeShareResponse,
    SharedDocumentResponse,
    ShareTokenInfo,
    DOC_TYPE_NAMES,
)

router = APIRouter(tags=["share"])


def generate_share_token() -> str:
    """Generate a cryptographically secure share token."""
    return secrets.token_urlsafe(48)  # 64 characters


def get_share_url(token: str) -> str:
    """Build the full share URL for a token."""
    settings = get_settings()
    # Use frontend URL from FRONTEND_ORIGINS or default
    frontend_origins = settings.frontend_origins
    if frontend_origins:
        # Get first origin as base URL (frontend_origins is a comma-separated string)
        base_url = frontend_origins.split(",")[0].strip().rstrip("/")
    else:
        base_url = "http://localhost:3000"
    return f"{base_url}/shared/{token}"


# =============================================================================
# AUTHENTICATED ENDPOINTS (Job owner only)
# =============================================================================

@router.post("/jobs/{job_id}/share", response_model=CreateShareResponse)
@limiter.limit("30/minute")
async def create_share_token(
    request: Request,
    job_id: str,
    share_request: CreateShareRequest,
    user: AuthUser = Depends(get_active_user),
):
    """
    Create a share token for a document.
    
    The share link allows anyone with the link to view the document
    without authentication. Links are time-limited and can be revoked.
    
    Args:
        job_id: Job UUID
        share_request: Share configuration (doc_type, expiration, max_views)
    
    Returns:
        Share token info including full URL to share
    """
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Get job and verify ownership
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to share this job")
    
    # Job must be completed
    if job.status not in ("completed", "completed_with_warnings"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot share documents from job with status '{job.status}'. Job must be completed."
        )
    
    # Verify the requested document exists
    doc_type = share_request.doc_type
    if doc_type != "all":
        artifacts = job.artifacts
        if not artifacts:
            raise HTTPException(status_code=400, detail="Job has no artifacts to share")
        
        artifacts_dict = artifacts.model_dump(exclude_none=True) if hasattr(artifacts, "model_dump") else {}
        
        # Map doc_type to artifact fields
        doc_mapping = {
            "doc_0": ("doc_0_path", "source_ledger"),
            "doc_1": ("doc_1_path", "jump_start"),
            "doc_2": ("doc_2_path", "semantic_brief"),
            "doc_3": ("doc_3_path", "producer_packet_md"),
        }
        
        if doc_type in doc_mapping:
            path_field, inline_field = doc_mapping[doc_type]
            has_doc = bool(artifacts_dict.get(path_field) or artifacts_dict.get(inline_field))
            if not has_doc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Document {doc_type} ({DOC_TYPE_NAMES[doc_type]}) not found in job artifacts"
                )
    
    # Generate token and calculate expiration
    token = generate_share_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=share_request.expires_in_hours)
    
    # Insert share token into database
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        share_id = str(uuid.uuid4())
        result = client.table("share_tokens").insert({
            "id": share_id,
            "job_id": job_id,
            "doc_type": doc_type,
            "token": token,
            "created_by": user.user_id,
            "expires_at": expires_at.isoformat(),
            "max_views": share_request.max_views,
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create share token")
        
        logger.info(
            "Share token created",
            extra={
                "job_id": job_id,
                "doc_type": doc_type,
                "user_id": user.user_id,
                "expires_in_hours": share_request.expires_in_hours,
                "event": "share_created",
            }
        )
        
        return CreateShareResponse(
            share_id=share_id,
            token=token,
            share_url=get_share_url(token),
            doc_type=doc_type,
            expires_at=expires_at,
            max_views=share_request.max_views,
        )
        
    except Exception as e:
        logger.error(f"Failed to create share token: {e}")
        raise HTTPException(status_code=500, detail="Failed to create share token")


@router.get("/jobs/{job_id}/shares", response_model=ListSharesResponse)
@limiter.limit("60/minute")
async def list_share_tokens(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    List all share tokens for a job.
    
    Returns active and expired tokens (not revoked ones).
    Only the job owner can list shares.
    """
    # Validate job_id format
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")
    
    # Get job and verify ownership
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view shares for this job")
    
    # Get share tokens from database
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = client.table("share_tokens").select("*").eq(
            "job_id", job_id
        ).order("created_at", desc=True).execute()
        
        now = datetime.now(timezone.utc)
        shares = []
        
        for row in result.data or []:
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            is_expired = expires_at < now
            
            shares.append(ShareTokenInfo(
                share_id=row["id"],
                token=row["token"][-8:],  # Only show last 8 chars for security
                doc_type=row["doc_type"],
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
                expires_at=expires_at,
                view_count=row["view_count"] or 0,
                max_views=row["max_views"],
                is_revoked=row["is_revoked"],
                is_expired=is_expired,
                share_url=get_share_url(row["token"]) if not row["is_revoked"] else "",
            ))
        
        return ListSharesResponse(job_id=job_id, shares=shares)
        
    except Exception as e:
        logger.error(f"Failed to list share tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to list share tokens")


@router.delete("/jobs/{job_id}/share/{share_id}", response_model=RevokeShareResponse)
@limiter.limit("30/minute")
async def revoke_share_token(
    request: Request,
    job_id: str,
    share_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """
    Revoke a share token.
    
    The share link will immediately stop working.
    Only the job owner can revoke shares.
    """
    # Validate UUIDs
    try:
        uuid.UUID(job_id)
        uuid.UUID(share_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    # Get job and verify ownership
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke shares for this job")
    
    # Update share token in database
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        result = client.table("share_tokens").update({
            "is_revoked": True
        }).eq("id", share_id).eq("job_id", job_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Share token not found")
        
        logger.info(
            "Share token revoked",
            extra={
                "job_id": job_id,
                "share_id": share_id,
                "user_id": user.user_id,
                "event": "share_revoked",
            }
        )
        
        return RevokeShareResponse(
            share_id=share_id,
            message="Share link has been revoked"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke share token: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke share token")


# =============================================================================
# PUBLIC ENDPOINT (No authentication required)
# =============================================================================

@router.get("/shared/{token}", response_model=SharedDocumentResponse)
@limiter.limit("60/minute")
async def get_shared_document(
    request: Request,
    token: str,
):
    """
    Get a shared document by token.
    
    This is a PUBLIC endpoint - no authentication required.
    The token itself serves as authorization.
    
    Returns document content if:
    - Token exists and is not revoked
    - Token has not expired
    - Max views not exceeded (if set)
    """
    if not token or len(token) < 32:
        raise HTTPException(status_code=400, detail="Invalid share token")
    
    # Get share token from database
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=503, detail="Service unavailable")
    
    try:
        result = client.table("share_tokens").select("*").eq("token", token).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Share link not found or expired")
        
        share = result.data[0]
        
        # Check if revoked
        if share["is_revoked"]:
            raise HTTPException(status_code=410, detail="This share link has been revoked")
        
        # Check expiration
        expires_at = datetime.fromisoformat(share["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=410, detail="This share link has expired")
        
        # Check max views
        view_count = share["view_count"] or 0
        max_views = share["max_views"]
        if max_views is not None and view_count >= max_views:
            raise HTTPException(status_code=410, detail="This share link has reached its view limit")
        
        # Increment view count
        client.table("share_tokens").update({
            "view_count": view_count + 1
        }).eq("id", share["id"]).execute()
        
        # Get job and document content
        job_id = share["job_id"]
        doc_type = share["doc_type"]
        
        job = get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Associated job not found")
        
        # Get document content
        artifacts = job.artifacts
        if not artifacts:
            raise HTTPException(status_code=404, detail="Document content not available")
        
        artifacts_dict = artifacts.model_dump(exclude_none=True) if hasattr(artifacts, "model_dump") else {}
        
        markdown = None
        data = None
        doc_title = DOC_TYPE_NAMES.get(doc_type, "Document")
        
        if doc_type == "all":
            # Return all documents combined
            all_docs = []
            for dt in ["doc_0", "doc_1", "doc_2", "doc_3"]:
                doc_content = _get_document_content(artifacts_dict, dt, job_id)
                if doc_content:
                    all_docs.append(f"# {DOC_TYPE_NAMES[dt]}\n\n{doc_content}")
            markdown = "\n\n---\n\n".join(all_docs) if all_docs else None
            doc_title = "All Documents"
        else:
            markdown = _get_document_content(artifacts_dict, doc_type, job_id)
        
        if not markdown:
            raise HTTPException(status_code=404, detail="Document content not available")
        
        logger.info(
            "Shared document accessed",
            extra={
                "job_id": job_id,
                "doc_type": doc_type,
                "view_count": view_count + 1,
                "event": "share_viewed",
            }
        )
        
        return SharedDocumentResponse(
            job_id=job_id,
            job_title=job.title,
            doc_type=doc_type,
            doc_title=doc_title,
            markdown=markdown,
            data=data,
            expires_at=expires_at,
            view_count=view_count + 1,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get shared document: {e}")
        raise HTTPException(status_code=500, detail="Failed to load shared document")


def _get_document_content(artifacts_dict: dict, doc_type: str, job_id: str) -> Optional[str]:
    """Get markdown content for a document type."""
    # Map doc_type to artifact fields
    doc_mapping = {
        "doc_0": {"path_field": "doc_0_path", "inline_field": "source_ledger"},
        "doc_1": {"path_field": "doc_1_path", "inline_field": "jump_start"},
        "doc_2": {"path_field": "doc_2_path", "inline_field": "semantic_brief"},
        "doc_3": {"path_field": "doc_3_path", "inline_field": "producer_packet_md"},
    }
    
    if doc_type not in doc_mapping:
        return None
    
    mapping = doc_mapping[doc_type]
    
    # Try inline data first
    inline_data = artifacts_dict.get(mapping["inline_field"])
    if inline_data:
        if isinstance(inline_data, dict):
            markdown = inline_data.get("markdown")
            if markdown and "stored in Supabase Storage" not in markdown:
                return markdown
        elif isinstance(inline_data, str):
            # For producer_packet_md which is a string
            return inline_data
    
    # Try storage path
    storage_path = artifacts_dict.get(mapping["path_field"])
    if storage_path:
        try:
            from backend.integrations.supabase_storage import get_storage_client
            storage_client = get_storage_client()
            if storage_client:
                doc_data = storage_client.download_document(storage_path)
                if isinstance(doc_data, dict):
                    return doc_data.get("markdown")
        except Exception as e:
            logger.warning(f"Failed to fetch {doc_type} from storage for job {job_id}: {e}")
    
    return None
