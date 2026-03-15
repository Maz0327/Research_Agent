-- Migration 026: Atomic share view count increment
--
-- Fixes race condition in GET /shared/{token} where concurrent requests
-- could exceed max_views due to non-atomic read-modify-write.
-- See: TODO(audit-H8) in share_routes.py

CREATE OR REPLACE FUNCTION increment_share_view_count(
    p_share_id UUID,
    p_max_views INT DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    new_count INT;
BEGIN
    UPDATE share_tokens
    SET view_count = COALESCE(view_count, 0) + 1
    WHERE id = p_share_id
      AND (p_max_views IS NULL OR COALESCE(view_count, 0) < p_max_views)
    RETURNING view_count INTO new_count;

    RETURN new_count;  -- NULL if no row updated (limit reached)
END;
$$ LANGUAGE plpgsql;
