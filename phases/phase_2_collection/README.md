# Phase 2 — Data Collection

**Goal:** Ingest **real** public feedback from Reddit and Google Play Store into Supabase.

**Duration:** 4–5 hours · **Depends on:** Phase 1 · **Status:** Complete

## Real data scraping (recommended)

```bash
# Scrape both sources at once
.venv\Scripts\python.exe scripts/scrape_all.py --reddit-limit 150 --playstore-count 500

# Reddit only (RSS + old.reddit HTML — real posts)
.venv\Scripts\python.exe scripts/collect_reddit.py --scrape --limit 150

# Play Store only (google-play-scraper — real reviews)
.venv\Scripts\python.exe scripts/scrape_playstore.py --count 500
```

Add `--dry-run` to preview without writing to Supabase.

## How real data is fetched

| Source | Method | Library / endpoint |
|--------|--------|-------------------|
| **Play Store** | Live API scrape | `google-play-scraper` → `com.spotify.music` |
| **Reddit** | RSS search feeds | `reddit.com/r/{sub}/search.rss` |
| **Reddit** | HTML search pages | `old.reddit.com/r/{sub}/search` (scores + body) |

Reddit's public `.json` API is blocked (403). RSS + old.reddit HTML are used instead.

Play Store reviews are filtered to discovery-related keywords by default. Use `--all-reviews` on `scrape_playstore.py` to import everything fetched.

## Files in this phase

| File | Purpose |
|------|---------|
| `collectors/play_store_scraper.py` | Real Play Store review fetcher |
| `collectors/reddit_collector.py` | RSS + HTML live scrape + manual HTML import |
| `collectors/csv_importer.py` | Optional CSV import (exported files) |
| `collectors/normalizer.py` | Unified review shape |
| `services/ingestion_service.py` | Dedup + ingestion run tracking |
| `scripts/scrape_all.py` | Scrape Reddit + Play Store |
| `scripts/scrape_playstore.py` | Play Store only |
| `scripts/collect_reddit.py` | Reddit only |
| `scripts/import_csv.py` | CSV file import (optional) |
| `sample_data/` | Synthetic data for offline testing only |

## Manual / offline fallbacks

```bash
# Save Reddit HTML manually
.venv\Scripts\python.exe scripts/collect_reddit.py --print-urls
.venv\Scripts\python.exe scripts/collect_reddit.py --html-dir data/reddit_html

# Import a Play Store CSV export
.venv\Scripts\python.exe scripts/import_csv.py --source play_store --file data/play_store_reviews.csv
```

## Exit criteria

- [x] Live Play Store scrape inserts real reviews
- [x] Live Reddit scrape inserts real posts (RSS + HTML)
- [x] 50+ total reviews from 2 sources
- [x] Dedup on re-run
- [x] Ingestion runs logged

## Next

→ [Phase 3 — Groq analysis](../phase_3_analysis/)
