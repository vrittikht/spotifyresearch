"""Enrich research report answers from themes when Groq synthesis left them empty."""

from __future__ import annotations

from typing import Any

from components.constants import RESEARCH_QUESTIONS

QUESTION_CATEGORY_MAP: dict[str, str | None] = {
    "q1_discovery_struggles": "discovery_barrier",
    "q2_rec_frustrations": "rec_frustration",
    "q3_listening_behaviors": "listening_behavior",
    "q4_repeat_listening": "repeat_listening",
    "q5_segment_differences": "segment_insight",
    "q6_unmet_needs": "unmet_need",
}


def _themes_for_category(themes: list[dict[str, Any]], category: str | None) -> list[dict[str, Any]]:
    if category is None:
        return themes
    matched = [t for t in themes if t.get("category") == category]
    return matched if matched else themes


def _build_summary(themes: list[dict[str, Any]], fallback: str) -> str:
    descriptions = [str(t.get("description") or "").strip() for t in themes[:3] if t.get("description")]
    if descriptions:
        return " ".join(descriptions)
    return fallback


def enrich_research_answers(
    report: dict[str, Any],
    themes: list[dict[str, Any]],
    total_relevant: int,
    segments: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Fill empty summaries, theme lists, and evidence counts from stored themes."""
    stored = report.get("research_answers") or {}
    enriched: dict[str, dict[str, Any]] = {}

    for key in RESEARCH_QUESTIONS:
        answer = dict(stored.get(key) or {})
        category = QUESTION_CATEGORY_MAP.get(key)
        matching = _themes_for_category(themes, category)
        theme_names = [str(t.get("name") or "") for t in matching if t.get("name")]
        evidence = sum(
            int(t.get("review_count") or t.get("review_count_estimate") or 0) for t in matching
        )

        if key == "q5_segment_differences" and segments:
            if not answer.get("summary"):
                seg_lines = [
                    f"{s['segment'].replace('_', ' ').title()} ({s['count']} reviews)"
                    for s in segments[:5]
                ]
                answer["summary"] = (
                    f"Analysis spans {len(segments)} user segments. "
                    f"Largest groups: {', '.join(seg_lines)}."
                )
            if not answer.get("evidence_count"):
                answer["evidence_count"] = total_relevant
            if not answer.get("top_themes"):
                answer["top_themes"] = [
                    s["segment"].replace("_", " ").title() for s in segments[:3]
                ]
        else:
            if not answer.get("summary"):
                answer["summary"] = _build_summary(
                    matching,
                    f"Findings drawn from {len(matching)} theme(s) across user feedback.",
                )
            if not answer.get("evidence_count") and evidence:
                answer["evidence_count"] = evidence
            elif not answer.get("evidence_count") and total_relevant:
                answer["evidence_count"] = max(1, total_relevant // max(len(RESEARCH_QUESTIONS), 1))
            if not answer.get("top_themes") and theme_names:
                answer["top_themes"] = theme_names[:3]

        enriched[key] = answer

    return enriched
