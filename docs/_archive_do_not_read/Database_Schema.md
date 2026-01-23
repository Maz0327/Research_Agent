# Database Schema Reference

**Document Type:** Reference (Non-Authoritative)
**Location:** `docs/Database_Schema.md`
**Status:** Final
**Last Updated:** January 13, 2026

> **Note:** This is a reference document for database schema structure.
> For authoritative specifications, see [`docs/authoritative/INDEX.md`](authoritative/INDEX.md) — the Repo Constitution.
> If any content here conflicts with INDEX.md, **INDEX.md wins**.

---

## Overview

This document defines the database schema for the Research Agent system. It describes the intended table structures and relationships.

### Design Principles

1. **Sources are first-class entities** — Not buried in JSONB
2. **Extractions stored per-source** — Enables source isolation validation
3. **Documents are versioned** — Can regenerate without losing history
4. **Validation audit trail** — Every check is logged
5. **Multi-user ready** — Proper user isolation and queryability
6. **JSONB for complex nested data** — Don't over-normalize internal structures

---

## Entity Relationship Diagram

```
┌─────────────────┐
│   auth.users    │ (Supabase managed)
└────────┬────────┘
         │
         │ 1:M
         ▼
┌─────────────────┐       ┌─────────────────┐
│  user_settings  │       │   admin_users   │
└─────────────────┘       └─────────────────┘
         │
         │ 1:M
         ▼
┌─────────────────┐
│      jobs       │
└────────┬────────┘
         │
    ┌────┴────┬──────────────┬──────────────┐
    │         │              │              │
    │ 1:M     │ 1:M          │ 1:1          │ 1:1
    ▼         ▼              ▼              ▼
┌────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────────┐
│sources │ │ documents │ │ synthesis │ │ booster_results │
└───┬────┘ └───────────┘ └───────────┘ └─────────────────┘
    │
    │ 1:1
    ▼
┌─────────────┐
│ extractions │
└─────────────┘

┌─────────────┐
│ validations │ ←── References jobs and optionally sources
└─────────────┘

┌─────────────┐
│ error_logs  │ ←── References jobs, sources, users
└─────────────┘
```

---

## Table Specifications

### 1. `jobs`

The central job record. One row per research job.

```sql
CREATE TABLE jobs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    title TEXT,
    topic TEXT,
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'processing_sources',
            'extracting',
            'validating',
            'synthesizing',
            'assembling',
            'completed',
            'completed_with_warnings',
            'failed',
            'cancelled'
        )),
    stage TEXT,
    progress_percent INTEGER NOT NULL DEFAULT 0
        CHECK (progress_percent BETWEEN 0 AND 100),
    
    -- Configuration
    pipeline TEXT NOT NULL DEFAULT 'full'
        CHECK (pipeline IN ('full', 'quick', 'sources_only')),
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Scope lock (set after first source analyzed)
    scope_lock JSONB,
    -- Schema: { topic: string, boundaries: string[], not_about: string[] }
    
    -- Aggregated stats (denormalized for quick queries)
    source_count INTEGER NOT NULL DEFAULT 0,
    high_confidence_count INTEGER NOT NULL DEFAULT 0,
    
    -- Job-level warnings and errors
    warnings JSONB DEFAULT '[]',
    error TEXT,
    
    -- Cost tracking
    api_costs JSONB DEFAULT '{}',
    -- Schema: { gemini: { calls, tokens_in, tokens_out, cost }, supadata: { calls, cost } }
    
    -- Booster status (quick lookup without joining booster_results)
    booster_status TEXT DEFAULT 'not_requested'
        CHECK (booster_status IN ('not_requested', 'pending', 'running', 'completed', 'failed')),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    stage_started_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_user_created ON jobs(user_id, created_at DESC);
CREATE INDEX idx_jobs_status_created ON jobs(status, created_at DESC);
```

**Notes:**
- `warnings` is an array of warning objects, not a map
- `config` stores job-specific settings (overrides user defaults)
- `scope_lock` is set during first extraction to prevent drift

---

### 2. `sources`

One row per source within a job. This is the key table for source isolation.

