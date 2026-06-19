"""Phase 1 smoke test — run from repo root: python phases/phase_1_database/smoke_test.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services import supabase_client as db


def main() -> int:
    print("Phase 1 smoke test\n" + "=" * 40)

    test_review = {
        "source": "reddit",
        "source_id": "phase1_smoke_test_001",
        "title": "Phase 1 smoke test",
        "body": "Discover Weekly keeps playing the same songs every week.",
        "metadata": {"subreddit": "spotify", "test": True},
        "status": "pending",
    }

    review_id: str | None = None
    run_id: str | None = None

    try:
        print("\n1. Insert test review...")
        review_id, is_new = db.upsert_review(test_review)
        assert is_new, "Expected new review on first insert"
        print(f"   OK — inserted {review_id}")

        print("\n2. Read review back...")
        row = db.get_review_by_source("reddit", test_review["source_id"])
        assert row and row["body"] == test_review["body"]
        print(f"   OK — body matches")

        print("\n3. Dedup check...")
        _, is_new_again = db.upsert_review(test_review)
        assert not is_new_again, "Duplicate should be skipped"
        print("   OK — duplicate skipped")

        print("\n4. Ingestion run...")
        run_id = db.create_ingestion_run("reddit")
        db.complete_ingestion_run(run_id, records_fetched=1, records_new=1)
        runs = db.get_ingestion_runs(limit=1)
        assert runs and runs[0]["status"] == "completed"
        print(f"   OK — run {run_id} completed")

        print("\n5. Overview stats...")
        stats = db.get_overview_stats()
        assert "total_reviews" in stats
        print(f"   OK — total_reviews={stats['total_reviews']}, themes={stats['total_themes']}")

        print("\n" + "=" * 40)
        print("All Phase 1 checks passed.")
        return 0

    except Exception as exc:
        print(f"\nFAILED: {exc}")
        print("\nIf tables are missing, run supabase/migrations/001_initial.sql in Supabase SQL Editor.")
        return 1

    finally:
        if review_id:
            try:
                db.delete_review(review_id)
                print("\nCleaned up test review.")
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
