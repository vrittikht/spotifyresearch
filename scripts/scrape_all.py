#!/usr/bin/env python3
"""CLI: scrape real Reddit + Play Store data and ingest into Supabase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.normalizer import normalize_reddit_post
from collectors.play_store_scraper import scrape_spotify_reviews
from collectors.reddit_collector import DEFAULT_KEYWORDS, DEFAULT_SUBREDDITS, collect_reddit
from services.ingestion_service import ingest_reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape real Reddit + Play Store data into Supabase")
    parser.add_argument("--reddit-limit", type=int, default=150, help="Max Reddit posts (default: 150)")
    parser.add_argument("--playstore-count", type=int, default=500, help="Max Play Store reviews to fetch")
    parser.add_argument("--subreddits", nargs="+", default=DEFAULT_SUBREDDITS)
    parser.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    parser.add_argument("--reddit-only", action="store_true")
    parser.add_argument("--playstore-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    scrape_reddit = not args.playstore_only
    scrape_playstore = not args.reddit_only
    exit_code = 0

    if scrape_reddit:
        print(f"\n=== Reddit (live scrape, limit={args.reddit_limit}) ===")
        result = collect_reddit(
            subreddits=args.subreddits,
            keywords=args.keywords,
            scrape=True,
            limit=args.reddit_limit,
        )
        for note in result.warnings:
            print(f"  {note}")
        normalized = [normalize_reddit_post(p.to_dict()) for p in result.posts]
        print(f"Fetched: {result.fetched} | Unique: {result.unique}")
        if result.errors:
            for err in result.errors[:5]:
                print(f"  Error: {err}")

        if normalized:
            if args.dry_run:
                print(f"Dry run — would ingest {len(normalized)} Reddit posts")
            else:
                ingest = ingest_reviews(normalized, source="reddit")
                print(f"Reddit ingestion: inserted={ingest.inserted}, skipped={ingest.skipped}")
                if ingest.errors:
                    exit_code = 1
        else:
            print("No Reddit posts collected.")
            exit_code = 1

    if scrape_playstore:
        print(f"\n=== Play Store (live scrape, count={args.playstore_count}) ===")
        ps = scrape_spotify_reviews(count=args.playstore_count)
        print(f"Fetched: {ps.fetched} | Selected: {ps.filtered}")
        if ps.errors:
            for err in ps.errors:
                print(f"  Error: {err}")

        if ps.reviews:
            if args.dry_run:
                print(f"Dry run — would ingest {len(ps.reviews)} Play Store reviews")
            else:
                ingest = ingest_reviews(ps.reviews, source="play_store")
                print(f"Play Store ingestion: inserted={ingest.inserted}, skipped={ingest.skipped}")
                if ingest.errors:
                    exit_code = 1
        else:
            print("No Play Store reviews collected.")
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
