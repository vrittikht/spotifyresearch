# Spotify Discovery Research Agent — Part 1

## Case Study Context

This project is **Part 1 of a Product Management case study** for Spotify. It is **not the final product MVP**.

**Part 1** is an **AI-powered Review Discovery Engine** — a research tool that analyzes public user feedback at scale and generates structured insights to inform product decisions.

| | Part 1 (This Project) | Future Parts |
|---|---|---|
| **Purpose** | Research & discovery analysis | Product solution design |
| **Output** | Themes, patterns, evidence-backed insights | Feature spec, prototype, roadmap |
| **Audience** | PM doing discovery research | Stakeholders evaluating a product bet |

The engine exists to answer hard research questions **before** building anything. Its output becomes the evidence base for Part 2 (problem definition) and Part 3 (solution design).

---

## Executive Summary

Spotify has one of the world's most sophisticated recommendation systems, yet a large share of listening still comes from familiar artists, repeat playlists, and previously saved content — not meaningful discovery of new music.

User feedback about discovery and recommendations is abundant across public channels, but it is fragmented, unstructured, and impossible to analyze manually at scale.

**Part 1** builds a lean research engine deployed as a **single Streamlit application** — one public URL that ingests feedback, analyzes it with Groq, and surfaces patterns product teams can act on. Scoped for a solo builder in **4–5 days**, within a **17-day** overall case study timeline.

---

## Background

### Strategic Context

Spotify has identified **meaningful music discovery** as a growth opportunity. Before designing solutions, product teams must understand *why* users struggle to discover new music and *what* prevents engagement with unfamiliar content.

### Current State

Discovery-related feedback is scattered across:

- Google Play Store and Apple App Store reviews
- Reddit posts from **public pages** (r/spotify, r/truespotify — no Reddit API)
- Spotify Community forums

This feedback is unstructured text at high volume. Manual analysis is slow, inconsistent, and does not scale.

### The Gap

Without a systematic research tool, PMs rely on anecdotal evidence, small sample sizes, and untested assumptions — increasing risk when prioritizing discovery investments.

---

## Problem Statement

**Spotify lacks a scalable way to analyze public user feedback about music discovery and recommendations.**

Thousands of users discuss recommendation quality, discovery experiences, and listening habits online. Extracting patterns from this feedback requires manual effort that does not scale.

Part 1 addresses this with a focused research pipeline:

```
Public Sources → Collection Scripts → Supabase → Groq Analysis → Insight Generation → Streamlit Dashboard
```

---

## Research Questions

Part 1 must help answer these six questions with evidence from real user feedback:

| # | Research Question | What the Engine Surfaces |
|---|---|---|
| 1 | **Why do users struggle to discover new music?** | Discovery barriers, friction points, context of failure |
| 2 | **What are the most common frustrations with recommendations?** | Rec failure categories, sentiment, frequency-ranked themes |
| 3 | **What listening behaviors are users trying to achieve?** | Jobs-to-be-done, intent signals, desired outcomes |
| 4 | **What causes users to repeatedly listen to the same content?** | Repeat-listening drivers, comfort-seeking patterns |
| 5 | **Which user segments experience different discovery challenges?** | Segment tags, cross-segment theme comparison |
| 6 | **What unmet needs emerge consistently across reviews?** | Recurring need statements, opportunity themes |

---

## Scope — Part 1

### In Scope

#### Data Collection
- Google Play Store reviews (CSV import)
- Reddit posts from public subreddit/search pages (no Reddit API)
- App Store reviews (CSV import — optional if time-constrained)

> **Pragmatic cut:** Start with Reddit + Play Store. Add App Store only if ahead of schedule.

#### AI Analysis (Groq)
Per review, extract:
- Pain points
- Jobs-to-be-done
- Discovery barriers
- Recommendation frustrations
- Listening behaviors
- Repeat-listening causes
- User segment (inferred)
- Sentiment and emotional tone
- Unmet needs

#### Insight Generation
- Theme clustering and labeling (Groq batch synthesis)
- Frequency and sentiment aggregation
- Segment and source breakdowns
- Research summary report mapped to the six questions

#### Interface & Deployment
- **Streamlit dashboard** — theme explorer, evidence viewer, segment comparison, research report
- **Single public URL** — deployed via GitHub → Streamlit Community Cloud
- **Supabase** — persistent storage for reviews, analysis, themes, reports

### Out of Scope — Part 1

- Final product MVP or user-facing Spotify feature
- Separate backend server (FastAPI, Render, etc.)
- Spotify internal analytics or listening data
- Real-time streaming ingestion or message queues
- Automated product changes or model retraining
- Reddit API, PRAW, or Reddit developer credentials
- Spotify Community forums (deferred — hard to scrape reliably in 5 days)
- User authentication (single-user research tool)
- Multiple deployments or microservices

---

## Constraints

| Constraint | Detail |
|---|---|
| **Builder** | Solo developer / PM |
| **Part 1 timeline** | 4–5 days |
| **Total case study** | 17 days |
| **Application** | Streamlit (single app) |
| **Deployment** | GitHub → Streamlit Community Cloud → one public URL |
| **Database** | Supabase (PostgreSQL) |
| **AI** | Groq API ([GroqCloud](https://console.groq.com)) |
| **Reddit data** | Public pages only — no Reddit API |
| **Excluded** | Reddit API/PRAW, FastAPI, Render, Docker, Kubernetes, Redis, RabbitMQ, Celery, microservices |

---

## Expected Outcome — Part 1

### Deliverables

1. **Live Streamlit app** — one public URL demonstrating the full research pipeline
2. **Curated dataset** — 200–500 discovery-relevant reviews from public sources
3. **Structured analysis** — every relevant review tagged with research dimensions
4. **Research dashboard** — themes, segments, evidence quotes, summary report
5. **Case study artifact** — demo-ready tool that shows PM thinking, not just code

### Success Criteria

Part 1 succeeds when you can:

- [ ] Share **one public Streamlit URL** that loads the research dashboard
- [ ] Demonstrate ingestion from at least **2 public sources**
- [ ] Show **AI-structured analysis** on 200+ reviews
- [ ] Answer all **6 research questions** with aggregated evidence
- [ ] Display **top themes** with supporting user quotes
- [ ] Compare patterns across **at least 2 user segments**

### What "Impressive" Looks Like for a PM Portfolio

- Clear problem framing tied to Spotify strategy
- Evidence-backed insights, not AI-generated fluff
- Original user quotes surfaced alongside themes
- Segment and source comparisons that show analytical depth
- A dashboard that tells a research story, not just displays data
- One clean URL a reviewer can open without setup instructions

---

## Downstream Value

Output from Part 1 feeds directly into:

- **Part 2 — Problem Definition:** Synthesize top themes into a focused problem statement with user evidence
- **Part 3 — Solution Design:** Prioritize opportunity areas and sketch an AI-native discovery feature
- **Part 4 — Case Study Write-up:** Screenshots, insights, and PM narrative for portfolio presentation

Part 1 is the research foundation. Everything else in the case study builds on the insights this engine produces.

---

## Related Documents

- [Architecture](./architecture.md) — System design, schema, modules, prompts, and build roadmap
