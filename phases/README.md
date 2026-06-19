# Phase-wise project layout

This folder mirrors the [implementation plan](../implementationplan.md). Each phase has its own directory with a README and (where useful) scripts or notes for that stage.

| Phase | Folder | Status |
|-------|--------|--------|
| 0 — Project setup | [phase_0_setup](./phase_0_setup/) | Done |
| 1 — Database & data layer | [phase_1_database](./phase_1_database/) | Done |
| 2 — Data collection | [phase_2_collection](./phase_2_collection/) | Done |
| 3 — Groq analysis | [phase_3_analysis](./phase_3_analysis/) | Done |
| 4 — Insight generation | [phase_4_insights](./phase_4_insights/) | Done |
| 5 — Streamlit dashboard | [phase_5_dashboard](./phase_5_dashboard/) | Done |
| 6 — Admin & CLI | [phase_6_admin](./phase_6_admin/) | Done |
| 7 — Deploy & polish | [phase_7_deploy](./phase_7_deploy/) | Done (deploy pending) |

**Pipeline:**

```
Public Sources → Collection → Supabase → Groq Analysis → Insights → Streamlit Dashboard
     Phase 2        Phase 2      Phase 1      Phase 3        Phase 4      Phase 5
```

Run the app from the repo root: `streamlit run app.py`
