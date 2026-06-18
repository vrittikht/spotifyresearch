#!/usr/bin/env python3
"""CLI: collect Reddit posts from public pages (no Reddit API)."""

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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Reddit posts from public pages (no Reddit API)"
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
        default=15,
        help="Max posts per subreddit+keyword search (live mode only)",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        help="Import from manually saved HTML files (recommended; respects robots.txt)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt live fetch (usually blocked by Reddit robots.txt)",
    )
    parser.add_argument(
        "--print-urls",
        action="store_true",
        help="Print search URLs to open manually in a browser",
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
        return

    result = collect_reddit(
        subreddits=args.subreddits,
        keywords=args.keywords,
        limit_per_search=args.limit,
        html_dir=args.html_dir,
        live=args.live,
        user_agent=user_agent,
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
    elif normalized:
        print(f"Sample: {normalized[0]['title'][:80]}")
    elif not args.live and not args.html_dir:
        print("Run with --print-urls for manual collection instructions.")


if __name__ == "__main__":
    main()
