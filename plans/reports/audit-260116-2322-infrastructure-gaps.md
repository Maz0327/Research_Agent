# Research Agent Infrastructure Gap Analysis

**Date:** 2026-01-16 23:22
**Auditor:** Database Admin (Subagent a332bf8)
**Scope:** Storage buckets and database schema alignment
**Status:** CRITICAL GAPS IDENTIFIED

---

## Executive Summary

The Research Agent has implemented a full semantic pipeline (Phases 0-10 complete) but is **storing all data in JSONB fields** instead of the structured database schema defined in `docs/Database_Schema.md`. Additionally, **no Supabase storage buckets** are configured for file uploads.

**Critical Findings:**
1. Screenshot uploads save to local temp files with no cloud storage
2. Semantic extraction data stored in JSONB `artifacts` field, not dedicated tables
3. Database schema specification exists but is **not implemented**
4. 6 major tables defined in spec are **missing from migrations**

**Impact:** Data is queryable only through JSONB operators, no referential integrity, no source isolation validation at DB level.

**Recommendation:** Either (A) implement the full schema per spec, or (B) update spec to match current JSONB-based approach.

---

## 1. Storage Bucket Analysis

### Current Configuration

**Backend Code Analysis:**
- `jobs_routes.py` Line 426-534: `/screenshot-input` endpoint implemented
- Screenshot handling:
  - Accepts uploads up to 10MB (PNG, JPG, WEBP)
  - Saves to local temp directory: `tempfile.gettempdir() / "research_agent_screenshots"`
  - File path stored in `config_json.screenshot_path`
  - File cleaned up after OCR extraction (Line 232-238 in `ocr_extraction.py`)

**Storage Backend:**
- **No Supabase storage client found** in codebase
- **No bucket creation scripts** in migrations
- **No environment variables** for storage configuration in `config.py`

### Missing Infrastructure

#### Supabase Storage Buckets Needed

```sql
-- Create bucket for screenshot uploads
INSERT INTO storage.buckets (id, name, public)
VALUES ('screenshots', 'screenshots', false);

-- RLS policies for screenshot bucket
CREATE POLICY "Users can upload own screenshots"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'screenshots'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can read own screenshots"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id = 'screenshots'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Service role can manage all screenshots"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'screenshots');
```

#### Code Changes Required

**1. Add Supabase Storage Client**
```python
# backend/integrations/supabase_storage.py (NEW FILE)
from supabase import create_client
from backend.config import require_supabase

def upload_screenshot(user_id: str, job_id: str, file_content: bytes, filename: str) -> str:
    """Upload screenshot to Supabase storage bucket."""
    settings = require_supabase()
    client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # Upload to user-specific folder
    path = f"{user_id}/{job_id}/{filename}"
    client.storage.from_('screenshots').upload(path, file_content)

    # Return public URL
    return client.storage.from_('screenshots').get_public_url(path)
```

**2. Update jobs_routes.py**
```python
# Replace lines 463-477 (temp file save) with:
from backend.integrations.supabase_storage import upload_screenshot

# Upload to Supabase storage
screenshot_url = upload_screenshot(
    user_id=user.user_id if user else "anonymous",
    job_id=job.job_id,
    file_content=content,
    filename=screenshot.filename or "screenshot.png"
)

# Store URL instead of local path
config_json["screenshot_url"] = screenshot_url
```

### Storage Strategy Assessment

**Current Approach:** Temporary local files, deleted after processing
- ✅ Low cost (no storage fees)
- ✅ Simple implementation
- ❌ No audit trail (files deleted immediately)
- ❌ Cannot re-process screenshots
- ❌ Multi-instance deployment issues (Railway/Docker)

**Recommended Approach:** Supabase Storage with retention policy
- ✅ Persistent storage for debugging
- ✅ Multi-instance compatible
- ✅ User-scoped access control
- ✅ Can regenerate OCR if needed
- ❌ Storage costs (~$0.021/GB/month)

**Cost Estimate:**
- Average screenshot: 500KB
- 1000 screenshots/month: 500MB
- Monthly cost: ~$0.01 (negligible)

