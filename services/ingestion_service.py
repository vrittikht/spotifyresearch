"""Ingest normalized reviews into Supabase with dedup and run tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

from services import supabase_client as db


@dataclass
class IngestResult:
    run_id: str
    source: str
    fetched: int
    inserted: int
    skipped: int
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.errors or self.inserted > 0 or self.skipped > 0


def ingest_reviews(reviews: list[dict], source: str) -> IngestResult:
    """
    Upsert reviews into Supabase, skipping duplicates on (source, source_id).
    Creates and completes an ingestion_runs record.
    """
    if source not in db.INGESTION_SOURCES:
        raise ValueError(f"Invalid source: {source}")

    run_id = db.create_ingestion_run(source)
    inserted = 0
    skipped = 0
    errors: list[str] = []

    for review in reviews:
        try:
            payload = {**review, "source": review.get("source", source), "ingestion_run_id": run_id}
            _, is_new = db.upsert_review(payload)
            if is_new:
                inserted += 1
            else:
                skipped += 1
        except Exception as exc:
            sid = review.get("source_id", "?")
            errors.append(f"{source_id_label(source, sid)}: {exc}")

    try:
        db.complete_ingestion_run(
            run_id,
            records_fetched=len(reviews),
            records_new=inserted,
            error="; ".join(errors[:3]) if errors and inserted == 0 and skipped == 0 else None,
        )
    except Exception as exc:
        errors.append(f"Failed to complete ingestion run: {exc}")

    return IngestResult(
        run_id=run_id,
        source=source,
        fetched=len(reviews),
        inserted=inserted,
        skipped=skipped,
        errors=errors,
    )


def source_id_label(source: str, source_id: str) -> str:
    return f"{source}:{source_id}"
