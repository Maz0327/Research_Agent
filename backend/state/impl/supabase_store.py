"""Supabase job store implementation with atomic JSONB operations."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

import httpx
from loguru import logger
from supabase import create_client, Client

from backend.config import get_settings
from backend.models.job_record import Artifacts, JobRecord, Outputs
from backend.state.interface import JobStore, safe_merge
from backend.utils.error_handling import sanitize_error_message
from backend.utils.validators import validate_uuid, ValidationError

# Constants
SUPABASE_API_TIMEOUT = 15.0  # seconds


@lru_cache()
def _get_supabase_client() -> Client:
    """Get singleton Supabase client for RPC calls."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key,
    )


# Public alias for external modules (e.g., error_logger)
def get_supabase_client() -> Client:
    """Get Supabase client. Public wrapper around _get_supabase_client."""
    return _get_supabase_client()


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


def _normalize_jsonb_field(data: Any, field_name: str | None = None, job_id: str | None = None) -> dict:
    """Normalize JSONB field to dict, handling corrupted list/string data.

    Args:
        data: Raw JSONB data from database
        field_name: Name of the field being normalized (for logging)
        job_id: Job ID for logging context
    """
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        # Corrupted: merge all dict items in the list
        merged = {}
        for item in data:
            if isinstance(item, dict):
                merged.update(item)
            elif isinstance(item, str):
                try:
                    import json
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        merged.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        # Enhanced logging with field name and job_id
        context_parts = []
        if field_name:
            context_parts.append(f"field={field_name}")
        context_parts.append(f"items={len(data)}")
        if job_id:
            context_parts.append(f"job_id={job_id}")
        logger.warning(f"Normalized corrupted JSONB list to dict: {' '.join(context_parts)}")
        return merged
    if isinstance(data, str):
        try:
            import json
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return {}


def _record_from_db_row(row: dict[str, Any]) -> JobRecord:
    """Convert database row to JobRecord."""
    job_id = row.get("id")

    # Parse artifacts (with corruption handling)
    # Pass all fields from DB to Artifacts - Pydantic ignores unknown fields
    artifacts_data = _normalize_jsonb_field(row.get("artifacts"), field_name="artifacts", job_id=job_id)
    artifacts = Artifacts(**artifacts_data)

    # Parse outputs (with corruption handling)
    outputs_data = _normalize_jsonb_field(row.get("outputs"), field_name="outputs", job_id=job_id)
    outputs = Outputs(**outputs_data)

    return JobRecord(
        job_id=row["id"],
        user_id=row.get("user_id"),
        title=row.get("title"),
        pipeline=row.get("pipeline", "semantic"),
        created_at=_parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
        status=row.get("status", "queued"),
        stage=row.get("stage"),
        stage_started_at=_parse_datetime(row.get("stage_started_at")),
        progress_percent=row.get("progress_percent", 0),
        error=row.get("error"),
        config_json=row.get("config_json") or {},
        warnings=row.get("warnings") or [],
        total_sources=row.get("total_sources"),
        total_claims=row.get("total_claims"),
        api_costs=row.get("api_costs"),
        artifacts=artifacts,
        outputs=outputs,
    )


