"""Job storage interface."""
from abc import ABC, abstractmethod
from typing import Optional

from backend.models.job_record import JobRecord


class JobStore(ABC):
    """Abstract interface for job storage."""
    
    @abstractmethod
    def create_job(self, config_json: dict) -> JobRecord:
        """
        Create a new job record.
        
        Args:
            config_json: Job configuration as JSON dict
            
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
        partial_outputs: Optional[dict] = None,
        partial_artifacts: Optional[dict] = None,
        warnings_append: Optional[list[str]] = None,
    ) -> Optional[JobRecord]:
        """
        Update a job record with partial updates.
        
        Args:
            job_id: Job identifier
            status: New status (optional)
            stage: New stage (optional)
            progress_percent: New progress percentage (optional)
            partial_outputs: Partial outputs dict to merge (optional)
            partial_artifacts: Partial artifacts dict to merge (optional)
            warnings_append: List of warnings to append (optional)
            
        Returns:
            Updated JobRecord if found and updated, None otherwise
        """
        pass

