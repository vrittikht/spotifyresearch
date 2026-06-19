"""Sidebar footer shown on all dashboard pages."""

from __future__ import annotations

import streamlit as st

from services import supabase_client as db


def render_sidebar_footer() -> None:
    try:
        stats = db.get_overview_stats()
        st.sidebar.divider()
        st.sidebar.caption("**Dataset snapshot**")
        st.sidebar.write(f"Reviews: {stats.get('total_reviews', 0)}")
        st.sidebar.write(f"Relevant: {stats.get('relevant_reviews', 0)}")
        st.sidebar.write(f"Themes: {stats.get('total_themes', 0)}")
    except Exception:
        st.sidebar.caption("Connect Supabase to load stats.")

    st.sidebar.divider()
    st.sidebar.caption(
        "[GitHub](https://github.com/vrittikht/spotifyresearch) · "
        "Spotify Discovery Research Agent"
    )
