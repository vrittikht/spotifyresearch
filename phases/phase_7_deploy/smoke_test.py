"""Phase 7 smoke test — verify deploy readiness and exit criteria."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prompts.synthesis import RESEARCH_ANSWER_KEYS
from components.report_helpers import enrich_research_answers
from services import supabase_client as db


def main() -> int:
    print("Phase 7 deploy readiness\n" + "=" * 40)

    stats = db.get_overview_stats()
    themes = db.get_themes()
    report = db.get_latest_report()

    checks = [
        ("300+ reviews", stats.get("total_reviews", 0) >= 300),
        ("250+ relevant", stats.get("relevant_reviews", 0) >= 250),
        ("10+ themes", len(themes) >= 10),
        ("Report exists", report is not None),
    ]

    for label, passed in checks:
        print(f"  [{'OK' if passed else 'FAIL'}] {label}")

    if report:
        enriched = enrich_research_answers(
            report, themes, stats.get("relevant_reviews", 0), db.get_segment_breakdown()
        )
        missing = [k for k in RESEARCH_ANSWER_KEYS if not enriched.get(k, {}).get("summary")]
        print(f"  [{'OK' if not missing else 'WARN'}] 6 research answers ({len(RESEARCH_ANSWER_KEYS) - len(missing)}/6 with summary)")

    files = [
        ROOT / "app.py",
        ROOT / "requirements.txt",
        ROOT / ".streamlit" / "secrets.toml.example",
    ]
    for f in files:
        print(f"  [{'OK' if f.exists() else 'FAIL'}] {f.name}")

    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        print("  [WARN] secrets.toml exists locally — must stay gitignored")

    all_pass = all(p for _, p in checks)
    print("\n" + "=" * 40)
    print("Ready to deploy." if all_pass else "Fix failing checks before deploy.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
