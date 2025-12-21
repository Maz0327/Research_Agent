"""Supabase job store implementation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from loguru import logger

from backend.config import get_settings
from backend.models.job_record import Artifacts, JobRecord, Outputs
from backend.state.interface import JobStore
from backend.utils.error_handling import sanitize_error_message

# Constants
SUPABASE_API_TIMEOUT = 5.0  # seconds


def _rest_base_url() -> str:
    """Base URL for Supabase PostgREST."""
    settings = get_settings()
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is not configured")
    base_url = str(settings.supabase_url)
    return base_url.rstrip("/") + "/rest/v1"


def _headers() -> dict[str, str]:
    """Headers required by Supabase REST."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO format datetime string from Supabase."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None


def _record_from_db_row(row: dict[str, Any]) -> JobRecord:
    """Convert database row to JobRecord."""
    # Parse artifacts
    artifacts_data = row.get("artifacts") or {}
    artifacts = Artifacts(
        drive_folder_url=artifacts_data.get("drive_folder_url"),
        doc_urls=artifacts_data.get("doc_urls"),
    )

    # Parse outputs
    outputs_data = row.get("outputs") or {}
    outputs = Outputs(
        research_map_md=outputs_data.get("research_map_md"),
        source_shortlist_md=outputs_data.get("source_shortlist_md"),
        youtube_index_md=outputs_data.get("youtube_index_md"),
        quote_bank_md=outputs_data.get("quote_bank_md"),
        claims_ledger_md=outputs_data.get("claims_ledger_md"),
        evidence_table_md=outputs_data.get("evidence_table_md"),
        missing_angles_md=outputs_data.get("missing_angles_md"),
    )

    return JobRecord(
        job_id=row["id"],
        user_id=row.get("user_id"),
        created_at=_parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
        status=row.get("status", "queued"),
        stage=row.get("stage"),
        progress_percent=row.get("progress_percent", 0),
        config_json=row.get("config_json") or {},
        warnings=row.get("warnings") or [],
        artifacts=artifacts,
        outputs=outputs,
    )


class SupabaseJobStore(JobStore):
    """Supabase job store implementation."""

    def create_job(self, config_json: dict, user_id: str | None = None) -> JobRecord:
        """Create a new job record in Supabase."""
        url = _rest_base_url() + "/jobs"
        headers = _headers()
        headers["Prefer"] = "return=representation"

        # Extract pipeline from config_json for the database column
        # Support both old (quick/full) and new (documentary modes) pipeline values
        pipeline = config_json.get("pipeline", "investigation")

        payload: dict[str, Any] = {
            "status": "queued",
            "pipeline": pipeline,  # Add pipeline as separate column for database constraint
            "config_json": config_json,
            # these are initialized empty so later updates can safely merge into them
            "warnings": [],
            "artifacts": {},
            "outputs": {},
        }

        # Add user_id if provided (for job ownership)
        if user_id:
            payload["user_id"] = user_id

        logger.info("Creating job in Supabase with config_json keys=%s (user: %s)", list(config_json.keys()), user_id or "anonymous")
        logger.debug("Supabase job insert payload: %r", payload)

        with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to create job in Supabase: %s",
                sanitize_error_message(e),
            )
            raise

        data = resp.json()
        if isinstance(data, list):
            if not data:
                raise RuntimeError("Supabase returned an empty list when creating a job")
            data = data[0]

        job = _record_from_db_row(data)
        logger.info(f"Created job {job.job_id} in Supabase")
        return job

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Get a job record by ID from Supabase."""
        url = _rest_base_url() + "/jobs"
        headers = _headers()
        params = {
            "id": f"eq.{job_id}",
            "limit": 1,
        }

        with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
            resp = client.get(url, headers=headers, params=params)

        if resp.status_code == 404:
            return None

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to fetch job %s from Supabase: %s",
                job_id,
                sanitize_error_message(e),
            )
            raise

        data = resp.json()
        if not data:
            return None

        return _record_from_db_row(data[0])

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
        """Update a job record in Supabase."""
        # First get the current job to merge updates
        current_job = self.get_job(job_id)
        if not current_job:
            logger.warning(f"Job {job_id} not found for update")
            return None

        # Build update payload
        payload: dict[str, Any] = {}

        if status is not None:
            payload["status"] = status
        if stage is not None:
            payload["stage"] = stage
        if progress_percent is not None:
            payload["progress_percent"] = progress_percent

        # Append warnings
        if warnings_append:
            new_warnings = current_job.warnings + warnings_append
            payload["warnings"] = new_warnings

        # Merge partial outputs
        if partial_outputs:
            outputs_dict = current_job.outputs.model_dump(exclude_none=True)
            outputs_dict.update(partial_outputs)
            payload["outputs"] = outputs_dict

        # Merge partial artifacts
        if partial_artifacts:
            artifacts_dict = current_job.artifacts.model_dump(exclude_none=True)
            artifacts_dict.update(partial_artifacts)
            payload["artifacts"] = artifacts_dict

        if not payload:
            # No changes, return current job
            return current_job

        url = _rest_base_url() + "/jobs"
        headers = _headers()
        headers["Prefer"] = "return=representation"
        params = {"id": f"eq.{job_id}"}

        logger.info(f"Updating job {job_id} in Supabase with keys=%s", list(payload.keys()))
        logger.debug("Supabase job update payload: %r", payload)

        with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
            resp = client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code == 404:
            logger.warning(f"Job {job_id} not found for update")
            return None

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to update job %s: %s",
                job_id,
                sanitize_error_message(e),
            )
            raise

        data = resp.json()
        if isinstance(data, list):
            if not data:
                return None
            data = data[0]

        return _record_from_db_row(data)

    def list_jobs(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobRecord]:
        """List jobs, optionally filtered by user_id."""
        url = _rest_base_url() + "/jobs"
        headers = _headers()

        # Build query parameters
        params = {
            "order": "created_at.desc",  # Sort by created_at descending
            "limit": limit,
            "offset": offset,
        }

        # Filter by user_id if provided
        # Note: RLS policies will also enforce user filtering on the database side
        if user_id is not None:
            params["user_id"] = f"eq.{user_id}"

        logger.debug(f"Listing jobs with params: {params}")

        with httpx.Client(timeout=SUPABASE_API_TIMEOUT) as client:
            resp = client.get(url, headers=headers, params=params)

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(
                "Failed to list jobs from Supabase: %s",
                sanitize_error_message(e),
            )
            raise

        data = resp.json()
        if not isinstance(data, list):
            logger.warning(f"Expected list from Supabase, got: {type(data)}")
            return []

        jobs = [_record_from_db_row(row) for row in data]
        logger.info(f"Listed {len(jobs)} jobs from Supabase")
        return jobs
