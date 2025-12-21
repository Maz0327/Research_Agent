# Jobs API Implementation Summary

## Changes Made

### 1. CORS Middleware Configuration

**File:** `backend/app/main.py`

- Reads `FRONTEND_ORIGINS` environment variable (comma-separated)
- Parses and strips origins into explicit list
- Uses explicit `allow_origins` list (no wildcard `"*"`)
- Sets `allow_credentials=False` (no cookies used)
- Sets `allow_methods=["*"]` and `allow_headers=["*"]`
- Only configures middleware if `FRONTEND_ORIGINS` is set

**Environment Variable:**
```bash
FRONTEND_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### 2. POST /jobs Endpoint

**File:** `backend/app/main.py` + `backend/models/job.py`

**Request Body:**
```json
{
  "prompt": "Research topic here",
  "pipeline": "quick" | "full",
  "options": {} // optional
}
```

**Implementation:**
- Validates prompt is not empty
- Builds `config_json` with prompt, pipeline, and budget defaults
- Creates job in Supabase via `create_job()` with:
  - `status="queued"` (default from JobRecord)
  - `progress_percent=0` (default from JobRecord)
  - `artifacts=null` (default from JobRecord)
  - `error=null` (extracted from warnings on failure, defaults to None)
- Enqueues Celery task: `run_research_job.delay(job_id, prompt)`
- Returns: `{ "job_id": "..." }`

**Pipeline Budgets:**
- `quick`: 20 URLs, 60 min transcripts, 10 claims, 3 links/claim
- `full`: 50 URLs, 120 min transcripts, 25 claims, 6 links/claim

### 3. GET /jobs/{job_id} Endpoint

**File:** `backend/app/main.py` + `backend/models/job.py`

**Response:**
```json
{
  "id": "...",
  "prompt": "...",
  "pipeline": "quick" | "full",
  "status": "queued" | "running" | "completed" | "failed",
  "progress_percent": 0-100,
  "artifacts": {
    "drive_folder_url": "...",
    "doc_urls": [...]
  } | null,
  "error": "..." | null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": null // TODO: Add updated_at tracking
}
```

**Implementation:**
- Retrieves job from Supabase via `get_job(job_id)`
- Extracts `prompt` and `pipeline` from `config_json`
- Extracts `error` from warnings if status is "failed" (looks for "Fatal error:" prefix)
- Converts artifacts to dict (None if empty)
- Returns all fields including timestamps

### 4. GET /health Endpoint

**File:** `backend/app/main.py`

Already implemented and returns 200 OK with:
```json
{
  "status": "ok",
  "environment": "dev"
}
```

## Configuration

### Environment Variables

Add to `.env`:
```bash
FRONTEND_ORIGINS=http://localhost:3000
```

For multiple origins (comma-separated):
```bash
FRONTEND_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## Testing

### Create Job
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Test research topic",
    "pipeline": "quick"
  }'
```

### Check Status
```bash
curl http://localhost:8000/jobs/{job_id}
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Notes

1. **CORS**: Only enabled if `FRONTEND_ORIGINS` is set. If not set, CORS middleware is not configured (frontend calls will fail unless same-origin).

2. **Error Handling**: Errors are extracted from the `warnings` list when status is "failed". The worker appends "Fatal error: ..." to warnings on failure.

3. **updated_at**: Currently returns `null` as `JobRecord` model doesn't track `updated_at`. TODO: Add `updated_at` tracking to database schema and model.

4. **Artifacts**: Returns `null` if artifacts dict is empty or not set.

5. **Field Names**: Response uses `id` (not `job_id`) per user requirements, handled via Pydantic field alias.






