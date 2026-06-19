"""Aggregate analyses and generate themes + research report via Groq."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from prompts.synthesis import FIELD_TEXT_KEYS
from components.report_helpers import enrich_research_answers
from services import supabase_client as db
from services.groq_service import synthesize_themes

QUOTE_MAX_LEN = 140
STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "are", "was", "have", "not"}


@dataclass
class ReportResult:
    report_id: str
    theme_ids: list[str]
    theme_count: int
    total_relevant: int
    linked_reviews: int = 0
    errors: list[str] = field(default_factory=list)


def group_by(analyses: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for analysis in analyses:
        if field == "source":
            review = analysis.get("reviews") or {}
            key = str(review.get("source") or "unknown")
        else:
            key = str(analysis.get(field) or "unknown")
        counts[key] += 1
    return dict(counts.most_common())


def count_by(analyses: list[dict[str, Any]], field: str) -> dict[str, int]:
    return group_by(analyses, field)


def frequency_count(
    analyses: list[dict[str, Any]],
    field: str,
    top: int = 20,
) -> list[dict[str, Any]]:
    text_key = FIELD_TEXT_KEYS.get(field, "text")
    counts: Counter[str] = Counter()

    for analysis in analyses:
        for item in analysis.get(field) or []:
            if isinstance(item, dict):
                text = str(item.get(text_key) or item.get("text") or "").strip()
            else:
                text = str(item).strip()
            if text:
                counts[text] += 1

    return [{"text": text, "count": count} for text, count in counts.most_common(top)]


def select_representative_quotes(analyses: list[dict[str, Any]], n: int = 30) -> list[dict[str, str]]:
    quotes: list[dict[str, str]] = []
    seen: set[str] = set()

    for analysis in analyses:
        review = analysis.get("reviews") or {}
        body = (review.get("body") or "").strip()
        title = (review.get("title") or "").strip()
        text = body or title
        if not text or len(text) < 20:
            continue

        key = text[:80].lower()
        if key in seen:
            continue
        seen.add(key)

        snippet = text if len(text) <= QUOTE_MAX_LEN else text[: QUOTE_MAX_LEN - 3] + "..."
        quotes.append(
            {
                "quote": snippet,
                "source": str(review.get("source") or "unknown"),
                "segment": str(analysis.get("user_segment") or "unknown"),
                "sentiment": str(analysis.get("sentiment") or "neutral"),
            }
        )
        if len(quotes) >= n:
            break

    return quotes


def prepare_synthesis_input(analyses: list[dict[str, Any]]) -> dict[str, Any]:
    """Compress relevant analyses into token-safe summary for Groq synthesis."""
    return {
        "total_relevant": len(analyses),
        "by_segment": group_by(analyses, "user_segment"),
        "by_source": group_by(analyses, "source"),
        "top_barriers": frequency_count(analyses, "discovery_barriers", top=12),
        "top_frustrations": frequency_count(analyses, "rec_frustrations", top=12),
        "top_behaviors": frequency_count(analyses, "listening_behaviors", top=12),
        "top_repeat_causes": frequency_count(analyses, "repeat_listening_causes", top=12),
        "top_unmet_needs": frequency_count(analyses, "unmet_needs", top=12),
        "sentiment_distribution": count_by(analyses, "sentiment"),
        "sample_quotes": select_representative_quotes(analyses, n=15),
    }


def _theme_keywords(theme: dict[str, Any]) -> set[str]:
    words: set[str] = set()
    for text in (theme.get("name", ""), theme.get("description", "")):
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            if len(word) > 3 and word not in STOPWORDS:
                words.add(word)
    for quote in theme.get("example_quotes") or []:
        if isinstance(quote, dict):
            q = quote.get("quote", "")
        else:
            q = str(quote)
        for word in re.findall(r"[a-z0-9]+", q.lower()):
            if len(word) > 4 and word not in STOPWORDS:
                words.add(word)
    return words


def _score_review_for_theme(theme: dict[str, Any], analysis: dict[str, Any]) -> int:
    review = analysis.get("reviews") or {}
    haystack = " ".join(
        [
            str(review.get("title") or ""),
            str(review.get("body") or ""),
            str(analysis.get("user_segment") or ""),
        ]
    ).lower()

    keywords = _theme_keywords(theme)
    if not keywords:
        return 0

    score = sum(2 for kw in keywords if kw in haystack)
    category = theme.get("category")
    field_map = {
        "discovery_barrier": "discovery_barriers",
        "rec_frustration": "rec_frustrations",
        "listening_behavior": "listening_behaviors",
        "repeat_listening": "repeat_listening_causes",
        "unmet_need": "unmet_needs",
    }
    field = field_map.get(category or "")
    if field:
        text_key = FIELD_TEXT_KEYS.get(field, "text")
        for item in analysis.get(field) or []:
            if isinstance(item, dict):
                text = str(item.get(text_key) or "").lower()
                if any(kw in text for kw in keywords):
                    score += 3
    return score


def link_themes_to_reviews(
    themes: list[dict[str, Any]],
    theme_ids: list[str],
    analyses: list[dict[str, Any]],
    max_per_theme: int = 15,
) -> int:
    """Populate theme_reviews junction by keyword/category matching."""
    total_linked = 0
    for theme, theme_id in zip(themes, theme_ids):
        scored: list[tuple[int, str]] = []
        for analysis in analyses:
            review = analysis.get("reviews") or {}
            review_id = review.get("id")
            if not review_id:
                continue
            score = _score_review_for_theme(theme, analysis)
            if score > 0:
                scored.append((score, str(review_id)))

        scored.sort(key=lambda x: x[0], reverse=True)
        review_ids = [rid for _, rid in scored[:max_per_theme]]
        if review_ids:
            total_linked += db.link_theme_reviews(theme_id, review_ids)
    return total_linked


def _theme_to_db_row(theme: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": theme["name"],
        "description": theme["description"],
        "category": theme["category"],
        "review_count": int(theme.get("review_count_estimate") or 0),
        "example_quotes": theme.get("example_quotes") or [],
        "segment_breakdown": theme.get("segment_breakdown") or {},
        "source_breakdown": theme.get("source_breakdown") or {},
        "avg_sentiment_score": theme.get("avg_sentiment_score"),
    }


def generate_report(title: str | None = None) -> ReportResult:
    """
    Full insight pipeline: fetch analyses → aggregate → Groq synthesis → save themes + report.
    """
    analyses = db.get_analyses_with_reviews(is_relevant=True)
    if not analyses:
        raise RuntimeError("No relevant analyses found — run Phase 3 analysis first")

    synthesis_input = prepare_synthesis_input(analyses)
    synthesis = synthesize_themes(synthesis_input)

    themes = synthesis.get("themes") or []
    if not themes:
        raise RuntimeError("Groq synthesis returned no themes")

    # Backfill empty research answers from theme data before persisting
    draft_report = {
        "research_answers": synthesis.get("research_answers") or {},
        "content": {"executive_summary": synthesis.get("executive_summary", "")},
    }
    enriched_answers = enrich_research_answers(
        draft_report,
        [{**t, "review_count": t.get("review_count_estimate", 0)} for t in themes],
        len(analyses),
        segments=db.get_segment_breakdown(),
    )
    synthesis["research_answers"] = enriched_answers

    db_rows = [_theme_to_db_row(t) for t in themes]
    theme_ids = db.save_themes(db_rows)

    report_title = title or f"Spotify Discovery Research Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    report_payload = {
        "report_type": "research_summary",
        "title": report_title,
        "content": {"executive_summary": synthesis.get("executive_summary", "")},
        "research_answers": synthesis.get("research_answers") or {},
    }
    report_id = db.save_report(report_payload, theme_ids=theme_ids)

    linked = link_themes_to_reviews(themes, theme_ids, analyses)

    return ReportResult(
        report_id=report_id,
        theme_ids=theme_ids,
        theme_count=len(theme_ids),
        total_relevant=len(analyses),
        linked_reviews=linked,
    )
