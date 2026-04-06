# Phase 4: Live Testing & Validation

## Context Links
- [plan.md](plan.md)
- Blog post endpoint: `backend/app/routes/jobs_routes.py:1306`
- Social kit endpoint: `backend/app/routes/jobs_routes.py:1389`
- Script endpoint: `backend/app/routes/jobs_routes.py:1445`
- Voice profile stage: `backend/pipeline/stages/voice_profile_stage.py`
- Script stage: `backend/pipeline/stages/script_stage.py`
- Worker tasks: `backend/worker.py`

## Overview
- **Priority:** CRITICAL
- **Status:** Pending
- **Effort:** 2-3h
- **Blocked by:** Phase 1 (migration 027 + OpenAI balance)
- **Description:** Live-test all 3 new Tier 5 content endpoints, verify Whisper transcription, smoke-test voice mimicry after migration

## Key Insights
- 3 endpoints exist in code but never tested against prod: blog-post, script, social-kit
- Voice mimicry depends on `voice_profiles` table (migration 027) — blocked until Phase 1
- Whisper depends on OpenAI balance — blocked until Phase 1
- Script endpoint accepts `GenerateScriptRequest` with tone and target_length params
- All 3 tasks are Celery async — need to monitor task completion via job status polling

## Requirements

### Functional
- All 3 content generation endpoints return 200 and enqueue tasks
- Celery tasks complete successfully (status → completed, not failed)
- Generated content is stored and retrievable via job status endpoint
- Whisper transcription works for at least one YouTube video
- Voice profile creation works after migration 027

### Non-Functional
- Each endpoint responds in <5s (just queuing)
- Celery tasks complete in <5min
- No silent failures (errors surfaced to user)

## Pre-Requisites
- [ ] Phase 1 complete: migration 027 deployed, OpenAI balance > $0
- [ ] A completed job exists in prod to test against (or create a new test job first)

## Implementation Steps

### 4.1 — Create Test Job (if needed)
1. Create a video analysis job with 1-2 YouTube URLs via the UI or API
2. Wait for completion (all 4 core docs generated)
3. Note the `job_id` for subsequent tests

### 4.2 — Test Blog Post Endpoint
```bash
curl -X POST https://your-api.up.railway.app/jobs/{job_id}/blog-post \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json"
```
1. Verify 200 response with `"blog_post_status": "queued"`
2. Poll `GET /jobs/{job_id}` until `blog_post_status` = `completed`
3. Verify blog post content exists in response
4. Check Railway logs for errors

### 4.3 — Test Script Endpoint
```bash
curl -X POST https://your-api.up.railway.app/jobs/{job_id}/script \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"tone": "conversational", "target_length": "medium"}'
```
1. Verify 200 response with `"script_status": "queued"`
2. Poll until `script_status` = `completed`
3. Verify script content in response
4. Check for provenance chain (script → creator brief → semantic brief → sources)

### 4.4 — Test Social Kit Endpoint
```bash
curl -X POST https://your-api.up.railway.app/jobs/{job_id}/social-kit \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json"
```
1. Verify 200 response with `"social_kit_status": "queued"`
2. Poll until `social_kit_status` = `completed`
3. Verify social kit content (multiple platform variants)

### 4.5 — Test Whisper Transcription
1. Create a new video analysis job with a short YouTube video (<5 min)
2. Use a video known to have no captions (forces Whisper fallback)
3. Monitor Railway worker logs for Whisper API calls
4. Verify transcript is extracted (not empty/null)
5. If fails: check OpenAI error message in logs (balance, rate limit, API key issue)

### 4.6 — Smoke Test Voice Mimicry
1. Via API or UI, create a voice profile:
   ```bash
   curl -X POST https://your-api.up.railway.app/voice-profiles \
     -H "Authorization: Bearer {token}" \
     -H "Content-Type: application/json" \
     -d '{"creator_name": "Test Creator", "source_video_urls": ["https://youtube.com/watch?v=..."]}'
   ```
2. Verify profile saved in `voice_profiles` table
3. If script endpoint supports voice profile selection, test with `voice_profile_id` parameter
4. This is a smoke test — full voice mimicry is v2; just verify the table works and basic CRUD succeeds

### 4.7 — Error Scenario Testing
1. Test blog-post on a non-completed job → should return 400/422
2. Test script on a non-existent job → should return 404
3. Test double-trigger (call script while already running) → should return 409 or reject
4. Verify error messages are user-friendly, not stack traces

## Todo Checklist

- [ ] 4.1 Have/create a completed test job in prod
- [ ] 4.2 Test `POST /jobs/{id}/blog-post` — queues + completes
- [ ] 4.3 Test `POST /jobs/{id}/script` — queues + completes
- [ ] 4.4 Test `POST /jobs/{id}/social-kit` — queues + completes
- [ ] 4.5 Test Whisper transcription on a no-caption video
- [ ] 4.6 Create a voice profile via API after migration 027
- [ ] 4.7 Test error scenarios (non-completed job, double-trigger, 404)
- [ ] Document any bugs found → file as issues or fix inline

## Success Criteria
- All 3 content endpoints: queue → run → complete → content retrievable
- Whisper transcription produces non-empty transcript
- Voice profile CRUD works (create, read, list, delete)
- Error scenarios return proper HTTP status codes, not 500s
- No silent failures in Railway logs

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Celery task fails with import/config error on prod | HIGH | Check Railway worker logs; may need env var on worker service |
| Generated content is empty/garbage | MED | Check LLM prompts, verify job has sufficient source data |
| Whisper still fails after balance top-up | MED | Check exact error: could be API key mismatch, region, or model deprecation |
| Voice profile endpoint doesn't exist yet | LOW | If missing, test directly via Supabase insert instead |

## Security Considerations
- Use a test account, not admin, for endpoint testing
- Do not expose bearer tokens in logs or plan files
- Verify RLS on voice_profiles prevents cross-user access
