# Phase 3 — Groq Analysis

**Goal:** Analyze pending reviews with Groq; store structured JSON in the `analysis` table.

**Duration:** 5–6 hours · **Depends on:** Phase 2 · **Status:** Complete

## Files in this phase

| File | Purpose |
|------|---------|
| `prompts/extraction.py` | System instruction + user prompt template |
| `services/groq_service.py` | `extract_review()` — Groq API + JSON validation |
| `services/analysis_service.py` | `analyze_batch()` — batch orchestration + status lifecycle |
| `scripts/run_analysis.py` | CLI wrapper |

## Run analysis

```bash
# Analyze up to 100 pending reviews
.venv\Scripts\python.exe scripts/run_analysis.py --limit 100 --verbose

# Process all pending reviews
.venv\Scripts\python.exe scripts/run_analysis.py --limit 300 --verbose

# Retry failed reviews
.venv\Scripts\python.exe scripts/run_analysis.py --limit 50 --retry
```

## Analysis flow (per review)

1. Fetch review where `status = pending`
2. Set `status = analyzing`
3. Call `groq_service.extract_review(review)`
4. If `is_relevant = false` → `status = skipped`, save analysis
5. If `is_relevant = true` → `status = analyzed`, save full analysis
6. On exception → `status = failed`

Rate limiting: batches of 10, 1-second delay between batches. On Groq **429 rate limit**, the batch stops early and remaining reviews stay `pending` (use `--reset-failed` if older runs marked them `failed`).

## Groq token limits

Free tier has a daily token cap (~100k TPD for `llama-3.3-70b-versatile`). If you hit the limit:

```bash
# Wait for reset (usually next day), then:
.venv\Scripts\python.exe scripts/run_analysis.py --reset-failed --limit 200
```

Consider `GROQ_MODEL = "llama-3.1-8b-instant"` (default) for higher daily volume; use `llama-3.3-70b-versatile` for higher quality.

## Exit criteria

- [x] `run_analysis.py --limit 100` completes without crashing
- [x] 100+ reviews with status `analyzed` or `skipped`
- [x] Relevant reviews have barriers, frustrations, segment, sentiment
- [x] Irrelevant reviews marked `skipped`
- [x] All pending reviews processed with `llama-3.1-8b-instant`

## Next

→ [Phase 4 — Insight generation](../phase_4_insights/)
