-- Migration 014: Add atomic JSONB merge functions
-- Fixes race condition in update_job() by performing merges atomically in PostgreSQL
-- Date: 2025-12-28

-- Function to atomically merge JSONB data into a job's outputs
CREATE OR REPLACE FUNCTION merge_job_outputs(
    p_job_id UUID,
    p_outputs JSONB
)
RETURNS jobs AS $$
DECLARE
    result jobs;
BEGIN
    UPDATE jobs
    SET outputs = COALESCE(outputs, '{}'::jsonb) || p_outputs
    WHERE id = p_job_id
    RETURNING * INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to atomically merge JSONB data into a job's artifacts
CREATE OR REPLACE FUNCTION merge_job_artifacts(
    p_job_id UUID,
    p_artifacts JSONB
)
RETURNS jobs AS $$
DECLARE
    result jobs;
BEGIN
    UPDATE jobs
    SET artifacts = COALESCE(artifacts, '{}'::jsonb) || p_artifacts
    WHERE id = p_job_id
    RETURNING * INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to atomically append warnings to a job
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

-- Combined function for atomic job update with all merge operations
-- This is the main function used by the application
CREATE OR REPLACE FUNCTION atomic_update_job(
    p_job_id UUID,
    p_status TEXT DEFAULT NULL,
    p_stage TEXT DEFAULT NULL,
    p_progress_percent INTEGER DEFAULT NULL,
    p_title TEXT DEFAULT NULL,
    p_error TEXT DEFAULT NULL,
    p_partial_outputs JSONB DEFAULT NULL,
    p_partial_artifacts JSONB DEFAULT NULL,
    p_warnings_append JSONB DEFAULT NULL,
    p_update_stage_timestamp BOOLEAN DEFAULT FALSE
)
RETURNS jobs AS $$
DECLARE
    result jobs;
    update_fields TEXT[] := ARRAY[]::TEXT[];
    set_clause TEXT := '';
BEGIN
    -- Build dynamic SET clause for non-null fields
    IF p_status IS NOT NULL THEN
        update_fields := array_append(update_fields, format('status = %L', p_status));
    END IF;

    IF p_stage IS NOT NULL THEN
        update_fields := array_append(update_fields, format('stage = %L', p_stage));
        IF p_update_stage_timestamp THEN
            update_fields := array_append(update_fields, 'stage_started_at = NOW()');
        END IF;
    END IF;

    IF p_progress_percent IS NOT NULL THEN
        update_fields := array_append(update_fields, format('progress_percent = %s', p_progress_percent));
    END IF;

    IF p_title IS NOT NULL THEN
        update_fields := array_append(update_fields, format('title = %L', p_title));
    END IF;

    IF p_error IS NOT NULL THEN
        update_fields := array_append(update_fields, format('error = %L', p_error));
    END IF;

    -- Atomic JSONB merges using || operator
    IF p_partial_outputs IS NOT NULL THEN
        update_fields := array_append(update_fields, format('outputs = COALESCE(outputs, ''{}''::jsonb) || %L::jsonb', p_partial_outputs));
    END IF;

    IF p_partial_artifacts IS NOT NULL THEN
        update_fields := array_append(update_fields, format('artifacts = COALESCE(artifacts, ''{}''::jsonb) || %L::jsonb', p_partial_artifacts));
    END IF;

    IF p_warnings_append IS NOT NULL THEN
        update_fields := array_append(update_fields, format('warnings = COALESCE(warnings, ''[]''::jsonb) || %L::jsonb', p_warnings_append));
    END IF;

    -- If no fields to update, just return the current record
    IF array_length(update_fields, 1) IS NULL OR array_length(update_fields, 1) = 0 THEN
        SELECT * INTO result FROM jobs WHERE id = p_job_id;
        RETURN result;
    END IF;

    -- Build and execute the update
    set_clause := array_to_string(update_fields, ', ');

    EXECUTE format('UPDATE jobs SET %s WHERE id = %L RETURNING *', set_clause, p_job_id)
    INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permissions to authenticated users (service role will have access)
GRANT EXECUTE ON FUNCTION merge_job_outputs(UUID, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION merge_job_artifacts(UUID, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION append_job_warnings(UUID, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION atomic_update_job(UUID, TEXT, TEXT, INTEGER, TEXT, TEXT, JSONB, JSONB, JSONB, BOOLEAN) TO authenticated;

-- Grant to service_role for worker access
GRANT EXECUTE ON FUNCTION merge_job_outputs(UUID, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION merge_job_artifacts(UUID, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION append_job_warnings(UUID, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION atomic_update_job(UUID, TEXT, TEXT, INTEGER, TEXT, TEXT, JSONB, JSONB, JSONB, BOOLEAN) TO service_role;

-- Add comment for documentation
COMMENT ON FUNCTION atomic_update_job IS
'Atomically updates job fields including JSONB merges for outputs, artifacts, and warnings.
Prevents race conditions by performing all operations in a single transaction.';
