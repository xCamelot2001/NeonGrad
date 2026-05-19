-- ============================================================
-- CareerPilot — Initial Schema
-- Apply this in the Supabase SQL editor:
--   supabase.com → your project → SQL Editor → paste + run
-- ============================================================

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── profiles ────────────────────────────────────────────────
-- One row per user (id mirrors auth.users.id)
CREATE TABLE IF NOT EXISTS profiles (
  id                UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  cv_raw_text       TEXT,
  cv_structured     JSONB,            -- {summary, skills[], experience[], education[]}
  linkedin_url      TEXT,
  target_roles      TEXT[]   DEFAULT '{}',
  target_locations  TEXT[]   DEFAULT '{}',
  salary_min        INTEGER,
  salary_max        INTEGER,
  experience_level  TEXT     DEFAULT 'mid'
                    CHECK (experience_level IN ('junior', 'mid', 'senior')),
  excluded_companies TEXT[]  DEFAULT '{}',
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ── jobs ────────────────────────────────────────────────────
-- Raw jobs fetched from APIs — shared across all users
CREATE TABLE IF NOT EXISTS jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source        TEXT NOT NULL,             -- 'adzuna' | 'jsearch'
  external_id   TEXT NOT NULL,
  title         TEXT NOT NULL,
  company       TEXT NOT NULL,
  location      TEXT,
  salary_min    INTEGER,
  salary_max    INTEGER,
  jd_raw        TEXT NOT NULL,
  jd_structured JSONB,    -- {required_skills[], nice_to_haves[], seniority, tech_stack[]}
  url           TEXT NOT NULL,
  posted_at     TIMESTAMPTZ,
  fetched_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (source, external_id)
);

-- ── job_rankings ─────────────────────────────────────────────
-- Per-user AI-assessed fit scores
CREATE TABLE IF NOT EXISTS job_rankings (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  job_id              UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  relevance_score     FLOAT    DEFAULT 0.0 CHECK (relevance_score BETWEEN 0 AND 1),
  gap_analysis        JSONB,   -- {matched_skills[], missing_skills[], gap_severity}
  strategy            TEXT     DEFAULT 'decent'
                      CHECK (strategy IN ('strong_match', 'decent', 'stretch', 'skip')),
  strategy_reasoning  TEXT,
  ranked_at           TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS job_rankings_user_score
  ON job_rankings (user_id, relevance_score DESC);

-- ── applications ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  job_id            UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  status            TEXT DEFAULT 'not_applied'
                    CHECK (status IN ('not_applied','applied','interviewing','offer','rejected')),
  tailored_cv_text  TEXT,
  cover_letter_text TEXT,
  tailored_at       TIMESTAMPTZ,
  applied_at        TIMESTAMPTZ,
  outcome_notes     TEXT,
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS applications_user_status
  ON applications (user_id, status);

-- ── interview_preps ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS interview_preps (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id       UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  company_research     JSONB,  -- {mission, culture, recent_news, tech_stack}
  behavioral_questions JSONB,  -- [{question, answer, star_points}]
  technical_questions  JSONB,  -- [{question, hint, model_answer}]
  created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Row Level Security
-- ============================================================

ALTER TABLE profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_rankings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications    ENABLE ROW LEVEL SECURITY;
ALTER TABLE interview_preps ENABLE ROW LEVEL SECURITY;
-- jobs table is shared — no RLS needed

-- profiles: users can only read/write their own row
CREATE POLICY "profiles_self" ON profiles
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- job_rankings: scoped to the user
CREATE POLICY "rankings_self" ON job_rankings
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- applications: scoped to the user
CREATE POLICY "applications_self" ON applications
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- interview_preps: visible if the user owns the application
CREATE POLICY "preps_self" ON interview_preps
  USING (
    EXISTS (
      SELECT 1 FROM applications a
      WHERE a.id = interview_preps.application_id
        AND a.user_id = auth.uid()
    )
  );

-- ============================================================
-- updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER applications_updated_at
  BEFORE UPDATE ON applications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
