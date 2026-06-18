"""Connection tests for external services (Phase 0 smoke checks)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from collectors.reddit_collector import DEFAULT_USER_AGENT, test_public_access
from services.groq_config import DEFAULT_GROQ_MODEL, GROQ_BASE_URL


@dataclass
class ConnectionResult:
    name: str
    ok: bool
    message: str


def _configured(value: str) -> bool:
    return bool(value and value.strip() and not value.startswith("your-"))


def test_supabase(url: str, key: str) -> ConnectionResult:
    if not _configured(url) or not _configured(key):
        return ConnectionResult(
            "Supabase",
            False,
            "Not configured — set SUPABASE_URL and SUPABASE_SERVICE_KEY in .streamlit/secrets.toml",
        )
    try:
        from supabase import create_client

        client = create_client(url, key)
        client.table("reviews").select("id", count="exact").limit(1).execute()
        return ConnectionResult("Supabase", True, "Connected successfully")
    except Exception as exc:
        error = str(exc)
        if "reviews" in error.lower() or "relation" in error.lower() or "42P01" in error:
            return ConnectionResult(
                "Supabase",
                True,
                "Connected — database reachable (run Phase 1 migration to create tables)",
            )
        return ConnectionResult("Supabase", False, f"Connection failed: {error}")


def test_groq(api_key: str, model: str = DEFAULT_GROQ_MODEL) -> ConnectionResult:
    if not _configured(api_key):
        return ConnectionResult(
            "Groq",
            False,
            "Not configured — set GROQ_API_KEY in .streamlit/secrets.toml",
        )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        response = client.chat.completions.create(
            model=model or DEFAULT_GROQ_MODEL,
            messages=[{"role": "user", "content": "Reply with exactly: ok"}],
            max_tokens=16,
            temperature=0,
        )
        text = (response.choices[0].message.content or "").strip().lower()
        if "ok" in text:
            return ConnectionResult("Groq", True, "API key valid — test call succeeded")
        return ConnectionResult("Groq", True, f"API reachable (response: {text[:50]})")
    except Exception as exc:
        return ConnectionResult("Groq", False, f"Connection failed: {exc}")


def test_reddit_public(user_agent: str = DEFAULT_USER_AGENT) -> ConnectionResult:
    ok, message = test_public_access(user_agent=user_agent or DEFAULT_USER_AGENT)
    # ok=True means workflow is understood (robots policy or HTML files found)
    return ConnectionResult("Reddit (public pages)", ok, message)


def run_all_tests(
    supabase_url: str,
    supabase_key: str,
    groq_api_key: str,
    reddit_user_agent: str = DEFAULT_USER_AGENT,
    groq_model: str = DEFAULT_GROQ_MODEL,
) -> list[ConnectionResult]:
    """Run connection tests for all external services."""
    tests: list[Callable[[], ConnectionResult]] = [
        lambda: test_supabase(supabase_url, supabase_key),
        lambda: test_groq(groq_api_key, groq_model),
        lambda: test_reddit_public(reddit_user_agent),
    ]
    return [test() for test in tests]
