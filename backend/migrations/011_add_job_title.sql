-- Migration 011: Add title and stage_started_at columns to jobs table
-- These columns support AI-generated job titles and accurate ETA calculation

-- Add title column for AI-generated short titles
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS title TEXT;

-- Add stage_started_at for tracking stage timing (used for ETA calculation)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS stage_started_at TIMESTAMPTZ;

-- Add index for title search (optional, for future search functionality)
CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title) WHERE title IS NOT NULL;

COMMENT ON COLUMN jobs.title IS 'AI-generated short title for the job (3-6 words)';
COMMENT ON COLUMN jobs.stage_started_at IS 'Timestamp when current stage started, for ETA calculation';
