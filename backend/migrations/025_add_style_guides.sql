-- Migration 025: Add style_guides table for creator style preferences
-- Phase 2B of UX Overhaul

CREATE TABLE IF NOT EXISTS style_guides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    template_base TEXT NOT NULL CHECK (
        template_base IN (
            'deep_dive_explainer',
            'investigative_storyteller',
            'casual_conversationalist',
            'custom'
        )
    ),
    overrides JSONB DEFAULT '{}',
    section_preferences JSONB DEFAULT '[]',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast lookups by user
CREATE INDEX IF NOT EXISTS idx_style_guides_user_id ON style_guides(user_id);

-- Enable RLS
ALTER TABLE style_guides ENABLE ROW LEVEL SECURITY;

-- RLS: users can only see their own guides
CREATE POLICY style_guides_select ON style_guides
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY style_guides_insert ON style_guides
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY style_guides_update ON style_guides
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY style_guides_delete ON style_guides
    FOR DELETE USING (auth.uid() = user_id);

-- Allow service role full access (backend uses service role key)
CREATE POLICY style_guides_service_role ON style_guides
    FOR ALL USING (true)
    WITH CHECK (true);
