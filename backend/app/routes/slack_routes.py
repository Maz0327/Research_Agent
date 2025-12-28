"""API routes module."""
import urllib.parse
from fastapi import APIRouter, HTTPException, Header, Request
from loguru import logger

from backend.config import require_slack
from backend.integrations.slack import verify_slack_signature
from backend.state import create_job
from backend.worker import run_research_job

router = APIRouter()


@router.post("/slack/command")
async def slack_command(
    request: Request,
    x_slack_request_timestamp: str = Header(..., alias="X-Slack-Request-Timestamp"),
    x_slack_signature: str = Header(..., alias="X-Slack-Signature"),
):
    """
    Handle Slack slash command.
    
    Verifies signature and creates a research job from the command text.
    
    Note: We need to read the raw body first for signature verification,
    then parse form data manually.
    """
    settings = require_slack()
    
    # Get raw request body for signature verification
    body_bytes = await request.body()
    body = body_bytes.decode("utf-8")
    
    # Verify signature
    try:
        if not verify_slack_signature(
            signing_secret=settings.slack_signing_secret,
            timestamp=x_slack_request_timestamp,
            body=body,
            signature=x_slack_signature,
        ):
            logger.warning("Invalid Slack signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    except ValueError as e:
        logger.warning(f"Signature verification error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    # Parse form data from body
    form_data = {}
    for pair in body.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            # URL decode
            form_data[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
    
    # Extract required fields
    text = form_data.get("text", "").strip()
    user_id = form_data.get("user_id", "")
    user_name = form_data.get("user_name", "")
    channel_id = form_data.get("channel_id", "")
    channel_name = form_data.get("channel_name", "")
    response_url = form_data.get("response_url", "")
    team_id = form_data.get("team_id", "")
    
    # Validate topic
    if not text:
        return {
            "response_type": "ephemeral",
            "text": "❌ Please provide a research topic. Usage: /research <topic>",
        }
    
    # Create job with config_json
    try:
        config_json = {"topic": text}
        job = create_job(config_json=config_json)
    except Exception as e:
        logger.exception(f"Failed to create job: {e}")
        return {
            "response_type": "ephemeral",
            "text": f"❌ Failed to create research job: {str(e)}",
        }
    
    # Enqueue Celery task with Slack payload
    slack_payload = {
        "user_id": user_id,
        "user_name": user_name,
        "channel_id": channel_id,
        "channel_name": channel_name,
        "response_url": response_url,
        "team_id": team_id,
    }
    
    logger.info(
        f"Enqueuing research job {job.job_id} from Slack user {user_id} "
        f"for topic: {text}"
    )
    
    run_research_job.delay(job.job_id, text, slack_payload=slack_payload)
    
    # Return immediate response (must be within 3 seconds)
    return {
        "response_type": "ephemeral",
        "text": f"✅ Started research job: `{job.job_id}`\nTopic: {text}",
    }
