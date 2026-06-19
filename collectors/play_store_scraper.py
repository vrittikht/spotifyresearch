"""Fetch real Google Play Store reviews for the Spotify app."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from google_play_scraper import Sort, reviews
from google_play_scraper.exceptions import NotFoundError

SPOTIFY_APP_ID = "com.spotify.music"
DEFAULT_COUNTRY = "us"
DEFAULT_LANG = "en"

DISCOVERY_KEYWORDS = (
    "discover",
    "recommend",
    "algorithm",
    "playlist",
    "weekly",
    "radio",
    "repeat",
    "same song",
    "music discovery",
    "release radar",
    "daily mix",
    "suggestion",
    "autoplay",
    "shuffle",
    "genre",
    "new music",
    "wrapped",
    "blend",
    "dj ",
    "feed",
    "home screen",
)

SORT_MAP = {
    "newest": Sort.NEWEST,
    "rating": Sort.RATING,
    "relevant": Sort.MOST_RELEVANT,
}


@dataclass
class PlayStoreScrapeResult:
    fetched: int
    filtered: int
    reviews: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _matches_discovery(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in DISCOVERY_KEYWORDS)


def _to_review_row(raw: dict[str, Any]) -> dict[str, Any]:
    review_id = str(raw.get("reviewId") or raw.get("review_id") or "")
    content = (raw.get("content") or "").strip()
    at = raw.get("at")
    published_at: str | None = None
    if isinstance(at, datetime):
        published_at = at.replace(tzinfo=timezone.utc).isoformat()

    return {
        "source": "play_store",
        "source_id": review_id or _hash_id(content, raw.get("userName", "")),
        "title": None,
        "body": content,
        "rating": raw.get("score"),
        "metadata": {
            "app_id": SPOTIFY_APP_ID,
            "user_name": raw.get("userName"),
            "thumbs_up": raw.get("thumbsUpCount"),
            "review_created_version": raw.get("reviewCreatedVersion"),
            "platform": "android",
        },
        "published_at": published_at,
        "status": "pending",
    }


def _hash_id(content: str, user: str) -> str:
    import hashlib

    digest = hashlib.sha256(f"{content}|{user}".encode()).hexdigest()[:16]
    return f"ps_{digest}"


def scrape_spotify_reviews(
    count: int = 500,
    sort: str = "newest",
    country: str = DEFAULT_COUNTRY,
    lang: str = DEFAULT_LANG,
    discovery_only: bool = True,
    min_filtered: int = 50,
    request_delay: float = 0.5,
) -> PlayStoreScrapeResult:
    """
    Fetch real Spotify Play Store reviews via google-play-scraper.

    When discovery_only=True, keeps reviews mentioning discovery/recommendation themes.
    Falls back to unfiltered batch if too few matches.
    """
    sort_key = SORT_MAP.get(sort, Sort.NEWEST)
    errors: list[str] = []
    raw_reviews: list[dict[str, Any]] = []
    token = None

    try:
        while len(raw_reviews) < count:
            batch_size = min(200, count - len(raw_reviews))
            batch, token = reviews(
                SPOTIFY_APP_ID,
                lang=lang,
                country=country,
                sort=sort_key,
                count=batch_size,
                continuation_token=token,
            )
            if not batch:
                break
            raw_reviews.extend(batch)
            if not token:
                break
            time.sleep(request_delay)
    except NotFoundError as exc:
        errors.append(f"Spotify app not found: {exc}")
    except Exception as exc:
        errors.append(f"Play Store fetch failed: {exc}")

    normalized = [_to_review_row(row) for row in raw_reviews if (row.get("content") or "").strip()]

    if discovery_only:
        filtered = [row for row in normalized if _matches_discovery(row["body"])]
        if len(filtered) < min_filtered:
            filtered = normalized[: max(min_filtered, len(filtered))]
    else:
        filtered = normalized

    return PlayStoreScrapeResult(
        fetched=len(raw_reviews),
        filtered=len(filtered),
        reviews=filtered,
        errors=errors,
    )


def scrape_to_normalized(
    count: int = 500,
    sort: str = "newest",
    discovery_only: bool = True,
) -> PlayStoreScrapeResult:
    """Convenience wrapper used by CLI scripts."""
    return scrape_spotify_reviews(count=count, sort=sort, discovery_only=discovery_only)
