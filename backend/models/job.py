"""Job-related Pydantic models."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(BaseModel):
    """Job status model shared between FastAPI and Celery workers."""
    
    # Supabase column is "id", but we expose it as "job_id" in the API
    job_id: str = Field(alias="id")
    topic: str
    status: str
    result: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class CreateJobRequest(BaseModel):
    """Request model for creating a new research job."""
    topic: str
    # Later we will add: time_range, depth, source_types, etc.


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    topic: str
    status: str
    result: dict | None = None

