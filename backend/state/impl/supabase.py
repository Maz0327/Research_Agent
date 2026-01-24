"""Supabase implementation of job persistence."""
from __future__ import annotations

from typing import Any, Optional

import httpx
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.config import require_supabase
from backend.models.job import JobStatus

# Retry configuration for connection resilience
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.NetworkError,
)

supabase_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)


def _rest_base_url() -> str:
    """
    Base URL for Supabase PostgREST.
    Example: https://xxxx.supabase.co/rest/v1
    """
    settings = require_supabase()
    # Cast to string (handles both str and AnyUrl types)
    base_url = str(settings.supabase_url)
    return base_url.rstrip("/") + "/rest/v1"


def _headers() -> dict[str, str]:
    """
    Headers required by Supabase REST.
    Uses the service role key, so ONLY for backend/server-side.
    """
    settings = require_supabase()
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def create_job(topic: str) -> JobStatus:
    """
    Insert a new job row into Supabase and return the created record.
    """
    url = _rest_base_url() + "/jobs"
    headers = _headers()
    # Ask Supabase to return the inserted row
    headers["Prefer"] = "return=representation"

    payload = {
        "topic": topic,
        "status": "queued",
    }

    logger.info(f"Creating job in Supabase for topic={topic!r}")

    @supabase_retry
    def _execute():
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp

    try:
        resp = _execute()
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(f"Failed to create job in Supabase after retries: {e}")
        raise
    except httpx.HTTPError as e:
        logger.error(f"Failed to create job in Supabase: {e} - body={resp.text!r}")
        raise

    data = resp.json()
    # Supabase returns a list when using "return=representation"
    if isinstance(data, list):
        if not data:
            raise RuntimeError("Supabase returned an empty list when creating a job.")
        data = data[0]

    job = JobStatus.model_validate(data)
    logger.info(f"Created job {job.job_id} in Supabase.")
    return job


def get_job(job_id: str) -> Optional[JobStatus]:
    """
    Fetch a single job by ID from Supabase.
    Returns None if not found.
    """
    url = _rest_base_url() + "/jobs"
    headers = _headers()
    params = {
        "id": f"eq.{job_id}",
        "limit": 1,
    }

    @supabase_retry
    def _execute():
        with httpx.Client(timeout=5.0) as client:
            return client.get(url, headers=headers, params=params)

    try:
        resp = _execute()
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(f"Failed to fetch job {job_id} after retries: {e}")
        raise

    if resp.status_code == 404:
        return None

    try:
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch job {job_id} from Supabase: {e} - body={resp.text!r}")
        raise

    data = resp.json()
    if not data:
        return None

    job = JobStatus.model_validate(data[0])
    return job


def update_job_status(job_id: str, status: str, result: Optional[dict[str, Any]] = None) -> None:
    """
    Update status/result for an existing job.
    """
    url = _rest_base_url() + "/jobs"
    headers = _headers()
    # We don't need the updated row back here
    headers["Prefer"] = "return=minimal"

    payload: dict[str, Any] = {"status": status}
    if result is not None:
        payload["result"] = result

    params = {
        "id": f"eq.{job_id}",
    }

    logger.info(f"Updating job {job_id} in Supabase to status={status!r}")

    @supabase_retry
    def _execute():
        with httpx.Client(timeout=5.0) as client:
            return client.patch(url, headers=headers, params=params, json=payload)

    try:
        resp = _execute()
    except RETRYABLE_EXCEPTIONS as e:
        logger.error(f"Failed to update job {job_id} after retries: {e}")
        raise

    if resp.status_code == 404:
        logger.warning(f"Job {job_id} not found for update")
        return
    
    if resp.status_code not in (200, 204):
        logger.error(
            f"Failed to update job {job_id} status to {status}: "
            f"{resp.status_code} - body={resp.text!r}"
        )
        resp.raise_for_status()

