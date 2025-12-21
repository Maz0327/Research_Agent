-- Migration: 007_add_user_settings.sql
-- Description: Add user_settings table for per-user configuration
-- Date: 2024-12-20

-- Create user_settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Google Drive Settings
    drive_folder_id TEXT,
    use_custom_folder BOOLEAN DEFAULT false,

    -- Pipeline Settings
    default_pipeline TEXT DEFAULT 'investigation' CHECK (default_pipeline IN ('quick', 'full', 'breaking_news', 'investigation', 'profile', 'controversy')),
    auto_extract_claims BOOLEAN DEFAULT true,
    max_sources INTEGER DEFAULT 25 CHECK (max_sources >= 5 AND max_sources <= 50),

    -- Notification Settings
    email_on_complete BOOLEAN DEFAULT true,
    email_on_failure BOOLEAN DEFAULT true,
    email_summary BOOLEAN DEFAULT false,

    -- Display Settings
    jobs_per_page INTEGER DEFAULT 10 CHECK (jobs_per_page >= 5 AND jobs_per_page <= 25),
    default_sort TEXT DEFAULT 'newest' CHECK (default_sort IN ('newest', 'oldest', 'status')),
    show_progress_details BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Ensure one settings row per user
    UNIQUE(user_id)
);

-- Enable Row-Level Security
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Users can view own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can insert own settings" ON user_settings;
DROP POLICY IF EXISTS "Users can update own settings" ON user_settings;
DROP POLICY IF EXISTS "Service role bypass for settings" ON user_settings;

-- Users can only view their own settings
CREATE POLICY "Users can view own settings"
    ON user_settings FOR SELECT
    USING (user_id = auth.uid());

-- Users can insert their own settings
CREATE POLICY "Users can insert own settings"
    ON user_settings FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can update their own settings
CREATE POLICY "Users can update own settings"
    ON user_settings FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Service role can do anything (for backend operations)
CREATE POLICY "Service role bypass for settings"
    ON user_settings FOR ALL
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
    );

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists (for idempotency)
DROP TRIGGER IF EXISTS user_settings_updated_at ON user_settings;

-- Trigger to auto-update updated_at
CREATE TRIGGER user_settings_updated_at
    BEFORE UPDATE ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_settings_updated_at();

-- Comment on table
COMMENT ON TABLE user_settings IS 'Per-user configuration settings for Research Agent';
COMMENT ON COLUMN user_settings.drive_folder_id IS 'Custom Google Drive folder ID for research output';
COMMENT ON COLUMN user_settings.default_pipeline IS 'Default research pipeline mode';
COMMENT ON COLUMN user_settings.max_sources IS 'Maximum sources to process per job';
