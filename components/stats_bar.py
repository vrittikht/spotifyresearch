"""Metric tiles for dashboard overview."""

from __future__ import annotations

import streamlit as st


def render_stats_bar(stats: dict) -> None:
    """Four KPI metrics: total reviews, relevant, themes, dominant sentiment."""
    sentiment = stats.get("sentiment") or {}
    top_sentiment = max(sentiment, key=sentiment.get, default="—") if sentiment else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Reviews", stats.get("total_reviews", 0))
    c2.metric("Relevant Reviews", stats.get("relevant_reviews", 0))
    c3.metric("Themes", stats.get("total_themes", 0))
    c4.metric("Top Sentiment", str(top_sentiment).replace("_", " ").title())
