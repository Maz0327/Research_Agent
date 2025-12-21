-- Migration 006: Secure RLS policies
-- Removes anonymous job visibility to prevent information disclosure

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view own jobs" ON jobs;
DROP POLICY IF EXISTS "Users can insert jobs" ON jobs;
DROP POLICY IF EXISTS "Users can update own jobs" ON jobs;
DROP POLICY IF EXISTS "Users can delete own jobs" ON jobs;

-- Policy: Users can ONLY view their own jobs (no anonymous job access)
CREATE POLICY "Users can view own jobs" ON jobs
    FOR SELECT
    USING (
        user_id = auth.uid()
    );

-- Policy: Users can only insert jobs assigned to themselves
CREATE POLICY "Users can insert jobs" ON jobs
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
    );

-- Policy: Users can only update their own jobs
CREATE POLICY "Users can update own jobs" ON jobs
    FOR UPDATE
    USING (
        user_id = auth.uid()
    );

-- Policy: Users can only delete their own jobs
CREATE POLICY "Users can delete own jobs" ON jobs
    FOR DELETE
    USING (
        user_id = auth.uid()
    );

-- Note: Service role key bypasses RLS by default in Supabase
-- This allows the backend worker to access all jobs
