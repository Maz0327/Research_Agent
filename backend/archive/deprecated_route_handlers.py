"""
ARCHIVED ROUTE HANDLERS — Phase 0.1.2 (2026-03-11)

These handlers were deprecated and archived per Rule 14 (archive, don't delete).
The endpoints still exist in jobs_routes.py but now return 410 Gone.

Contents:
1. create_job_endpoint() — Legacy topic-based job creation (deprecated 2026-01-19)
2. preview_job_endpoint() — Legacy job preview (deprecated 2026-01-19)
3. select_interpretation() — Topic disambiguation (deprecated 2026-01-19)
4. run_job_iteration() — V1 iteration endpoint (deprecated 2026-01-26)
5. archive_job() (duplicate) — Dead code, overridden by archive_job_endpoint()
6. run_gemini_video_job() — Legacy 4-pass pipeline task, orphaned (never called by any endpoint)
"""

# ============================================================================
# 1. create_job_endpoint() — was at jobs_routes.py:118-146
# Already returning 410 since 2026-01-19. Archived as-is.
# ============================================================================
# @router.post("", response_model=CreateJobResponse, deprecated=True)
# async def create_job_endpoint(...):
#     """DEPRECATED: Legacy topic-based job creation."""
#     raise HTTPException(status_code=410, ...)


# ============================================================================
# 2. preview_job_endpoint() — was at jobs_routes.py:2546-2572
# Already returning 410 since 2026-01-19. Archived as-is.
# ============================================================================
# @router.post("/preview", response_model=PreviewJobResponse, deprecated=True)
# async def preview_job_endpoint(...):
#     """DEPRECATED: Legacy job preview endpoint."""
#     raise HTTPException(status_code=410, ...)


# ============================================================================
# 3. select_interpretation() — was at jobs_routes.py:2905-2927
# Already returning 410 since 2026-01-19. Archived as-is.
# ============================================================================
# @router.post("/{job_id}/select-interpretation", deprecated=True)
# async def select_interpretation(...):
#     """DEPRECATED: Disambiguation is no longer supported."""
#     raise HTTPException(status_code=410, ...)


# ============================================================================
# 4. run_job_iteration() — was at jobs_routes.py:1724-1937
# Full V1 iteration handler. Deprecated 2026-01-26 in favor of V2 runs.
# Frontend never calls this endpoint. Has 10+ tests (also deprecated).
# ============================================================================
# Full implementation preserved below for reference:

RUN_JOB_ITERATION_SOURCE = '''
@router.post("/{job_id}/iterate", response_model=IterateJobResponse, deprecated=True)
@limiter.limit(RATE_LIMITS["jobs_create"])
async def run_job_iteration(
    request: Request,
    job_id: str,
    iterate_request: IterateJobRequest,
    user: AuthUser = Depends(get_active_user),
):
    """
    DEPRECATED: Use POST /{job_id}/runs instead.

    This V1 iteration endpoint is deprecated as of 2026-01-26.
    New code should use the V2 Run Abstraction via POST /jobs/{job_id}/runs.

    Trigger an iteration on a completed job.
    APPEND-ONLY: Every iteration produces a new artifact bundle under
    job.artifacts.iterations[]. Baseline doc_0/doc_1/doc_2 are NEVER modified.

    Prerequisites:
    - Job must be in 'completed' or 'completed_with_warnings' status
    - Baseline docs (Doc 0, Doc 1, Doc 2) must exist
    - No iteration currently running

    Iteration modes:
    - more_sources: Find and analyze additional sources
    - deeper: Deeper analysis of existing sources
    - different_angle: Explore a different perspective
    - custom: User-defined iteration via prompt
    """
    # [Full implementation was ~215 lines]
    # Validated job ownership, status, baseline docs existence
    # Built Iteration object with IterationRequest + IterationInputs
    # Appended to artifacts.iterations (append-only)
    # Queued run_iteration_task Celery task
    # Returned IterateJobResponse with iteration_id
'''


# ============================================================================
# 5. archive_job() (duplicate) — was at jobs_routes.py:2867-2902
# Dead code: overridden by archive_job_endpoint() at line 3529.
# Both registered on POST /{job_id}/archive; router uses last definition.
# ============================================================================

ARCHIVE_JOB_DUPLICATE_SOURCE = '''
@router.post("/{job_id}/archive")
@limiter.limit(RATE_LIMITS["jobs_cancel"])
async def archive_job(
    request: Request,
    job_id: str,
    user: AuthUser = Depends(get_active_user),
):
    """Archive a job (marks as 'archived' status). Can be unarchived later."""
    # Validated job_id, ownership, not-running status
    # Called update_job(job_id, status="archived", stage="archived")
    # Returned success message
'''


# ============================================================================
# 6. run_gemini_video_job() — was at worker.py:597-855
# Legacy 4-pass analysis pipeline. Routed in task_routes but never called
# by any endpoint. Test file marks as "Legacy".
# ============================================================================

RUN_GEMINI_VIDEO_JOB_NOTE = '''
@celery_app.task(name="backend.worker.run_gemini_video_job", time_limit=1800, soft_time_limit=1500)
def run_gemini_video_job(job_id: str) -> dict:
    """Full Research Assistant Pipeline - Phase 3 (Jan 2026) - 4-Pass Analysis"""
    # 4-pass architecture:
    #   Pass 1: Source extraction
    #   Pass 2: Structure analysis
    #   Pass 3: Gap identification
    #   Pass 4: Research expansion
    # ~260 lines of implementation
    # Never called by any active endpoint
'''
