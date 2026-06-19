"""Map source-specific records to the unified review schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def normalize_reddit_post(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a scraped Reddit post into a review record."""
    post_id = str(raw.get("post_id") or raw.get("source_id") or "")
    subreddit = str(raw.get("subreddit") or "")
    url = str(raw.get("url") or raw.get("permalink") or "")
    title = (raw.get("title") or "").strip() or None
    body = (raw.get("body") or raw.get("selftext") or "").strip()
    if not body and title:
        body = title

    return {
        "source": "reddit",
        "source_id": post_id,
        "title": title,
        "body": body,
        "rating": None,
        "metadata": {
            "subreddit": subreddit,
            "score": raw.get("score"),
            "url": url,
            "keyword": raw.get("keyword"),
            "permalink": raw.get("permalink") or url,
        },
        "published_at": _parse_datetime(raw.get("published_at")),
        "status": "pending",
    }


def normalize_play_store_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Play Store CSV row into a review record."""
    source_id = str(raw.get("source_id") or "")
    body = (raw.get("body") or raw.get("review") or raw.get("text") or "").strip()
    if not body:
        raise ValueError("Play Store review body is empty")

    rating = raw.get("rating")
    if rating is not None:
        rating = int(rating)
        if not 1 <= rating <= 5:
            rating = None

    metadata = dict(raw.get("metadata") or {})
    metadata.setdefault("platform", "android")

    return {
        "source": "play_store",
        "source_id": source_id,
        "title": None,
        "body": body,
        "rating": rating,
        "metadata": metadata,
        "published_at": _parse_datetime(raw.get("published_at")),
        "status": "pending",
    }


def normalize_app_store_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize an App Store CSV row into a review record."""
    record = normalize_play_store_row(raw)
    record["source"] = "app_store"
    record["metadata"] = {**record["metadata"], "platform": "ios"}
    return record


def normalize(raw: dict[str, Any], source: str) -> dict[str, Any]:
    if source == "reddit":
        return normalize_reddit_post(raw)
    if source == "play_store":
        return normalize_play_store_row(raw)
    if source == "app_store":
        return normalize_app_store_row(raw)
    raise ValueError(f"Unsupported source for normalize(): {source}")