```sql
CREATE TABLE sources (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Source identity (assigned BEFORE any LLM call)
    source_index INTEGER NOT NULL,
    source_id TEXT GENERATED ALWAYS AS ('SRC_' || source_index) STORED,
    
    -- Source type and analysis mode
    source_type TEXT NOT NULL
        CHECK (source_type IN ('youtube', 'article', 'text', 'screenshot')),
    analysis_mode TEXT NOT NULL
        CHECK (analysis_mode IN (
            'transcript_grounded',
            'caption_grounded',
            'video_only',
            'text_provided',
            'ocr_extracted',
            'article_fetched'
        )),
    confidence_ceiling TEXT NOT NULL
        CHECK (confidence_ceiling IN ('high', 'medium', 'low')),
    
    -- Metadata (resolved before LLM)
    url TEXT,
    title TEXT NOT NULL,
    creator TEXT,
    published_at DATE,
    duration_seconds INTEGER,
    description TEXT,
    
    -- Transcript provenance
    transcript_provenance JSONB NOT NULL DEFAULT '{}',
    -- Schema: {
    --   method: 'supadata' | 'whisper' | 'youtube_captions' | 'none',
    --   quality: 'full' | 'partial' | 'unavailable',
    --   timestamp_reliability: 'high' | 'medium' | 'low' | 'none',
    --   acquisition_timestamp: ISO datetime,
    --   failure_log: [{ service, error, timestamp }]
    -- }
    
    -- Content storage
    full_text TEXT,
    full_text_storage TEXT NOT NULL DEFAULT 'unavailable'
        CHECK (full_text_storage IN ('inline', 'blob_reference', 'unavailable')),
    blob_reference TEXT,
    
    -- Processing status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',
            'acquiring',
            'acquired',
            'extracting',
            'extracted',
            'failed'
        )),
    
    -- Skim summary (factual, non-interpretive)
    skim_summary TEXT,
    
    -- Degradation tracking
    degradation_notes JSONB DEFAULT '[]',
    -- Schema: [{ stage, issue, impact, timestamp }]
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    UNIQUE(job_id, source_index)
);

-- Indexes
CREATE INDEX idx_sources_job_id ON sources(job_id);
CREATE INDEX idx_sources_status ON sources(status);
CREATE INDEX idx_sources_analysis_mode ON sources(analysis_mode);
CREATE INDEX idx_sources_confidence ON sources(confidence_ceiling);
CREATE INDEX idx_sources_job_status ON sources(job_id, status);
```

**Critical Rules:**
- `source_id` is auto-generated from `source_index` — never set manually
- `analysis_mode` and `confidence_ceiling` are set BEFORE extraction
- `title` is required — resolved from metadata before LLM calls

---

### 3. `extractions`

One row per source. Stores the LLM extraction results.

```sql
CREATE TABLE extractions (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL UNIQUE REFERENCES sources(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Extraction results (complex nested structures in JSONB)
    key_points JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   key_point_id: string,
    --   statement: string,
    --   confidence: 'high' | 'medium' | 'low',
    --   timestamp: string | null,
    --   supporting_quote_ids: string[] | null,
    --   supporting_observation_ids: string[] | null
    -- }]
    
    claims JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   claim_id: string,
    --   statement: string,
    --   speaker: string | null,
    --   timestamp: string | null,
    --   confidence: 'high' | 'medium' | 'low',
    --   verifiable: boolean,
    --   claim_type: 'factual' | 'opinion' | 'prediction'
    -- }]
    
    quotes JSONB DEFAULT '[]',
    -- Schema: [{
    --   quote_id: string,
    --   text: string,
    --   speaker: string | null,
    --   timestamp: string | null,
    --   context: string | null,
    --   verification_status: 'verified' | 'unverified' | 'failed'
    -- }]
    -- MUST be empty [] for video_only, text_provided, ocr_extracted modes
    
    observations JSONB DEFAULT '[]',
    -- Schema: [{
    --   observation_id: string,
    --   description: string,
    --   timestamp: string | null,
    --   type: 'visual' | 'behavioral' | 'contextual',
    --   approximate: true
    -- }]
    -- ONLY used for video_only mode (mutually exclusive with quotes)
    
    themes JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   theme_id: string,
    --   name: string,
    --   description: string,
    --   supporting_key_point_ids: string[]
    -- }]
    
    tensions JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   tension_id: string,
    --   description: string,
    --   nature: 'contradiction' | 'ambiguity' | 'gap',
    --   related_key_point_ids: string[]
    -- }]
    
    entities JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   name: string,
    --   type: 'person' | 'organization' | 'location' | 'event' | 'concept',
    --   first_mention_timestamp: string | null
    -- }]
    
    gaps JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   gap_id: string,
    --   description: string,
    --   importance: 'high' | 'medium' | 'low'
    -- }]
    
    -- Extraction metadata
    extraction_metadata JSONB NOT NULL,
    -- Schema: {
    --   extracted_at: ISO datetime,
    --   model: string,
    --   model_version: string,
    --   confidence_ceiling_applied: 'high' | 'medium' | 'low',
    --   retry_count: number,
    --   prompt_version: string
    -- }
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_extractions_job_id ON extractions(job_id);
CREATE INDEX idx_extractions_source_id ON extractions(source_id);
CREATE INDEX idx_extractions_status ON extractions(status);
```

