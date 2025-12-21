-- Migration 005: Add user authentication support
-- Adds user_id column and enables Row-Level Security (RLS)

-- Add user_id column to jobs table (nullable for backward compatibility)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Create index for faster user-based queries
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id);

-- Enable Row-Level Security on jobs table
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own jobs
-- Anonymous jobs (user_id IS NULL) are visible to all authenticated users
CREATE POLICY "Users can view own jobs" ON jobs
    FOR SELECT
    USING (
        user_id = auth.uid()
        OR user_id IS NULL  -- Allow viewing anonymous jobs
    );

-- Policy: Users can insert jobs (will be assigned their user_id by API)
CREATE POLICY "Users can insert jobs" ON jobs
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        OR user_id IS NULL  -- Allow anonymous job creation
    );

-- Policy: Users can update their own jobs
CREATE POLICY "Users can update own jobs" ON jobs
    FOR UPDATE
    USING (
        user_id = auth.uid()
        OR user_id IS NULL  -- Allow updating anonymous jobs
    );

-- Policy: Users can delete their own jobs
CREATE POLICY "Users can delete own jobs" ON jobs
    FOR DELETE
    USING (user_id = auth.uid());

-- Policy: Service role bypasses RLS (for Celery worker)
-- Note: Service role key already bypasses RLS by default in Supabase
-- This is just for documentation purposes

COMMENT ON COLUMN jobs.user_id IS 'User ID from Supabase auth. NULL for anonymous/legacy jobs.';