class SupabaseJobStore(JobStore):
    """Supabase job store implementation with atomic JSONB operations."""

    def __init__(self) -> None:
        """Initialize the store with HTTP client for connection pooling."""
        self._http_client: Optional[httpx.Client] = None

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=SUPABASE_API_TIMEOUT,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._http_client

    def create_job(self, config_json: dict, user_id: str | None = None) -> JobRecord:
        """Create a new job record in Supabase."""
        url = _rest_base_url() + "/jobs"
        headers = _headers()
        headers["Prefer"] = "return=representation"

        # Extract pipeline from config_json for the database column
        pipeline = config_json.get("pipeline", "investigation")

        payload: dict[str, Any] = {
            "status": "queued",
            "pipeline": pipeline,
            "config_json": config_json,
            "warnings": [],
            "artifacts": {},
            "outputs": {},
        }

        # Add user_id if provided (for job ownership)
        if user_id:
            # Validate user_id format
            try:
                user_id = validate_uuid(user_id, "user_id")
                payload["user_id"] = user_id
            except ValidationError as e:
                logger.error(f"Invalid user_id format in create_job: {e}")
                raise ValueError(f"Invalid user_id: {e}") from e

        logger.info(
            "Creating job in Supabase with config_json keys=%s (user: %s)",
            list(config_json.keys()),
            user_id or "anonymous",
        )

        client = self._get_http_client()
        resp = client.post(url, headers=headers, json=payload)

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Failed to create job in Supabase: %s", sanitize_error_message(e))
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
        """Get a job record by ID from Supabase.

        Args:
            job_id: The UUID of the job to retrieve

        Returns:
            JobRecord if found, None if not found

        Raises:
            ValidationError: If job_id is not a valid UUID format
        """
        # Validate UUID format - raise exception instead of returning None
        try:
            job_id = validate_uuid(job_id, "job_id")
        except ValidationError as e:
            logger.warning(f"Invalid job_id format in get_job: {e}")
            raise  # Re-raise ValidationError instead of returning None

        url = _rest_base_url() + "/jobs"
        headers = _headers()
        params = {
            "id": f"eq.{job_id}",
            "limit": 1,
        }

        client = self._get_http_client()
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
        Update a job record in Supabase using atomic operations.

        Uses PostgreSQL RPC functions for atomic JSONB merges to prevent race conditions.
        Falls back to non-atomic behavior if RPC is not available.

        Args:
            job_id: UUID of the job to update
            status: New status value
            stage: New stage value (also updates stage_started_at)
            progress_percent: New progress percentage (0-100)
            title: New job title
            error: Error message if job failed
            partial_outputs: JSONB dict to merge into outputs (atomic)
            partial_artifacts: JSONB dict to merge into artifacts (atomic)
            warnings_append: List of warnings to append (atomic)
            config_json: Full replacement of config_json
            artifacts: Full replacement of artifacts
            warnings: Full replacement of warnings
            interpretations: Disambiguation interpretations list (optional)
            selected_interpretations: User-selected interpretation indices (optional)

        Returns:
            Updated JobRecord or None if job not found

        Raises:
            ValidationError: If job_id is not a valid UUID format
        """
        # Validate UUID format
        try:
            job_id = validate_uuid(job_id, "job_id")
        except ValidationError as e:
            logger.warning(f"Invalid job_id format in update_job: {e}")
            raise

        # Check if we need atomic merge operations
        needs_atomic = bool(partial_outputs or partial_artifacts or warnings_append)

        # Guard: Prevent silent data loss when artifacts= is used with atomic path
        # The atomic path only supports partial_artifacts (merge), not artifacts (full replace)
        if needs_atomic and artifacts is not None:
            raise ValueError(
                f"Invalid update_job call for job {job_id}: "
                "artifacts= cannot be used with atomic updates (partial_outputs/partial_artifacts/warnings_append). "
                "Use partial_artifacts= instead for atomic merge semantics."
            )

        if needs_atomic:
            return self._update_job_atomic(
                job_id=job_id,
                status=status,
                stage=stage,
                progress_percent=progress_percent,
                title=title,
                error=error,
                partial_outputs=partial_outputs,
                partial_artifacts=partial_artifacts,
                warnings_append=warnings_append,
            )
        else:
            return self._update_job_simple(
                job_id=job_id,
                status=status,
                stage=stage,
                progress_percent=progress_percent,
                title=title,
                error=error,
                config_json=config_json,
                artifacts=artifacts,
                warnings=warnings,
                interpretations=interpretations,
                selected_interpretations=selected_interpretations,
            )

    def _update_job_atomic(
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
    ) -> Optional[JobRecord]:
        """Update job using atomic RPC function for JSONB merges."""
        try:
            client = _get_supabase_client()

            # Prepare RPC parameters
            # Note: Pass dicts directly - Supabase client handles dict→JSONB conversion
            # Do NOT use json.dumps() as it causes double-encoding
            rpc_params = {
                "p_job_id": job_id,
                "p_status": status,
                "p_stage": stage,
                "p_progress_percent": progress_percent,
                "p_title": title,
                "p_error": error,
                "p_partial_outputs": partial_outputs,
                "p_partial_artifacts": partial_artifacts,
                "p_warnings_append": warnings_append,
                "p_update_stage_timestamp": stage is not None,
            }

            logger.debug(f"Calling atomic_update_job RPC for job {job_id}")
            result = client.rpc("atomic_update_job", rpc_params).execute()

            if not result.data:
                logger.warning(f"Job {job_id} not found for atomic update")
                return None

            # RPC returns a single row, not a list
            row = result.data if isinstance(result.data, dict) else result.data[0]
            return _record_from_db_row(row)

        except Exception as e:
            # Log the error and fall back to non-atomic update
            logger.warning(
                f"Atomic update failed for job {job_id}, falling back to non-atomic: {sanitize_error_message(e)}"
            )
            return self._update_job_fallback(
                job_id=job_id,
                status=status,
                stage=stage,
                progress_percent=progress_percent,
                title=title,
                error=error,
                partial_outputs=partial_outputs,
                partial_artifacts=partial_artifacts,
                warnings_append=warnings_append,
            )

    def _update_job_fallback(
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
    ) -> Optional[JobRecord]:
        """
        Fallback update method using READ-MERGE-WRITE pattern.

        WARNING: This method has race conditions. Use only as fallback when
        atomic RPC is unavailable (e.g., migration not applied).
        """
        # Build payload for simple fields
        payload: dict[str, Any] = {}

        if status is not None:
            payload["status"] = status
        if progress_percent is not None:
            payload["progress_percent"] = progress_percent
        if title is not None:
            payload["title"] = title
        if error is not None:
            payload["error"] = error
        if stage is not None:
            payload["stage"] = stage
            payload["stage_started_at"] = datetime.now(timezone.utc).isoformat()

        # For merge operations, fetch current state (race condition here)
        if partial_outputs or partial_artifacts or warnings_append:
            current_job = self.get_job(job_id)
            if not current_job:
                logger.warning(f"Job {job_id} not found for update")
                return None

            if warnings_append:
                new_warnings = (current_job.warnings or []) + warnings_append
                payload["warnings"] = new_warnings

            if partial_outputs:
                outputs_dict = current_job.outputs.model_dump(exclude_none=True)
                payload["outputs"] = safe_merge(outputs_dict, partial_outputs)

            if partial_artifacts:
                artifacts_dict = current_job.artifacts.model_dump(exclude_none=True)
                payload["artifacts"] = safe_merge(artifacts_dict, partial_artifacts)

        if not payload:
            return self.get_job(job_id)

        return self._patch_job(job_id, payload)

    def _update_job_simple(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress_percent: Optional[int] = None,
        title: Optional[str] = None,
        error: Optional[str] = None,
        config_json: Optional[dict] = None,
        artifacts: Optional[Artifacts] = None,
        warnings: Optional[list[str]] = None,
        interpretations: Optional[list[dict]] = None,
        selected_interpretations: Optional[list[int]] = None,
    ) -> Optional[JobRecord]:
        """Update job with simple field replacements (no merge needed)."""
        payload: dict[str, Any] = {}

        if status is not None:
            payload["status"] = status
        if progress_percent is not None:
            payload["progress_percent"] = progress_percent
        if title is not None:
            payload["title"] = title
        if error is not None:
            payload["error"] = error
        if stage is not None:
            payload["stage"] = stage
            payload["stage_started_at"] = datetime.now(timezone.utc).isoformat()
        if artifacts is not None:
            payload["artifacts"] = artifacts.model_dump(exclude_none=True)
        if warnings is not None:
            payload["warnings"] = warnings
        if config_json is not None:
            payload["config_json"] = config_json
        if interpretations is not None:
            payload["interpretations"] = interpretations
        if selected_interpretations is not None:
            payload["selected_interpretations"] = selected_interpretations

        if not payload:
            return self.get_job(job_id)

        return self._patch_job(job_id, payload)

    def _patch_job(self, job_id: str, payload: dict[str, Any]) -> Optional[JobRecord]:
        """Execute PATCH request to update job."""
        url = _rest_base_url() + "/jobs"
        headers = _headers()
        headers["Prefer"] = "return=representation"
        params = {"id": f"eq.{job_id}"}

        logger.debug(f"Updating job {job_id} in Supabase with keys: {list(payload.keys())}")

        client = self._get_http_client()
        resp = client.patch(url, headers=headers, params=params, json=payload)

        if resp.status_code == 404:
            logger.warning(f"Job {job_id} not found for update")
            return None

        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = resp.text
            except Exception:
                pass
            logger.error(
                "Failed to update job %s: %s | Response: %s | Payload keys: %s",
                job_id,
                sanitize_error_message(e),
                error_body[:500] if error_body else "N/A",
                list(payload.keys()),
            )

            # If it's a 400 error and we sent stage_started_at, retry without it
            if resp.status_code == 400 and "stage_started_at" in payload:
                logger.warning("Retrying update without stage_started_at (column may not exist)")
                retry_payload = {k: v for k, v in payload.items() if k != "stage_started_at"}
                if retry_payload:
                    retry_resp = client.patch(url, headers=headers, params=params, json=retry_payload)
                    if retry_resp.status_code < 400:
                        data = retry_resp.json()
                        if isinstance(data, list):
                            if not data:
                                return None
                            data = data[0]
                        return _record_from_db_row(data)
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to update job %s: %s", job_id, sanitize_error_message(e))
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
        status: Optional[str] = None,
        pipeline: Optional[str] = None,
    ) -> list[JobRecord]:
        """List jobs with optional filtering.

        Args:
            user_id: Filter by user ID (UUID)
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            status: Filter by job status (queued, running, completed, failed, cancelled)
            pipeline: Filter by pipeline type

        Returns:
            List of JobRecord objects

        Raises:
            ValidationError: If user_id is provided but not a valid UUID
        """
        url = _rest_base_url() + "/jobs"
        headers = _headers()

        params: dict[str, Any] = {
            "order": "created_at.desc",
            "limit": limit,
            "offset": offset,
        }

        # Validate and add user_id filter
        if user_id is not None:
            try:
                user_id = validate_uuid(user_id, "user_id")
                params["user_id"] = f"eq.{user_id}"
            except ValidationError as e:
                logger.warning(f"Invalid user_id format in list_jobs: {e}")
                raise

        # Add status filter
        if status is not None:
            valid_statuses = {"queued", "running", "completed", "failed", "cancelled"}
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
            params["status"] = f"eq.{status}"

        # Add pipeline filter
        if pipeline is not None:
            valid_pipelines = {"quick", "full", "breaking_news", "investigation", "profile", "controversy"}
            if pipeline not in valid_pipelines:
                raise ValueError(f"Invalid pipeline: {pipeline}. Must be one of {valid_pipelines}")
            params["pipeline"] = f"eq.{pipeline}"

        logger.debug(f"Listing jobs with params: {params}")

        client = self._get_http_client()
        resp = client.get(url, headers=headers, params=params)

        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error("Failed to list jobs from Supabase: %s", sanitize_error_message(e))
            raise

        data = resp.json()
        if not isinstance(data, list):
            logger.warning(f"Expected list from Supabase, got: {type(data)}")
            return []

        jobs = [_record_from_db_row(row) for row in data]
        logger.debug(f"Listed {len(jobs)} jobs from Supabase")
        return jobs

    def close(self) -> None:
        """Close HTTP client connection."""
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()
            self._http_client = None

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        self.close()
