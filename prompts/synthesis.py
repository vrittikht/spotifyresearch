"""Prompt 2 — theme synthesis and research report (Groq Call #2)."""

from __future__ import annotations

import json

SYSTEM_INSTRUCTION = """You are a senior product researcher at Spotify preparing a discovery research brief.
Given aggregated analysis data from hundreds of user reviews, synthesize patterns into
clear themes and answer six research questions with evidence-backed summaries.

Rules:
- Every theme must be grounded in the frequency data provided.
- Include 2–3 verbatim user quotes per theme from the sample_quotes provided.
- Rank themes by frequency × severity.
- Be specific — name actual Spotify features (Discover Weekly, Daily Mix, Radio, etc.) when data supports it.
- Write for a PM audience: clear, concise, actionable.
- Produce 10–20 themes across multiple categories."""

USER_PROMPT_TEMPLATE = """Here is aggregated research data from {total_relevant} discovery-relevant user reviews:

SEGMENT BREAKDOWN:      {by_segment}
SOURCE BREAKDOWN:       {by_source}
TOP DISCOVERY BARRIERS: {top_barriers}
TOP REC FRUSTRATIONS:   {top_frustrations}
TOP LISTENING BEHAVIORS: {top_behaviors}
TOP REPEAT-LISTENING CAUSES: {top_repeat_causes}
TOP UNMET NEEDS:        {top_unmet_needs}
SENTIMENT DISTRIBUTION: {sentiment_distribution}
SAMPLE USER QUOTES:     {sample_quotes}

Return JSON matching this schema:
{{
  "themes": [{{
    "name": string,
    "description": string,
    "category": "discovery_barrier"|"rec_frustration"|"listening_behavior"|"repeat_listening"|"unmet_need"|"segment_insight",
    "review_count_estimate": number,
    "example_quotes": [{{ "quote": string, "source": string }}],
    "segment_breakdown": {{ "segment_name": number }},
    "source_breakdown": {{ "source_name": number }},
    "avg_sentiment_score": number
  }}],
  "research_answers": {{
    "q1_discovery_struggles":  {{ "summary": string, "top_themes": [string], "evidence_count": number }},
    "q2_rec_frustrations":     {{ "summary": string, "top_themes": [string], "evidence_count": number }},
    "q3_listening_behaviors":  {{ "summary": string, "top_themes": [string], "evidence_count": number }},
    "q4_repeat_listening":     {{ "summary": string, "top_themes": [string], "evidence_count": number }},
    "q5_segment_differences":  {{ "summary": string, "top_themes": [string], "evidence_count": number }},
    "q6_unmet_needs":          {{ "summary": string, "top_themes": [string], "evidence_count": number }}
  }},
  "executive_summary": string
}}"""

RESEARCH_ANSWER_KEYS = (
    "q1_discovery_struggles",
    "q2_rec_frustrations",
    "q3_listening_behaviors",
    "q4_repeat_listening",
    "q5_segment_differences",
    "q6_unmet_needs",
)

VALID_THEME_CATEGORIES = {
    "discovery_barrier",
    "rec_frustration",
    "listening_behavior",
    "repeat_listening",
    "unmet_need",
    "segment_insight",
}

FIELD_TEXT_KEYS = {
    "discovery_barriers": "barrier",
    "rec_frustrations": "frustration",
    "listening_behaviors": "behavior",
    "repeat_listening_causes": "cause",
    "unmet_needs": "need",
    "pain_points": "text",
}


def build_user_prompt(synthesis_input: dict) -> str:
    def fmt(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    return USER_PROMPT_TEMPLATE.format(
        total_relevant=synthesis_input.get("total_relevant", 0),
        by_segment=fmt(synthesis_input.get("by_segment", {})),
        by_source=fmt(synthesis_input.get("by_source", {})),
        top_barriers=fmt(synthesis_input.get("top_barriers", [])),
        top_frustrations=fmt(synthesis_input.get("top_frustrations", [])),
        top_behaviors=fmt(synthesis_input.get("top_behaviors", [])),
        top_repeat_causes=fmt(synthesis_input.get("top_repeat_causes", [])),
        top_unmet_needs=fmt(synthesis_input.get("top_unmet_needs", [])),
        sentiment_distribution=fmt(synthesis_input.get("sentiment_distribution", {})),
        sample_quotes=fmt(synthesis_input.get("sample_quotes", [])),
    )
