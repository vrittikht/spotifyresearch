"""Batch orchestration for Groq review analysis."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from services import supabase_client as db
from services.groq_service import extract_review

BATCH_SIZE = 10
BATCH_DELAY_SECONDS = 1.0
RATE_LIMIT_WAIT_SECONDS = 65


@dataclass
class AnalysisResult:
    processed: int = 0
    analyzed: int = 0
    skipped: int = 0
    failed: int = 0
    rate_limited: int = 0
    stopped_early: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def completed(self) -> int:
        return self.analyzed + self.skipped


def is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate_limit" in text or "rate limit" in text


def _parse_retry_seconds(exc: Exception) -> float | None:
    match = re.search(r"try again in (\d+)m([\d.]+)s", str(exc), re.I)
    if match:
        return int(match.group(1)) * 60 + float(match.group(2))
    match = re.search(r"try again in ([\d.]+)s", str(exc), re.I)
    if match:
        return float(match.group(1))
    return None


def analyze_review(review: dict[str, Any]) -> str:
    """
    Analyze a single review. Returns final status: analyzed | skipped | failed.
    """
    review_id = str(review["id"])
    db.update_review_status(review_id, "analyzing")

    try:
        analysis = extract_review(review)
        db.save_analysis(review_id, analysis)

        if analysis.get("is_relevant"):
            db.update_review_status(review_id, "analyzed")
            return "analyzed"

        db.update_review_status(review_id, "skipped")
        return "skipped"

    except Exception as exc:
        db.update_review_status(review_id, "failed")
        raise exc


def analyze_batch(
    limit: int = 100,
    retry: bool = False,
    on_progress: Callable[[AnalysisResult, dict[str, Any], str], None] | None = None,
) -> AnalysisResult:
    """
    Process pending (or failed with --retry) reviews through Groq extraction.

    Rate limiting: BATCH_SIZE reviews per batch, BATCH_DELAY_SECONDS between batches.
    """
    status = "failed" if retry else "pending"
    reviews = db.get_reviews(status=status, limit=limit)
    result = AnalysisResult()

    for index, review in enumerate(reviews):
        review_id = str(review["id"])
        try:
            final_status = analyze_review(review)
            result.processed += 1
            if final_status == "analyzed":
                result.analyzed += 1
            elif final_status == "skipped":
                result.skipped += 1

            if on_progress:
                on_progress(result, review, final_status)

        except Exception as exc:
            if is_rate_limit_error(exc):
                db.update_review_status(review_id, "pending")
                result.rate_limited += 1
                result.stopped_early = True
                wait = _parse_retry_seconds(exc) or RATE_LIMIT_WAIT_SECONDS
                result.errors.append(f"Rate limit hit — stopped batch (wait ~{wait:.0f}s before retry)")
                break

            result.processed += 1
            result.failed += 1
            result.errors.append(f"{review_id}: {exc}")
            if on_progress:
                on_progress(result, review, "failed")

        if result.stopped_early:
            break

        if (index + 1) % BATCH_SIZE == 0 and index + 1 < len(reviews):
            time.sleep(BATCH_DELAY_SECONDS)

    return result
