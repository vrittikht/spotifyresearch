#!/usr/bin/env python3
"""CLI: scrape real Spotify Play Store reviews and ingest into Supabase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.play_store_scraper import scrape_spotify_reviews
from services.ingestion_service import ingest_reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape real Spotify Play Store reviews")
    parser.add_argument("--count", type=int, default=500, help="Max reviews to fetch (default: 500)")
    parser.add_argument(
        "--sort",
        choices=["newest", "rating", "relevant"],
        default="newest",
        help="Play Store sort order",
    )
    parser.add_argument(
        "--all-reviews",
        action="store_true",
        help="Skip discovery keyword filter (import all fetched reviews)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch only — do not write to Supabase")
    args = parser.parse_args()

    print(f"Fetching up to {args.count} real Play Store reviews for com.spotify.music...")
    result = scrape_spotify_reviews(
        count=args.count,
        sort=args.sort,
        discovery_only=not args.all_reviews,
    )

    print(f"Fetched: {result.fetched} | Selected: {result.filtered}")
    if result.errors:
        for err in result.errors:
            print(f"  Error: {err}")
        if not result.reviews:
            return 1

    if not result.reviews:
        print("No reviews matched. Try --all-reviews or increase --count.")
        return 1

    sample = result.reviews[0]["body"][:100]
    print(f"Sample: {sample}")

    if args.dry_run:
        print(f"Dry run — would ingest {len(result.reviews)} reviews")
        return 0

    ingest = ingest_reviews(result.reviews, source="play_store")
    print(f"Ingestion run {ingest.run_id}: inserted={ingest.inserted}, skipped={ingest.skipped}")
    return 0 if not ingest.errors or ingest.inserted > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
