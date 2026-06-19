# Phase 5 — Streamlit Dashboard

**Goal:** Five dashboard pages rendering real Supabase data (no live Groq on page load).

**Duration:** 6–8 hours · **Depends on:** Phase 4 · **Status:** Complete

## Pages

| Page | File | Content |
|------|------|---------|
| Overview | `app.py` | KPIs, sentiment pie, source bar chart, executive summary |
| Themes | `pages/1_Themes.py` | Category filter, ranked theme cards with quotes |
| Evidence | `pages/2_Evidence.py` | Source/segment/sentiment/keyword filters + analysis detail |
| Segments | `pages/3_Segments.py` | Bar chart + top barriers/frustrations per segment |
| Research Report | `pages/4_Research_Report.py` | All 6 research questions with summaries |

## Shared components

| Component | Purpose |
|-----------|---------|
| `components/stats_bar.py` | Overview metric tiles |
| `components/theme_card.py` | Expandable theme with quotes |
| `components/quote_block.py` | Styled quote + source badge |
| `components/filters.py` | Evidence and theme filters |
| `components/styles.py` | Spotify-adjacent CSS |
| `components/constants.py` | Labels and colors |

## Run locally

```bash
streamlit run app.py
```

Navigate via the sidebar: Overview, Themes, Evidence, Segments, Research Report.

## Exit criteria

- [x] All 5 pages load without errors
- [x] Overview shows real Supabase stats
- [x] Themes page displays generated themes with quotes
- [x] Evidence page filters work
- [x] Segments page compares multiple segments
- [x] Research Report shows all 6 questions
- [x] No Groq calls on page load

## Next

→ [Phase 6 — Admin & CLI](../phase_6_admin/)
