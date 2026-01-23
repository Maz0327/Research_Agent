-- Migration 022: Add iteration tracking columns and concurrency protection
-- Purpose:
--   1. Add iteration tracking columns to jobs table
--   2. Update atomic_update_job RPC to support iteration fields
--   3. Add unique partial index to prevent concurrent iterations (TOCTOU fix)
-- Date: 2026-01-23

-- ============================================================================
-- Step 1: Add iteration tracking columns
-- ============================================================================
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_status text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_id text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_started_at timestamptz;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_completed_at timestamptz;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_error text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS iteration_progress_percent integer;

-- Add check constraint for iteration_progress_percent
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_iteration_progress_percent_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_iteration_progress_percent_check
    CHECK (iteration_progress_percent IS NULL OR (iteration_progress_percent >= 0 AND iteration_progress_percent <= 100));

-- ============================================================================
-- Step 2: Add unique partial index to prevent concurrent iterations
-- This is the TOCTOU race condition fix: database enforces only one
-- queued/running iteration per job at a time
-- ============================================================================
DROP INDEX IF EXISTS idx_one_active_iteration_per_job;
CREATE UNIQUE INDEX idx_one_active_iteration_per_job
    ON jobs (id)
    WHERE iteration_status IN ('queued', 'running');

COMMENT ON INDEX idx_one_active_iteration_per_job IS
'Prevents race condition: only one queued or running iteration allowed per job.
If two requests try to start an iteration simultaneously, the second will fail
with a unique constraint violation, which the API converts to HTTP 409.';

-- ============================================================================
-- Step 3: Update atomic_update_job RPC to support iteration fields
-- ============================================================================

-- Drop existing function signatures to avoid conflicts
DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean,
    text, timestamptz, timestamptz, text, integer,
    text, timestamptz, timestamptz, text, integer
);

DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean,
    text, timestamptz, timestamptz, text, integer,
    text, timestamptz, timestamptz, text, integer,
    text, text, timestamptz, timestamptz, text, integer
);

-- Recreate atomic_update_job with iteration fields
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
    p_booster_progress_percent integer DEFAULT NULL,
    -- Producer fields
    p_producer_status text DEFAULT NULL,
    p_producer_started_at timestamptz DEFAULT NULL,
    p_producer_completed_at timestamptz DEFAULT NULL,
    p_producer_error text DEFAULT NULL,
    p_producer_progress_percent integer DEFAULT NULL,
    -- Iteration fields (NEW)
    p_iteration_status text DEFAULT NULL,
    p_iteration_id text DEFAULT NULL,
    p_iteration_started_at timestamptz DEFAULT NULL,
    p_iteration_completed_at timestamptz DEFAULT NULL,
    p_iteration_error text DEFAULT NULL,
    p_iteration_progress_percent integer DEFAULT NULL
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
        -- Booster fields
        booster_status = CASE WHEN p_booster_status IS NOT NULL THEN p_booster_status ELSE booster_status END,
        booster_started_at = CASE WHEN p_booster_started_at IS NOT NULL THEN p_booster_started_at ELSE booster_started_at END,
        booster_completed_at = CASE WHEN p_booster_completed_at IS NOT NULL THEN p_booster_completed_at ELSE booster_completed_at END,
        booster_error = CASE WHEN p_booster_error IS NOT NULL THEN p_booster_error ELSE booster_error END,
        booster_progress_percent = CASE WHEN p_booster_progress_percent IS NOT NULL THEN p_booster_progress_percent ELSE booster_progress_percent END,
        -- Producer fields
        producer_status = CASE WHEN p_producer_status IS NOT NULL THEN p_producer_status ELSE producer_status END,
        producer_started_at = CASE WHEN p_producer_started_at IS NOT NULL THEN p_producer_started_at ELSE producer_started_at END,
        producer_completed_at = CASE WHEN p_producer_completed_at IS NOT NULL THEN p_producer_completed_at ELSE producer_completed_at END,
        producer_error = CASE WHEN p_producer_error IS NOT NULL THEN p_producer_error ELSE producer_error END,
        producer_progress_percent = CASE WHEN p_producer_progress_percent IS NOT NULL THEN p_producer_progress_percent ELSE producer_progress_percent END,
        -- Iteration fields (NEW)
        iteration_status = CASE WHEN p_iteration_status IS NOT NULL THEN p_iteration_status ELSE iteration_status END,
        iteration_id = CASE WHEN p_iteration_id IS NOT NULL THEN p_iteration_id ELSE iteration_id END,
        iteration_started_at = CASE WHEN p_iteration_started_at IS NOT NULL THEN p_iteration_started_at ELSE iteration_started_at END,
        iteration_completed_at = CASE WHEN p_iteration_completed_at IS NOT NULL THEN p_iteration_completed_at ELSE iteration_completed_at END,
        iteration_error = CASE WHEN p_iteration_error IS NOT NULL THEN p_iteration_error ELSE iteration_error END,
        iteration_progress_percent = CASE WHEN p_iteration_progress_percent IS NOT NULL THEN p_iteration_progress_percent ELSE iteration_progress_percent END
    WHERE id = p_job_id
    RETURNING * INTO result;

    RETURN result;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION atomic_update_job TO service_role;
GRANT EXECUTE ON FUNCTION atomic_update_job TO authenticated;

-- Comment for documentation
COMMENT ON FUNCTION atomic_update_job IS
'Atomically updates job fields including JSONB merges for outputs, artifacts, and warnings.
Includes booster, producer, and iteration tracking fields.
Updated in migration 022: Added iteration fields and concurrency protection.';
