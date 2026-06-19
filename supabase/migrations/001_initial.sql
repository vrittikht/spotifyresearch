-- Spotify Discovery Research Agent — Phase 1 schema
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

create extension if not exists "pgcrypto";

-- ─── Ingestion Runs ───────────────────────────────────────────────
create table if not exists ingestion_runs (
  id              uuid primary key default gen_random_uuid(),
  source          text not null check (source in ('reddit', 'play_store', 'app_store')),
  status          text not null default 'running'
                    check (status in ('running', 'completed', 'failed')),
  records_fetched int  not null default 0,
  records_new     int  not null default 0,
  error_message   text,
  started_at      timestamptz not null default now(),
  completed_at    timestamptz
);

-- ─── Reviews (raw feedback) ───────────────────────────────────────
create table if not exists reviews (
  id               uuid primary key default gen_random_uuid(),
  source           text not null check (source in ('reddit', 'play_store', 'app_store')),
  source_id        text not null,
  title            text,
  body             text not null,
  rating           int check (rating between 1 and 5),
  metadata         jsonb not null default '{}',
  published_at     timestamptz,
  ingested_at      timestamptz not null default now(),
  status           text not null default 'pending'
                     check (status in ('pending', 'analyzing', 'analyzed', 'skipped', 'failed')),
  ingestion_run_id uuid references ingestion_runs(id),
  unique (source, source_id)
);

create index if not exists idx_reviews_status    on reviews(status);
create index if not exists idx_reviews_source    on reviews(source);
create index if not exists idx_reviews_published on reviews(published_at desc);

-- ─── Analysis (Groq output per review) ────────────────────────────
create table if not exists analysis (
  id                      uuid primary key default gen_random_uuid(),
  review_id               uuid not null unique references reviews(id) on delete cascade,
  is_relevant             boolean not null default false,
  pain_points             jsonb not null default '[]',
  jobs_to_be_done         jsonb not null default '[]',
  discovery_barriers      jsonb not null default '[]',
  rec_frustrations        jsonb not null default '[]',
  listening_behaviors     jsonb not null default '[]',
  repeat_listening_causes jsonb not null default '[]',
  user_segment            text,
  sentiment               text check (sentiment in ('positive', 'negative', 'neutral', 'mixed')),
  emotions                text[] not null default '{}',
  unmet_needs             jsonb not null default '[]',
  confidence              float check (confidence between 0 and 1),
  analyzed_at             timestamptz not null default now()
);

create index if not exists idx_analysis_relevant on analysis(is_relevant) where is_relevant = true;
create index if not exists idx_analysis_segment  on analysis(user_segment);

-- ─── Themes (aggregated patterns) ─────────────────────────────────
create table if not exists themes (
  id                  uuid primary key default gen_random_uuid(),
  name                text not null,
  description         text not null,
  category            text not null
                        check (category in (
                          'discovery_barrier', 'rec_frustration',
                          'listening_behavior', 'repeat_listening',
                          'unmet_need', 'segment_insight'
                        )),
  review_count        int not null default 0,
  example_quotes      jsonb not null default '[]',
  segment_breakdown   jsonb not null default '{}',
  source_breakdown    jsonb not null default '{}',
  avg_sentiment_score float,
  generated_at        timestamptz not null default now()
);

create index if not exists idx_themes_category on themes(category);

-- ─── Theme ↔ Review junction ──────────────────────────────────────
create table if not exists theme_reviews (
  theme_id  uuid not null references themes(id) on delete cascade,
  review_id uuid not null references reviews(id) on delete cascade,
  primary key (theme_id, review_id)
);

-- ─── Insight Reports ──────────────────────────────────────────────
create table if not exists insight_reports (
  id               uuid primary key default gen_random_uuid(),
  report_type      text not null default 'research_summary'
                     check (report_type in ('research_summary', 'segment_comparison', 'opportunity_brief')),
  title            text not null,
  content          jsonb not null default '{}',
  research_answers jsonb not null default '{}',
  generated_at     timestamptz not null default now()
);

-- ─── Report ↔ Theme junction ──────────────────────────────────────
create table if not exists report_themes (
  report_id uuid not null references insight_reports(id) on delete cascade,
  theme_id  uuid not null references themes(id) on delete cascade,
  primary key (report_id, theme_id)
);

-- ─── Dashboard views ──────────────────────────────────────────────
create or replace view v_theme_summary as
select id, name, category, review_count, avg_sentiment_score,
       example_quotes, segment_breakdown, source_breakdown
from themes
order by review_count desc;

create or replace view v_review_evidence as
select r.id, r.source, r.title, r.body, r.rating, r.published_at,
       a.user_segment, a.sentiment, a.discovery_barriers,
       a.rec_frustrations, a.unmet_needs
from reviews r
join analysis a on a.review_id = r.id
where a.is_relevant = true;
