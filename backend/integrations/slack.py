"""Slack integration for webhooks and signature verification."""
import hashlib
import hmac
import time
from typing import Optional

import httpx
from loguru import logger

from backend.config import require_slack

# Constants
SLACK_API_TIMEOUT = 5.0  # seconds for response_url
SLACK_API_LONG_TIMEOUT = 10.0  # seconds for chat.postMessage
SLACK_SIGNATURE_VERSION = "v0"
SLACK_TIMESTAMP_TOLERANCE = 60 * 5  # 5 minutes


def verify_slack_signature(
    signing_secret: str, timestamp: str, body: str, signature: str
) -> bool:
    """
    Verify Slack request signature using v0 HMAC.
    
    Args:
        signing_secret: Slack signing secret from environment
        timestamp: X-Slack-Request-Timestamp header value
        body: Raw request body as string
        signature: X-Slack-Signature header value (format: v0=<hex>)
        
    Returns:
        True if signature is valid, False otherwise
        
    Raises:
        ValueError: If timestamp is too old (>5 minutes)
    """
    # Check timestamp to prevent replay attacks
    current_time = int(time.time())
    request_time = int(timestamp)
    
    if abs(current_time - request_time) > SLACK_TIMESTAMP_TOLERANCE:
        logger.warning(f"Request timestamp too old: {request_time} (current: {current_time})")
        raise ValueError("Request timestamp is too old")
    
    # Create signature base string
    sig_basestring = f"{SLACK_SIGNATURE_VERSION}:{timestamp}:{body}"
    
    # Compute expected signature
    expected_signature = f"{SLACK_SIGNATURE_VERSION}=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    
    # Compare signatures using constant-time comparison
    return hmac.compare_digest(expected_signature, signature)


def post_slack_message(
    response_url: str,
    text: str,
    ephemeral: bool = False,
) -> bool:
    """
    Post a message to Slack using response_url.
    
    Args:
        response_url: Slack response URL from slash command
        text: Message text to post
        ephemeral: If True, message is only visible to the user
        
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "text": text,
        "response_type": "ephemeral" if ephemeral else "in_channel",
    }
    
    try:
        with httpx.Client(timeout=SLACK_API_TIMEOUT) as client:
            resp = client.post(response_url, json=payload)
            resp.raise_for_status()
            logger.info("Posted Slack message to response_url")
            return True
    except Exception as e:
        logger.error(f"Failed to post Slack message: {e}")
        return False


def post_slack_message_api(
    channel_id: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> bool:
    """
    Post a message to Slack using chat.postMessage API (requires bot token).
    
    Args:
        channel_id: Slack channel ID
        text: Message text to post
        thread_ts: Optional thread timestamp to reply in thread
        
    Returns:
        True if successful, False otherwise
    """
    settings = require_slack()
    
    if not settings.slack_bot_token:
        logger.error("SLACK_BOT_TOKEN not configured")
        return False
    
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {settings.slack_bot_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "channel": channel_id,
        "text": text,
    }
    
    if thread_ts:
        payload["thread_ts"] = thread_ts
    
    try:
        with httpx.Client(timeout=SLACK_API_LONG_TIMEOUT) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error')}")
                return False
            
            logger.info(f"Posted Slack message to channel {channel_id}")
            return True
    except Exception as e:
        logger.error(f"Failed to post Slack message via API: {e}")
        return False
