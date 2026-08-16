-- Migration 002: Add performance indexes
-- Run in Supabase SQL Editor: Dashboard > SQL > New Query

-- ═══════════════════════════════════════════════════════════════
-- Jobs table indexes
-- ═══════════════════════════════════════════════════════════════

-- Index for fetching user's jobs (most common query)
CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs (user_id);

-- Index for filtering by status (running, completed, failed)
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);

-- Composite index for user + status (dashboard filtering)
CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON jobs (user_id, status);

-- Index for sorting by creation date (job list ordering)
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs (created_at DESC);

-- Composite index for user + created_at (user's recent jobs)
CREATE INDEX IF NOT EXISTS idx_jobs_user_created ON jobs (user_id, created_at DESC);

-- Index for job lookups by share token
CREATE INDEX IF NOT EXISTS idx_jobs_share_token ON jobs (share_token) WHERE share_token IS NOT NULL;

-- ═══════════════════════════════════════════════════════════════
-- Error logs table indexes (if exists)
-- ═══════════════════════════════════════════════════════════════

-- Index for error log lookups by job
CREATE INDEX IF NOT EXISTS idx_error_logs_job_id ON error_logs (job_id);

-- Index for recent errors (admin dashboard)
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs (created_at DESC);

-- ═══════════════════════════════════════════════════════════════
-- Verify indexes were created
-- ═══════════════════════════════════════════════════════════════

-- Run this to verify:
-- SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;
