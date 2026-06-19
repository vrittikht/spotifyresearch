"""Parse Play Store / App Store review CSV files into normalized review records."""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collectors.normalizer import normalize

ENCODINGS = ("utf-8-sig", "utf-8", "latin-1", "cp1252")

# Column name aliases (lowercase) → canonical field
TEXT_COLUMNS = ("review text", "review", "content", "body", "text", "comment", "review_text")
RATING_COLUMNS = ("star rating", "rating", "score", "stars", "star_rating")
DATE_COLUMNS = (
    "review submit date and time",
    "review date",
    "date",
    "at",
    "timestamp",
    "review_submit_date",
    "submitted_at",
)
ID_COLUMNS = ("review id", "review_id", "id", "review link", "review_link")


@dataclass
class CsvImportResult:
    fetched: int
    reviews: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    encoding: str = "utf-8"


def _normalize_header(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _detect_columns(headers: list[str]) -> dict[str, str | None]:
    normalized = {_normalize_header(h): h for h in headers}
    keys = set(normalized)

    def pick(candidates: tuple[str, ...]) -> str | None:
        for candidate in candidates:
            if candidate in keys:
                return normalized[candidate]
        for candidate in candidates:
            for key in keys:
                if candidate in key:
                    return normalized[key]
        return None

    return {
        "text": pick(TEXT_COLUMNS),
        "rating": pick(RATING_COLUMNS),
        "date": pick(DATE_COLUMNS),
        "id": pick(ID_COLUMNS),
    }


def _read_csv_rows(filepath: Path) -> tuple[list[str], list[dict[str, str]], str]:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            with open(filepath, newline="", encoding=encoding) as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("CSV has no header row")
                rows = [dict(row) for row in reader]
                return list(reader.fieldnames), rows, encoding
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    raise ValueError(f"Could not decode {filepath} with {ENCODINGS}") from last_error


def _parse_rating(value: str | None) -> int | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    match = re.search(r"(\d)", text)
    if not match:
        return None
    rating = int(match.group(1))
    return rating if 1 <= rating <= 5 else None


def _parse_date(value: str | None) -> str | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return None


def _make_source_id(source: str, row: dict[str, str], columns: dict[str, str | None], index: int) -> str:
    if columns["id"] and row.get(columns["id"], "").strip():
        raw_id = row[columns["id"]].strip()
        slug = re.sub(r"[^\w-]", "_", raw_id)[:120]
        return slug or f"row_{index}"

    text_col = columns["text"]
    date_col = columns["date"]
    text = (row.get(text_col or "", "") or "").strip()
    date = (row.get(date_col or "", "") or "").strip()
    digest = hashlib.sha256(f"{text}|{date}|{index}".encode()).hexdigest()[:16]
    return f"{source}_{digest}"


def parse_csv(filepath: str | Path, source: str = "play_store") -> CsvImportResult:
    """Parse a CSV file into normalized review dicts (not yet written to Supabase)."""
    if source not in ("play_store", "app_store"):
        raise ValueError(f"Unsupported CSV source: {source}")

    path = Path(filepath)
    if not path.exists():
        return CsvImportResult(fetched=0, errors=[f"File not found: {path}"])

    errors: list[str] = []
    reviews: list[dict[str, Any]] = []

    try:
        headers, rows, encoding = _read_csv_rows(path)
    except ValueError as exc:
        return CsvImportResult(fetched=0, errors=[str(exc)])

    columns = _detect_columns(headers)
    if not columns["text"]:
        return CsvImportResult(
            fetched=0,
            errors=[
                f"Could not find review text column. Headers: {headers}. "
                f"Expected one of: {TEXT_COLUMNS}"
            ],
        )

    for index, row in enumerate(rows):
        text = (row.get(columns["text"] or "", "") or "").strip()
        if not text or len(text) < 10:
            continue

        raw: dict[str, Any] = {
            "source_id": _make_source_id(source, row, columns, index),
            "body": text,
            "title": None,
            "rating": _parse_rating(row.get(columns["rating"] or "", "")),
            "published_at": _parse_date(row.get(columns["date"] or "", "")),
            "metadata": {"csv_row": index + 2, "file": path.name},
        }
        try:
            reviews.append(normalize(raw, source))
        except Exception as exc:
            errors.append(f"Row {index + 2}: {exc}")

    return CsvImportResult(fetched=len(reviews), reviews=reviews, errors=errors, encoding=encoding)


def import_csv(filepath: str | Path, source: str = "play_store") -> CsvImportResult:
    """Parse CSV and return normalized reviews ready for ingestion."""
    return parse_csv(filepath, source=source)
