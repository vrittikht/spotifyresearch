#!/usr/bin/env python3
"""CLI: import Play Store / App Store review CSV into Supabase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.csv_importer import import_csv
from services.ingestion_service import ingest_reviews


def main() -> int:
    parser = argparse.ArgumentParser(description="Import review CSV into Supabase")
    parser.add_argument(
        "--source",
        required=True,
        choices=["play_store", "app_store"],
        help="Review source type",
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="Path to CSV file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only — do not write to Supabase",
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}")
        return 1

    parsed = import_csv(args.file, source=args.source)
    print(f"Parsed {parsed.fetched} reviews from {args.file.name} (encoding: {parsed.encoding})")

    if parsed.errors:
        print(f"Parse warnings ({len(parsed.errors)}):")
        for err in parsed.errors[:5]:
            print(f"  - {err}")

    if not parsed.reviews:
        print("No reviews to import.")
        return 1

    if args.dry_run:
        sample = parsed.reviews[0]["body"][:80]
        print(f"Dry run — would ingest {len(parsed.reviews)} reviews")
        print(f"Sample: {sample}")
        return 0

    ingest = ingest_reviews(parsed.reviews, source=args.source)
    print(f"Ingestion run {ingest.run_id}: inserted={ingest.inserted}, skipped={ingest.skipped}")
    if ingest.errors:
        print(f"Ingestion errors ({len(ingest.errors)}):")
        for err in ingest.errors[:5]:
            print(f"  - {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