**Decision:** Implement Supabase storage buckets.

---

## 2. Database Schema Status

### Schema Specification vs. Reality

The project includes a comprehensive schema specification in `docs/Database_Schema.md` (930 lines, last updated 2026-01-13) defining **10 tables** for structured semantic data storage. However, **only 3 of these tables exist** in the actual database.

#### Tables Defined in Spec

| Table | Purpose | Rows/Job | Spec Section | Status |
|-------|---------|----------|--------------|--------|
| `jobs` | Main job record | 1 | §1 | ✅ EXISTS (modified) |
| `sources` | Individual sources | 1-25 | §2 | ❌ MISSING |
| `extractions` | Per-source extraction | 1-25 | §3 | ❌ MISSING |
| `synthesis` | Cross-source analysis | 0-1 | §4 | ❌ MISSING |
| `documents` | Output docs (0/1/2/3) | 3-4+ | §5 | ❌ MISSING |
| `validations` | Validation audit trail | Many | §6 | ❌ MISSING |
| `booster_results` | Optional booster | 0-1 | §7 | ❌ MISSING |
| `user_settings` | User preferences | 1/user | §8 | ✅ EXISTS |
| `admin_users` | Admin access | 1/admin | §9 | ✅ EXISTS |
| `error_logs` | Error tracking | Variable | §10 | ✅ EXISTS |

**Summary:**
- **3/10 tables exist** (30% implementation)
- **6/10 core semantic tables missing** (sources, extractions, synthesis, documents, validations, booster_results)

### Current Data Storage Strategy

#### Jobs Table (Actual Schema)

Based on `backend/models/job_record.py` and existing migrations:

```sql
CREATE TABLE jobs (
    -- Identity
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    title TEXT,
    pipeline TEXT DEFAULT 'investigation',

    -- Status
    status TEXT DEFAULT 'queued',
    stage TEXT,
    progress_percent INTEGER DEFAULT 0,
    stage_started_at TIMESTAMPTZ,

    -- Configuration (JSONB - everything goes here)
    config_json JSONB DEFAULT '{}',

    -- Warnings and errors
    warnings TEXT[],  -- Array, not JSONB
    error TEXT,

    -- Legacy fields (from pre-Phase 0)
    interpretations JSONB,
    selected_interpretations INTEGER[],
    timeline_events JSONB,
    entities JSONB,
    reddit_posts JSONB,
    discovered_angles JSONB,
    coverage_analysis JSONB,
    recommended_angle JSONB,
    quality_gate_stats JSONB,
    total_sources INTEGER,
    total_claims INTEGER,
    api_costs JSONB,
    manual_guidance JSONB,
    niche TEXT,
    notebooklm_packet_url TEXT,
    documentary_blueprint_url TEXT,

    -- Outputs (JSONB blobs)
    artifacts JSONB,  -- Contains ALL semantic data
    outputs JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Key Observation:** The `artifacts` JSONB field contains ALL semantic extraction data:

```jsonb
{
  "source_ledger": { ... },           // Doc 0
  "jump_start": { ... },              // Doc 1
  "semantic_brief": { ... },          // Doc 2
  "semantic_extractions": [...],      // Per-source extractions
  "booster_output": { ... },          // Booster results
  "producer_packet": { ... },         // Doc 3
  "clips": [...],                     // Video clips
  "quotes": [...]                     // Extracted quotes
}
```

### Data Model Comparison

#### Spec Approach: Structured Relational Tables

```
jobs (1) ──┬── sources (1:M)
           │    └── extractions (1:1)
           │
           ├── synthesis (1:1)
           ├── documents (1:M)
           ├── validations (1:M)
           └── booster_results (1:1)
```

**Pros:**
- ✅ Referential integrity enforced by DB
- ✅ Source isolation validated at schema level
- ✅ Queryable with standard SQL
- ✅ Indexable for performance
- ✅ Clear data boundaries per spec

**Cons:**
- ❌ Requires significant migration work
- ❌ More complex queries (JOINs)
- ❌ Schema changes require migrations

#### Current Approach: JSONB Everything

```
jobs (1)
  └── artifacts JSONB (contains everything)
