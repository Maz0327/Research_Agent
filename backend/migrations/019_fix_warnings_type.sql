-- Migration 019: Fix atomic_update_job warnings type mismatch
-- Purpose: Fix COALESCE type error (jsonb vs text[])
-- The warnings column is jsonb, but migration 018 incorrectly used text[]
-- Error: "COALESCE types jsonb and text[] cannot be matched" (code 42804)

-- Drop the broken function (15-param signature from migration 018)
DROP FUNCTION IF EXISTS atomic_update_job(
    uuid, text, text, integer, text, text, jsonb, jsonb, text[], boolean,
    text, timestamptz, timestamptz, text, integer
);

-- Recreate with correct types: p_warnings_append is JSONB, not text[]
CREATE OR REPLACE FUNCTION atomic_update_job(
    p_job_id uuid,
    p_status text DEFAULT NULL,
    p_stage text DEFAULT NULL,
    p_progress_percent integer DEFAULT NULL,
    p_title text DEFAULT NULL,
    p_error text DEFAULT NULL,
    p_partial_outputs jsonb DEFAULT NULL,
    p_partial_artifacts jsonb DEFAULT NULL,
    p_warnings_append jsonb DEFAULT NULL,  -- FIXED: was text[], now jsonb
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
            THEN COALESCE(warnings, '[]'::jsonb) || p_warnings_append  -- FIXED: '[]'::jsonb not ARRAY[]::text[]
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
COMMENT ON FUNCTION atomic_update_job IS
'Atomically updates job fields including JSONB merges for outputs, artifacts, and warnings.
Includes booster tracking fields. Fixed in migration 019 to use jsonb for warnings (not text[]).';
