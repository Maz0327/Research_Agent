"""Share token models for document sharing."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Valid document types for sharing
DocType = Literal["doc_0", "doc_1", "doc_2", "doc_3", "all"]


class CreateShareRequest(BaseModel):
    """Request to create a share token for a document."""
    doc_type: DocType = Field(
        ...,
        description="Document type to share: doc_0 (Source Ledger), doc_1 (Jump-Start), doc_2 (Semantic Brief), doc_3 (Producer Packet), or all"
    )
    expires_in_hours: int = Field(
        72,
        ge=1,
        le=720,  # Max 30 days
        description="Hours until the share link expires (1-720, default 72)"
    )
    max_views: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Maximum number of views allowed. Null = unlimited."
    )


class CreateShareResponse(BaseModel):
    """Response after creating a share token."""
    share_id: str = Field(..., description="Unique share token ID")
    token: str = Field(..., description="Share token for the URL")
    share_url: str = Field(..., description="Full share URL to copy")
    doc_type: DocType = Field(..., description="Document type being shared")
    expires_at: datetime = Field(..., description="When the share link expires")
    max_views: Optional[int] = Field(None, description="Maximum views allowed")


class ShareTokenInfo(BaseModel):
    """Information about a share token."""
    share_id: str = Field(..., description="Unique share token ID")
    token: str = Field(..., description="Share token (last 8 chars shown)")
    doc_type: DocType = Field(..., description="Document type being shared")
    created_at: datetime = Field(..., description="When the share was created")
    expires_at: datetime = Field(..., description="When the share expires")
    view_count: int = Field(..., description="Current view count")
    max_views: Optional[int] = Field(None, description="Maximum views allowed")
    is_revoked: bool = Field(..., description="Whether the share is revoked")
    is_expired: bool = Field(..., description="Whether the share has expired")
    share_url: str = Field(..., description="Full share URL")


class ListSharesResponse(BaseModel):
    """Response listing all share tokens for a job."""
    job_id: str = Field(..., description="Job ID")
    shares: list[ShareTokenInfo] = Field(..., description="List of share tokens")


class SharedDocumentResponse(BaseModel):
    """Response containing shared document content."""
    job_id: str = Field(..., description="Job ID")
    job_title: Optional[str] = Field(None, description="Job title for display")
    doc_type: DocType = Field(..., description="Document type")
    doc_title: str = Field(..., description="Document title (e.g., 'Source Ledger')")
    markdown: Optional[str] = Field(None, description="Document markdown content")
    data: Optional[dict] = Field(None, description="Document structured data")
    expires_at: datetime = Field(..., description="When the share expires")
    view_count: int = Field(..., description="Current view count")


class RevokeShareResponse(BaseModel):
    """Response after revoking a share token."""
    share_id: str = Field(..., description="Share token ID that was revoked")
    message: str = Field(..., description="Success message")


# Document type display names
DOC_TYPE_NAMES = {
    "doc_0": "Source Ledger",
    "doc_1": "Jump-Start Directions",
    "doc_2": "Semantic Brief",
    "doc_3": "Producer Packet",
    "all": "All Documents",
}
