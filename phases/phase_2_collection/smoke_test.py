"""Phase 2 smoke test — import sample data and verify Supabase counts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services import supabase_client as db

SAMPLE_CSV = ROOT / "phases" / "phase_2_collection" / "sample_data" / "play_store_reviews.csv"
SAMPLE_HTML = ROOT / "phases" / "phase_2_collection" / "sample_data" / "reddit_html"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def run_script(args: list[str]) -> None:
    cmd = [str(PYTHON), *args]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}")


def main() -> int:
    print("Phase 2 smoke test\n" + "=" * 40)

    if not PYTHON.exists():
        print(f"Missing venv Python at {PYTHON}")
        return 1

    before = db.get_overview_stats()
    print(f"Before: total_reviews={before['total_reviews']}")

    print("\n1. Import Play Store sample CSV...")
    run_script(
        [
            "scripts/import_csv.py",
            "--source",
            "play_store",
            "--file",
            str(SAMPLE_CSV),
        ]
    )

    print("\n2. Import Reddit sample HTML...")
    run_script(
        [
            "scripts/collect_reddit.py",
            "--html-dir",
            str(SAMPLE_HTML),
            "--limit",
            "100",
        ]
    )

    print("\n3. Dedup check (re-run imports)...")
    run_script(["scripts/import_csv.py", "--source", "play_store", "--file", str(SAMPLE_CSV)])
    run_script(["scripts/collect_reddit.py", "--html-dir", str(SAMPLE_HTML), "--limit", "100"])

    after = db.get_overview_stats()
    runs = db.get_ingestion_runs(limit=5)
    pending = db.get_reviews(status="pending", limit=1000)

    print("\n4. Verify counts...")
    print(f"   total_reviews={after['total_reviews']}")
    print(f"   by_source={after['by_source']}")
    print(f"   pending={len(pending)}")
    print(f"   recent_runs={len(runs)}")

    reddit_count = after["by_source"].get("reddit", 0)
    play_count = after["by_source"].get("play_store", 0)

    if after["total_reviews"] < 50:
        print(f"\nFAILED: expected 50+ reviews, got {after['total_reviews']}")
        return 1
    if reddit_count < 1 or play_count < 1:
        print(f"\nFAILED: need both sources (reddit={reddit_count}, play_store={play_count})")
        return 1
    if len(runs) < 2:
        print("\nFAILED: expected ingestion runs to be logged")
        return 1

    print("\n" + "=" * 40)
    print("All Phase 2 checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