**Critical Rules:**
- 1:1 with sources — enforced by UNIQUE constraint on source_id
- `quotes` and `observations` are mutually exclusive based on analysis_mode
- `extraction_metadata.confidence_ceiling_applied` must match source's ceiling

---

### 4. `synthesis`

One row per job. Stores cross-source analysis results.

```sql
CREATE TABLE synthesis (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Cross-source analysis results
    cross_source_themes JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   theme_id: string,
    --   name: string,
    --   description: string,
    --   source_ids: string[],
    --   prevalence: number (0-1),
    --   supporting_evidence: [{ source_id, key_point_id }],
    --   confidence: 'high' | 'medium' | 'low',
    --   single_source: boolean
    -- }]
    
    cross_source_tensions JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   tension_id: string,
    --   description: string,
    --   nature: 'contradiction' | 'disagreement' | 'gap',
    --   sources_involved: string[],
    --   position_a: { source_id, statement },
    --   position_b: { source_id, statement },
    --   resolution_status: 'unresolved' | 'explained' | 'needs_research'
    -- }]
    
    source_concordance JSONB NOT NULL DEFAULT '{}',
    -- Schema: {
    --   sources_agree_on: string[],
    --   sources_disagree_on: string[],
    --   single_source_claims: string[]
    -- }
    
    confidence_assessment JSONB NOT NULL DEFAULT '{}',
    -- Schema: {
    --   overall_confidence: 'high' | 'medium' | 'low',
    --   confidence_rationale: string,
    --   strongest_areas: string[],
    --   weakest_areas: string[],
    --   limiting_factors: string[]
    -- }
    
    synthesis_gaps JSONB NOT NULL DEFAULT '[]',
    -- Schema: [{
    --   gap_id: string,
    --   description: string,
    --   importance: 'high' | 'medium' | 'low',
    --   would_help: string,
    --   related_tensions: string[]
    -- }]
    
    narrative_threads JSONB DEFAULT '[]',
    -- Schema: [{
    --   thread_id: string,
    --   name: string,
    --   description: string,
    --   source_sequence: string[],
    --   key_moments: [{ source_id, timestamp, description }]
    -- }]
    
    -- Metadata
    synthesis_metadata JSONB NOT NULL,
    -- Schema: {
    --   synthesized_at: ISO datetime,
    --   model: string,
    --   sources_analyzed: number,
    --   source_ids: string[]
    -- }
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped')),
    error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index
CREATE INDEX idx_synthesis_job_id ON synthesis(job_id);
CREATE INDEX idx_synthesis_status ON synthesis(status);
```

**Notes:**
- `skipped` status used when job has only 1 source (no cross-source analysis needed)
- Synthesis is the ONLY stage that sees multiple sources together

---

### 5. `documents`

Stores generated output documents with versioning.

