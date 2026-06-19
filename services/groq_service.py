"""Groq API wrapper for review extraction (OpenAI-compatible SDK)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from openai import OpenAI

from prompts.extraction import (
    SYSTEM_INSTRUCTION,
    VALID_SEGMENTS,
    VALID_SENTIMENTS,
    build_user_prompt,
)
from services.config import get_secret
from services.groq_config import DEFAULT_GROQ_MODEL, GROQ_BASE_URL

REQUIRED_FIELDS = ("is_relevant",)
LIST_FIELDS = (
    "pain_points",
    "jobs_to_be_done",
    "discovery_barriers",
    "rec_frustrations",
    "listening_behaviors",
    "repeat_listening_causes",
    "unmet_needs",
)


@lru_cache(maxsize=1)
def get_groq_client() -> OpenAI:
    api_key = get_secret("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in .streamlit/secrets.toml")
    return OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)


def get_model() -> str:
    return get_secret("GROQ_MODEL", DEFAULT_GROQ_MODEL) or DEFAULT_GROQ_MODEL


def _parse_json_content(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _ensure_list(value: Any, field: str) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"{field} must be a list")


def validate_extraction(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize Groq extraction JSON."""
    if not isinstance(data, dict):
        raise ValueError("Extraction response must be a JSON object")

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    is_relevant = bool(data["is_relevant"])
    segment = str(data.get("user_segment") or "unknown")
    if segment not in VALID_SEGMENTS:
        segment = "unknown"

    sentiment = str(data.get("sentiment") or "neutral")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "neutral"

    confidence = data.get("confidence")
    if confidence is None:
        confidence = 0.5 if is_relevant else 0.0
    else:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))

    emotions = data.get("emotions") or []
    if not isinstance(emotions, list):
        emotions = [str(emotions)]

    normalized: dict[str, Any] = {
        "is_relevant": is_relevant,
        "user_segment": segment,
        "sentiment": sentiment,
        "confidence": confidence,
        "emotions": [str(e) for e in emotions],
    }

    for field in LIST_FIELDS:
        normalized[field] = _ensure_list(data.get(field), field)

    return normalized


def minimal_skipped_analysis() -> dict[str, Any]:
    """Minimal analysis row for irrelevant reviews."""
    return {
        "is_relevant": False,
        "pain_points": [],
        "jobs_to_be_done": [],
        "discovery_barriers": [],
        "rec_frustrations": [],
        "listening_behaviors": [],
        "repeat_listening_causes": [],
        "user_segment": "unknown",
        "sentiment": "neutral",
        "emotions": [],
        "unmet_needs": [],
        "confidence": 0.0,
    }


def extract_review(review: dict[str, Any]) -> dict[str, Any]:
    """
    Call Groq to extract structured research signals from a single review.
    Returns validated analysis dict ready for save_analysis().
    """
    client = get_groq_client()
    response = client.chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": build_user_prompt(review)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = response.choices[0].message.content or ""
    if not raw.strip():
        raise ValueError("Empty response from Groq")

    parsed = _parse_json_content(raw)
    return validate_extraction(parsed)


def validate_synthesis(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize Groq synthesis JSON."""
    from prompts.synthesis import RESEARCH_ANSWER_KEYS, VALID_THEME_CATEGORIES

    if not isinstance(data, dict):
        raise ValueError("Synthesis response must be a JSON object")

    themes = data.get("themes") or []
    if not isinstance(themes, list):
        raise ValueError("themes must be a list")

    normalized_themes: list[dict[str, Any]] = []
    for theme in themes:
        if not isinstance(theme, dict):
            continue
        category = str(theme.get("category") or "discovery_barrier")
        if category not in VALID_THEME_CATEGORIES:
            category = "discovery_barrier"
        normalized_themes.append(
            {
                "name": str(theme.get("name") or "Untitled theme"),
                "description": str(theme.get("description") or ""),
                "category": category,
                "review_count_estimate": int(theme.get("review_count_estimate") or 0),
                "example_quotes": theme.get("example_quotes") or [],
                "segment_breakdown": theme.get("segment_breakdown") or {},
                "source_breakdown": theme.get("source_breakdown") or {},
                "avg_sentiment_score": theme.get("avg_sentiment_score"),
            }
        )

    if not normalized_themes:
        raise ValueError("No valid themes in synthesis response")

    research_answers: dict[str, Any] = {}
    raw_answers = data.get("research_answers") or {}
    for key in RESEARCH_ANSWER_KEYS:
        answer = raw_answers.get(key) or {}
        if not isinstance(answer, dict):
            answer = {}
        research_answers[key] = {
            "summary": str(answer.get("summary") or ""),
            "top_themes": answer.get("top_themes") or [],
            "evidence_count": int(answer.get("evidence_count") or 0),
        }

    executive_summary = str(
        data.get("executive_summary")
        or data.get("summary")
        or (raw_answers.get("q1_discovery_struggles") or {}).get("summary")
        or ""
    ).strip()
    if not executive_summary and normalized_themes:
        top_names = ", ".join(t["name"] for t in normalized_themes[:5])
        executive_summary = (
            f"Analysis of {len(normalized_themes)} themes from user feedback. "
            f"Top patterns include: {top_names}."
        )
    if not executive_summary:
        raise ValueError("Missing executive_summary in synthesis response")

    return {
        "themes": normalized_themes,
        "research_answers": research_answers,
        "executive_summary": executive_summary,
    }


def _compact_synthesis_input(data: dict[str, Any]) -> dict[str, Any]:
    """Further shrink input when Groq rejects payload size."""
    compact = dict(data)
    for key in (
        "top_barriers",
        "top_frustrations",
        "top_behaviors",
        "top_repeat_causes",
        "top_unmet_needs",
    ):
        compact[key] = (data.get(key) or [])[:8]
    compact["sample_quotes"] = (data.get("sample_quotes") or [])[:8]
    return compact


def synthesize_themes(synthesis_input: dict[str, Any]) -> dict[str, Any]:
    """Groq Call #2 — theme synthesis and six research answers."""
    from prompts.synthesis import SYSTEM_INSTRUCTION, build_user_prompt

    client = get_groq_client()
    payload = synthesis_input

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=get_model(),
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": build_user_prompt(payload)},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            break
        except Exception as exc:
            err = str(exc)
            if attempt == 0 and ("413" in err or "too large" in err.lower() or "TPM" in err):
                payload = _compact_synthesis_input(synthesis_input)
                continue
            raise

    raw = response.choices[0].message.content or ""
    if not raw.strip():
        raise ValueError("Empty synthesis response from Groq")

    parsed = _parse_json_content(raw)
    return validate_synthesis(parsed)
