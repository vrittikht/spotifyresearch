#!/usr/bin/env python3
"""CLI: collect Reddit posts and ingest into Supabase (no Reddit API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.normalizer import normalize_reddit_post
from collectors.reddit_collector import (
    DEFAULT_KEYWORDS,
    DEFAULT_SUBREDDITS,
    RedditPublicCollector,
    collect_reddit,
)
from services.config import get_secret
from services.ingestion_service import ingest_reviews


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect Reddit posts from public pages and ingest into Supabase"
    )
    parser.add_argument(
        "--subreddits",
        nargs="+",
        default=DEFAULT_SUBREDDITS,
        help="Target subreddits (default: spotify truespotify)",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=DEFAULT_KEYWORDS,
        help="Search keywords",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max unique posts to collect (default: 100)",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        help="Import from manually saved HTML files (offline fallback)",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Live scrape real Reddit data via RSS + old.reddit HTML (default when no --html-dir)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Legacy live HTML mode (prefer --scrape)",
    )
    parser.add_argument(
        "--print-urls",
        action="store_true",
        help="Print search URLs to open manually in a browser",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only — do not write to Supabase",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output file",
    )
    args = parser.parse_args()

    user_agent = get_secret("REDDIT_USER_AGENT", "spotify-research-collector/1.0")

    if args.print_urls:
        collector = RedditPublicCollector(user_agent=user_agent)
        print("Open these URLs in your browser, then save each page as HTML:")
        for sub in args.subreddits:
            for kw in args.keywords:
                print(collector.build_search_url(sub, kw))
        print("\nSave files to: data/reddit_html/{subreddit}_{keyword}.html")
        print("Then run: python scripts/collect_reddit.py --html-dir data/reddit_html")
        return 0

    html_dir = args.html_dir
    use_scrape = args.scrape or (html_dir is None and not args.live and not args.print_urls)

    if html_dir is None and not args.scrape and not args.live:
        default_dir = ROOT / "data" / "reddit_html"
        if default_dir.exists() and list(default_dir.glob("*.html")):
            html_dir = default_dir
            use_scrape = False

    result = collect_reddit(
        subreddits=args.subreddits,
        keywords=args.keywords,
        limit_per_search=args.limit,
        html_dir=html_dir,
        live=args.live,
        scrape=use_scrape and html_dir is None,
        user_agent=user_agent,
        limit=args.limit,
    )

    if result.warnings:
        print("Notes:")
        for note in result.warnings:
            print(f"  {note}")

    normalized = [normalize_reddit_post(p.to_dict()) for p in result.posts]

    print(f"Fetched: {result.fetched} | Unique posts: {result.unique}")
    if result.errors:
        print(f"Errors ({len(result.errors)}):")
        for err in result.errors[:5]:
            print(f"  - {err}")

    if args.output and normalized:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(normalized, indent=2, default=str), encoding="utf-8")
        print(f"Saved {len(normalized)} posts to {args.output}")

    if not normalized:
        if not args.live and not html_dir and not use_scrape:
            print("Run with --scrape for live data or --print-urls for manual collection.")
        return 0 if not result.errors else 1

    if args.dry_run:
        print(f"Dry run — would ingest {len(normalized)} reviews")
        print(f"Sample: {normalized[0]['title'][:80] if normalized[0].get('title') else normalized[0]['body'][:80]}")
        return 0

    ingest = ingest_reviews(normalized, source="reddit")
    print(f"Ingestion run {ingest.run_id}: inserted={ingest.inserted}, skipped={ingest.skipped}")
    if ingest.errors:
        print(f"Ingestion errors ({len(ingest.errors)}):")
        for err in ingest.errors[:5]:
            print(f"  - {err}")
        return 1

    if normalized:
        title = normalized[0].get("title") or normalized[0]["body"]
        print(f"Sample: {title[:80]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
