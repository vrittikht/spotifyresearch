"""Evidence library — filterable reviews with full analysis."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components.constants import SOURCE_LABELS
from components.empty_state import show_empty
from components.filters import filter_evidence_rows, render_evidence_filters
from components.sidebar_footer import render_sidebar_footer
from components.styles import apply_dashboard_style, page_header
from services import supabase_client as db

st.set_page_config(page_title="Evidence", page_icon="📋", layout="wide")
apply_dashboard_style()
page_header("Evidence", "Filterable review quotes with structured analysis")

try:
    rows = db.get_evidence(limit=500)
except Exception as exc:
    st.error(f"Could not load evidence: {exc}")
    st.stop()

if not rows:
    show_empty(
        "No evidence yet",
        "Analyze pending reviews to populate the evidence library.",
        "python scripts/run_analysis.py --limit 200",
    )
    render_sidebar_footer()
    st.stop()

source, segment, sentiment, keyword = render_evidence_filters(rows)
filtered = filter_evidence_rows(rows, source, segment, sentiment, keyword)
st.caption(f"{len(filtered)} of {len(rows)} reviews")

table_rows = []
for row in filtered:
    review = row.get("reviews") or {}
    body = review.get("body") or ""
    table_rows.append(
        {
            "source": SOURCE_LABELS.get(review.get("source", ""), review.get("source", "")),
            "segment": (row.get("user_segment") or "unknown").replace("_", " "),
            "sentiment": row.get("sentiment") or "unknown",
            "preview": (body[:120] + "…") if len(body) > 120 else body,
            "_row": row,
        }
    )

if not table_rows:
    st.warning("No reviews match your filters.")
    st.stop()

df = pd.DataFrame([{k: v for k, v in r.items() if k != "_row"} for r in table_rows])
st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("Review detail")
for i, item in enumerate(table_rows[:50]):
    row = item["_row"]
    review = row.get("reviews") or {}
    title = review.get("title") or item["preview"][:60]
    with st.expander(f"{item['source']} · {item['sentiment']} · {title}"):
        if review.get("title"):
            st.markdown(f"**{review['title']}**")
        st.write(review.get("body") or "")
        if review.get("rating"):
            st.caption(f"Rating: {review['rating']}/5")

        st.markdown("**Analysis**")
        analysis_fields = {
            "user_segment": row.get("user_segment"),
            "sentiment": row.get("sentiment"),
            "confidence": row.get("confidence"),
            "discovery_barriers": row.get("discovery_barriers"),
            "rec_frustrations": row.get("rec_frustrations"),
            "listening_behaviors": row.get("listening_behaviors"),
            "repeat_listening_causes": row.get("repeat_listening_causes"),
            "unmet_needs": row.get("unmet_needs"),
            "pain_points": row.get("pain_points"),
            "emotions": row.get("emotions"),
        }
        st.json(analysis_fields)

render_sidebar_footer()
