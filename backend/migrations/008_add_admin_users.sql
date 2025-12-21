-- Migration: Add admin_users table for admin role management
-- Created: 2024-12-20

-- Admin users table
CREATE TABLE IF NOT EXISTS admin_users (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES auth.users(id)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_admin_users_user_id ON admin_users(user_id);

-- RLS policies
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Only admins can view admin list
CREATE POLICY "Admins can view admin list" ON admin_users
    FOR SELECT
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
        OR EXISTS (SELECT 1 FROM admin_users au WHERE au.user_id = auth.uid())
    );

-- Only service role can modify admins (for backend operations)
CREATE POLICY "Service role can manage admins" ON admin_users
    FOR ALL
    USING (current_setting('request.jwt.claims', true)::json->>'role' = 'service_role');
