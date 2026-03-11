#!/usr/bin/env python3
"""
API Balance Checker — checks balances/usage for all configured providers.

Usage:
    python -m backend.scripts.check_api_balances              # check all
    python -m backend.scripts.check_api_balances --json        # JSON output
    python -m backend.scripts.check_api_balances -p kimi       # single provider
    python -m backend.scripts.check_api_balances -p openai tavily  # multiple

Providers:
    ✅ kimi        — direct balance (Moonshot /v1/users/me/balance)
    ✅ supadata     — credits via /v1/me
    ✅ openai       — cost data via admin key, or key validation fallback
    ✅ tavily       — usage/credits via /usage
    ✅ anthropic    — key validation (admin key for usage data)
    ✅ perplexity   — key validation via /chat/completions
    ✅ serper       — key validation via /search
    ✅ brave        — key validation via /web/search
    ✅ exa          — key validation via /search
    ✅ jina         — key validation via reader
    ✅ assemblyai   — key validation via /v2/transcript
    ✅ claimbuster  — key validation via /score/text
    ✅ google       — key validation via /models
    ✅ youtube      — key validation + quota check
    ✅ supabase     — project list via management API
    ✅ railway      — account validation via GraphQL
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Load .env if running standalone
# ---------------------------------------------------------------------------
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        # Override empty-string env vars (e.g. shell exports ANTHROPIC_API_KEY="")
        if value and (not os.environ.get(key)):
            os.environ[key] = value


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------
class Status:
    OK = "✅ OK"
    LOW = "⚠️  LOW"
    EMPTY = "❌ EMPTY"
    ERROR = "🔴 ERROR"
    SKIP = "⏭️  SKIP"
    UNKNOWN = "❓ UNKNOWN"


def _result(provider: str, status: str, balance=None, details=None, error=None):
    return {
        "provider": provider,
        "status": status,
        "balance": balance,
        "details": details or {},
        "error": error,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _check_401(resp, provider):
    """Common 401 check."""
    if resp.status_code == 401:
        return _result(provider, Status.ERROR, error="Invalid API key (401)")
    return None


# ===========================================================================
#  TIER 1 — Direct balance/usage endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# Kimi / Moonshot — direct balance
# ---------------------------------------------------------------------------
def check_kimi() -> dict:
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        return _result("Moonshot/Kimi", Status.SKIP, details={"reason": "KIMI_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://api.moonshot.ai/v1/users/me/balance",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r := _check_401(resp, "Moonshot/Kimi"):
            return r
        resp.raise_for_status()
        data = resp.json()

        balance_data = data.get("data", data)
        available = balance_data.get("available_balance", balance_data.get("balance"))

        if available is not None:
            available = float(available)
            status = Status.OK if available > 2.0 else (Status.LOW if available > 0 else Status.EMPTY)
            return _result("Moonshot/Kimi", status, balance=f"¥{available:.2f}", details=balance_data)
        return _result("Moonshot/Kimi", Status.UNKNOWN, details=data)

    except Exception as e:
        return _result("Moonshot/Kimi", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Supadata — credits
# ---------------------------------------------------------------------------
def check_supadata() -> dict:
    api_key = os.getenv("SUPADATA_API_KEY")
    if not api_key:
        return _result("Supadata", Status.SKIP, details={"reason": "SUPADATA_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://api.supadata.ai/v1/me",
            headers={"x-api-key": api_key},
            timeout=10,
        )
        if r := _check_401(resp, "Supadata"):
            return r
        resp.raise_for_status()
        data = resp.json()

        max_credits = data.get("maxCredits", 0)
        used_credits = data.get("usedCredits", 0)
        remaining = max_credits - used_credits
        plan = data.get("plan", "unknown")

        if max_credits > 0:
            status = Status.OK if remaining > 100 else (Status.LOW if remaining > 0 else Status.EMPTY)
            return _result("Supadata", status, balance=f"{remaining}/{max_credits} credits",
                           details={"plan": plan, "max": max_credits, "used": used_credits, "remaining": remaining})
        return _result("Supadata", Status.UNKNOWN, details=data)

    except Exception as e:
        return _result("Supadata", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# OpenAI — admin key for costs, regular key for validation
# ---------------------------------------------------------------------------
def check_openai() -> dict:
    admin_key = os.getenv("OPENAI_ADMIN_KEY")
    if not admin_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return _result("OpenAI", Status.SKIP, details={"reason": "OPENAI_API_KEY not set"})

        try:
            resp = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if r := _check_401(resp, "OpenAI"):
                return r
            if resp.status_code == 429:
                error_data = resp.json().get("error", {})
                if "insufficient_quota" in error_data.get("code", ""):
                    return _result("OpenAI", Status.EMPTY, error="insufficient_quota — $0 balance",
                                   details={"dashboard": "https://platform.openai.com/usage"})
                return _result("OpenAI", Status.LOW, error="Rate limited (429)",
                               details={"dashboard": "https://platform.openai.com/usage"})
            resp.raise_for_status()
            return _result("OpenAI", Status.UNKNOWN,
                           details={"note": "Key valid but no OPENAI_ADMIN_KEY set for cost data",
                                    "dashboard": "https://platform.openai.com/usage"})
        except Exception as e:
            return _result("OpenAI", Status.ERROR, error=str(e))

    try:
        now = int(datetime.now(timezone.utc).timestamp())
        start_of_month = int(datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0).timestamp())
        resp = httpx.get(
            "https://api.openai.com/v1/organization/costs",
            headers={"Authorization": f"Bearer {admin_key}"},
            params={"start_time": start_of_month, "end_time": now, "bucket_width": "1d"},
            timeout=15,
        )
        if r := _check_401(resp, "OpenAI"):
            return r
        resp.raise_for_status()
        data = resp.json()

        total_cost = sum(
            bucket.get("results", [{}])[0].get("amount", {}).get("value", 0)
            for bucket in data.get("data", [])
            if bucket.get("results")
        )
        return _result("OpenAI", Status.OK, balance=f"${total_cost:.2f} spent this month",
                        details={"monthly_spend": total_cost, "dashboard": "https://platform.openai.com/usage"})

    except Exception as e:
        return _result("OpenAI", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Tavily — direct usage/credits endpoint
# ---------------------------------------------------------------------------
def check_tavily() -> dict:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return _result("Tavily", Status.SKIP, details={"reason": "TAVILY_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://api.tavily.com/usage",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r := _check_401(resp, "Tavily"):
            return r
        resp.raise_for_status()
        data = resp.json()

        plan_usage = data.get("plan_usage", data.get("usage", 0))
        plan_limit = data.get("plan_limit", data.get("limit"))
        current_plan = data.get("current_plan", "unknown")

        if plan_limit and plan_limit > 0:
            remaining = plan_limit - plan_usage
            status = Status.OK if remaining > 50 else (Status.LOW if remaining > 0 else Status.EMPTY)
            return _result("Tavily", status, balance=f"{remaining}/{plan_limit} credits",
                           details={"plan": current_plan, "used": plan_usage, "limit": plan_limit,
                                    "dashboard": "https://app.tavily.com/home"})
        return _result("Tavily", Status.OK, balance=f"{plan_usage} used",
                        details={"plan": current_plan, "used": plan_usage,
                                 "dashboard": "https://app.tavily.com/home"})

    except Exception as e:
        return _result("Tavily", Status.ERROR, error=str(e))


# ===========================================================================
#  TIER 2 — Key validation only (no balance endpoint)
# ===========================================================================

# ---------------------------------------------------------------------------
# Anthropic — key validation (usage requires admin key)
# ---------------------------------------------------------------------------
def check_anthropic() -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _result("Anthropic", Status.SKIP, details={"reason": "ANTHROPIC_API_KEY not set"})

    try:
        # Use a minimal message request to validate the key
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 1,
                  "messages": [{"role": "user", "content": "ping"}]},
            timeout=15,
        )
        if resp.status_code == 401:
            return _result("Anthropic", Status.ERROR, error="Invalid API key (401)")
        if resp.status_code == 400:
            # 400 can mean invalid model — key might still be valid. Try to detect
            error_msg = resp.json().get("error", {}).get("message", "")
            if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                return _result("Anthropic", Status.ERROR, error=f"Bad request: {error_msg}")
            # Assume key is valid but model/request was wrong
            return _result("Anthropic", Status.OK,
                           details={"note": "Key accepted. Check billing manually.",
                                    "dashboard": "https://console.anthropic.com/settings/billing"})
        if resp.status_code == 429:
            error_data = resp.json().get("error", {})
            msg = error_data.get("message", "")
            if "credit" in msg.lower() or "balance" in msg.lower():
                return _result("Anthropic", Status.EMPTY, error="No credits remaining",
                               details={"dashboard": "https://console.anthropic.com/settings/billing"})
            return _result("Anthropic", Status.OK,
                           details={"note": "Key valid (rate limited). Check billing manually.",
                                    "dashboard": "https://console.anthropic.com/settings/billing"})
        if resp.status_code in (200, 201):
            return _result("Anthropic", Status.OK,
                           details={"note": "Key valid. Check billing manually.",
                                    "dashboard": "https://console.anthropic.com/settings/billing"})
        resp.raise_for_status()
        return _result("Anthropic", Status.UNKNOWN, details={"status_code": resp.status_code})

    except Exception as e:
        return _result("Anthropic", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Perplexity — key validation via minimal completion
# ---------------------------------------------------------------------------
def check_perplexity() -> dict:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return _result("Perplexity", Status.SKIP, details={"reason": "PERPLEXITY_API_KEY not set"})

    try:
        resp = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "sonar", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
            timeout=15,
        )
        if resp.status_code == 401:
            return _result("Perplexity", Status.ERROR, error="Invalid API key (401)")
        if resp.status_code == 429:
            return _result("Perplexity", Status.LOW, error="Rate limited (429)",
                           details={"dashboard": "https://www.perplexity.ai/settings/api"})
        if resp.status_code == 402:
            return _result("Perplexity", Status.EMPTY, error="Payment required — no credits",
                           details={"dashboard": "https://www.perplexity.ai/settings/api"})
        if resp.status_code in (200, 201):
            return _result("Perplexity", Status.OK,
                           details={"note": "Key valid. Check billing manually.",
                                    "dashboard": "https://www.perplexity.ai/settings/api"})
        resp.raise_for_status()
        return _result("Perplexity", Status.UNKNOWN, details={"status_code": resp.status_code})

    except Exception as e:
        return _result("Perplexity", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Google AI / Gemini — key validation
# ---------------------------------------------------------------------------
def check_google() -> dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _result("Google AI", Status.SKIP, details={"reason": "GOOGLE_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
            timeout=10,
        )
        if resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
            return _result("Google AI", Status.ERROR, error="Invalid API key")
        if resp.status_code == 429:
            error_data = resp.json().get("error", {})
            if "free_tier" in str(error_data).lower():
                return _result("Google AI", Status.EMPTY, error="Free tier quota exhausted",
                               details={"dashboard": "https://console.cloud.google.com/billing"})
            return _result("Google AI", Status.LOW, error="Rate limited (429)",
                           details={"dashboard": "https://console.cloud.google.com/billing"})
        resp.raise_for_status()
        model_count = len(resp.json().get("models", []))
        return _result("Google AI", Status.UNKNOWN,
                        details={"note": f"Key valid ({model_count} models). Check billing manually.",
                                 "dashboard": "https://console.cloud.google.com/billing"})
    except Exception as e:
        return _result("Google AI", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# YouTube Data API — key validation + quota check
# ---------------------------------------------------------------------------
def check_youtube() -> dict:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return _result("YouTube", Status.SKIP, details={"reason": "YOUTUBE_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"key": api_key, "part": "id", "chart": "mostPopular", "maxResults": 1},
            timeout=10,
        )
        if resp.status_code == 400 and "API_KEY_INVALID" in resp.text:
            return _result("YouTube", Status.ERROR, error="Invalid API key")
        if resp.status_code == 403:
            error_data = resp.json().get("error", {})
            errors = error_data.get("errors", [{}])
            reason = errors[0].get("reason", "") if errors else ""
            if reason == "quotaExceeded":
                return _result("YouTube", Status.EMPTY, error="Daily quota exhausted (10k units)",
                               details={"dashboard": "https://console.cloud.google.com/apis/dashboard"})
            return _result("YouTube", Status.ERROR, error=f"Forbidden: {reason}",
                           details={"dashboard": "https://console.cloud.google.com/apis/dashboard"})
        resp.raise_for_status()
        return _result("YouTube", Status.OK,
                        details={"note": "Key valid, quota available. 10k units/day.",
                                 "dashboard": "https://console.cloud.google.com/apis/dashboard"})
    except Exception as e:
        return _result("YouTube", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Serper.dev — key validation (consumes 1 credit per search)
# ---------------------------------------------------------------------------
def check_serper() -> dict:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return _result("Serper", Status.SKIP, details={"reason": "SERPER_API_KEY not set"})

    try:
        # Use a minimal search — costs 1 credit but validates key + checks quota
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": "test", "num": 1},
            timeout=10,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            return _result("Serper", Status.ERROR, error=f"Invalid API key ({resp.status_code})")
        if resp.status_code == 429:
            return _result("Serper", Status.EMPTY, error="Rate limited / quota exhausted",
                           details={"dashboard": "https://serper.dev/dashboard"})
        resp.raise_for_status()
        # Check remaining credits from response headers if available
        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining is not None:
            remaining = int(remaining)
            if remaining > 100:
                status = Status.OK
            elif remaining > 0:
                status = Status.LOW
            else:
                status = Status.EMPTY
            return _result("Serper", status, balance=f"{remaining} credits",
                           error=f"Only {remaining} credits left" if status == Status.LOW else None,
                           details={"dashboard": "https://serper.dev/dashboard"})
        return _result("Serper", Status.OK,
                        details={"note": "Key valid. Check credits on dashboard.",
                                 "dashboard": "https://serper.dev/dashboard"})

    except Exception as e:
        return _result("Serper", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Brave Search — key validation
# ---------------------------------------------------------------------------
def check_brave() -> dict:
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return _result("Brave Search", Status.SKIP, details={"reason": "BRAVE_SEARCH_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={"q": "test", "count": 1},
            timeout=10,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            return _result("Brave Search", Status.ERROR, error=f"Invalid API key ({resp.status_code})")
        if resp.status_code == 429:
            return _result("Brave Search", Status.EMPTY, error="Rate limited / quota exhausted",
                           details={"dashboard": "https://api.search.brave.com/app/dashboard"})
        resp.raise_for_status()
        # Check rate limit headers
        remaining = resp.headers.get("x-ratelimit-remaining")
        if remaining:
            return _result("Brave Search", Status.OK, balance=f"{remaining} req remaining",
                           details={"dashboard": "https://api.search.brave.com/app/dashboard"})
        return _result("Brave Search", Status.OK,
                        details={"note": "Key valid. Check usage on dashboard.",
                                 "dashboard": "https://api.search.brave.com/app/dashboard"})

    except Exception as e:
        return _result("Brave Search", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Exa.ai — key validation via search
# ---------------------------------------------------------------------------
def check_exa() -> dict:
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return _result("Exa", Status.SKIP, details={"reason": "EXA_API_KEY not set"})

    try:
        resp = httpx.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={"query": "test", "numResults": 1, "useAutoprompt": False},
            timeout=10,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            return _result("Exa", Status.ERROR, error=f"Invalid API key ({resp.status_code})")
        if resp.status_code == 402:
            return _result("Exa", Status.EMPTY, error="Payment required — no credits",
                           details={"dashboard": "https://dashboard.exa.ai"})
        if resp.status_code == 429:
            return _result("Exa", Status.LOW, error="Rate limited (429)",
                           details={"dashboard": "https://dashboard.exa.ai"})
        resp.raise_for_status()
        return _result("Exa", Status.OK,
                        details={"note": "Key valid. Check credits on dashboard.",
                                 "dashboard": "https://dashboard.exa.ai"})

    except Exception as e:
        return _result("Exa", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Jina AI — key validation via reader
# ---------------------------------------------------------------------------
def check_jina() -> dict:
    api_key = os.getenv("JINA_AI_READER_API_KEY")
    if not api_key:
        return _result("Jina AI", Status.SKIP, details={"reason": "JINA_AI_READER_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://r.jina.ai/https://example.com",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            return _result("Jina AI", Status.ERROR, error="Invalid API key (401)")
        if resp.status_code == 402:
            return _result("Jina AI", Status.EMPTY, error="No tokens remaining",
                           details={"dashboard": "https://jina.ai/reader"})
        if resp.status_code == 429:
            return _result("Jina AI", Status.LOW, error="Rate limited",
                           details={"dashboard": "https://jina.ai/reader"})
        if resp.status_code in (200, 201):
            # Check headers for token balance info
            remaining = resp.headers.get("x-tokens-remaining") or resp.headers.get("x-ratelimit-remaining")
            if remaining:
                return _result("Jina AI", Status.OK, balance=f"{remaining} tokens",
                               details={"dashboard": "https://jina.ai/reader"})
            return _result("Jina AI", Status.OK,
                           details={"note": "Key valid. Check token balance on dashboard.",
                                    "dashboard": "https://jina.ai/reader"})
        resp.raise_for_status()
        return _result("Jina AI", Status.UNKNOWN, details={"status_code": resp.status_code})

    except Exception as e:
        return _result("Jina AI", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# AssemblyAI — key validation
# ---------------------------------------------------------------------------
def check_assemblyai() -> dict:
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        return _result("AssemblyAI", Status.SKIP, details={"reason": "ASSEMBLYAI_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://api.assemblyai.com/v2/transcript",
            headers={"Authorization": api_key},
            params={"limit": 1},
            timeout=10,
        )
        if resp.status_code == 401:
            return _result("AssemblyAI", Status.ERROR, error="Invalid API key (401)")
        if resp.status_code == 402:
            return _result("AssemblyAI", Status.EMPTY, error="Payment required",
                           details={"dashboard": "https://www.assemblyai.com/dashboard/account/billing"})
        resp.raise_for_status()
        return _result("AssemblyAI", Status.OK,
                        details={"note": "Key valid. Check usage on dashboard.",
                                 "dashboard": "https://www.assemblyai.com/dashboard/account/billing"})

    except Exception as e:
        return _result("AssemblyAI", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# ClaimBuster — key validation
# ---------------------------------------------------------------------------
def check_claimbuster() -> dict:
    api_key = os.getenv("CLAIMBUSTER_API_KEY")
    if not api_key:
        return _result("ClaimBuster", Status.SKIP, details={"reason": "CLAIMBUSTER_API_KEY not set"})

    try:
        resp = httpx.get(
            "https://idir.uta.edu/claimbuster/api/v2/score/text/The earth is round",
            headers={"x-api-key": api_key},
            timeout=20,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            return _result("ClaimBuster", Status.ERROR, error=f"Invalid API key ({resp.status_code})")
        resp.raise_for_status()
        return _result("ClaimBuster", Status.OK,
                        details={"note": "Key valid (free academic API).",
                                 "dashboard": "https://idir.uta.edu/claimbuster/"})

    except Exception as e:
        return _result("ClaimBuster", Status.ERROR, error=str(e))


# ===========================================================================
#  TIER 3 — Infrastructure / DevOps
# ===========================================================================

# ---------------------------------------------------------------------------
# Supabase — management API (project list)
# ---------------------------------------------------------------------------
def check_supabase() -> dict:
    token = os.getenv("SUPABASE_ACCESS_TOKEN")
    if not token:
        return _result("Supabase", Status.SKIP, details={"reason": "SUPABASE_ACCESS_TOKEN not set"})

    try:
        resp = httpx.get(
            "https://api.supabase.com/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 401:
            return _result("Supabase", Status.ERROR, error="Invalid access token (401)")
        resp.raise_for_status()
        projects = resp.json()
        project_count = len(projects) if isinstance(projects, list) else 0
        return _result("Supabase", Status.OK, balance=f"{project_count} project(s)",
                        details={"note": f"Token valid. {project_count} project(s) accessible.",
                                 "dashboard": "https://supabase.com/dashboard"})

    except Exception as e:
        return _result("Supabase", Status.ERROR, error=str(e))


# ---------------------------------------------------------------------------
# Railway — GraphQL validation
# ---------------------------------------------------------------------------
def check_railway() -> dict:
    token = os.getenv("RAILWAY_TOKEN")
    if not token:
        return _result("Railway", Status.SKIP, details={"reason": "RAILWAY_TOKEN not set"})

    try:
        resp = httpx.post(
            "https://backboard.railway.com/graphql/v2",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": "{ me { name email } }"},
            timeout=10,
        )
        if resp.status_code == 401 or resp.status_code == 403:
            # Try as project token — different auth pattern
            resp2 = httpx.post(
                "https://backboard.railway.com/graphql/v2",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"query": "{ projects { edges { node { name } } } }"},
                timeout=10,
            )
            if resp2.status_code in (200, 201):
                data2 = resp2.json()
                if not (data2 or {}).get("errors"):
                    return _result("Railway", Status.OK,
                                   details={"note": "Project token valid.",
                                            "dashboard": "https://railway.app/account/billing"})
            return _result("Railway", Status.ERROR, error="Token expired/invalid. Regenerate at railway.app.",
                           details={"dashboard": "https://railway.app/account/tokens"})

        resp.raise_for_status()
        data = resp.json() or {}
        errors = data.get("errors")
        if errors:
            return _result("Railway", Status.ERROR, error=errors[0].get("message", str(errors)),
                           details={"dashboard": "https://railway.app/account/billing"})
        me = (data.get("data") or {}).get("me") or {}
        name = me.get("name") or me.get("email") or "authenticated"
        return _result("Railway", Status.OK,
                        details={"note": f"Token valid (user: {name}).",
                                 "dashboard": "https://railway.app/account/billing"})

    except Exception as e:
        return _result("Railway", Status.ERROR, error=str(e))


# ===========================================================================
# Aggregate
# ===========================================================================
ALL_CHECKS = {
    # Tier 1 — direct balance
    "openai": check_openai,
    "kimi": check_kimi,
    "supadata": check_supadata,
    "tavily": check_tavily,
    # Tier 2 — key validation
    "anthropic": check_anthropic,
    "perplexity": check_perplexity,
    "google": check_google,
    "youtube": check_youtube,
    "serper": check_serper,
    "brave": check_brave,
    "exa": check_exa,
    "jina": check_jina,
    "assemblyai": check_assemblyai,
    "claimbuster": check_claimbuster,
    # Tier 3 — infrastructure
    "supabase": check_supabase,
    "railway": check_railway,
}


def run_all(providers=None) -> list[dict]:
    results = []
    targets = {p: ALL_CHECKS[p] for p in (providers or ALL_CHECKS)}
    for name, check_fn in targets.items():
        results.append(check_fn())
    return results


def print_table(results: list[dict]):
    print()
    print("=" * 80)
    print(f"  API BALANCE CHECK — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print()
    for r in results:
        status = r["status"]
        provider = r["provider"]
        balance = r["balance"] or "—"
        error = r.get("error") or ""
        note = r.get("details", {}).get("note", "")

        print(f"  {status:<12} {provider:<18} {balance:<28}", end="")
        if error:
            print(f"  {error}")
        elif note:
            print(f"  {note}")
        else:
            print()

    print()
    print("-" * 80)

    # Summary
    issues = [r for r in results if r["status"] in (Status.LOW, Status.EMPTY, Status.ERROR)]
    skipped = [r for r in results if r["status"] == Status.SKIP]
    healthy = [r for r in results if r["status"] in (Status.OK, Status.UNKNOWN)]

    if issues:
        print(f"  ⚠️  {len(issues)} provider(s) need attention!")
        for r in issues:
            dashboard = r.get("details", {}).get("dashboard", "")
            print(f"     → {r['provider']}: {r.get('error', r['status'])}")
            if dashboard:
                print(f"       {dashboard}")
    else:
        print(f"  ✅ All {len(healthy)} active provider(s) healthy", end="")
        if skipped:
            print(f"  ({len(skipped)} skipped — no key set)")
        else:
            print()
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Check API balances for Research Agent")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--provider", "-p", choices=list(ALL_CHECKS.keys()), nargs="+",
                        help="Check specific provider(s)")
    args = parser.parse_args()

    results = run_all(args.provider)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_table(results)

    # Exit code: 1 if any provider is EMPTY or ERROR
    critical = [r for r in results if r["status"] in (Status.EMPTY, Status.ERROR)]
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
