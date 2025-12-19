# Research Agent v1 Implementation - Execution Plan

## Pre-Implementation Analysis Complete ✅

### Current State Assessment

#### ✅ What's Working
- **Solid 10-stage pipeline**: Core research flow is functional
- **Clean architecture**: FastAPI + Celery + Redis + Supabase
- **Good structure**: Models, pipeline, integrations directories exist
- **API integrations**: OpenAI, Perplexity, YouTube, Google Drive working
- **Git branch**: Currently on `claude/analyze-prd-tep-v1-9fNGO`

#### ⚠️ Environment Issues Found
1. **No .env file**: Config expects env vars but file doesn't exist
2. **Redis not running**: No Redis process detected
3. **Missing Reddit API config**: Config has username/password but not client_id/secret/user_agent
4. **Mode mismatch**: Current modes (CLAIMS_EVIDENCE, TIMELINE, QUICK_BRIEF, INVESTIGATION) don't match TEP requirements

#### 🎯 Critical Gaps (from V1_Analysis)
1. **Timeline extraction**: NOT implemented
2. **Entity extraction**: Field exists but no logic
3. **Research modes**: Wrong modes (4 current vs 4 documentary-specific needed)
4. **Angle Discovery**: NOT implemented
5. **Documentary Intelligence**: NOT implemented
6. **Frontend**: Minimal, no polling/status
7. **Output**: 10 separate files vs single NotebookLM packet

---

## Execution Strategy

### Phase Order (Modified from TEP)

Based on current state, I'll execute in this order:

#### **PHASE 0: Environment & Prerequisites** (Do First)
- [ ] Create/update .env file with all required API keys
- [ ] Add Reddit API credentials to config.py
- [ ] Start Redis (required for Celery)
- [ ] Verify database schema current state
- [ ] Document environment setup

#### **PHASE 1: Database & Configuration** (Days 1-2)
- [ ] 1.1: Run database migrations (cleanup, fix modes, add vision fields)
- [ ] 1.2: Update configuration models (DocumentaryMode enum, mode configs)
- [ ] 1.3: Update config.py for Reddit API and cost tracking

#### **PHASE 2: Core Features** (Days 3-7)
- [ ] 2.1: Timeline extraction (backend/pipeline/timeline.py)
- [ ] 2.2: Entity extraction (backend/pipeline/entities.py)
- [ ] 2.3: Reddit integration (backend/integrations/reddit_client.py)
- [ ] 2.4: Angle discovery (backend/pipeline/angle_discovery.py)
- [ ] 2.5: Documentary intelligence (backend/pipeline/documentary_intelligence.py)
- [ ] 2.6: Update worker.py pipeline (integrate all new stages)

