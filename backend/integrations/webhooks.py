"""Webhook client for sending job events to external systems.

Provides HMAC-signed webhook delivery for automation integrations
like Zapier, Make.com, n8n, or custom endpoints.
"""
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx
from loguru import logger


class WebhookEvent(str, Enum):
    """Webhook event types."""
    JOB_STARTED = "job.started"
    STAGE_COMPLETED = "stage.completed"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"


# Default timeout for webhook requests
WEBHOOK_TIMEOUT = 10.0

# Maximum retries for failed webhooks
MAX_RETRIES = 1


class WebhookClient:
    """Client for sending webhooks to external endpoints."""

    def __init__(self, timeout: float = WEBHOOK_TIMEOUT, max_retries: int = MAX_RETRIES):
        self.timeout = timeout
        self.max_retries = max_retries

    async def fire(
        self,
        webhook_url: str,
        event_type: WebhookEvent,
        payload: dict,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Send webhook to external endpoint.

        Args:
            webhook_url: Target webhook URL
            event_type: Type of event being sent
            payload: Event payload data
            secret: Optional secret for HMAC signature

        Returns:
            True if webhook delivered successfully, False otherwise
        """
        if not webhook_url:
            logger.warning("No webhook URL provided, skipping")
            return False

        # Build webhook payload
        webhook_payload = {
            "event": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload,
        }

        # Serialize payload
        body = json.dumps(webhook_payload, default=str)

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ResearchAgent/1.0",
            "X-Webhook-Event": event_type.value,
        }

        # Add HMAC signature if secret provided
        if secret:
            signature = self._generate_signature(body, secret)
            headers["X-Webhook-Signature"] = signature
            headers["X-Webhook-Signature-256"] = f"sha256={signature}"

        # Send with retry
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook_url,
                        content=body,
                        headers=headers,
                    )

                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook delivered: {event_type.value} -> {webhook_url}")
                    return True

                logger.warning(
                    f"Webhook returned {response.status_code}: {webhook_url}"
                )

            except httpx.TimeoutException:
                logger.warning(f"Webhook timeout: {webhook_url} (attempt {attempt + 1})")
            except httpx.RequestError as e:
                logger.error(f"Webhook request failed: {e} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Webhook unexpected error: {e}")
                break  # Don't retry on unexpected errors

        logger.error(f"Webhook delivery failed after {self.max_retries + 1} attempts: {webhook_url}")
        return False

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def fire_job_started(
        self,
        webhook_url: str,
        job_id: str,
        topic: str,
        mode: str,
        secret: Optional[str] = None,
    ) -> bool:
        """Fire job.started event."""
        return await self.fire(
            webhook_url=webhook_url,
            event_type=WebhookEvent.JOB_STARTED,
            payload={
                "job_id": job_id,
                "topic": topic,
                "mode": mode,
            },
            secret=secret,
        )

    async def fire_stage_completed(
        self,
        webhook_url: str,
        job_id: str,
        stage_name: str,
        stage_data: Optional[dict] = None,
        secret: Optional[str] = None,
    ) -> bool:
        """Fire stage.completed event."""
        return await self.fire(
            webhook_url=webhook_url,
            event_type=WebhookEvent.STAGE_COMPLETED,
            payload={
                "job_id": job_id,
                "stage": stage_name,
                "preview": self._create_stage_preview(stage_data) if stage_data else None,
            },
            secret=secret,
        )

    async def fire_job_completed(
        self,
        webhook_url: str,
        job_id: str,
        topic: str,
        drive_folder_url: Optional[str] = None,
        artifacts: Optional[dict] = None,
        secret: Optional[str] = None,
    ) -> bool:
        """Fire job.completed event."""
        return await self.fire(
            webhook_url=webhook_url,
            event_type=WebhookEvent.JOB_COMPLETED,
            payload={
                "job_id": job_id,
                "topic": topic,
                "drive_folder_url": drive_folder_url,
                "artifacts": artifacts or {},
            },
            secret=secret,
        )

    async def fire_job_failed(
        self,
        webhook_url: str,
        job_id: str,
        error_message: str,
        stage: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> bool:
        """Fire job.failed event."""
        return await self.fire(
            webhook_url=webhook_url,
            event_type=WebhookEvent.JOB_FAILED,
            payload={
                "job_id": job_id,
                "error": error_message,
                "failed_stage": stage,
            },
            secret=secret,
        )

    async def fire_job_cancelled(
        self,
        webhook_url: str,
        job_id: str,
        cancelled_by: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> bool:
        """Fire job.cancelled event."""
        return await self.fire(
            webhook_url=webhook_url,
            event_type=WebhookEvent.JOB_CANCELLED,
            payload={
                "job_id": job_id,
                "cancelled_by": cancelled_by,
            },
            secret=secret,
        )

    def _create_stage_preview(self, stage_data: dict) -> dict:
        """Create preview of stage data for webhook."""
        preview = {}

        # Limit data to prevent huge payloads
        for key, value in stage_data.items():
            if isinstance(value, list):
                preview[key] = {
                    "count": len(value),
                    "sample": value[:3] if len(value) > 3 else value,
                }
            elif isinstance(value, dict):
                preview[key] = {
                    "keys": list(value.keys())[:5],
                }
            elif isinstance(value, str) and len(value) > 500:
                preview[key] = value[:500] + "..."
            else:
                preview[key] = value

        return preview


# Singleton instance
_webhook_client: Optional[WebhookClient] = None


def get_webhook_client() -> WebhookClient:
    """Get or create webhook client singleton."""
    global _webhook_client
    if _webhook_client is None:
        _webhook_client = WebhookClient()
    return _webhook_client
