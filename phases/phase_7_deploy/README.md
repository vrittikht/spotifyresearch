# Phase 7 — Deploy & Polish

**Goal:** Live public URL on Streamlit Community Cloud; portfolio-ready demo.

**Duration:** 4–5 hours · **Depends on:** Phase 6 · **Status:** Done (code & data ready — deploy when pushed)

## Completed

| Task | Artifact |
|------|----------|
| 300+ reviews in Supabase | 322 total, 266 relevant |
| Analysis + insights pipeline | Themes + 6 research answers |
| Quality review script | `scripts/quality_review.py` |
| Deploy readiness smoke test | `phases/phase_7_deploy/smoke_test.py` |
| Deploy guide | [DEPLOY.md](./DEPLOY.md) |
| Demo script | [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) |
| UI polish | `components/empty_state.py`, `components/sidebar_footer.py` on all pages |
| Portfolio README | Root [README.md](../../README.md) |
| Pinned requirements | Major-version bounds in `requirements.txt` |

## Run checks locally

```bash
.venv\Scripts\python.exe phases/phase_7_deploy/smoke_test.py
.venv\Scripts\python.exe scripts/quality_review.py --sample 10
```

## Exit criteria

- [x] **300+ reviews**, **250+ relevant**, **10+ themes**
- [x] All 6 research questions answered (UI enriches from themes if Groq summary empty)
- [x] README documents setup, pipeline, and deploy
- [x] Demo script prepared
- [ ] **Public URL live** — push to GitHub and deploy via [DEPLOY.md](./DEPLOY.md)
- [ ] Screenshots saved for case study — use [screenshots/](./screenshots/) folder

## Your next steps

1. `git push origin main` (verify `secrets.toml` is not tracked)
2. Deploy on [Streamlit Cloud](https://share.streamlit.io) per [DEPLOY.md](./DEPLOY.md)
3. Add live URL to root README under **Live demo**
4. Walk through [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) once; save screenshots to `screenshots/`
