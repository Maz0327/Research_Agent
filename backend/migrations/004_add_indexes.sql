-- Migration: Add performance indexes
-- Description: Add indexes for common query patterns
-- Date: 2025-12-18

-- Index for filtering by pipeline mode
CREATE INDEX IF NOT EXISTS idx_jobs_pipeline ON jobs(pipeline);

-- Index for angle discovery queries
CREATE INDEX IF NOT EXISTS idx_jobs_discovered_angles ON jobs USING GIN (discovered_angles);

-- Index for entity lookups
CREATE INDEX IF NOT EXISTS idx_jobs_entities ON jobs USING GIN (entities);

-- Index for timeline queries
CREATE INDEX IF NOT EXISTS idx_jobs_timeline_events ON jobs USING GIN (timeline_events);
