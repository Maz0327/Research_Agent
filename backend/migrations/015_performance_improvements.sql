-- Migration 015: Performance improvements
-- Date: 2025-12-28
-- Purpose: Add composite indexes and utility functions for performance

-- =============================================================================
-- 1. Composite index for job listing with user and status filtering
-- =============================================================================
-- This optimizes queries like: SELECT * FROM jobs WHERE user_id = ? AND status = ? ORDER BY created_at DESC

CREATE INDEX IF NOT EXISTS idx_jobs_user_status_created
ON jobs (user_id, status, created_at DESC);

-- =============================================================================
-- 2. Function to get job counts by user IDs in a single query
-- =============================================================================
-- This eliminates N+1 queries in admin dashboard

CREATE OR REPLACE FUNCTION get_job_counts_by_users(user_ids UUID[])
RETURNS TABLE (user_id UUID, job_count BIGINT)
LANGUAGE SQL STABLE
AS $$
    SELECT
        j.user_id,
        COUNT(*)::BIGINT as job_count
    FROM jobs j
    WHERE j.user_id = ANY(user_ids)
    GROUP BY j.user_id
$$;

-- Grant execute to authenticated users (needed for RPC calls)
GRANT EXECUTE ON FUNCTION get_job_counts_by_users(UUID[]) TO authenticated;
GRANT EXECUTE ON FUNCTION get_job_counts_by_users(UUID[]) TO service_role;

-- =============================================================================
-- 3. Index for status-only queries (used in admin stats)
-- =============================================================================
-- This optimizes: SELECT COUNT(*) FROM jobs WHERE status = 'running'

CREATE INDEX IF NOT EXISTS idx_jobs_status
ON jobs (status);

-- =============================================================================
-- 4. Partial index for failed jobs (used in admin dashboard)
-- =============================================================================
-- This optimizes: SELECT COUNT(*) FROM jobs WHERE status = 'failed'

CREATE INDEX IF NOT EXISTS idx_jobs_failed
ON jobs (created_at DESC)
WHERE status = 'failed';

-- =============================================================================
-- 5. Partial index for running jobs
-- =============================================================================
-- This optimizes: SELECT COUNT(*) FROM jobs WHERE status = 'running'

CREATE INDEX IF NOT EXISTS idx_jobs_running
ON jobs (created_at DESC)
WHERE status = 'running';

-- =============================================================================
-- Verification
-- =============================================================================
-- List all indexes on jobs table
-- SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'jobs';
