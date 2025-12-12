"""Celery worker configuration and task definitions."""
from celery import Celery
from loguru import logger

from backend.config import get_settings
from backend.pipelines.youtube_search import search_youtube_videos
from backend.state import get_job, update_job_status

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "research_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "backend.worker.run_research_job": {"queue": "research"},
    },
    task_default_queue="research",
    task_default_exchange="research",
    task_default_routing_key="research",
)


@celery_app.task(name="backend.worker.run_research_job")
def run_research_job(job_id: str, topic: str) -> dict:
    """
    Research job task that searches YouTube and aggregates results.
    
    Args:
        job_id: Unique identifier for the research job
        topic: Research topic string
        
    Returns:
        Dictionary with research results including YouTube videos
    """
    logger.info(f"Starting research job {job_id} for topic: {topic}")
    
    try:
        # Update status to running
        update_job_status(job_id, "running", None)
        
        # Search YouTube for videos related to the topic
        videos = search_youtube_videos(topic, max_results=5)
        
        # Build result dictionary
        result = {
            "topic": topic,
            "youtube": {
                "video_count": len(videos),
                "videos": [
                    {
                        "video_id": v.video_id,
                        "title": v.title,
                        "channel_title": v.channel_title,
                        "published_at": v.published_at,
                    }
                    for v in videos
                ],
            },
        }
        
        # Update job status to completed with result
        update_job_status(job_id, "completed", result)
        
        logger.info(f"Research job {job_id} completed successfully. Found {len(videos)} YouTube videos.")
        return result
        
    except Exception as e:
        logger.exception(f"Error in research job {job_id}: {e}")
        
        # Update job status to failed with error details
        error_result = {
            "error": str(e),
            "topic": topic,
        }
        update_job_status(job_id, "failed", error_result)
        
        return error_result