```sql
CREATE TABLE documents (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Document identity
    document_type TEXT NOT NULL
        CHECK (document_type IN (
            'source_ledger',         -- Doc 0
            'jump_start_directions', -- Doc 1
            'semantic_brief',        -- Doc 2
            'producer_packet'        -- Doc 3
        )),
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Content
    content JSONB NOT NULL,
    
    -- Rendered versions
    markdown_rendered TEXT,
    
    -- Versioning
    is_current BOOLEAN NOT NULL DEFAULT true,
    superseded_by UUID REFERENCES documents(id),
    supersedes UUID REFERENCES documents(id),
    
    -- Generation metadata
    generation_metadata JSONB,
    -- Schema: {
    --   generated_at: ISO datetime,
    --   source_count: number,
    --   synthesis_included: boolean,
    --   booster_included: boolean
    -- }
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partial unique index: only one current doc per type per job
CREATE UNIQUE INDEX idx_documents_current 
    ON documents(job_id, document_type) 
    WHERE is_current = true;

-- Other indexes
CREATE INDEX idx_documents_job_id ON documents(job_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_job_type ON documents(job_id, document_type);
```

**Notes:**
- Versioning allows regeneration without losing history
- `is_current` flag enables quick "get latest" queries
- Doc 3 (producer_packet) is gated: only generated with 4+ sources, 1+ high-confidence

---

### 6. `validations`

Audit trail for all validation checks.

```sql
CREATE TABLE validations (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    
    -- Validation details
    stage TEXT NOT NULL
        CHECK (stage IN ('extraction', 'synthesis', 'assembly')),
    validation_check TEXT NOT NULL,
    -- Values: V1 (schema), V2 (source_id), V3 (ceiling), V4 (quotes), 
    --         V5 (grounding), V6 (mode_rules), V7 (empty), V8 (cross_ref),
    --         V9 (doc_schema), V10 (gating)
    
    severity TEXT NOT NULL
        CHECK (severity IN ('hard_fail', 'soft_fail', 'warning')),
    
    -- Result
    passed BOOLEAN NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    
    -- Resolution (for failures)
    action_taken TEXT,
    -- Values: 'retry', 'degrade', 'abort', 'none'
    retry_attempted BOOLEAN NOT NULL DEFAULT false,
    retry_succeeded BOOLEAN,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_validations_job_id ON validations(job_id);
CREATE INDEX idx_validations_source_id ON validations(source_id);
CREATE INDEX idx_validations_check ON validations(validation_check);
CREATE INDEX idx_validations_severity ON validations(severity);
CREATE INDEX idx_validations_failed ON validations(passed) WHERE passed = false;
```

**Notes:**
- Every validation check creates a row (pass or fail)
- Enables queries like "show all V4 failures across all jobs"
- `source_id` is NULL for job-level validations (synthesis, assembly)

---

### 7. `booster_results`

Stores optional deep research booster output.

```sql
CREATE TABLE booster_results (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Stage outputs
    stage1_deep_gaps JSONB,
    -- Schema: [{ gap_id, description, why_important, what_would_help }]
    
    stage2_research_directions JSONB,
    -- Schema: [{ direction_id, description, sources_to_find, search_strategy }]
    
    stage3_search_queries JSONB,
    -- Schema: [{ query_id, query, platform, expected_results }]
    
    stage4_context_bundle JSONB,
    -- Schema: { summary, key_questions, research_priorities, suggested_workflow }
    
    -- Progress tracking
    stages_completed INTEGER NOT NULL DEFAULT 0
        CHECK (stages_completed BETWEEN 0 AND 4),
    current_stage INTEGER
        CHECK (current_stage BETWEEN 1 AND 4),
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index
CREATE INDEX idx_booster_results_job_id ON booster_results(job_id);
CREATE INDEX idx_booster_results_status ON booster_results(status);
```

**Notes:**
- Booster is optional — row only created if requested
- Each stage builds on previous stages
- Augments Doc 1 only — does not modify Doc 0 or Doc 2

---

### 8. `user_settings`

User preferences and configuration.

