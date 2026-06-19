#!/usr/bin/env python3
"""CLI: generate themes and research report from analyzed reviews (Phase 4)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from prompts.synthesis import RESEARCH_ANSWER_KEYS
from services import supabase_client as db
from services.insight_service import generate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate insight themes and research report")
    parser.add_argument("--title", help="Custom report title")
    args = parser.parse_args()

    relevant = len(db.get_analyses_with_reviews(is_relevant=True))
    print(f"Relevant analyses available: {relevant}")
    if relevant < 10:
        print("Need at least 10 relevant analyses. Run Phase 3 first.")
        return 1

    print("Running Groq synthesis (this may take 30–60 seconds)...")
    result = generate_report(title=args.title)

    report = db.get_latest_report()
    themes = db.get_themes()

    print(f"\nReport ID: {result.report_id}")
    print(f"Themes saved: {result.theme_count}")
    print(f"Reviews linked to themes: {result.linked_reviews}")

    if report:
        answers = report.get("research_answers") or {}
        missing = [k for k in RESEARCH_ANSWER_KEYS if k not in answers]
        print(f"Research answers: {len(answers)}/{len(RESEARCH_ANSWER_KEYS)}")
        if missing:
            print(f"  Missing keys: {missing}")
            return 1

        summary = (report.get("content") or {}).get("executive_summary", "")
        if summary:
            print(f"\nExecutive summary preview:\n{summary[:400]}...")

    categories = {t.get("category") for t in themes}
    print(f"\nTheme categories: {', '.join(sorted(categories))}")
    print(f"Total themes in DB: {len(themes)}")

    if result.theme_count < 10:
        print("Warning: fewer than 10 themes generated.")
        return 1

    print("\nPhase 4 insight generation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
