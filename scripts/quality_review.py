#!/usr/bin/env python3
"""Spot-check random analyses for Phase 7 quality review."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services import supabase_client as db


def _safe_text(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality review — spot-check analyses and themes")
    parser.add_argument("--sample", type=int, default=10, help="Number of analyses to spot-check")
    args = parser.parse_args()

    analyses = db.get_analyses_with_reviews(is_relevant=True)
    themes = db.get_themes()
    stats = db.get_overview_stats()

    print("=== Dataset ===")
    print(f"Total reviews:    {stats.get('total_reviews', 0)}")
    print(f"Relevant:         {stats.get('relevant_reviews', 0)}")
    print(f"Themes:           {len(themes)}")
    print(f"Target (Phase 7): 300+ reviews, 250+ relevant, 10+ themes")

    ok = (
        stats.get("total_reviews", 0) >= 300
        and stats.get("relevant_reviews", 0) >= 250
        and len(themes) >= 10
    )
    print(f"Exit criteria:    {'PASS' if ok else 'NEEDS WORK'}")
    print()

    if not analyses:
        print("No analyses to review.")
        return 1

    sample = random.sample(analyses, min(args.sample, len(analyses)))
    print(f"=== Spot-check ({len(sample)} analyses) ===")
    for i, row in enumerate(sample, 1):
        review = row.get("reviews") or {}
        body = _safe_text((review.get("body") or "")[:100])
        print(f"\n{i}. [{row.get('sentiment')}] {row.get('user_segment')}")
        print(f"   {body}...")
        barriers = row.get("discovery_barriers") or []
        if barriers and isinstance(barriers[0], dict):
            print(f"   Barrier: {_safe_text(str(barriers[0].get('barrier', ''))[:80])}")

    print("\n=== Top themes ===")
    for t in themes[:5]:
        print(f"- {t.get('name')} ({t.get('review_count')} reviews) — {t.get('category')}")

    report = db.get_latest_report()
    if report:
        answers = report.get("research_answers") or {}
        print(f"\n=== Report ===")
        print(f"Title: {report.get('title')}")
        print(f"Research answers: {len(answers)}/6")
    else:
        print("\nNo insight report found.")
        return 1

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
