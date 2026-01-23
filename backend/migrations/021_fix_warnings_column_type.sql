-- Migration 021: Fix warnings column type mismatch
-- Purpose: Convert jobs.warnings from text[] to jsonb to match RPC expectations
-- Error: "COALESCE types jsonb and text[] cannot be matched" (code 42804)
--
-- The RPC uses: COALESCE(warnings, '[]'::jsonb) || p_warnings_append
-- But if warnings column is text[], PostgreSQL cannot match types in COALESCE
--
-- This migration:
-- 1. Converts warnings column from text[] to jsonb
-- 2. Recreates atomic_update_job RPC (same logic, but now column type matches)

-- Step 1: Convert warnings column from text[] to jsonb
-- Using a safe conversion that handles existing data
ALTER TABLE jobs
ALTER COLUMN warnings TYPE jsonb
USING COALESCE(to_jsonb(warnings), '[]'::jsonb);

-- Set default to empty jsonb array
ALTER TABLE jobs
ALTER COLUMN warnings SET DEFAULT '[]'::jsonb;

-- Step 2: Drop existing function signatures to avoid conflicts
-- Drop the 20-param signature from migration 020
DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean,
    text, timestamptz, timestamptz, text, integer,
    text, timestamptz, timestamptz, text, integer
);

-- Drop any older signatures that might exist
DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean,
    text, timestamptz, timestamptz, text, integer
);

DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, jsonb, boolean
);

-- Step 3: Recreate atomic_update_job with all fields (including producer tracking)
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
    p_producer_progress_percent integer DEFAULT NULL
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
        -- Now safe: warnings column is jsonb, COALESCE with '[]'::jsonb works
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
        producer_progress_percent = CASE WHEN p_producer_progress_percent IS NOT NULL THEN p_producer_progress_percent ELSE producer_progress_percent END
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
Includes booster and producer tracking fields.
Fixed in migration 021: warnings column converted from text[] to jsonb.';

-- Also update the standalone append_job_warnings function to match
DROP FUNCTION IF EXISTS append_job_warnings(uuid, jsonb);

CREATE OR REPLACE FUNCTION append_job_warnings(
    p_job_id UUID,
    p_warnings JSONB
)
RETURNS jobs AS $$
DECLARE
    result jobs;
BEGIN
    UPDATE jobs
    SET warnings = COALESCE(warnings, '[]'::jsonb) || p_warnings
    WHERE id = p_job_id
    RETURNING * INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION append_job_warnings(UUID, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION append_job_warnings(UUID, JSONB) TO authenticated;
