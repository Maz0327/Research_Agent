-- Migration 018: Add booster tracking fields
-- Purpose: Track booster execution state separately from main job status
-- This prevents booster from overwriting jobs.status (which must remain 'completed')

-- Add booster tracking columns
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS booster_status text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_started_at timestamptz DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_completed_at timestamptz DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_error text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS booster_progress_percent integer DEFAULT NULL;

-- Add constraint for booster_status values
-- Allowed: NULL (never run), 'queued', 'running', 'completed', 'failed'
ALTER TABLE jobs
ADD CONSTRAINT booster_status_check
CHECK (booster_status IS NULL OR booster_status IN ('queued', 'running', 'completed', 'failed'));

-- Add constraint for booster_progress_percent range
ALTER TABLE jobs
ADD CONSTRAINT booster_progress_percent_check
CHECK (booster_progress_percent IS NULL OR (booster_progress_percent >= 0 AND booster_progress_percent <= 100));

-- Add index for filtering by booster_status
CREATE INDEX IF NOT EXISTS idx_jobs_booster_status ON jobs(booster_status) WHERE booster_status IS NOT NULL;

-- Update RPC function to include booster fields
-- Drop and recreate to include new columns
DROP FUNCTION IF EXISTS atomic_update_job(uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean);

CREATE OR REPLACE FUNCTION atomic_update_job(
    p_job_id uuid,
    p_status text DEFAULT NULL,
    p_stage text DEFAULT NULL,
    p_progress_percent integer DEFAULT NULL,
    p_title text DEFAULT NULL,
    p_error text DEFAULT NULL,
    p_partial_outputs jsonb DEFAULT NULL,
    p_partial_artifacts jsonb DEFAULT NULL,
    p_warnings_append jsonb DEFAULT NULL,
    p_update_stage_timestamp boolean DEFAULT false,
    -- Booster fields
    p_booster_status text DEFAULT NULL,
    p_booster_started_at timestamptz DEFAULT NULL,
    p_booster_completed_at timestamptz DEFAULT NULL,
    p_booster_error text DEFAULT NULL,
    p_booster_progress_percent integer DEFAULT NULL
)
RETURNS jobs
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    result jobs;
BEGIN
    UPDATE jobs
    SET
        status = COALESCE(p_status, status),
        stage = COALESCE(p_stage, stage),
        progress_percent = COALESCE(p_progress_percent, progress_percent),
        title = COALESCE(p_title, title),
        error = COALESCE(p_error, error),
        outputs = CASE
            WHEN p_partial_outputs IS NOT NULL
            THEN COALESCE(outputs, '{}'::jsonb) || p_partial_outputs
            ELSE outputs
        END,
        artifacts = CASE
            WHEN p_partial_artifacts IS NOT NULL
            THEN COALESCE(artifacts, '{}'::jsonb) || p_partial_artifacts
            ELSE artifacts
        END,
        warnings = CASE
            WHEN p_warnings_append IS NOT NULL
            THEN COALESCE(warnings, '[]'::jsonb) || p_warnings_append
            ELSE warnings
        END,
        stage_started_at = CASE
            WHEN p_update_stage_timestamp THEN now()
            ELSE stage_started_at
        END,
        -- Booster fields (explicit set, not COALESCE to allow NULL clearing)
        booster_status = CASE WHEN p_booster_status IS NOT NULL THEN p_booster_status ELSE booster_status END,
        booster_started_at = CASE WHEN p_booster_started_at IS NOT NULL THEN p_booster_started_at ELSE booster_started_at END,
        booster_completed_at = CASE WHEN p_booster_completed_at IS NOT NULL THEN p_booster_completed_at ELSE booster_completed_at END,
        booster_error = CASE WHEN p_booster_error IS NOT NULL THEN p_booster_error ELSE booster_error END,
        booster_progress_percent = CASE WHEN p_booster_progress_percent IS NOT NULL THEN p_booster_progress_percent ELSE booster_progress_percent END
    WHERE id = p_job_id
    RETURNING * INTO result;

    RETURN result;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION atomic_update_job TO service_role;

-- Comment for documentation
COMMENT ON COLUMN jobs.booster_status IS 'Booster execution status: NULL (never run), queued, running, completed, failed';
COMMENT ON COLUMN jobs.booster_started_at IS 'When booster execution started';
COMMENT ON COLUMN jobs.booster_completed_at IS 'When booster execution completed (success or failure)';
COMMENT ON COLUMN jobs.booster_error IS 'Error message if booster failed';
COMMENT ON COLUMN jobs.booster_progress_percent IS 'Booster progress (0-100)';
