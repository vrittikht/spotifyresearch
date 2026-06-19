# Phase 6 — Admin & CLI

**Goal:** Run the full pipeline from the Admin page and CLI scripts.

**Duration:** 3–4 hours · **Depends on:** Phase 5 · **Status:** Complete

## Admin page

Open **Admin** in the Streamlit sidebar (`pages/5_Admin.py`):

| Section | Actions |
|---------|---------|
| **Pipeline status** | Total, analyzed, pending, skipped, failed |
| **1. Collect** | Reddit scrape, Play Store scrape, CSV upload |
| **2. Analyze** | Run analysis (pending), retry failed — with progress bar |
| **3. Insights** | Generate research report |
| **History** | Recent `ingestion_runs` table |

Batch limit on Admin UI: **50** per action (Streamlit Cloud safe).

## CLI scripts

```bash
# Individual stages
.venv\Scripts\python.exe scripts/collect_reddit.py --scrape --limit 50
.venv\Scripts\python.exe scripts/scrape_playstore.py --count 100
.venv\Scripts\python.exe scripts/run_analysis.py --limit 200
.venv\Scripts\python.exe scripts/generate_insights.py

# Full pipeline
.venv\Scripts\python.exe scripts/run_full_pipeline.py --reddit-limit 50 --playstore-count 100 --analyze-limit 200

# Analyze + insights only (data already collected)
.venv\Scripts\python.exe scripts/run_full_pipeline.py --skip-collect
```

## Files

| File | Purpose |
|------|---------|
| `pages/5_Admin.py` | Pipeline control panel |
| `scripts/run_full_pipeline.py` | End-to-end CLI |
| `scripts/cli_utils.py` | Shared CLI logging |

## Exit criteria

- [x] Admin page triggers each pipeline stage
- [x] Progress/spinner feedback during long operations
- [x] Status counts + ingestion history visible
- [x] `run_full_pipeline.py` runs collect → analyze → generate

## Next

→ [Phase 7 — Deploy & polish](../phase_7_deploy/)
