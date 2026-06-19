"""Expandable theme card with quotes and breakdowns."""

from __future__ import annotations

from typing import Any

import streamlit as st

from components.constants import THEME_CATEGORY_LABELS
from components.quote_block import render_quote_block


def render_theme_card(theme: dict[str, Any]) -> None:
    category = theme.get("category", "")
    cat_label = THEME_CATEGORY_LABELS.get(category, category.replace("_", " ").title())
    count = theme.get("review_count", 0)
    label = f"**{theme.get('name', 'Untitled')}** — {cat_label} ({count} reviews)"

    with st.expander(label, expanded=False):
        st.markdown(theme.get("description") or "_No description._")

        quotes = theme.get("example_quotes") or []
        if quotes:
            st.markdown("**Example quotes**")
            for quote in quotes[:3]:
                render_quote_block(quote)

        col1, col2 = st.columns(2)
        seg = theme.get("segment_breakdown") or {}
        src = theme.get("source_breakdown") or {}
        if seg:
            col1.markdown("**By segment**")
            for name, n in sorted(seg.items(), key=lambda x: x[1], reverse=True):
                col1.write(f"- {name.replace('_', ' ')}: {n}")
        if src:
            col2.markdown("**By source**")
            for name, n in sorted(src.items(), key=lambda x: x[1], reverse=True):
                col2.write(f"- {name}: {n}")

        score = theme.get("avg_sentiment_score")
        if score is not None:
            st.caption(f"Avg sentiment score: {score:.2f}")
