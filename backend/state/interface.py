"""Job storage interface."""
from abc import ABC, abstractmethod
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
    ) -> list[JobRecord]:
        """
        List jobs, optionally filtered by user_id.

        Args:
            user_id: Optional user ID to filter by (None for all jobs)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)

        Returns:
            List of JobRecords, sorted by created_at descending
        """
        pass
