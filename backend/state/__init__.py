"""Job persistence interface and implementations."""
from backend.models.job_record import Artifacts, JobRecord
from backend.state.factory import get_job_store
from backend.state.interface import JobStore

# Export the factory function and interface
__all__ = [
    "JobStore",
    "JobRecord",
    "Artifacts",
    "get_job_store",
    "create_job",
    "get_job",
    "update_job",
    "update_job_status",  # Backward compatibility
    "list_jobs",
]


def create_job(
    config_json: dict | None = None,
    topic: str | None = None,
    user_id: str | None = None,
) -> JobRecord:
    """
    Create a new job with the given configuration.

    Args:
        config_json: Job configuration as JSON dict (preferred)
        topic: Legacy topic string (will be wrapped in config_json if provided)
        user_id: Optional user ID for job ownership

    Returns:
        Created JobRecord
    """
    store = get_job_store()

    # Backward compatibility: if topic is provided, wrap it in config_json
    if topic:
        if config_json:
            config_json["topic"] = topic
        else:
            config_json = {"topic": topic}
    elif not config_json:
        config_json = {}

    return store.create_job(config_json, user_id=user_id)


def get_job(job_id: str) -> JobRecord | None:
    """
    Get a job by ID.
    
    Args:
        job_id: Job identifier
        
    Returns:
        JobRecord if found, None otherwise
    """
    store = get_job_store()
    return store.get_job(job_id)


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress_percent: int | None = None,
    title: str | None = None,
    error: str | None = None,
    partial_outputs: dict | None = None,
    partial_artifacts: dict | None = None,
    warnings_append: list[str] | None = None,
    config_json: dict | None = None,
    artifacts: Artifacts | None = None,
    warnings: list[str] | None = None,
    interpretations: list[dict] | None = None,
    selected_interpretations: list[int] | None = None,
) -> JobRecord | None:
    """
    Update a job with partial updates.

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
        Updated JobRecord if found, None otherwise
    """
    store = get_job_store()
    return store.update_job(
        job_id,
        status=status,
        stage=stage,
        progress_percent=progress_percent,
        title=title,
        error=error,
        partial_outputs=partial_outputs,
        partial_artifacts=partial_artifacts,
        warnings_append=warnings_append,
        config_json=config_json,
        artifacts=artifacts,
        warnings=warnings,
        interpretations=interpretations,
        selected_interpretations=selected_interpretations,
    )


# Backward compatibility: update_job_status function
def update_job_status(job_id: str, status: str, result: dict | None = None) -> None:
    """
    Update job status (backward compatibility wrapper).

    This is kept for compatibility with existing code.
    New code should use update_job() instead.
    """
    store = get_job_store()
    # If result is provided, merge it into outputs (legacy behavior)
    partial_outputs = None
    if result:
        # Store result in outputs for backward compatibility
        partial_outputs = {"legacy_result": result}

    store.update_job(job_id, status=status, partial_outputs=partial_outputs)


def list_jobs(
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[JobRecord]:
    """
    List jobs, optionally filtered by user_id.

    Args:
        user_id: Optional user ID to filter by
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip (for pagination)

    Returns:
        List of JobRecords, sorted by created_at descending
    """
    store = get_job_store()
    return store.list_jobs(user_id=user_id, limit=limit, offset=offset)
