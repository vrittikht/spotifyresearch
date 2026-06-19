"""Themes explorer — ranked patterns with quotes."""

from __future__ import annotations

import streamlit as st

from components.empty_state import show_empty
from components.filters import render_theme_category_filter
from components.sidebar_footer import render_sidebar_footer
from components.styles import apply_dashboard_style, page_header
from components.theme_card import render_theme_card
from services import supabase_client as db

st.set_page_config(page_title="Themes", page_icon="🏷️", layout="wide")
apply_dashboard_style()
page_header("Themes", "Discovery patterns ranked by review count")

try:
    themes = db.get_themes()
except Exception as exc:
    st.error(f"Could not load themes: {exc}")
    st.stop()

if not themes:
    show_empty(
        "No themes yet",
        "Generate themes and a research report from your analyzed reviews.",
        "python scripts/generate_insights.py",
    )
    render_sidebar_footer()
    st.stop()

category = render_theme_category_filter(themes)
filtered = themes if not category else [t for t in themes if t.get("category") == category]
filtered = sorted(filtered, key=lambda t: t.get("review_count") or 0, reverse=True)

st.caption(f"Showing {len(filtered)} theme(s)")
for theme in filtered:
    render_theme_card(theme)

render_sidebar_footer()
