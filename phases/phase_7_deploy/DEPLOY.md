# Deploy to Streamlit Community Cloud

## Prerequisites

- GitHub repo: [github.com/vrittikht/spotifyresearch](https://github.com/vrittikht/spotifyresearch)
- Supabase project with migration applied
- Groq API key
- Data already in Supabase (322+ reviews recommended)

## 1. Push code to GitHub

Ensure secrets are **not** committed:

```bash
git status   # .streamlit/secrets.toml must NOT appear
git push origin main
```

## 2. Create Streamlit Cloud app

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. **New app** → connect `vrittikht/spotifyresearch`
3. **Main file path:** `app.py`
4. **Branch:** `main`

## 3. Configure secrets

In Streamlit Cloud → **Settings → Secrets**, paste:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_KEY = "your-service-role-key"
GROQ_API_KEY = "gsk_..."
GROQ_MODEL = "llama-3.1-8b-instant"
REDDIT_USER_AGENT = "spotify-research-collector/1.0 (PM case study; public pages only)"
```

Use the **service_role** Supabase key for writes from Admin page.

## 4. Deploy checklist

- [ ] `requirements.txt` complete
- [ ] `app.py` at repo root
- [ ] No secrets in git
- [ ] App loads within ~60 seconds
- [ ] All 6 sidebar pages work (Overview, Themes, Evidence, Segments, Research Report, Admin)
- [ ] Data visible (not empty states)

## 5. After deploy

- Add your live URL to `README.md` under **Live demo**
- Run through [DEMO_SCRIPT.md](./DEMO_SCRIPT.md) once
- Capture screenshots for your case study (Part 4)

## Notes

- **Admin page** batch limit is 50 (Cloud timeout safe). Use CLI locally for bulk:
  ```bash
  python scripts/run_full_pipeline.py
  ```
- Dashboard pages read from Supabase only — no Groq calls on page load.
