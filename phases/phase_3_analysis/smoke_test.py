"""Phase 3 smoke test — analyze a small batch and verify Supabase."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services import supabase_client as db
from services.analysis_service import analyze_batch


def main() -> int:
    print("Phase 3 smoke test\n" + "=" * 40)

    pending_before = len(db.get_reviews(status="pending", limit=1000))
    print(f"Pending reviews: {pending_before}")
    if pending_before == 0:
        print("No pending reviews — run Phase 2 collection first.")
        return 1

    batch_size = min(5, pending_before)
    print(f"\nAnalyzing {batch_size} reviews...")
    result = analyze_batch(limit=batch_size)

    print(f"Result: analyzed={result.analyzed}, skipped={result.skipped}, failed={result.failed}")
    if result.failed > 0:
        print("FAILED: smoke test batch had failures")
        for err in result.errors[:3]:
            print(f"  {err}")
        return 1

    analyses = db.get_analyses_with_reviews(is_relevant=True)
    print(f"Relevant analyses in DB: {len(analyses)}")

    if analyses:
        sample = analyses[0]
        print(f"Sample segment: {sample.get('user_segment')}, sentiment: {sample.get('sentiment')}")

    print("\n" + "=" * 40)
    print("Phase 3 smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
