-- Migration: Add error_logs table for admin error tracking
-- Created: 2024-12-20

-- Error logs table
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),

    -- User-friendly info
    user_message TEXT NOT NULL,
    error_category VARCHAR(50) NOT NULL,  -- 'api_error', 'memory', 'timeout', 'validation', etc.

    -- Technical details
    technical_message TEXT NOT NULL,
    stack_trace TEXT,
    error_code VARCHAR(50),

    -- Context
    stage VARCHAR(50),  -- Pipeline stage where error occurred
    endpoint VARCHAR(100),  -- API endpoint if applicable
    request_data JSONB,  -- Sanitized request context

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_error_logs_job_id ON error_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_category ON error_logs(error_category);
CREATE INDEX IF NOT EXISTS idx_error_logs_created_at ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON error_logs(resolved) WHERE resolved = false;

-- Enable RLS
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;

-- Only admins and service role can view error logs
CREATE POLICY "Admins can view error logs" ON error_logs
    FOR SELECT
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid())
    );

-- Service role can insert (for backend logging)
CREATE POLICY "Service role can insert error logs" ON error_logs
    FOR INSERT
    WITH CHECK (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');

-- Admins can update (for resolving errors)
CREATE POLICY "Admins can update error logs" ON error_logs
    FOR UPDATE
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid())
    );
