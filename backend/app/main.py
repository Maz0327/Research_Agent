"""FastAPI application main module."""
from fastapi import FastAPI, HTTPException
from loguru import logger

from backend.app.routes import router as slack_router
from backend.config import get_settings
from backend.models.job import CreateJobRequest, JobStatusResponse
from backend.state import create_job, get_job
from backend.worker import run_research_job

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Research Agent API",
    description="Cloud-based research backend for aggregating content from multiple sources",
    version="0.1.0",
)

# Include routers
app.include_router(slack_router, tags=["slack"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.post("/jobs", response_model=JobStatusResponse)
async def create_job_endpoint(request: CreateJobRequest):
    """
    Create a new research job.
    
    Args:
        request: Job creation request with topic
        
    Returns:
        Initial job status response
    """
    # Validate and clean topic
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    
    # Create job with config_json containing topic
    config_json = {"topic": topic}
    job = create_job(config_json=config_json)
    
    # Enqueue Celery task
    logger.info(f"Enqueuing research job {job.job_id} for topic: {topic}")
    run_research_job.delay(job.job_id, topic)
    
    # Convert to response model (backward compatibility)
    return JobStatusResponse(
        job_id=job.job_id,
        topic=topic,  # Extract from config_json
        status=job.status,
        result=None,  # Legacy field, not in new model
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a research job.
    
    Args:
        job_id: Unique identifier for the research job
        
    Returns:
        Job status response or 404 if not found
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    # Extract topic from config_json (backward compatibility)
    topic = job.config_json.get("topic", "")
    
    return JobStatusResponse(
        job_id=job.job_id,
        topic=topic,
        status=job.status,
        result=None,  # Legacy field, not in new model
    )


