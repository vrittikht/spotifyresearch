# Spotify Discovery Research Agent

AI-powered **Review Discovery Engine** for a Spotify PM case study (Part 1). Collects public user feedback from Reddit and the Play Store, extracts structured insights with Groq, and surfaces themes and research answers in a Streamlit dashboard.

**Live demo:** [spotify-research.streamlit.app](https://spotify-research.streamlit.app/)

## What it does

```
Public Sources → Collection → Supabase → Groq Analysis → Insight Synthesis → Streamlit Dashboard
```

| Stage | Output |
|-------|--------|
| Collection | 300+ normalized reviews (Reddit + Play Store) |
| Analysis | Per-review JSON: barriers, frustrations, segment, sentiment |
| Synthesis | 10+ themes + report answering 6 PM research questions |
| Dashboard | Overview, Themes, Evidence, Segments, Research Report, Admin |

This is a **research instrument**, not a product MVP — it turns scattered discovery feedback into evidence-backed PM insights.

## Stack

Streamlit · Supabase (Postgres) · Groq (Llama 3.1) · Python

## Quick start

```bash
git clone https://github.com/vrittikht/spotifyresearch.git
cd spotifyresearch
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit secrets.toml — see below
streamlit run app.py
```

### Secrets (`.streamlit/secrets.toml`)

| Key | Purpose |
|-----|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | **service_role** key (required for Admin + CLI writes) |
| `GROQ_API_KEY` | Groq API key (`gsk_...`) |
| `GROQ_MODEL` | Default: `llama-3.1-8b-instant` |
| `REDDIT_USER_AGENT` | Optional, for public Reddit fetches |

Run the migration in Supabase SQL Editor: `supabase/migrations/001_initial.sql`

## Full pipeline (CLI)

Collect real data, analyze, and generate insights locally (recommended before deploy):

```bash
.venv\Scripts\python.exe scripts/scrape_all.py --reddit-limit 150 --playstore-count 500
.venv\Scripts\python.exe scripts/run_analysis.py --limit 300
.venv\Scripts\python.exe scripts/generate_insights.py
```

Or run end-to-end:

```bash
.venv\Scripts\python.exe scripts/run_full_pipeline.py
```

Verify deploy readiness:

```bash
.venv\Scripts\python.exe phases/phase_7_deploy/smoke_test.py
.venv\Scripts\python.exe scripts/quality_review.py --sample 10
```

## Dashboard pages

| Page | Purpose |
|------|---------|
| **Overview** | Stats, sentiment, sources, executive summary |
| **Themes** | Ranked discovery patterns with user quotes |
| **Evidence** | Filterable review library + AI extraction JSON |
| **Segments** | Barriers and frustrations by user segment |
| **Research Report** | Six PM research questions with evidence counts |
| **Admin** | Pipeline controls (batch limit 50 on Cloud) |

Dashboard pages read from Supabase only — no Groq calls on page load.

## Deploy to Streamlit Community Cloud

1. Push to GitHub (ensure `.streamlit/secrets.toml` is **not** committed).
2. [share.streamlit.io](https://share.streamlit.io) → New app → repo `vrittikht/spotifyresearch`, main file `app.py`.
3. Add secrets in Streamlit Cloud settings (same keys as `secrets.toml.example`).
4. Pre-load data in Supabase via CLI locally — Cloud Admin is limited to 50 reviews per batch.

Full checklist: [phases/phase_7_deploy/DEPLOY.md](./phases/phase_7_deploy/DEPLOY.md)

**5-minute demo script:** [phases/phase_7_deploy/DEMO_SCRIPT.md](./phases/phase_7_deploy/DEMO_SCRIPT.md)

## Project docs

- [problemstatement.md](./problemstatement.md) — scope and research questions
- [architecture.md](./architecture.md) — schema, prompts, module design
- [implementationplan.md](./implementationplan.md) — phase-wise build plan
- [phases/](./phases/) — per-phase READMEs and smoke tests

## Current dataset (local)

| Metric | Target | Status |
|--------|--------|--------|
| Total reviews | 300+ | 322 |
| Relevant analyses | 250+ | 266 |
| Themes | 10+ | 10 |
| Research answers | 6/6 | ✓ |

Sources: Reddit (118) + Play Store (204)

## License

Portfolio / case study project.
