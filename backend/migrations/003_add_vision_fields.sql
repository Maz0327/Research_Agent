-- Migration: Add vision-required fields
-- Description: Add fields for timeline, entities, angles, and documentary intelligence
-- Date: 2025-12-18

-- Core vision features
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS timeline_events JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS entities JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS manual_guidance JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS reddit_posts JSONB DEFAULT '[]'::jsonb;

-- Output tracking
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS notebooklm_packet_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS documentary_blueprint_url TEXT;

-- Metrics
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_sources INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_claims INTEGER DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS api_costs JSONB DEFAULT '{}'::jsonb;

-- Angle discovery
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS discovered_angles JSONB DEFAULT '[]'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS coverage_analysis JSONB DEFAULT '{}'::jsonb;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS recommended_angle JSONB DEFAULT '{}'::jsonb;
