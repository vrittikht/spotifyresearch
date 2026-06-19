"""Shared CLI logging helpers."""

from __future__ import annotations

from datetime import datetime


def log_info(message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {message}")


def log_error(message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] ERROR: {message}", file=__import__("sys").stderr)
