-- Migration 016: Add disambiguation fields for topic interpretation flow
-- These fields support the disambiguation workflow where ambiguous topics
-- are paused for user selection before research continues.

-- Add interpretations column (JSONB array of interpretation options)
-- Format: [{"label": "Short Name", "description": "Brief explanation", "topic": "Refined topic"}]
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS interpretations JSONB;

-- Add selected_interpretations column (array of selected indices)
-- Format: [0, 1] for first two interpretations, or [0] for single selection
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS selected_interpretations INTEGER[];

-- Add disambiguating status if using check constraint
-- (Optional - only if status is validated by database)
-- ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check;
-- ALTER TABLE jobs ADD CONSTRAINT jobs_status_check
--   CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'disambiguating'));

-- Create index for quick lookup of jobs awaiting disambiguation
CREATE INDEX IF NOT EXISTS idx_jobs_disambiguating
  ON jobs (status)
  WHERE status = 'disambiguating';

COMMENT ON COLUMN jobs.interpretations IS 'JSON array of disambiguation options when topic is ambiguous';
COMMENT ON COLUMN jobs.selected_interpretations IS 'Array of indices user selected from interpretations';
