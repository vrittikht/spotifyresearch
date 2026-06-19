# Phase 4 — Insight Generation

**Goal:** Aggregate analyzed reviews into themes and a research report answering all 6 research questions.

**Duration:** 4–5 hours · **Depends on:** Phase 3 · **Status:** Complete

## Files in this phase

| File | Purpose |
|------|---------|
| `prompts/synthesis.py` | Prompt 2 — theme synthesis + research answers |
| `services/insight_service.py` | Aggregation, `generate_report()`, theme–review linking |
| `services/groq_service.py` | `synthesize_themes()` — Groq Call #2 |
| `scripts/generate_insights.py` | CLI wrapper |

## Run insight generation

```bash
.venv\Scripts\python.exe scripts/generate_insights.py
```

Optional custom title:

```bash
.venv\Scripts\python.exe scripts/generate_insights.py --title "Spotify Discovery Research — June 2026"
```

## Research answer keys (all required)

- `q1_discovery_struggles`
- `q2_rec_frustrations`
- `q3_listening_behaviors`
- `q4_repeat_listening`
- `q5_segment_differences`
- `q6_unmet_needs`

## Exit criteria

- [x] `generate_insights.py` produces themes + report
- [x] 10–20 themes across multiple categories
- [x] `insight_reports` with all 6 research answers + executive summary
- [x] `theme_reviews` junction populated

## Next

→ [Phase 5 — Streamlit dashboard](../phase_5_dashboard/)
