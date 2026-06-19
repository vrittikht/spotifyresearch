"""Supabase data access layer — Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from supabase import Client

from services.config import get_secret

REVIEW_STATUSES = ("pending", "analyzing", "analyzed", "skipped", "failed")
INGESTION_SOURCES = ("reddit", "play_store", "app_store")


@lru_cache(maxsize=1)
def get_client() -> "Client":
    from supabase import create_client

    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in secrets.toml")
    return create_client(url, key)


def _first_row(response: Any) -> dict[str, Any] | None:
    data = response.data
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


# ─── Reviews ────────────────────────────────────────────────────────


def insert_review(review: dict[str, Any]) -> str:
    payload = _review_payload(review)
    row = _first_row(get_client().table("reviews").insert(payload).execute())
    if not row:
        raise RuntimeError("Failed to insert review")
    return str(row["id"])


def get_review_by_source(source: str, source_id: str) -> dict[str, Any] | None:
    response = (
        get_client()
        .table("reviews")
        .select("*")
        .eq("source", source)
        .eq("source_id", source_id)
        .limit(1)
        .execute()
    )
    return _first_row(response)


def upsert_review(review: dict[str, Any]) -> tuple[str, bool]:
    """Insert review or return existing id. Returns (review_id, is_new)."""
    source = review["source"]
    source_id = review["source_id"]
    existing = get_review_by_source(source, source_id)
    if existing:
        return str(existing["id"]), False
    return insert_review(review), True


def update_review_status(review_id: str, status: str) -> None:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    get_client().table("reviews").update({"status": status}).eq("id", review_id).execute()


def get_reviews(
    status: str | None = None,
    source: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = get_client().table("reviews").select("*").order("ingested_at", desc=True).limit(limit)
    if status:
        query = query.eq("status", status)
    if source:
        query = query.eq("source", source)
    return query.execute().data or []


def reset_failed_reviews(limit: int = 1000) -> int:
    """Reset failed reviews back to pending (for rate-limit recovery)."""
    failed = get_reviews(status="failed", limit=limit)
    for review in failed:
        update_review_status(str(review["id"]), "pending")
    return len(failed)


def get_pending_reviews(limit: int = 50) -> list[dict[str, Any]]:
    return get_reviews(status="pending", limit=limit)


def delete_review(review_id: str) -> None:
    """Helper for smoke tests."""
    get_client().table("reviews").delete().eq("id", review_id).execute()


# ─── Ingestion runs ───────────────────────────────────────────────


def create_ingestion_run(source: str) -> str:
    if source not in INGESTION_SOURCES:
        raise ValueError(f"Invalid source: {source}")
    row = _first_row(
        get_client().table("ingestion_runs").insert({"source": source, "status": "running"}).execute()
    )
    if not row:
        raise RuntimeError("Failed to create ingestion run")
    return str(row["id"])


def complete_ingestion_run(
    run_id: str,
    records_fetched: int,
    records_new: int,
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "records_fetched": records_fetched,
        "records_new": records_new,
        "status": "failed" if error else "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        payload["error_message"] = error
    get_client().table("ingestion_runs").update(payload).eq("id", run_id).execute()


def get_ingestion_runs(limit: int = 20) -> list[dict[str, Any]]:
    return (
        get_client()
        .table("ingestion_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


# ─── Analysis ─────────────────────────────────────────────────────


def save_analysis(review_id: str, analysis: dict[str, Any]) -> str:
    payload = {
        "review_id": review_id,
        "is_relevant": analysis.get("is_relevant", False),
        "pain_points": analysis.get("pain_points", []),
        "jobs_to_be_done": analysis.get("jobs_to_be_done", []),
        "discovery_barriers": analysis.get("discovery_barriers", []),
        "rec_frustrations": analysis.get("rec_frustrations", []),
        "listening_behaviors": analysis.get("listening_behaviors", []),
        "repeat_listening_causes": analysis.get("repeat_listening_causes", []),
        "user_segment": analysis.get("user_segment"),
        "sentiment": analysis.get("sentiment"),
        "emotions": analysis.get("emotions", []),
        "unmet_needs": analysis.get("unmet_needs", []),
        "confidence": analysis.get("confidence"),
    }
    row = _first_row(get_client().table("analysis").upsert(payload, on_conflict="review_id").execute())
    if not row:
        raise RuntimeError("Failed to save analysis")
    return str(row["id"])


def get_analyses_with_reviews(is_relevant: bool = True) -> list[dict[str, Any]]:
    query = get_client().table("analysis").select("*, reviews(*)").order("analyzed_at", desc=True)
    if is_relevant:
        query = query.eq("is_relevant", True)
    return query.execute().data or []


# ─── Themes & reports ─────────────────────────────────────────────


def save_themes(themes: list[dict[str, Any]]) -> list[str]:
    if not themes:
        return []
    rows = get_client().table("themes").insert(themes).execute().data or []
    return [str(row["id"]) for row in rows]


def link_theme_reviews(theme_id: str, review_ids: list[str]) -> int:
    if not review_ids:
        return 0
    links = [{"theme_id": theme_id, "review_id": rid} for rid in review_ids]
    get_client().table("theme_reviews").upsert(links, on_conflict="theme_id,review_id").execute()
    return len(review_ids)


def save_report(report: dict[str, Any], theme_ids: list[str] | None = None) -> str:
    payload = {
        "report_type": report.get("report_type", "research_summary"),
        "title": report["title"],
        "content": report.get("content", {}),
        "research_answers": report.get("research_answers", {}),
    }
    row = _first_row(get_client().table("insight_reports").insert(payload).execute())
    if not row:
        raise RuntimeError("Failed to save report")
    report_id = str(row["id"])
    if theme_ids:
        links = [{"report_id": report_id, "theme_id": tid} for tid in theme_ids]
        get_client().table("report_themes").insert(links).execute()
    return report_id


def get_latest_report() -> dict[str, Any] | None:
    return _first_row(
        get_client()
        .table("insight_reports")
        .select("*")
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )


def get_themes(category: str | None = None) -> list[dict[str, Any]]:
    query = get_client().table("themes").select("*").order("review_count", desc=True)
    if category:
        query = query.eq("category", category)
    return query.execute().data or []


def get_theme_detail(theme_id: str) -> dict[str, Any] | None:
    theme = _first_row(get_client().table("themes").select("*").eq("id", theme_id).execute())
    if not theme:
        return None
    links = (
        get_client().table("theme_reviews").select("review_id").eq("theme_id", theme_id).execute().data
        or []
    )
    review_ids = [link["review_id"] for link in links]
    reviews: list[dict[str, Any]] = []
    if review_ids:
        reviews = get_client().table("reviews").select("*").in_("id", review_ids).execute().data or []
    return {**theme, "reviews": reviews}


# ─── Dashboard queries ────────────────────────────────────────────


def _table_count(client: Any, table: str, **filters: Any) -> int:
    query = client.table(table).select("*", count="exact", head=True)
    for key, value in filters.items():
        query = query.eq(key, value)
    return query.execute().count or 0


def get_overview_stats() -> dict[str, Any]:
    client = get_client()
    total_reviews = _table_count(client, "reviews")

    status_counts = {s: _table_count(client, "reviews", status=s) for s in REVIEW_STATUSES}
    status_counts = {k: v for k, v in status_counts.items() if v > 0}
    source_counts = {s: _table_count(client, "reviews", source=s) for s in INGESTION_SOURCES}
    source_counts = {k: v for k, v in source_counts.items() if v > 0}

    analysis_rows = (
        client.table("analysis").select("is_relevant, sentiment, user_segment").eq("is_relevant", True).execute().data
        or []
    )
    relevant = len(analysis_rows)
    sentiment_counts: dict[str, int] = {}
    segment_counts: dict[str, int] = {}
    for a in analysis_rows:
        s = a.get("sentiment") or "unknown"
        sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
        seg = a.get("user_segment") or "unknown"
        segment_counts[seg] = segment_counts.get(seg, 0) + 1

    theme_count = _table_count(client, "themes")

    return {
        "total_reviews": total_reviews,
        "relevant_reviews": relevant,
        "skipped_reviews": status_counts.get("skipped", 0),
        "total_themes": theme_count,
        "sentiment": sentiment_counts,
        "by_source": source_counts,
        "by_status": status_counts,
        "top_segments": sorted(
            [{"segment": k, "count": v} for k, v in segment_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5],
    }


def get_evidence(
    source: str | None = None,
    segment: str | None = None,
    sentiment: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    query = (
        get_client()
        .table("analysis")
        .select("*, reviews(*)")
        .eq("is_relevant", True)
        .order("analyzed_at", desc=True)
        .limit(limit)
    )
    if segment:
        query = query.eq("user_segment", segment)
    if sentiment:
        query = query.eq("sentiment", sentiment)
    rows = query.execute().data or []
    if source:
        rows = [r for r in rows if r.get("reviews", {}).get("source") == source]
    return rows


def get_segment_breakdown() -> list[dict[str, Any]]:
    rows = get_analyses_with_reviews(is_relevant=True)
    segments: dict[str, dict[str, Any]] = {}
    for row in rows:
        seg = row.get("user_segment") or "unknown"
        if seg not in segments:
            segments[seg] = {
                "segment": seg,
                "count": 0,
                "discovery_barriers": [],
                "rec_frustrations": [],
            }
        segments[seg]["count"] += 1
        segments[seg]["discovery_barriers"].extend(row.get("discovery_barriers") or [])
        segments[seg]["rec_frustrations"].extend(row.get("rec_frustrations") or [])
    return sorted(segments.values(), key=lambda x: x["count"], reverse=True)


# ─── Helpers ────────────────────────────────────────────────────────


def _review_payload(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": review["source"],
        "source_id": str(review["source_id"]),
        "title": review.get("title"),
        "body": review["body"],
        "rating": review.get("rating"),
        "metadata": review.get("metadata") or {},
        "published_at": review.get("published_at"),
        "status": review.get("status", "pending"),
        "ingestion_run_id": review.get("ingestion_run_id"),
    }
