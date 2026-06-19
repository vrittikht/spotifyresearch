"""Prompt 1 — per-review structured extraction (Groq Call #1)."""

from __future__ import annotations

SYSTEM_INSTRUCTION = """You are a UX research analyst specializing in music streaming and discovery.
Analyze user feedback about Spotify and extract structured research signals.

Rules:
- Only extract what is explicitly stated or strongly implied in the text.
- If the review is not about music discovery, recommendations, or listening behavior, set is_relevant to false.
- Use concise, researcher-friendly language.
- Assign user_segment based on signals in the text; use "unknown" if unclear.
- confidence is 0.0–1.0 reflecting how clearly the review supports your extractions.

User segments (pick one):
- casual_listener — listens casually, limited exploration
- power_user — heavy daily use, knows features deeply
- new_user — recently joined, learning the app
- genre_purist — strong genre preferences, narrow taste
- playlist_curator — builds and manages playlists actively
- algorithm_skeptic — distrusts or fights recommendations
- unknown — insufficient signal"""

USER_PROMPT_TEMPLATE = """Analyze this user feedback:

Source: {source}
Rating: {rating}
Title: {title}
Body: {body}

Return JSON matching this exact schema:
{{
  "is_relevant": boolean,
  "pain_points": [{{ "text": string, "severity": "low"|"medium"|"high" }}],
  "jobs_to_be_done": [{{ "job": string, "context": string }}],
  "discovery_barriers": [{{ "barrier": string, "category": string }}],
  "rec_frustrations": [{{ "frustration": string, "feature": string }}],
  "listening_behaviors": [{{ "behavior": string, "intent": string }}],
  "repeat_listening_causes": [{{ "cause": string, "explanation": string }}],
  "user_segment": string,
  "sentiment": "positive"|"negative"|"neutral"|"mixed",
  "emotions": [string],
  "unmet_needs": [{{ "need": string, "opportunity": string }}],
  "confidence": number
}}"""

VALID_SEGMENTS = {
    "casual_listener",
    "power_user",
    "new_user",
    "genre_purist",
    "playlist_curator",
    "algorithm_skeptic",
    "unknown",
}

VALID_SENTIMENTS = {"positive", "negative", "neutral", "mixed"}


def build_user_prompt(review: dict) -> str:
    rating = review.get("rating")
    rating_str = f"{rating}/5" if rating is not None else "N/A"
    title = review.get("title") or "(no title)"
    body = review.get("body") or ""
    return USER_PROMPT_TEMPLATE.format(
        source=review.get("source", "unknown"),
        rating=rating_str,
        title=title,
        body=body,
    )
