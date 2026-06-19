"""Shared filter controls for evidence and themes pages."""

from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from components.constants import SOURCE_LABELS, THEME_CATEGORY_LABELS


def render_evidence_filters(rows: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None, str]:
    segments = sorted({r.get("user_segment") or "unknown" for r in rows})
    sentiments = sorted({r.get("sentiment") or "unknown" for r in rows})
    sources = sorted(
        {(r.get("reviews") or {}).get("source") or "unknown" for r in rows}
    )

    c1, c2, c3, c4 = st.columns(4)
    source = c1.selectbox(
        "Source",
        ["All"] + [SOURCE_LABELS.get(s, s) for s in sources],
    )
    segment = c2.selectbox("Segment", ["All"] + [s.replace("_", " ") for s in segments])
    sentiment = c3.selectbox("Sentiment", ["All"] + sentiments)
    keyword = c4.text_input("Keyword search", placeholder="e.g. discover weekly")

    source_key = None if source == "All" else next(
        (k for k, v in SOURCE_LABELS.items() if v == source), source.lower()
    )
    segment_key = None if segment == "All" else segment.replace(" ", "_").lower()
    # Match display label back to stored segment id (e.g. "power user" -> "power_user")
    if segment_key and segment_key not in segments:
        for seg in segments:
            if seg.replace("_", " ") == segment.lower():
                segment_key = seg
                break
    sentiment_key = None if sentiment == "All" else sentiment

    return source_key, segment_key, sentiment_key, keyword.strip().lower()


def filter_evidence_rows(
    rows: list[dict[str, Any]],
    source: str | None,
    segment: str | None,
    sentiment: str | None,
    keyword: str,
) -> list[dict[str, Any]]:
    filtered = rows
    if source:
        filtered = [r for r in filtered if (r.get("reviews") or {}).get("source") == source]
    if segment:
        filtered = [r for r in filtered if (r.get("user_segment") or "unknown") == segment]
    if sentiment:
        filtered = [r for r in filtered if (r.get("sentiment") or "unknown") == sentiment]
    if keyword:
        filtered = [
            r
            for r in filtered
            if keyword in ((r.get("reviews") or {}).get("body") or "").lower()
            or keyword in ((r.get("reviews") or {}).get("title") or "").lower()
        ]
    return filtered


def render_theme_category_filter(themes: list[dict[str, Any]]) -> str | None:
    categories = sorted({t.get("category") for t in themes if t.get("category")})
    options = ["All categories"] + [
        THEME_CATEGORY_LABELS.get(c, c) for c in categories
    ]
    selected = st.selectbox("Category", options)
    if selected == "All categories":
        return None
    for key, label in THEME_CATEGORY_LABELS.items():
        if label == selected:
            return key
    return None


def top_items_from_json(items: list[Any], text_key: str, top: int = 3) -> list[str]:
    counts: Counter[str] = Counter()
    for item in items:
        if isinstance(item, dict):
            text = str(item.get(text_key) or item.get("text") or "").strip()
            if text:
                counts[text] += 1
    return [text for text, _ in counts.most_common(top)]
