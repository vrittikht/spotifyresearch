# Spotify Discovery Research Agent — Part 1

AI-powered Review Discovery Engine for a Spotify PM case study. Ingests public user feedback, analyzes it with Groq, and surfaces research-ready insights in a Streamlit dashboard.

## Stack

- Streamlit · Supabase · Groq · Python
- Deploy: GitHub → Streamlit Community Cloud

## Setup

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY
streamlit run app.py
```

## Reddit collection (no API)

Reddit blocks automated fetching via robots.txt. Save public search pages manually, then import:

```bash
python scripts/collect_reddit.py --print-urls
python scripts/collect_reddit.py --html-dir data/reddit_html
```

## Docs

- [problemstatement.md](./problemstatement.md)
- [architecture.md](./architecture.md)
- [implementationplan.md](./implementationplan.md)