```

**Pros:**
- ✅ Flexible schema (no migrations needed)
- ✅ Fast iteration during development
- ✅ Single-table queries
- ✅ Already implemented and working

**Cons:**
- ❌ No referential integrity
- ❌ Source isolation not enforced by DB
- ❌ Complex JSONB queries for analytics
- ❌ Cannot index nested fields easily
- ❌ Spec divergence (documentation debt)

### Missing Tables Detail

#### 1. `sources` Table (Spec §2)

**Purpose:** One row per source, enabling source isolation validation

**Key Fields:**
```sql
CREATE TABLE sources (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    source_index INTEGER NOT NULL,
    source_id TEXT GENERATED AS ('SRC_' || source_index) STORED,

    -- Identity (set BEFORE LLM)
    source_type TEXT NOT NULL,  -- youtube, article, text, screenshot
    analysis_mode TEXT NOT NULL,  -- 6 modes
    confidence_ceiling TEXT NOT NULL,  -- high, medium, low

    -- Metadata
    url TEXT,
    title TEXT NOT NULL,
    creator TEXT,
    published_at DATE,

    -- Content
    full_text TEXT,
    transcript_provenance JSONB,

    -- Status
    status TEXT NOT NULL DEFAULT 'pending',

    UNIQUE(job_id, source_index)
);
```

**Current Equivalent:** JSONB in `artifacts.source_ledger.sources[]`

**Gap Impact:**
- Cannot query "all VIDEO_ONLY sources across jobs"
- Cannot enforce "title required before LLM call" at DB level
- Cannot index by analysis_mode or confidence_ceiling

#### 2. `extractions` Table (Spec §3)

**Purpose:** Store LLM extraction results per source (1:1 with sources)

**Key Fields:**
```sql
CREATE TABLE extractions (
    id UUID PRIMARY KEY,
    source_id UUID UNIQUE REFERENCES sources(id),
    job_id UUID REFERENCES jobs(id),

    -- Extraction results
    key_points JSONB DEFAULT '[]',
    claims JSONB DEFAULT '[]',
    quotes JSONB DEFAULT '[]',
    observations JSONB DEFAULT '[]',
    themes JSONB DEFAULT '[]',
    tensions JSONB DEFAULT '[]',
    entities JSONB DEFAULT '[]',
    gaps JSONB DEFAULT '[]',

    -- Metadata
    extraction_metadata JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',

    CONSTRAINT unique_source UNIQUE(source_id)
);
```

**Current Equivalent:** JSONB in `artifacts.semantic_extractions[]`

**Gap Impact:**
- Cannot enforce 1:1 relationship with sources
- Cannot query "all extractions with HIGH confidence quotes"
- Cannot validate "VIDEO_ONLY mode has no quotes" at DB level

#### 3. `synthesis` Table (Spec §4)

**Purpose:** Store cross-source analysis (1:1 with jobs)

**Key Fields:**
```sql
CREATE TABLE synthesis (
    id UUID PRIMARY KEY,
    job_id UUID UNIQUE REFERENCES jobs(id),

    cross_source_themes JSONB DEFAULT '[]',
    cross_source_tensions JSONB DEFAULT '[]',
    source_concordance JSONB DEFAULT '{}',
    confidence_assessment JSONB DEFAULT '{}',
    synthesis_gaps JSONB DEFAULT '[]',
    narrative_threads JSONB DEFAULT '[]',

    synthesis_metadata JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
```

**Current Equivalent:** JSONB in `artifacts.semantic_brief.synthesis`

**Gap Impact:**
- Cannot enforce "synthesis only runs after all extractions complete"
- Cannot track synthesis status independently

#### 4. `documents` Table (Spec §5)

**Purpose:** Store generated documents with versioning

**Key Fields:**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),

    document_type TEXT NOT NULL,  -- source_ledger, jump_start_directions, semantic_brief, producer_packet
    version INTEGER NOT NULL DEFAULT 1,
    content JSONB NOT NULL,
    markdown_rendered TEXT,

    -- Versioning
    is_current BOOLEAN DEFAULT true,
    superseded_by UUID REFERENCES documents(id),

    generation_metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Only one current doc per type per job
    CONSTRAINT unique_current_doc UNIQUE(job_id, document_type) WHERE is_current = true
);
```

**Current Equivalent:** JSONB in `artifacts.source_ledger`, `artifacts.jump_start`, `artifacts.semantic_brief`, `artifacts.producer_packet`

**Gap Impact:**
- No document versioning (regeneration overwrites)
- Cannot query "all jobs with producer packets generated"
- Cannot track when documents were regenerated

#### 5. `validations` Table (Spec §6)

**Purpose:** Audit trail for all validation checks

**Key Fields:**
```sql
CREATE TABLE validations (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    source_id UUID REFERENCES sources(id),

    stage TEXT NOT NULL,  -- extraction, synthesis, assembly
    validation_check TEXT NOT NULL,  -- V1, V2, V3, etc.
    severity TEXT NOT NULL,  -- hard_fail, soft_fail, warning

    passed BOOLEAN NOT NULL,
    message TEXT NOT NULL,
    details JSONB,

    action_taken TEXT,  -- retry, degrade, abort, none
    retry_attempted BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Current Equivalent:** None (validations not persisted, only logged)

**Gap Impact:**
- **No audit trail** for validation failures
- Cannot query "all V4 (quote verification) failures"
- Cannot track retry success rates
- Cannot debug why extractions were rejected

#### 6. `booster_results` Table (Spec §7)

**Purpose:** Store optional deep research booster output

**Key Fields:**
```sql
CREATE TABLE booster_results (
    id UUID PRIMARY KEY,
    job_id UUID UNIQUE REFERENCES jobs(id),

    stage1_deep_gaps JSONB,
    stage2_research_directions JSONB,
    stage3_search_queries JSONB,
    stage4_context_bundle JSONB,

    stages_completed INTEGER DEFAULT 0,
    current_stage INTEGER,
    status TEXT DEFAULT 'pending',

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Current Equivalent:** JSONB in `artifacts.booster_output`

**Gap Impact:**
- Cannot track booster progress per stage
- Cannot query "all jobs where booster failed at stage 2"

---

## 3. Data Storage Strategy Analysis

### Current Implementation

**Where Semantic Data Lives:**

1. **Source Identity Packages** → `config_json.sources[]` (job config)
2. **Semantic Extractions** → `artifacts.semantic_extractions[]` (JSONB)
3. **Documents (Doc 0/1/2/3)** → `artifacts.{source_ledger, jump_start, semantic_brief, producer_packet}` (JSONB)
4. **Booster Output** → `artifacts.booster_output` (JSONB)
5. **Validation Results** → Not persisted (only in `warnings[]` array)

**Evidence from Code:**

`backend/state/impl/supabase_store.py`:
- `update_job()` merges JSONB into `artifacts` and `outputs` fields
- Uses atomic JSONB merge functions (`merge_job_artifacts`, `merge_job_outputs`)
- No calls to separate tables for sources/extractions/synthesis

`backend/pipeline/stages/document_assembly.py`:
- Documents stored as: `ctx.doc0`, `ctx.doc1`, `ctx.doc2`
- Saved via: `update_job(job_id, artifacts={"source_ledger": doc0.to_dict(), ...})`

### What Should Change

**Option A: Implement Full Schema (High Effort, High Value)**

Pros:
- ✅ Aligns code with specification
- ✅ Enables complex queries (analytics, debugging)
- ✅ Enforces data integrity at DB level
- ✅ Validates source isolation in schema

Cons:
- ❌ Requires major migration work
- ❌ Breaks existing jobs (need migration script)
- ❌ Slows feature development during transition

**Option B: Update Spec to Match Code (Low Effort, Documentation Debt)**

Pros:
- ✅ Fast (just update docs)
- ✅ No breaking changes
- ✅ Reflects current working system

Cons:
- ❌ Loses architectural benefits of structured schema
- ❌ Makes future analytics harder
- ❌ Violates "source isolation" principle (no DB enforcement)

**Option C: Hybrid Approach (Recommended)**

**Phase 1: Add Core Tables (Non-Breaking)**
- Create `sources`, `extractions`, `synthesis` tables
- Populate from existing `artifacts` JSONB during job processing
- Keep `artifacts` as canonical until migration complete
- Queries use new tables, writes go to both

**Phase 2: Migration Script**
- Backfill existing jobs from JSONB to structured tables
- Validate data integrity

**Phase 3: Deprecate JSONB Storage**
- Switch to structured tables as canonical
- Keep `artifacts` as denormalized cache for API responses

**Cost-Benefit:**
- Effort: Medium (3-5 migrations, dual-write code)
- Value: High (enables analytics, enforces integrity)
- Risk: Low (existing jobs keep working)

---

## 4. Action Items

### Priority 1: Storage Buckets (Required for Production)

**Why:** Screenshot uploads currently fail on cloud deployments (Railway, Docker) due to ephemeral filesystem.

**Tasks:**

1. **Create Supabase Storage Bucket**
   ```sql
   -- Run in Supabase SQL Editor
   INSERT INTO storage.buckets (id, name, public)
   VALUES ('screenshots', 'screenshots', false);
   ```

2. **Add RLS Policies**
   ```sql
   -- See full SQL in §1 above
   ```

3. **Add Storage Client**
   - Create `backend/integrations/supabase_storage.py`
   - Implement `upload_screenshot()` and `get_screenshot_url()`

4. **Update Screenshot Endpoint**
   - Modify `backend/app/routes/jobs_routes.py` lines 463-477
   - Replace temp file save with Supabase storage upload
   - Store URL in `config_json.screenshot_url` instead of local path

5. **Update OCR Stage**
   - Modify `backend/pipeline/stages/ocr_extraction.py`
   - Download from Supabase URL instead of local path
   - Remove temp file cleanup (no longer needed)

**Testing:**
```bash
# Upload screenshot via API
curl -X POST http://localhost:8000/jobs/screenshot-input \
  -H "Authorization: Bearer $TOKEN" \
  -F "topic=Test screenshot" \
  -F "screenshot=@screenshot.png"

# Verify file in Supabase storage bucket
# Check job config_json.screenshot_url exists
```

### Priority 2: Database Schema Migration (Optional, Long-Term)

**Why:** Enables analytics, debugging, and enforces data integrity per spec.

**Decision Point:** Requires product owner approval on Option A/B/C from §3.

**If Option C (Hybrid) Approved:**

1. **Migration 018: Add sources table**
   ```sql
   -- See full schema in §2.1 above
   CREATE TABLE sources (...);
   CREATE INDEX idx_sources_job_id ON sources(job_id);
   CREATE INDEX idx_sources_analysis_mode ON sources(analysis_mode);
   ```

2. **Migration 019: Add extractions table**
   ```sql
   CREATE TABLE extractions (...);
   CREATE UNIQUE INDEX idx_extractions_source_id ON extractions(source_id);
   ```

3. **Migration 020: Add synthesis table**
   ```sql
   CREATE TABLE synthesis (...);
   CREATE UNIQUE INDEX idx_synthesis_job_id ON synthesis(job_id);
   ```

4. **Migration 021: Add documents table**
   ```sql
   CREATE TABLE documents (...);
   CREATE UNIQUE INDEX idx_documents_current
       ON documents(job_id, document_type) WHERE is_current = true;
   ```

5. **Migration 022: Add validations table**
   ```sql
   CREATE TABLE validations (...);
   CREATE INDEX idx_validations_failed ON validations(passed) WHERE passed = false;
   ```

6. **Migration 023: Add booster_results table**
   ```sql
   CREATE TABLE booster_results (...);
   ```

7. **Dual-Write Implementation**
   - Update `backend/pipeline/stages/source_identity.py` to write to `sources` table
   - Update `backend/pipeline/stages/semantic_extraction.py` to write to `extractions` table
   - Update `backend/pipeline/stages/semantic_synthesis.py` to write to `synthesis` table
   - Update `backend/pipeline/stages/document_assembly.py` to write to `documents` table
   - Update `backend/pipeline/semantic_validation.py` to write to `validations` table
   - Update `backend/pipeline/stages/booster_stage.py` to write to `booster_results` table
   - Keep existing JSONB writes for backward compatibility

8. **Backfill Script**
   ```python
   # backend/scripts/backfill_structured_tables.py
   # Parse artifacts JSONB → populate structured tables for existing jobs
   ```

**Estimated Effort:** 2-3 weeks for full implementation + testing

### Priority 3: Documentation Alignment (Quick Win)

**If Option B (Update Spec) Chosen:**

1. Update `docs/Database_Schema.md`:
   - Remove specs for missing tables
   - Document actual JSONB schema for `artifacts` field
   - Add JSONB query examples

2. Update migration plan:
   - Remove "Phase 1: Add New Tables" section
   - Document JSONB best practices

3. Update `CLAUDE.md` and `RASS.md`:
   - Remove references to structured tables
   - Document JSONB-based approach as canonical

**Estimated Effort:** 2-4 hours

---

## 5. Recommendations

### Immediate Actions (This Week)

1. **Implement Supabase Storage Buckets** (Priority 1)
   - Required for production deployment
   - Fixes screenshot upload reliability
   - Low risk, high value

2. **Decision on Schema Approach**
   - Schedule 30-min discussion with product owner
   - Review Option A/B/C from §3
   - Commit to one approach

### Short-Term (Next Sprint)

3. **If Hybrid Approach:** Implement migrations 018-023
   - Add core tables (sources, extractions, synthesis)
   - Dual-write from pipeline stages
   - Keep JSONB as fallback

4. **If JSONB Approach:** Update documentation
   - Align spec with reality
   - Add JSONB query reference

### Long-Term (Future Quarter)

5. **Analytics Dashboard**
   - Requires structured schema (Option A or C)
   - Queries: "V4 failure rate by mode", "Most common gaps", etc.

6. **Data Warehouse Export**
   - Export to BigQuery/Snowflake for ML training
   - Structured schema makes this much easier

---

## Appendix: Migration Scripts

### A. Create Screenshots Bucket

```bash
#!/bin/bash
# scripts/setup_storage_bucket.sh

SUPABASE_URL="${SUPABASE_URL}"
SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_ROLE_KEY}"

curl -X POST "${SUPABASE_URL}/storage/v1/bucket" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "screenshots",
    "name": "screenshots",
    "public": false,
    "file_size_limit": 10485760,
    "allowed_mime_types": ["image/png", "image/jpeg", "image/webp"]
  }'

echo "✓ Screenshots bucket created"
```

### B. Backfill Sources Table (Example)

```python
# backend/scripts/backfill_sources.py
from backend.state import get_job, list_jobs
from supabase import create_client
from backend.config import require_supabase

def backfill_sources():
    settings = require_supabase()
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)

    jobs = list_jobs(limit=1000)

    for job in jobs:
        if not job.artifacts or not job.artifacts.source_ledger:
            continue

        source_ledger = job.artifacts.source_ledger
        sources = source_ledger.get('sources', [])

        for idx, source in enumerate(sources):
            # Insert into sources table
            db.table('sources').insert({
                'job_id': job.job_id,
                'source_index': idx + 1,
                'source_type': source['source_type'],
                'analysis_mode': source.get('transcript_provenance', {}).get('gemini_analysis_mode', 'unknown'),
                'confidence_ceiling': 'medium',  # Default
                'url': source.get('url'),
                'title': source.get('title'),
                'creator': source.get('creator'),
                'full_text': source.get('full_text'),
                'status': 'extracted',
            }).execute()

    print(f"✓ Backfilled sources for {len(jobs)} jobs")

if __name__ == '__main__':
    backfill_sources()
```

---

## Questions for Product Owner

1. **Storage Buckets:** Approve implementation? (Blocks cloud deployment)
2. **Schema Approach:** Choose Option A (full schema), B (JSONB only), or C (hybrid)?
3. **Migration Timeline:** If Option C, priority for Q1 2026?
4. **Analytics Needs:** Do we need queryable semantic data for dashboards/ML?

---

**END OF AUDIT**
