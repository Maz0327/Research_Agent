-- Migration 013: Add Quality Gate and Niche fields
-- PRD v4.3: Quality Gate filtering and Niche Overlay System
--
-- Adds:
-- - quality_gate_stats: JSONB storing QG results (approved/rejected counts, type weights)
-- - niche: TEXT field for niche overlay (downfalls, mysteries, etc.)

-- Add Quality Gate stats column
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS quality_gate_stats JSONB;

-- Add Niche column
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS niche TEXT;

-- Index for filtering by niche (partial index for non-null values)
CREATE INDEX IF NOT EXISTS idx_jobs_niche ON jobs(niche) WHERE niche IS NOT NULL;

-- Index for querying quality gate statistics (GIN for JSONB)
CREATE INDEX IF NOT EXISTS idx_jobs_quality_gate_stats ON jobs USING GIN (quality_gate_stats) WHERE quality_gate_stats IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN jobs.quality_gate_stats IS 'PRD v4.3 Quality Gate results: { total_discovered, after_dedup, approved_count, rejected_count, soft_rejected_count, type_weights, by_type, rejection_breakdown }';
COMMENT ON COLUMN jobs.niche IS 'PRD v4.3 Niche overlay applied: downfalls, mysteries, or NULL for default mode';

-- Example quality_gate_stats structure:
-- {
--   "total_discovered": 50,
--   "after_dedup": 42,
--   "approved_count": 25,
--   "rejected_count": 10,
--   "soft_rejected_count": 7,
--   "type_weights": {
--     "web": 0.25,
--     "news": 0.30,
--     "video": 0.20,
--     "academic": 0.15,
--     "discussion": 0.10
--   },
--   "by_type": {
--     "web": 6,
--     "news": 8,
--     "video": 5,
--     "academic": 4,
--     "discussion": 2
--   },
--   "rejection_breakdown": {
--     "duplicate": 5,
--     "junk_pattern": 3,
--     "domain_limit": 2,
--     "type_cap": 0,
--     "low_quality": 0
--   }
-- }
