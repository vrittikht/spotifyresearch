#!/usr/bin/env python3
"""CLI: run the full research pipeline — collect, analyze, generate insights."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from cli_utils import log_error, log_info
from collectors.normalizer import normalize_reddit_post
from collectors.play_store_scraper import scrape_spotify_reviews
from collectors.reddit_collector import collect_reddit
from services import supabase_client as db
from services.analysis_service import analyze_batch
from services.ingestion_service import ingest_reviews
from services.insight_service import generate_report


def run_collect(reddit_limit: int, playstore_count: int, skip_collect: bool) -> int:
    if skip_collect:
        log_info("Skipping collection (--skip-collect)")
        return 0

    log_info(f"Collecting up to {reddit_limit} Reddit posts (live scrape)...")
    reddit = collect_reddit(scrape=True, limit=reddit_limit)
    normalized = [normalize_reddit_post(p.to_dict()) for p in reddit.posts]
    if normalized:
        ingest = ingest_reviews(normalized, source="reddit")
        log_info(f"Reddit: inserted={ingest.inserted}, skipped={ingest.skipped}")
    else:
        log_info("Reddit: no new posts")

    if playstore_count > 0:
        log_info(f"Scraping up to {playstore_count} Play Store reviews...")
        scraped = scrape_spotify_reviews(count=playstore_count, discovery_only=True)
        if scraped.reviews:
            ingest = ingest_reviews(scraped.reviews, source="play_store")
            log_info(f"Play Store: inserted={ingest.inserted}, skipped={ingest.skipped}")
        else:
            log_info("Play Store: no reviews selected")

    return 0


def run_analyze(limit: int, retry: bool, skip_analyze: bool) -> int:
    if skip_analyze:
        log_info("Skipping analysis (--skip-analyze)")
        return 0

    label = "failed" if retry else "pending"
    pending = db.get_reviews(status=label, limit=limit)
    log_info(f"Analyzing up to {limit} {label} reviews ({len(pending)} found)...")
    if not pending:
        log_info("Nothing to analyze.")
        return 0

    result = analyze_batch(limit=limit, retry=retry)
    log_info(
        f"Analysis done — processed={result.processed}, analyzed={result.analyzed}, "
        f"skipped={result.skipped}, failed={result.failed}"
    )
    if result.stopped_early:
        log_error("Stopped early due to Groq rate limit — re-run later")
    if result.errors:
        for err in result.errors[:5]:
            log_error(err)
    return 0 if not result.failed or result.analyzed > 0 else 1


def run_insights(skip_insights: bool) -> int:
    if skip_insights:
        log_info("Skipping insight generation (--skip-insights)")
        return 0

    relevant = len(db.get_analyses_with_reviews(is_relevant=True))
    log_info(f"Generating insights from {relevant} relevant analyses...")
    if relevant < 10:
        log_error("Need at least 10 relevant analyses")
        return 1

    result = generate_report()
    log_info(
        f"Report {result.report_id} — {result.theme_count} themes, "
        f"{result.linked_reviews} review links"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Spotify discovery research pipeline")
    parser.add_argument("--reddit-limit", type=int, default=50, help="Max Reddit posts to scrape")
    parser.add_argument("--playstore-count", type=int, default=100, help="Play Store reviews (0=skip)")
    parser.add_argument("--analyze-limit", type=int, default=200, help="Max reviews to analyze")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed instead of pending")
    parser.add_argument("--skip-collect", action="store_true")
    parser.add_argument("--skip-analyze", action="store_true")
    parser.add_argument("--skip-insights", action="store_true")
    args = parser.parse_args()

    log_info("=== Phase: Collect ===")
    code = run_collect(args.reddit_limit, args.playstore_count, args.skip_collect)
    if code != 0:
        return code

    log_info("=== Phase: Analyze ===")
    code = run_analyze(args.analyze_limit, args.retry_failed, args.skip_analyze)
    if code != 0:
        return code

    log_info("=== Phase: Generate insights ===")
    return run_insights(args.skip_insights)


if __name__ == "__main__":
    raise SystemExit(main())