```sql
CREATE TABLE user_settings (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id),
    
    -- Profile
    username VARCHAR(50) UNIQUE,
    
    -- Default preferences
    default_pipeline TEXT DEFAULT 'full'
        CHECK (default_pipeline IN ('full', 'quick', 'sources_only')),
    max_sources INTEGER DEFAULT 25
        CHECK (max_sources BETWEEN 1 AND 50),
    
    -- Notification preferences
    email_on_complete BOOLEAN DEFAULT true,
    email_on_failure BOOLEAN DEFAULT true,
    email_summary BOOLEAN DEFAULT false,
    
    -- UI preferences
    jobs_per_page INTEGER DEFAULT 10
        CHECK (jobs_per_page BETWEEN 5 AND 100),
    default_sort TEXT DEFAULT 'newest'
        CHECK (default_sort IN ('newest', 'oldest', 'status')),
    show_progress_details BOOLEAN DEFAULT true,
    
    -- External integrations
    drive_folder_id TEXT,
    drive_folders JSONB DEFAULT '[]',
    default_folder_id VARCHAR(255),
    
    -- Admin flags
    is_banned BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX idx_user_settings_username ON user_settings(username);
CREATE INDEX idx_user_settings_banned ON user_settings(is_banned) WHERE is_banned = true;
```

---

### 9. `admin_users`

Admin access control.

```sql
CREATE TABLE admin_users (
    -- Identity
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    
    -- Grant tracking
    granted_at TIMESTAMPTZ DEFAULT now(),
    granted_by UUID REFERENCES auth.users(id)
);

-- Index
CREATE INDEX idx_admin_users_user_id ON admin_users(user_id);
```

---

### 10. `error_logs`

Comprehensive error tracking.

```sql
CREATE TABLE error_logs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References (all optional for flexibility)
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    
    -- Error classification
    error_category VARCHAR(50) NOT NULL,
    -- Values: 'transcript_acquisition', 'extraction', 'validation', 
    --         'synthesis', 'assembly', 'api', 'auth', 'unknown'
    stage VARCHAR(50),
    endpoint VARCHAR(100),
    error_code VARCHAR(50),
    
    -- Messages
    user_message TEXT NOT NULL,
    technical_message TEXT NOT NULL,
    stack_trace TEXT,
    
    -- Context
    request_data JSONB,
    
    -- Resolution tracking
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id),
    resolution_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_error_logs_job_id ON error_logs(job_id);
CREATE INDEX idx_error_logs_source_id ON error_logs(source_id);
CREATE INDEX idx_error_logs_user_id ON error_logs(user_id);
CREATE INDEX idx_error_logs_category ON error_logs(error_category);
CREATE INDEX idx_error_logs_created ON error_logs(created_at DESC);
CREATE INDEX idx_error_logs_unresolved ON error_logs(resolved) WHERE resolved = false;
```

---

## Table Summary

| Table | Purpose | Rows per Job | Key Relationships |
|-------|---------|--------------|-------------------|
| `jobs` | Main job record | 1 | user_id → auth.users |
| `sources` | Individual sources | 1-25 | job_id → jobs |
| `extractions` | Per-source extraction | 1-25 | source_id → sources (1:1) |
| `synthesis` | Cross-source analysis | 0-1 | job_id → jobs (1:1) |
| `documents` | Output docs (0/1/2/3) | 3-4+ | job_id → jobs |
| `validations` | Validation audit trail | Many | job_id, source_id |
| `booster_results` | Optional booster | 0-1 | job_id → jobs (1:1) |
| `user_settings` | User preferences | 1 per user | user_id → auth.users |
| `admin_users` | Admin access | 1 per admin | user_id → auth.users |
| `error_logs` | Error tracking | Variable | job_id, source_id, user_id |

---

## Migration Plan

### Phase 1: Add New Tables (Non-Breaking)

```sql
-- Create new tables without touching existing
CREATE TABLE sources (...);
CREATE TABLE extractions (...);
CREATE TABLE synthesis (...);
CREATE TABLE documents (...);
CREATE TABLE validations (...);
CREATE TABLE booster_results (...);

-- Add source_id FK to error_logs
ALTER TABLE error_logs ADD COLUMN source_id UUID REFERENCES sources(id);
CREATE INDEX idx_error_logs_source_id ON error_logs(source_id);
```

### Phase 2: Add New Columns to Jobs

```sql
ALTER TABLE jobs 
    ADD COLUMN scope_lock JSONB,
    ADD COLUMN source_count INTEGER DEFAULT 0,
    ADD COLUMN high_confidence_count INTEGER DEFAULT 0,
    ADD COLUMN booster_status TEXT DEFAULT 'not_requested';

-- Add check constraint
ALTER TABLE jobs ADD CONSTRAINT jobs_booster_status_check 
    CHECK (booster_status IN ('not_requested', 'pending', 'running', 'completed', 'failed'));
```

