"""Phase 4 smoke test — generate report and verify Supabase."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prompts.synthesis import RESEARCH_ANSWER_KEYS
from services import supabase_client as db
from services.insight_service import prepare_synthesis_input


def main() -> int:
    print("Phase 4 smoke test\n" + "=" * 40)

    analyses = db.get_analyses_with_reviews(is_relevant=True)
    print(f"Relevant analyses: {len(analyses)}")
    if len(analyses) < 10:
        print("Need at least 10 relevant analyses.")
        return 1

    prepared = prepare_synthesis_input(analyses)
    assert prepared["total_relevant"] == len(analyses)
    assert prepared["sample_quotes"]
    print(f"Sample quotes prepared: {len(prepared['sample_quotes'])}")

    report = db.get_latest_report()
    themes = db.get_themes()
    if not report or not themes:
        print("No report/themes yet — run: python scripts/generate_insights.py")
        return 1

    answers = report.get("research_answers") or {}
    missing = [k for k in RESEARCH_ANSWER_KEYS if k not in answers]
    if missing:
        print(f"Missing research answers: {missing}")
        return 1

    print(f"Themes: {len(themes)}")
    print(f"Report: {report.get('title')}")
    print("\n" + "=" * 40)
    print("Phase 4 smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
