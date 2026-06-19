# Phase 0 — Project Setup

**Goal:** Repo skeleton, dependencies, secrets, and connection tests.

**Duration:** 2–3 hours · **Status:** Complete

## What was built

| Item | Location |
|------|----------|
| Streamlit entry + connection tests | `app.py` |
| Secrets loader | `services/config.py` |
| Groq config | `services/groq_config.py` |
| Connection tests (Supabase, Groq, Reddit) | `services/connection_tests.py` |
| Dependencies | `requirements.txt` |
| Streamlit config | `.streamlit/config.toml`, `secrets.toml.example` |

## Exit criteria

- [x] `streamlit run app.py` launches without errors
- [x] Supabase, Groq, and Reddit connection tests pass
- [x] Repo on GitHub

## Next

→ [Phase 1 — Database & data layer](../phase_1_database/)
