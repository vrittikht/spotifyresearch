"""Spotify Discovery Research Agent — Overview dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.constants import SENTIMENT_COLORS, SOURCE_LABELS
from components.sidebar_footer import render_sidebar_footer
from components.stats_bar import render_stats_bar
from components.styles import apply_dashboard_style, page_header
from services import supabase_client as db
from services.config import load_secrets, secrets_configured
from services.connection_tests import run_all_tests

st.set_page_config(
    page_title="Overview — Spotify Discovery Research",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_dashboard_style()
page_header(
    "Spotify Discovery Research Agent",
    "Overview — discovery insights from public user feedback",
)

try:
    stats = db.get_overview_stats()
except Exception as exc:
    st.error(f"Could not load data from Supabase: {exc}")
    st.stop()

render_stats_bar(stats)

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Sentiment distribution")
    sentiment = stats.get("sentiment") or {}
    if sentiment:
        df_sent = pd.DataFrame(
            [{"sentiment": k, "count": v} for k, v in sentiment.items()]
        )
        fig = px.pie(
            df_sent,
            values="count",
            names="sentiment",
            color="sentiment",
            color_discrete_map=SENTIMENT_COLORS,
            hole=0.35,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sentiment data yet — run Phase 3 analysis.")

with col_right:
    st.subheader("Reviews by source")
    by_source = stats.get("by_source") or {}
    if by_source:
        df_src = pd.DataFrame(
            [
                {"source": SOURCE_LABELS.get(k, k), "count": v}
                for k, v in by_source.items()
            ]
        )
        fig = px.bar(df_src, x="source", y="count", color="source", color_discrete_sequence=["#1DB954"])
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No reviews ingested yet — run Phase 2 collection.")

st.divider()

col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("Executive summary")
    report = db.get_latest_report()
    if report:
        summary = (report.get("content") or {}).get("executive_summary", "")
        st.markdown(summary or "_No executive summary in latest report._")
        st.caption(f"Report: {report.get('title', 'Untitled')}")
    else:
        st.info("No insight report yet — run `scripts/generate_insights.py` (Phase 4).")

with col_b:
    st.subheader("Top segments")
    top_segments = stats.get("top_segments") or []
    if top_segments:
        for item in top_segments:
            seg = str(item.get("segment", "unknown")).replace("_", " ")
            st.write(f"**{seg.title()}** — {item.get('count', 0)} reviews")
    else:
        st.info("No segment data yet.")

st.divider()
st.markdown(
    """
    **Explore the dashboard**
    - **Themes** — ranked discovery patterns with user quotes
    - **Evidence** — filterable review library with analysis
    - **Segments** — compare barriers and frustrations by user segment
    - **Research Report** — answers to all six research questions
    """
)

with st.sidebar.expander("Connection tests (Phase 0)"):
    try:
        secrets = dict(st.secrets)
    except (FileNotFoundError, AttributeError):
        secrets = load_secrets()

    if not secrets_configured() and not secrets:
        st.warning("Configure `.streamlit/secrets.toml` first.")
    elif st.button("Run tests", key="conn_tests"):
        results = run_all_tests(
            supabase_url=str(secrets.get("SUPABASE_URL", "")),
            supabase_key=str(secrets.get("SUPABASE_SERVICE_KEY", "")),
            groq_api_key=str(secrets.get("GROQ_API_KEY", "")),
            groq_model=str(secrets.get("GROQ_MODEL", "llama-3.1-8b-instant")),
        )
        for result in results:
            if result.ok:
                st.success(f"{result.name}: {result.message}")
            else:
                st.error(f"{result.name}: {result.message}")

render_sidebar_footer()
