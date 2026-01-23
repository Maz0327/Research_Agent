"""In-memory job store implementation for local development.

NOTE: This store is for development/testing only. It is NOT suitable for
production use with multiple workers due to lack of persistence and
potential race conditions even with locking (each worker has its own store).
"""
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from backend.models.job_record import Artifacts, JobRecord, Outputs
from backend.state.interface import JobStore


class InMemoryJobStore(JobStore):
    """In-memory job store for local development.

    Thread-safe for single-worker development. For production,
    use SupabaseJobStore with proper database persistence.
    """

    def __init__(self):
        """Initialize in-memory storage with thread lock."""
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
    
    def create_job(self, config_json: dict, user_id: str | None = None) -> JobRecord:
        """Create a new job record."""
        job_id = str(uuid.uuid4())
        # Extract pipeline from config_json
        pipeline = config_json.get("pipeline", "investigation")
        job = JobRecord(
            job_id=job_id,
            user_id=user_id,
            pipeline=pipeline,
            created_at=datetime.now(timezone.utc),
            status="queued",
            config_json=config_json,
        )
        with self._lock:
            self._jobs[job_id] = job
        logger.info(f"Created job {job_id} in memory (user: {user_id or 'anonymous'})")
        return job
    
    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Get a job record by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress_percent: Optional[int] = None,
        title: Optional[str] = None,
        error: Optional[str] = None,
        partial_outputs: Optional[dict] = None,
        partial_artifacts: Optional[dict] = None,
        warnings_append: Optional[list[str]] = None,
        config_json: Optional[dict] = None,
        artifacts: Optional[Artifacts] = None,
        warnings: Optional[list[str]] = None,
        interpretations: Optional[list[dict]] = None,
        selected_interpretations: Optional[list[int]] = None,
        # Booster tracking fields (separate from main job status)
        booster_status: Optional[str] = None,
        booster_started_at: Optional[datetime] = None,
        booster_completed_at: Optional[datetime] = None,
        booster_error: Optional[str] = None,
        booster_progress_percent: Optional[int] = None,
        # Producer tracking fields (separate from main job status)
        producer_status: Optional[str] = None,
        producer_started_at: Optional[datetime] = None,
        producer_completed_at: Optional[datetime] = None,
        producer_error: Optional[str] = None,
        producer_progress_percent: Optional[int] = None,
    ) -> Optional[JobRecord]:
        """Update a job record with partial updates."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Job {job_id} not found for update")
                return None

            # Update simple fields
            if status is not None:
                job.status = status
            if stage is not None:
                # Track when stage changed for ETA calculation
                if job.stage != stage:
                    job.stage_started_at = datetime.now(timezone.utc)
                job.stage = stage
            if progress_percent is not None:
                job.progress_percent = progress_percent
            if title is not None:
                job.title = title
            if error is not None:
                job.error = error
            if config_json is not None:
                job.config_json = config_json

            # Disambiguation fields
            if interpretations is not None:
                job.interpretations = interpretations
            if selected_interpretations is not None:
                job.selected_interpretations = selected_interpretations

            # Full replacements
            if artifacts is not None:
                job.artifacts = artifacts
            if warnings is not None:
                job.warnings = warnings

            # Append warnings (merge operation)
            if warnings_append:
                job.warnings.extend(warnings_append)

            # Merge partial outputs
            if partial_outputs:
                if job.outputs is None:
                    job.outputs = Outputs()
                for key, value in partial_outputs.items():
                    if hasattr(job.outputs, key) and value is not None:
                        setattr(job.outputs, key, value)

            # Merge partial artifacts
            if partial_artifacts:
                if job.artifacts is None:
                    job.artifacts = Artifacts()
                for key, value in partial_artifacts.items():
                    if hasattr(job.artifacts, key) and value is not None:
                        setattr(job.artifacts, key, value)

            # Booster tracking fields
            if booster_status is not None:
                job.booster_status = booster_status
            if booster_started_at is not None:
                job.booster_started_at = booster_started_at
            if booster_completed_at is not None:
                job.booster_completed_at = booster_completed_at
            if booster_error is not None:
                job.booster_error = booster_error
            if booster_progress_percent is not None:
                job.booster_progress_percent = booster_progress_percent

            # Producer tracking fields
            if producer_status is not None:
                job.producer_status = producer_status
            if producer_started_at is not None:
                job.producer_started_at = producer_started_at
            if producer_completed_at is not None:
                job.producer_completed_at = producer_completed_at
            if producer_error is not None:
                job.producer_error = producer_error
            if producer_progress_percent is not None:
                job.producer_progress_percent = producer_progress_percent

            logger.debug(f"Updated job {job_id} in memory")
            return job

    def list_jobs(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobRecord]:
        """List jobs, optionally filtered by user_id."""
        with self._lock:
            jobs = list(self._jobs.values())

        # Exclude deleted and archived jobs by default
        jobs = [job for job in jobs if job.status not in ("deleted", "archived")]

        # Filter by user_id if provided (outside lock - operating on copy)
        if user_id is not None:
            jobs = [job for job in jobs if job.user_id == user_id]

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Apply pagination
        start = offset
        end = offset + limit

        return jobs[start:end]
