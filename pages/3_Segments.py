"""Segment comparison — barriers and frustrations by user segment."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.empty_state import show_empty
from components.filters import top_items_from_json
from components.sidebar_footer import render_sidebar_footer
from components.styles import apply_dashboard_style, page_header
from services import supabase_client as db

st.set_page_config(page_title="Segments", page_icon="👥", layout="wide")
apply_dashboard_style()
page_header("Segments", "Discovery challenges compared across user segments")

try:
    segments = db.get_segment_breakdown()
except Exception as exc:
    st.error(f"Could not load segment data: {exc}")
    st.stop()

if len(segments) < 1:
    show_empty(
        "No segment data",
        "Run analysis on reviews to infer user segments.",
        "python scripts/run_analysis.py --limit 200",
    )
    render_sidebar_footer()
    st.stop()

df_counts = pd.DataFrame(
    [
        {"segment": s["segment"].replace("_", " ").title(), "reviews": s["count"]}
        for s in segments
    ]
)
fig = px.bar(
    df_counts,
    x="segment",
    y="reviews",
    color="reviews",
    color_continuous_scale=["#535353", "#1DB954"],
    title="Reviews per segment",
)
fig.update_layout(margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.divider()

for seg in segments:
    name = seg["segment"].replace("_", " ").title()
    with st.expander(f"**{name}** — {seg['count']} reviews", expanded=len(segments) <= 3):
        barriers = top_items_from_json(seg.get("discovery_barriers") or [], "barrier", top=3)
        frustrations = top_items_from_json(seg.get("rec_frustrations") or [], "frustration", top=3)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Top discovery barriers**")
            if barriers:
                for b in barriers:
                    st.write(f"- {b}")
            else:
                st.caption("None extracted")
        with c2:
            st.markdown("**Top recommendation frustrations**")
            if frustrations:
                for f in frustrations:
                    st.write(f"- {f}")
            else:
                st.caption("None extracted")

render_sidebar_footer()
