-- Migration 017: Restrict RPC function permissions (Security Fix)
-- Date: 2026-01-01
-- Purpose: Remove authenticated role access to JSONB merge functions
-- These functions should only be called by service_role (backend worker)

-- =============================================================================
-- Security Issue:
-- SECURITY DEFINER functions with GRANT to authenticated could allow
-- cross-tenant updates if exposed through client context.
-- =============================================================================

-- Revoke execute from authenticated role (client-accessible)
REVOKE EXECUTE ON FUNCTION merge_job_outputs(UUID, JSONB) FROM authenticated;
REVOKE EXECUTE ON FUNCTION merge_job_artifacts(UUID, JSONB) FROM authenticated;
REVOKE EXECUTE ON FUNCTION append_job_warnings(UUID, JSONB) FROM authenticated;
REVOKE EXECUTE ON FUNCTION atomic_update_job(UUID, TEXT, TEXT, INTEGER, TEXT, TEXT, JSONB, JSONB, JSONB, BOOLEAN) FROM authenticated;

-- service_role retains access (backend worker uses this)
-- GRANT already exists from migration 014, no action needed

-- Verify: After running this migration, only service_role should have EXECUTE
-- Query to verify:
-- SELECT grantee, privilege_type
-- FROM information_schema.routine_privileges
-- WHERE routine_name = 'atomic_update_job';

COMMENT ON FUNCTION atomic_update_job IS
'Atomically updates job fields including JSONB merges for outputs, artifacts, and warnings.
Prevents race conditions by performing all operations in a single transaction.
SECURITY: Only service_role can execute (not authenticated clients).';
