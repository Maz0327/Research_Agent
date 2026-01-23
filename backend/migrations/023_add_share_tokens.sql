-- Migration 023: Add share_tokens table for document sharing
-- Allows users to create time-limited, revocable share links for documents

-- Create share_tokens table
CREATE TABLE IF NOT EXISTS share_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    doc_type VARCHAR(10) NOT NULL,  -- 'doc_0', 'doc_1', 'doc_2', 'doc_3', 'all'
    token VARCHAR(64) NOT NULL UNIQUE,  -- cryptographically secure token
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    view_count INT DEFAULT 0,
    max_views INT,  -- NULL = unlimited views
    is_revoked BOOLEAN DEFAULT FALSE,
    
    -- Constraints
    CONSTRAINT valid_doc_type CHECK (doc_type IN ('doc_0', 'doc_1', 'doc_2', 'doc_3', 'all'))
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_share_tokens_token ON share_tokens(token);
CREATE INDEX IF NOT EXISTS idx_share_tokens_job_id ON share_tokens(job_id);
CREATE INDEX IF NOT EXISTS idx_share_tokens_created_by ON share_tokens(created_by);
CREATE INDEX IF NOT EXISTS idx_share_tokens_expires_at ON share_tokens(expires_at);

-- RLS Policies
ALTER TABLE share_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only view share tokens they created
CREATE POLICY "Users can view own share tokens" ON share_tokens
    FOR SELECT
    USING (created_by = auth.uid());

-- Users can only create share tokens for their own jobs
CREATE POLICY "Users can create share tokens for own jobs" ON share_tokens
    FOR INSERT
    WITH CHECK (
        created_by = auth.uid() AND
        EXISTS (SELECT 1 FROM jobs WHERE jobs.id = share_tokens.job_id AND jobs.user_id = auth.uid())
    );

-- Users can only update (revoke) their own share tokens
CREATE POLICY "Users can update own share tokens" ON share_tokens
    FOR UPDATE
    USING (created_by = auth.uid());

-- Users can only delete their own share tokens
CREATE POLICY "Users can delete own share tokens" ON share_tokens
    FOR DELETE
    USING (created_by = auth.uid());

-- Comment on table
COMMENT ON TABLE share_tokens IS 'Time-limited share tokens for document sharing';
COMMENT ON COLUMN share_tokens.doc_type IS 'Document type: doc_0 (Source Ledger), doc_1 (Jump-Start), doc_2 (Semantic Brief), doc_3 (Producer Packet), or all';
COMMENT ON COLUMN share_tokens.token IS '64-character cryptographically secure share token';
COMMENT ON COLUMN share_tokens.max_views IS 'Maximum number of views allowed. NULL means unlimited.';
COMMENT ON COLUMN share_tokens.is_revoked IS 'If true, the share link is no longer valid';
