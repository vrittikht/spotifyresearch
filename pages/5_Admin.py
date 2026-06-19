"""Admin pipeline control panel."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from collectors.csv_importer import import_csv
from collectors.normalizer import normalize_reddit_post
from collectors.play_store_scraper import scrape_spotify_reviews
from collectors.reddit_collector import collect_reddit
from components.sidebar_footer import render_sidebar_footer
from components.styles import apply_dashboard_style, page_header
from services import supabase_client as db
from services.analysis_service import analyze_batch
from services.ingestion_service import ingest_reviews
from services.insight_service import generate_report

ADMIN_BATCH_LIMIT = 50

st.set_page_config(page_title="Admin", page_icon="⚙️", layout="wide")
apply_dashboard_style()
page_header("Admin", "Run the research pipeline from the dashboard")

st.caption(f"Batch limit: {ADMIN_BATCH_LIMIT} items per action (use CLI for bulk runs).")


def _load_stats() -> dict:
    return db.get_overview_stats()


def _render_status() -> None:
    stats = _load_stats()
    by_status = stats.get("by_status") or {}
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", stats.get("total_reviews", 0))
    c2.metric("Analyzed", by_status.get("analyzed", 0))
    c3.metric("Pending", by_status.get("pending", 0))
    c4.metric("Skipped", by_status.get("skipped", 0))
    c5.metric("Failed", by_status.get("failed", 0))


_render_status()
st.divider()

# ─── 1. Collect Data ───────────────────────────────────────────────
st.subheader("1. Collect data")

col_r, col_p = st.columns(2)

with col_r:
    st.markdown("**Reddit (live scrape)**")
    reddit_limit = st.number_input(
        "Reddit posts",
        min_value=5,
        max_value=ADMIN_BATCH_LIMIT,
        value=min(30, ADMIN_BATCH_LIMIT),
        key="reddit_limit",
    )
    if st.button("Collect Reddit", type="primary", key="btn_reddit"):
        with st.spinner("Scraping Reddit via RSS + old.reddit HTML..."):
            try:
                result = collect_reddit(scrape=True, limit=int(reddit_limit))
                normalized = [normalize_reddit_post(p.to_dict()) for p in result.posts]
                if not normalized:
                    st.warning("No posts collected. Check network or try again later.")
                else:
                    ingest = ingest_reviews(normalized, source="reddit")
                    st.success(
                        f"Reddit: fetched {result.unique}, inserted {ingest.inserted}, "
                        f"skipped {ingest.skipped}"
                    )
                    if result.errors:
                        st.warning("Some searches failed: " + "; ".join(result.errors[:2]))
            except Exception as exc:
                st.error(f"Reddit collection failed: {exc}")
        st.rerun()

with col_p:
    st.markdown("**Play Store (live scrape)**")
    ps_count = st.number_input(
        "Reviews to fetch",
        min_value=10,
        max_value=200,
        value=100,
        key="ps_count",
    )
    if st.button("Scrape Play Store", key="btn_playstore"):
        with st.spinner("Fetching Spotify Play Store reviews..."):
            try:
                scraped = scrape_spotify_reviews(count=int(ps_count), discovery_only=True)
                if not scraped.reviews:
                    st.warning("No reviews collected.")
                else:
                    ingest = ingest_reviews(scraped.reviews, source="play_store")
                    st.success(
                        f"Play Store: selected {scraped.filtered}, inserted {ingest.inserted}, "
                        f"skipped {ingest.skipped}"
                    )
            except Exception as exc:
                st.error(f"Play Store scrape failed: {exc}")
        st.rerun()

st.markdown("**Import CSV**")
uploaded = st.file_uploader("Upload Play Store / App Store CSV", type=["csv"], key="csv_upload")
csv_source = st.selectbox("CSV source type", ["play_store", "app_store"], key="csv_source")
if uploaded and st.button("Import CSV", key="btn_csv"):
    with st.spinner("Parsing and ingesting CSV..."):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = Path(tmp.name)
            parsed = import_csv(tmp_path, source=csv_source)
            tmp_path.unlink(missing_ok=True)
            if not parsed.reviews:
                st.warning("No valid rows in CSV.")
            else:
                ingest = ingest_reviews(parsed.reviews, source=csv_source)
                st.success(
                    f"CSV: parsed {parsed.fetched}, inserted {ingest.inserted}, skipped {ingest.skipped}"
                )
        except Exception as exc:
            st.error(f"CSV import failed: {exc}")
    st.rerun()

st.divider()

# ─── 2. Analyze ────────────────────────────────────────────────────
st.subheader("2. Analyze")

col_a, col_b = st.columns(2)
analyze_limit = st.slider(
    "Reviews per analysis run",
    min_value=5,
    max_value=ADMIN_BATCH_LIMIT,
    value=ADMIN_BATCH_LIMIT,
    key="analyze_limit",
)

with col_a:
    if st.button("Run analysis (pending)", type="primary", key="btn_analyze"):
        pending = db.get_reviews(status="pending", limit=int(analyze_limit))
        if not pending:
            st.info("No pending reviews.")
        else:
            progress = st.progress(0.0, text="Starting analysis...")
            status_box = st.empty()
            total = len(pending)

            def on_progress(result, _review, status_str):
                progress.progress(min(result.processed / total, 1.0))
                status_box.caption(
                    f"{result.processed}/{total} — last: {status_str} "
                    f"(analyzed={result.analyzed}, skipped={result.skipped}, failed={result.failed})"
                )

            with st.spinner("Running Groq analysis..."):
                try:
                    result = analyze_batch(limit=int(analyze_limit), on_progress=on_progress)
                    progress.progress(1.0)
                    msg = (
                        f"Done — analyzed={result.analyzed}, skipped={result.skipped}, "
                        f"failed={result.failed}"
                    )
                    if result.stopped_early:
                        st.warning(msg + " (stopped early — Groq rate limit)")
                    else:
                        st.success(msg)
                    if result.errors:
                        with st.expander("Errors"):
                            for err in result.errors[:10]:
                                st.write(err)
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")
            st.rerun()

with col_b:
    if st.button("Retry failed", key="btn_retry"):
        failed = db.get_reviews(status="failed", limit=int(analyze_limit))
        if not failed:
            st.info("No failed reviews.")
        else:
            with st.spinner("Retrying failed reviews..."):
                try:
                    result = analyze_batch(limit=int(analyze_limit), retry=True)
                    st.success(
                        f"Retry done — analyzed={result.analyzed}, skipped={result.skipped}, "
                        f"failed={result.failed}"
                    )
                except Exception as exc:
                    st.error(f"Retry failed: {exc}")
            st.rerun()

st.divider()

# ─── 3. Generate Insights ──────────────────────────────────────────
st.subheader("3. Generate insights")

if st.button("Generate research report", type="primary", key="btn_insights"):
    relevant = len(db.get_analyses_with_reviews(is_relevant=True))
    if relevant < 10:
        st.warning(f"Need at least 10 relevant analyses (have {relevant}).")
    else:
        with st.spinner("Running Groq synthesis — themes + research report..."):
            try:
                result = generate_report()
                st.success(
                    f"Report {result.report_id[:8]}… — {result.theme_count} themes, "
                    f"{result.linked_reviews} review links"
                )
            except Exception as exc:
                st.error(f"Insight generation failed: {exc}")
        st.rerun()

st.divider()

# ─── Ingestion history ─────────────────────────────────────────────
st.subheader("Ingestion history")
runs = db.get_ingestion_runs(limit=15)
if runs:
    df = pd.DataFrame(
        [
            {
                "source": r.get("source"),
                "status": r.get("status"),
                "fetched": r.get("records_fetched"),
                "new": r.get("records_new"),
                "started": r.get("started_at"),
                "completed": r.get("completed_at"),
            }
            for r in runs
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No ingestion runs yet.")

st.divider()
if st.button("Refresh status", key="btn_refresh"):
    st.rerun()

render_sidebar_footer()
