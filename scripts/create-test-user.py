#!/usr/bin/env python3
"""
Create a test user in Supabase Auth for production testing.

Usage:
    python scripts/create-test-user.py

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env
"""
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
import httpx

# Load .env from project root
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Test user credentials
TEST_EMAIL = "test@research-agent.dev"
TEST_PASSWORD = "TestUser2026!"


def create_test_user():
    """Create a test user using Supabase Admin API."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
        sys.exit(1)

    # Supabase Admin API endpoint
    url = f"{SUPABASE_URL}/auth/v1/admin/users"

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,  # Auto-confirm email
        "user_metadata": {
            "name": "Test User",
            "role": "tester",
        },
    }

    print(f"Creating test user: {TEST_EMAIL}")
    print(f"Supabase URL: {SUPABASE_URL}")

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30)

        if response.status_code == 200:
            user = response.json()
            print("\n✅ Test user created successfully!")
            print(f"   User ID: {user.get('id')}")
            print(f"   Email: {user.get('email')}")
            print(f"   Confirmed: {user.get('email_confirmed_at') is not None}")
            print("\n📝 Login credentials:")
            print(f"   Email: {TEST_EMAIL}")
            print(f"   Password: {TEST_PASSWORD}")
            return user
        elif response.status_code == 422:
            error = response.json()
            if "already been registered" in str(error):
                print(f"\n⚠️  User {TEST_EMAIL} already exists.")
                print("\n📝 Existing login credentials:")
                print(f"   Email: {TEST_EMAIL}")
                print(f"   Password: {TEST_PASSWORD}")
                return None
            else:
                print(f"ERROR: {error}")
                sys.exit(1)
        else:
            print(f"ERROR: {response.status_code} - {response.text}")
            sys.exit(1)

    except httpx.RequestError as e:
        print(f"ERROR: Request failed - {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_test_user()
