"""Configuration and secrets loading for CLI scripts and services."""

from __future__ import annotations

import pathlib
import tomllib
from typing import Any

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT_DIR / ".streamlit" / "secrets.toml"


def load_secrets() -> dict[str, Any]:
    """Load secrets from .streamlit/secrets.toml for CLI scripts."""
    if not SECRETS_PATH.exists():
        return {}
    with open(SECRETS_PATH, "rb") as file:
        return tomllib.load(file)


def get_secret(key: str, default: str = "") -> str:
    """Return a single secret value by key."""
    value = load_secrets().get(key, default)
    return str(value).strip() if value is not None else default


def secrets_configured() -> bool:
    """True if the secrets file exists and has at least one non-empty value."""
    secrets = load_secrets()
    return any(str(v).strip() for v in secrets.values())
