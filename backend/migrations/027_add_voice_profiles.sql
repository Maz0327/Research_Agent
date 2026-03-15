-- Migration 027: Add voice_profiles table
-- Voice profiles store analyzed creator voice patterns for script mimicry.

CREATE TABLE IF NOT EXISTS voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    creator_name TEXT NOT NULL,
    style_profile JSONB NOT NULL DEFAULT '{}',
    sentence_rhythm JSONB DEFAULT '{}',
    transition_patterns JSONB DEFAULT '[]',
    opening_patterns JSONB DEFAULT '[]',
    closing_patterns JSONB DEFAULT '[]',
    emphasis_patterns JSONB DEFAULT '{}',
    source_video_urls JSONB DEFAULT '[]',
    source_video_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_voice_profiles_user_id ON voice_profiles(user_id);

-- RLS policies (same pattern as style_guides)
ALTER TABLE voice_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own voice profiles"
    ON voice_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own voice profiles"
    ON voice_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own voice profiles"
    ON voice_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own voice profiles"
    ON voice_profiles FOR DELETE
    USING (auth.uid() = user_id);
