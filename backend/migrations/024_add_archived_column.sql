-- Migration: Add archived column to jobs table
-- Purpose: Allow users to archive jobs without deleting them

-- Add archived column with default false
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

-- Add index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_jobs_archived ON jobs(archived);

-- Add composite index for common query pattern (user + archived + created_at)
CREATE INDEX IF NOT EXISTS idx_jobs_user_archived_created ON jobs(user_id, archived, created_at DESC);

-- Comment for documentation
COMMENT ON COLUMN jobs.archived IS 'Whether the job has been archived by the user';
