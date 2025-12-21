-- Migration 012: Add error column to jobs table
-- This column stores error messages for failed jobs

-- Add error column if it doesn't exist
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS error TEXT;

-- Add index for querying failed jobs
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Add composite index for user job listing (improves list_jobs performance)
CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON jobs(user_id, created_at DESC);

-- Add index for stage queries (useful for monitoring)
CREATE INDEX IF NOT EXISTS idx_jobs_stage ON jobs(stage) WHERE status = 'running';
