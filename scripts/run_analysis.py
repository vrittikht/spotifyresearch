#!/usr/bin/env python3
"""CLI: analyze pending reviews with Groq and store results in Supabase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import supabase_client as db
from services.analysis_service import analyze_batch


def _safe_text(text: str, max_len: int = 60) -> str:
    cleaned = (text or "")[:max_len]
    return cleaned.encode("ascii", errors="replace").decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze reviews with Groq (Phase 3)")
    parser.add_argument("--limit", type=int, default=100, help="Max reviews to process (default: 100)")
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Re-process reviews with status=failed instead of pending",
    )
    parser.add_argument(
        "--reset-failed",
        action="store_true",
        help="Reset all failed reviews to pending before running (rate-limit recovery)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print progress per review")
    args = parser.parse_args()

    if args.reset_failed:
        count = db.reset_failed_reviews()
        print(f"Reset {count} failed reviews to pending")

    status_label = "failed" if args.retry else "pending"
    pending = db.get_reviews(status=status_label, limit=args.limit)
    print(f"Found {len(pending)} {status_label} reviews (limit={args.limit})")

    if not pending:
        print("Nothing to analyze.")
        return 0

    def on_progress(result, review, status):
        if args.verbose:
            title = _safe_text(review.get("title") or review.get("body") or "")
            print(f"  [{result.processed}/{len(pending)}] {status}: {title}")

    print("Starting Groq analysis...")
    result = analyze_batch(limit=args.limit, retry=args.retry, on_progress=on_progress if args.verbose else None)

    print(f"\nDone — processed={result.processed}, analyzed={result.analyzed}, "
          f"skipped={result.skipped}, failed={result.failed}, rate_limited={result.rate_limited}")

    if result.stopped_early:
        print("Stopped early due to Groq rate limit. Wait and re-run, or use --reset-failed --retry.")

    stats = db.get_overview_stats()
    by_status = stats.get("by_status", {})
    print(f"DB status counts: {by_status}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors[:10]:
            print(f"  - {err}")

    if result.failed > 0 and not args.retry:
        print("\nTip: re-run with --retry to re-process failed reviews.")

    return 0 if result.failed == 0 or result.completed > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
