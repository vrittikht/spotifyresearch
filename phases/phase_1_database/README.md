# Phase 1 — Database & Data Layer

**Goal:** Supabase schema migrated; `services/supabase_client.py` provides all read/write operations.

**Duration:** 3–4 hours · **Depends on:** Phase 0

## Files in this phase

| File | Purpose |
|------|---------|
| `supabase/migrations/001_initial.sql` | 7 tables + 2 views |
| `services/supabase_client.py` | Database access layer |
| `phases/phase_1_database/smoke_test.py` | Insert, dedup, and stats check |

## Run the migration

1. Open [Supabase SQL Editor](https://supabase.com/dashboard) for your project.
2. Paste and run the contents of `supabase/migrations/001_initial.sql`.
3. Confirm tables: `ingestion_runs`, `reviews`, `analysis`, `themes`, `theme_reviews`, `insight_reports`, `report_themes`.
4. Confirm views: `v_theme_summary`, `v_review_evidence`.

**Tip:** Use the **service_role** key (not anon) in `SUPABASE_SERVICE_KEY` for server-side writes.

## Smoke test

From repo root (with venv active and secrets filled in):

```bash
python phases/phase_1_database/smoke_test.py
```

Expected: insert review → read back → dedup skip → `get_overview_stats()` without errors → cleanup.

## Key functions (`services/supabase_client.py`)

**Write:** `insert_review`, `upsert_review`, `update_review_status`, `save_analysis`, `save_themes`, `save_report`, `create_ingestion_run`, `complete_ingestion_run`

**Read:** `get_reviews`, `get_pending_reviews`, `get_analyses_with_reviews`, `get_overview_stats`, `get_themes`, `get_theme_detail`, `get_evidence`, `get_segment_breakdown`, `get_latest_report`, `get_ingestion_runs`

## Exit criteria

- [ ] All tables visible in Supabase Table Editor
- [ ] Test review inserted and retrieved via `supabase_client.py`
- [ ] Dedup works — duplicate `(source, source_id)` is skipped
- [ ] `get_overview_stats()` returns counts (zeros OK if empty DB)

## Next

→ [Phase 2 — Data collection](../phase_2_collection/)
