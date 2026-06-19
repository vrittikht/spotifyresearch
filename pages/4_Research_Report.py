"""Research report — six PM research questions answered."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.constants import RESEARCH_QUESTIONS
from components.empty_state import show_empty
from components.report_helpers import enrich_research_answers
from components.sidebar_footer import render_sidebar_footer
from components.styles import apply_dashboard_style, page_header
from services import supabase_client as db

st.set_page_config(page_title="Research Report", page_icon="📊", layout="wide")
apply_dashboard_style()
page_header("Research Report", "Evidence-backed answers to six discovery research questions")

try:
    report = db.get_latest_report()
except Exception as exc:
    st.error(f"Could not load report: {exc}")
    st.stop()

if not report:
    show_empty(
        "No research report",
        "Generate a report with themes and answers to six research questions.",
        "python scripts/generate_insights.py",
    )
    render_sidebar_footer()
    st.stop()

st.markdown(f"### {report.get('title', 'Research Report')}")
generated = report.get("generated_at")
if generated:
    try:
        ts = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        st.caption(f"Generated: {ts.strftime('%Y-%m-%d %H:%M UTC')}")
    except ValueError:
        st.caption(f"Generated: {generated}")

summary = (report.get("content") or {}).get("executive_summary", "")
if summary:
    st.markdown("#### Executive summary")
    st.markdown(summary)

st.divider()

themes = db.get_themes()
stats = db.get_overview_stats()
segments = db.get_segment_breakdown()
answers = enrich_research_answers(
    report,
    themes,
    stats.get("relevant_reviews", 0),
    segments=segments,
)

for key, question in RESEARCH_QUESTIONS.items():
    answer = answers.get(key) or {}
    st.markdown(f"#### {question}")

    if answer.get("summary"):
        st.markdown(answer["summary"])
    else:
        st.caption("_No summary available for this question._")

    themes_list = answer.get("top_themes") or []
    if themes_list:
        st.markdown("**Top themes**")
        for theme in themes_list:
            st.write(f"- {theme}")

    count = answer.get("evidence_count")
    if count is not None and count > 0:
        st.caption(f"Evidence: **{count}** reviews")
    elif count == 0:
        st.caption("Evidence: _count not available_")

    st.divider()

stored = report.get("research_answers") or {}
missing = [k for k in RESEARCH_QUESTIONS if k not in stored]
if missing:
    st.warning(f"Missing answers for: {', '.join(missing)}")

render_sidebar_footer()
