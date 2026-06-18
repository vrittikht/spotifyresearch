"""Map source-specific records to the unified review schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_reddit_post(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a scraped Reddit post into a review record."""
    post_id = str(raw.get("post_id") or raw.get("source_id") or "")
    subreddit = str(raw.get("subreddit") or "")
    url = str(raw.get("url") or "")
    title = (raw.get("title") or "").strip() or None
    body = (raw.get("body") or raw.get("selftext") or "").strip()
    if not body and title:
        body = title

    score = raw.get("score")
    published_at = raw.get("published_at")
    if isinstance(published_at, str):
        published_at = None

    return {
        "source": "reddit",
        "source_id": post_id,
        "title": title,
        "body": body,
        "rating": None,
        "metadata": {
            "subreddit": subreddit,
            "score": score,
            "url": url,
            "keyword": raw.get("keyword"),
            "permalink": raw.get("permalink"),
        },
        "published_at": published_at,
        "status": "pending",
    }


def normalize(raw: dict[str, Any], source: str) -> dict[str, Any]:
    if source == "reddit":
        return normalize_reddit_post(raw)
    raise ValueError(f"Unsupported source for normalize(): {source}")