#### **PHASE 3: Frontend** (Days 8-10)
- [ ] 3.1: Create API routes (frontend/pages/api/jobs/*)
- [ ] 3.2: Job status polling page
- [ ] 3.3: Update job creation form (4 modes + advanced options)

#### **PHASE 4: Output Generation** (Days 10-11)
- [ ] 4.1: NotebookLM packet generator (single file)
- [ ] 4.2: Documentary blueprint generator (production-ready)
- [ ] 4.3: Dual output integration in worker

#### **PHASE 5: Testing** (Days 11-12)
- [ ] 5.1: Integration tests for 4 modes
- [ ] 5.2: Timeline/entity extraction tests
- [ ] 5.3: End-to-end testing

#### **PHASE 6: Deployment** (Day 13)
- [ ] 6.1: Deployment checklist verification
- [ ] 6.2: Environment variables check
- [ ] 6.3: Final validation

---

## Critical TEP Warnings to Remember

### DO NOT:
1. ❌ Skip timeline/entity extraction as "optimization"
2. ❌ Combine 4 documentary modes into 2 for "simplicity"
3. ❌ Output multiple files for NotebookLM
4. ❌ Skip Reddit integration
5. ❌ Use print() for debugging (use logger)
6. ❌ Hardcode API keys
7. ❌ Catch all exceptions without proper handling

### MUST DO:
1. ✅ Implement ALL 4 documentary modes exactly as specified
2. ✅ Create timeline extraction from scratch
3. ✅ Create entity extraction from scratch
4. ✅ Output single NotebookLM file
5. ✅ Implement job status polling in frontend
6. ✅ Add cost tracking
7. ✅ Test each pipeline stage independently
8. ✅ Preserve existing working code

---

## Mode Alignment Strategy

### Current Modes (job_config.py)
```python
CLAIMS_EVIDENCE = "claims_evidence"
TIMELINE = "timeline"
QUICK_BRIEF = "quick_brief"
INVESTIGATION = "investigation"
```

### Database Constraint (from PRD)
```sql
CHECK (pipeline IN ('quick', 'standard', 'deep', 'investigation'))
```

### TEP Documentary Modes (Target)
```python
BREAKING_NEWS = "breaking_news"
INVESTIGATION = "investigation"
PROFILE = "profile"
CONTROVERSY = "controversy"
```

### Resolution Plan
1. Keep database pipeline as-is initially (quick, standard, deep, investigation)
2. Create NEW DocumentaryMode enum for documentary types
3. Map pipeline modes to documentary behaviors
4. Update database constraint in Phase 1 to match documentary modes
5. Deprecate old ResearchMode, transition to DocumentaryMode

---

## Dependencies & Prerequisites

### Required API Keys (Need to Set Up)
```bash
# Core APIs
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
YOUTUBE_API_KEY=AIza...

# Reddit API (NEW - REQUIRED)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=ResearchAgent/1.0

# Supabase
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REFRESH_TOKEN=...
GOOGLE_DRIVE_ROOT_FOLDER_ID=...

# Cost Tracking (NEW)
OPENAI_GPT4O_INPUT_COST_PER_1M=5.00
OPENAI_GPT4O_OUTPUT_COST_PER_1M=15.00
OPENAI_GPT4O_MINI_INPUT_COST_PER_1M=0.15
OPENAI_GPT4O_MINI_OUTPUT_COST_PER_1M=0.60
PERPLEXITY_SONAR_COST_PER_1M=0.20
PERPLEXITY_SONAR_PRO_COST_PER_1M=3.00
```

### Required Python Packages (Need to Verify)
```bash
praw  # Reddit API wrapper (NEW)
spacy  # For entity extraction (NEW)
python -m spacy download en_core_web_sm  # spaCy model
```

### Required Services
- Redis (for Celery queue) - NOT RUNNING
- PostgreSQL (via Supabase) - Assumed running
- Celery worker - Need to verify

---

## File Creation Checklist

### New Files to Create (Phase 2)
```
backend/pipeline/timeline.py           (NEW - Timeline extraction)
backend/pipeline/entities.py           (NEW - Entity extraction)
backend/integrations/reddit_client.py  (NEW - Reddit integration)
backend/pipeline/angle_discovery.py    (NEW - Angle discovery)
backend/pipeline/documentary_intelligence.py  (NEW - Documentary layer)
```

### Files to Modify
```
backend/models/job_config.py           (UPDATE - Add DocumentaryMode)
backend/config.py                      (UPDATE - Add Reddit config)
backend/worker.py                      (UPDATE - Add new pipeline stages)
```

### Frontend Files (Phase 3)
```
frontend/pages/api/jobs/index.ts       (CREATE - API proxy)
frontend/pages/api/jobs/[id].ts        (CREATE - Job status API)
frontend/pages/jobs/[id].tsx           (CREATE - Status page)
frontend/pages/index.tsx               (MODIFY - Update form)
```

### Database Migrations
```
migrations/001_cleanup_redundant_fields.sql
migrations/002_fix_pipeline_modes.sql
migrations/003_add_vision_fields.sql
migrations/004_add_indexes.sql
```

---

## Risk Mitigation

### High Risk Areas
1. **Database migrations**: Could break existing jobs
   - Mitigation: Backup database first, test migrations on dev copy

2. **Worker pipeline changes**: Could break existing flow
   - Mitigation: Add new stages without removing old ones, use feature flags

3. **Redis dependency**: Pipeline won't work if Redis fails
   - Mitigation: Add Redis health check, clear error messages

4. **API cost overruns**: New features use more API calls
   - Mitigation: Implement strict budget controls, cost tracking per stage

### Medium Risk Areas
1. **Frontend breaking changes**: Users may have old UI cached
   - Mitigation: Version API endpoints, gradual rollout

2. **Reddit API rate limits**: Free tier has limits
   - Mitigation: Implement caching, respect rate limits, graceful degradation

---

## Success Criteria (from PRD)

### Must Have (Phase 1-2)
- ✅ 4 documentary modes working
- ✅ Timeline extraction producing chronological events
- ✅ Entity extraction identifying people/orgs/places
- ✅ Reddit integration fetching real posts
- ✅ Angle discovery finding unique perspectives

### Must Have (Phase 3-4)
- ✅ Single NotebookLM packet file generation
- ✅ Documentary blueprint with production elements
- ✅ Job creation with all options
- ✅ Real-time status updates

### Quality Gates
- ✅ No regression in existing pipeline
- ✅ All stages have error handling
- ✅ Costs tracked per job
- ✅ All tests passing

---

## Next Steps

### Immediate Actions (PHASE 0)
1. **Create .env file** with all required API keys
2. **Start Redis** service
3. **Update config.py** to include Reddit API fields
4. **Verify Supabase access** and check current schema
5. **Install new dependencies** (praw, spacy)

### After PHASE 0 Complete
1. Begin Phase 1: Database migrations
2. Create feature branch if needed
3. Run migrations in order
4. Verify no data loss

---

## Estimated Timeline

| Phase | Tasks | Days | Dependencies |
|-------|-------|------|--------------|
| 0 | Environment setup | 0.5 | None |
| 1 | Database & Config | 2 | Phase 0 |
| 2 | Core Features | 5 | Phase 1 |
| 3 | Frontend | 3 | Phase 2 |
| 4 | Output Generation | 2 | Phase 2 |
| 5 | Testing | 2 | Phase 2-4 |
| 6 | Deployment | 1 | Phase 5 |
| **Total** | | **15.5 days** | |

---

## Key Architectural Decisions

### Hybrid Approach Justification
Per V1_Analysis, we're implementing a **dual-purpose system**:

1. **Comprehensive Research Gathering** (existing strength)
   - Preserve current 10-stage pipeline
   - Add timeline and entity extraction
   - Enhance with Reddit integration

2. **Documentary Intelligence Layer** (new differentiator)
   - Angle discovery for unique perspectives
   - Narrative structure detection
   - Visual moment identification
   - Production-ready blueprint generation

3. **Dual Output System**
   - NotebookLM packet: For deep analysis
   - Documentary blueprint: For production

This leverages the existing 60% completion while adding the missing documentary focus.

---

## Notes & Considerations

### From TEP - Critical Implementation Notes
1. Use GPT-4o-mini for simple tasks (entity extraction, timeline parsing) to save costs
2. Use GPT-4o for complex reasoning (claim extraction, angle discovery)
3. Cache Perplexity responses for 24 hours
4. Max 10-15 Perplexity queries per job
5. Use spaCy for NER, fallback to regex patterns
6. Store timeline events and entities in dedicated JSONB columns
7. Generate manual guidance for Reddit/Twitter when automation fails

### Open Questions
1. Should we deprecate old ResearchMode immediately or phase it out?
2. Do we need backward compatibility for existing job configs?
3. Should Redis be Docker-ized or run natively?
4. How to handle existing jobs in database with old schema?

---

*Last Updated: 2025-12-19*
*Status: Ready to begin PHASE 0*