### Phase 3: Deprecate Legacy Columns

```sql
-- Mark as deprecated (don't delete yet)
COMMENT ON COLUMN jobs.reddit_posts IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.notebooklm_packet_url IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.documentary_blueprint_url IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.discovered_angles IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.coverage_analysis IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.recommended_angle IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.interpretations IS 'DEPRECATED: Legacy disambiguation - do not use';
COMMENT ON COLUMN jobs.selected_interpretations IS 'DEPRECATED: Legacy disambiguation - do not use';
COMMENT ON COLUMN jobs.timeline_events IS 'DEPRECATED: Moved to extractions - do not use';
COMMENT ON COLUMN jobs.entities IS 'DEPRECATED: Moved to extractions - do not use';
COMMENT ON COLUMN jobs.manual_guidance IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.total_sources IS 'DEPRECATED: Use source_count - do not use';
COMMENT ON COLUMN jobs.total_claims IS 'DEPRECATED: Compute from extractions - do not use';
COMMENT ON COLUMN jobs.niche IS 'DEPRECATED: Legacy pipeline - do not use';
COMMENT ON COLUMN jobs.quality_gate_stats IS 'DEPRECATED: Use validations table - do not use';
```

### Phase 4: Update Status Enum

```sql
-- Add new status values
ALTER TABLE jobs DROP CONSTRAINT IF EXISTS jobs_status_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_status_check 
    CHECK (status IN (
        'pending',
        'processing_sources',
        'extracting',
        'validating',
        'synthesizing',
        'assembling',
        'completed',
        'completed_with_warnings',
        'failed',
        'cancelled',
        -- Legacy values (keep for old jobs)
        'disambiguating',
        'processing',
        'analyzing'
    ));
```

### Phase 5: Drop Legacy Columns (Future)

Only after all old jobs are archived or migrated:

```sql
-- NOT YET - only after confirming no active use
-- ALTER TABLE jobs DROP COLUMN reddit_posts;
-- ALTER TABLE jobs DROP COLUMN notebooklm_packet_url;
-- etc.
```

---

## Queries Reference

### Common Queries

**Get job with all sources:**
```sql
SELECT j.*, 
       json_agg(s.*) as sources
FROM jobs j
LEFT JOIN sources s ON s.job_id = j.id
WHERE j.id = $1
GROUP BY j.id;
```

**Get full job with extractions:**
```sql
SELECT j.*,
       json_agg(json_build_object(
           'source', s.*,
           'extraction', e.*
       )) as source_extractions
FROM jobs j
LEFT JOIN sources s ON s.job_id = j.id
LEFT JOIN extractions e ON e.source_id = s.id
WHERE j.id = $1
GROUP BY j.id;
```

**Find all video_only sources:**
```sql
SELECT s.*, j.title as job_title, j.user_id
FROM sources s
JOIN jobs j ON j.id = s.job_id
WHERE s.analysis_mode = 'video_only';
```

**Get validation failures for a job:**
```sql
SELECT v.*, s.source_id as source_label
FROM validations v
LEFT JOIN sources s ON s.id = v.source_id
WHERE v.job_id = $1 AND v.passed = false
ORDER BY v.created_at;
```

**Get current documents for a job:**
```sql
SELECT * FROM documents
WHERE job_id = $1 AND is_current = true
ORDER BY document_type;
```

---

## Constraints Summary

| Constraint | Table | Rule |
|------------|-------|------|
| Source isolation | sources | source_index unique per job |
| 1:1 extraction | extractions | source_id is UNIQUE |
| 1:1 synthesis | synthesis | job_id is UNIQUE |
| 1:1 booster | booster_results | job_id is UNIQUE |
| Current doc | documents | Partial unique on (job_id, document_type) WHERE is_current |
| Confidence ceiling | sources | CHECK IN ('high', 'medium', 'low') |
| Analysis mode | sources | CHECK IN (6 valid modes) |
| Status values | jobs, sources, extractions, synthesis | CHECK constraints |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-13 | Initial specification |

---

**END OF SPECIFICATION**
