"""Job storage interface."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from backend.models.job_record import Artifacts, JobRecord


def safe_merge(target: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into target dict, skipping None values.

    This ensures consistent behavior between in-memory and Supabase stores:
    - None values in updates are ignored (don't overwrite existing values)
    - Non-None values are merged into target

    Args:
        target: Base dict to merge into (not modified)
        updates: Dict with updates to apply

    Returns:
        New merged dict
    """
    result = dict(target)
    for key, value in updates.items():
        if value is not None:
            result[key] = value
    return result


class JobStore(ABC):
    """Abstract interface for job storage."""

    @abstractmethod
    def create_job(self, config_json: dict, user_id: Optional[str] = None) -> JobRecord:
        """
        Create a new job record.

        Args:
            config_json: Job configuration as JSON dict
            user_id: Optional user ID for job ownership

        Returns:
            Created JobRecord with job_id
        """
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """
        Get a job record by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobRecord if found, None otherwise
        """
        pass

    @abstractmethod
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
        # Iteration tracking fields (separate from main job status)
        iteration_status: Optional[str] = None,
        iteration_id: Optional[str] = None,
        iteration_started_at: Optional[datetime] = None,
        iteration_completed_at: Optional[datetime] = None,
        iteration_error: Optional[str] = None,
        iteration_progress_percent: Optional[int] = None,
    ) -> Optional[JobRecord]:
        """
        Update a job record with partial updates.

        Args:
            job_id: Job identifier
            status: New status (optional)
            stage: New stage (optional)
            progress_percent: New progress percentage (optional)
            title: AI-generated short title (optional)
            error: Error message for failed jobs (optional)
            partial_outputs: Partial outputs dict to merge (optional)
            partial_artifacts: Partial artifacts dict to merge (optional)
            warnings_append: List of warnings to append (optional)
            config_json: Full config_json replacement (optional)
            artifacts: Full artifacts replacement (optional)
            warnings: Full warnings replacement (optional)
            interpretations: Disambiguation interpretations list (optional)
            selected_interpretations: User-selected interpretation indices (optional)
            booster_status: Booster execution status (queued/running/completed/failed)
            booster_started_at: When booster started
            booster_completed_at: When booster completed/failed
            booster_error: Booster error message if failed
            booster_progress_percent: Booster progress (0-100)
            producer_status: Producer execution status (queued/running/completed/failed)
            producer_started_at: When producer started
            producer_completed_at: When producer completed/failed
            producer_error: Producer error message if failed
            producer_progress_percent: Producer progress (0-100)
            iteration_status: Current iteration status (queued/running/completed/failed)
            iteration_id: Current iteration ID being processed (it_0001, ...)
            iteration_started_at: When current iteration started
            iteration_completed_at: When current iteration completed/failed
            iteration_error: Current iteration error message if failed
            iteration_progress_percent: Current iteration progress (0-100)

        Returns:
            Updated JobRecord if found and updated, None otherwise
        """
        pass

    @abstractmethod
    def list_jobs(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        archived: Optional[bool] = None,
    ) -> list[JobRecord]:
        """
        List jobs, optionally filtered by user_id.

        Args:
            user_id: Optional user ID to filter by (None for all jobs)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)
            archived: Filter by archived status (None/False = non-archived, True = archived)

        Returns:
            List of JobRecords, sorted by created_at descending
        """
        pass

    @abstractmethod
    def archive_job(self, job_id: str, archived: bool = True) -> Optional[JobRecord]:
        """
        Archive or unarchive a job.

        Args:
            job_id: Job identifier
            archived: True to archive, False to unarchive

        Returns:
            Updated JobRecord if found, None otherwise
        """
        pass
