#!/usr/bin/env python3
"""Test script for Slack command endpoint."""
import hashlib
import hmac
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Get signing secret from environment
SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "your-slack-signing-secret")
API_URL = os.getenv("API_URL", "http://localhost:8000/slack/command")


def generate_slack_signature(signing_secret: str, timestamp: str, body: str) -> str:
    """Generate Slack v0 signature."""
    sig_basestring = f"v0:{timestamp}:{body}"
    signature = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def test_slack_command(topic: str = "test research topic"):
    """Send a test Slack command request."""
    import urllib.parse
    
    timestamp = str(int(time.time()))
    
    # Build form data (simulating Slack's form-encoded payload)
    form_data = {
        "token": "test-token",
        "team_id": "T123456",
        "team_domain": "test-workspace",
        "channel_id": "C123456",
        "channel_name": "general",
        "user_id": "U123456",
        "user_name": "testuser",
        "command": "/research",
        "text": topic,
        "response_url": "https://hooks.slack.com/commands/T123456/123456/abcdef",
        "trigger_id": "123456.789.abcdef",
    }
    
    # Create body string (Slack sends as form-encoded, URL-encoded)
    body_parts = [f"{k}={urllib.parse.quote(v, safe='')}" for k, v in form_data.items()]
    body = "&".join(body_parts)
    
    # Generate signature
    signature = generate_slack_signature(SIGNING_SECRET, timestamp, body)
    
    # Prepare headers
    headers = {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    print(f"Testing Slack command endpoint: {API_URL}")
    print(f"Topic: {topic}")
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {signature[:20]}...")
    print()
    
    # Send request
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                API_URL,
                headers=headers,
                content=body,
            )
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
            
            if resp.status_code == 200:
                print("\n✅ Success! Job should be queued.")
            else:
                print(f"\n❌ Error: {resp.status_code}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "test research topic"
    test_slack_command(topic)

