# Phase 05: SSE Streaming

## Context Links
- [Brainstorm -- SSE](../../plans/reports/brainstorm-260405-1617-product-viability-overhaul.md#sse-streaming--progressive-ui)
- [Technical Validation](../../plans/reports/researcher-260406-1233-brainstorm-validation.md#claim-1-sse-streaming-from-celery--fastapi--nextjs)
- Worker: `backend/worker.py` (3517 lines)
- Frontend polling: `frontend/store/jobs.ts` uses TanStack Query polling

## Overview
- **Priority:** P2 (Phase 1 -- Product Feel)
- **Status:** pending
- **Effort:** 2-3 weeks
- **Depends on:** Phase 00
- **Description:** Replace polling with SSE streaming. Celery worker publishes events to Redis pub/sub. FastAPI SSE endpoint subscribes and streams to frontend. Progressive UI: source cards appear during ingestion, sections stream during synthesis.

## Key Insights
- Current UX: 3-minute wait with progress bar polling every 2s. Feels dead.
- Celery workers are separate processes -- cannot push SSE directly to FastAPI
- Redis pub/sub is the bridge: Celery publishes, FastAPI subscribes
- Redis is already available (Celery broker). No new infra needed.
- FastAPI `StreamingResponse` with async generators handles SSE natively
- Frontend `EventSource` API handles SSE natively
- Estimated 2-3 weeks because EVERY pipeline stage needs granular event emission

## Requirements

### Functional
- SSE endpoint: `GET /jobs/{id}/stream` -- authenticated, per-job event stream
- Events emitted at each pipeline stage with granular progress:
  - `source_started` / `source_completed` (with title, thumbnail)
  - `extraction_progress` (per-source, with preview snippet)
  - `synthesis_started` / `synthesis_streaming` (partial content)
  - `document_ready` (doc type, version)
  - `editorial_started` / `editorial_complete`
  - `job_completed` / `job_failed`
- Frontend progressive rendering: skeleton -> streaming text -> final
- Graceful fallback: if SSE connection drops, fall back to existing polling
- SSE auto-reconnect with `EventSource` retry mechanism

### Non-Functional
- SSE connection timeout: 10 minutes (max job duration)
- Event latency: < 500ms from Celery publish to frontend receipt
- Memory: SSE connections cleaned up on job completion
- Redis pub/sub channel cleanup after job done

## Architecture

### Event Flow
```
Celery Worker                Redis                FastAPI             Frontend
    |                          |                     |                   |
    |-- publish(event) ------->|                     |                   |
    |                          |-- notify ---------> |                   |
    |                          |                     |-- SSE event ----> |
    |                          |                     |                   |-- render
```

### Redis Channel Naming
```
Channel: job:{job_id}:events
```

### Event Schema
```json
{
  "event": "source_completed",
  "data": {
    "job_id": "abc-123",
    "stage": "extraction",
    "source_id": "SRC_1",
    "source_title": "Video Title",
    "thumbnail_url": "...",
    "progress_percent": 35,
    "timestamp": "2026-04-06T13:00:00Z"
  }
}
```

### SSE Message Format (HTTP)
```
event: source_completed
data: {"job_id":"abc-123","stage":"extraction",...}

event: synthesis_streaming
data: {"chunk":"The key finding across sources is...","section":"themes"}

```

## Related Code Files

### Files to MODIFY

| File | Change |
|------|--------|
| `backend/worker.py` | Add `publish_event()` calls throughout pipeline stages |
| `backend/pipeline/stage_runner.py` | Add event emission hooks around each stage |
| `backend/pipeline/stages/semantic_extraction.py` | Emit per-source extraction events |
| `backend/pipeline/stages/semantic_synthesis.py` (or new `gap_synthesis.py`) | Emit synthesis streaming events |
| `backend/pipeline/stages/document_assembly.py` | Emit document_ready events |
| `backend/pipeline/stages/editorial_pass.py` | Emit editorial_started/complete |
| `backend/pipeline/transcript_acquisition.py` | Emit source_started/completed |
| `backend/app/main.py` | Register SSE router |
| `frontend/store/jobs.ts` | Add SSE connection management alongside existing polling |
| `frontend/components/job-detail-v2/job-detail-content.tsx` | Progressive rendering based on SSE events |

### Files to CREATE

| File | Purpose | Lines |
|------|---------|-------|
| `backend/services/event_publisher.py` | Redis pub/sub publisher utility | ~60 |
| `backend/app/routes/sse_routes.py` | `GET /jobs/{id}/stream` SSE endpoint | ~80 |
| `frontend/hooks/use-job-stream.ts` | EventSource hook for SSE connection | ~80 |
| `frontend/components/job-detail-v2/streaming-skeleton.tsx` | Progressive loading skeleton | ~60 |
| `frontend/components/job-detail-v2/source-card-streaming.tsx` | Source card that appears during ingestion | ~50 |

## Implementation Steps

### Task 5.1: Create event publisher service
1. Create `backend/services/event_publisher.py`
2. `class EventPublisher`:
   - `__init__(self, redis_url: str)` -- connect to Redis
   - `publish(self, job_id: str, event_type: str, data: dict)` -- publish to `job:{job_id}:events`
   - `close_channel(self, job_id: str)` -- publish terminal event + cleanup
3. Singleton pattern: one publisher per worker process
4. JSON serialize event data
5. Include timestamp in every event

### Task 5.2: Create SSE endpoint
1. Create `backend/app/routes/sse_routes.py`
2. `GET /jobs/{id}/stream` endpoint:
   ```python
   @router.get("/jobs/{job_id}/stream")
   async def stream_job_events(job_id: str, user: AuthUser = Depends(get_current_user)):
       async def event_generator():
           pubsub = redis_client.pubsub()
           await pubsub.subscribe(f"job:{job_id}:events")
           try:
               async for message in pubsub.listen():
                   if message["type"] == "message":
                       yield f"data: {message['data']}\n\n"
           finally:
               await pubsub.unsubscribe()
       return StreamingResponse(event_generator(), media_type="text/event-stream")
   ```
3. Auth: verify user owns the job
4. Headers: `Cache-Control: no-cache`, `Connection: keep-alive`
5. Register router in `backend/app/main.py`

### Task 5.3: Add event emission to pipeline stages
1. In `backend/worker.py`, create helper:
   ```python
   def emit(job_id: str, event: str, data: dict):
       publisher.publish(job_id, event, data)
   ```
2. Add calls throughout pipeline:
   - Before transcript acquisition: `emit(job_id, "source_started", {source_id, url})`
   - After transcript: `emit(job_id, "source_completed", {source_id, title, thumbnail})`
   - During extraction: `emit(job_id, "extraction_progress", {source_id, preview})`
   - Before synthesis: `emit(job_id, "synthesis_started", {})`
   - During synthesis (if streaming Gemini): `emit(job_id, "synthesis_streaming", {chunk})`
   - After assembly: `emit(job_id, "document_ready", {doc_type, version})`
   - On completion: `emit(job_id, "job_completed", {})` + close channel
   - On failure: `emit(job_id, "job_failed", {error})` + close channel

### Task 5.4: Create frontend SSE hook
1. Create `frontend/hooks/use-job-stream.ts`
2. `useJobStream(jobId: string)` hook:
   - Opens `EventSource` to `GET /jobs/{jobId}/stream`
   - Parses events, dispatches to Zustand store or local state
   - Auto-reconnect on disconnect (EventSource does this by default)
   - Close connection on `job_completed` or `job_failed`
   - Fallback: if SSE fails to connect, use existing TanStack Query polling
3. Return: `{ events: StreamEvent[], isStreaming: boolean, latestStage: string }`

### Task 5.5: Progressive rendering components
1. Create `frontend/components/job-detail-v2/streaming-skeleton.tsx`:
   - Skeleton layout matching hero document structure
   - Sections fill in progressively as content arrives
2. Create `frontend/components/job-detail-v2/source-card-streaming.tsx`:
   - Appears in sidebar when `source_completed` event received
   - Animates in (Framer Motion fade-in)
3. Update `frontend/components/job-detail-v2/job-detail-content.tsx`:
   - If job is `running`, use `useJobStream` + show `StreamingSkeleton`
   - Source cards appear in sidebar as `source_completed` events arrive
   - When `document_ready` event received, render hero doc
   - When `job_completed`, switch to full static view

### Task 5.6: Fallback to polling
1. Keep existing TanStack Query polling in `frontend/store/jobs.ts` as fallback
2. In `useJobStream`, if SSE connection fails after 3 retries, set `useFallbackPolling = true`
3. Components check: if `useFallbackPolling`, use existing polling behavior
4. SSE is an enhancement, not a requirement

### Task 5.7: Test
1. Backend: unit test EventPublisher with mock Redis
2. Backend: integration test SSE endpoint (publish event, verify received)
3. Frontend: test EventSource connection and event parsing
4. Manual: start a job, observe events streaming in real-time
5. Manual: kill SSE connection mid-job, verify fallback to polling works
6. `pytest backend/tests/ -v` && `npm run build`

## Todo Checklist
- [ ] 5.1 Create `event_publisher.py` Redis pub/sub service
- [ ] 5.2 Create SSE endpoint `GET /jobs/{id}/stream`
- [ ] 5.3 Add event emission calls to all pipeline stages
- [ ] 5.4 Create `use-job-stream.ts` frontend hook
- [ ] 5.5 Progressive rendering components (skeleton, source cards)
- [ ] 5.6 Fallback-to-polling mechanism
- [ ] 5.7 Full test suite: unit, integration, manual

## Success Criteria
- Source cards appear within 2s of transcript acquisition
- Synthesis content streams progressively
- "Document ready" event triggers hero doc render
- If SSE fails, polling takes over transparently
- No SSE connection leaks (cleanup on completion/disconnect)
- Pipeline performance not degraded by event emission

## Risk Assessment
| Risk | Severity | Mitigation |
|------|----------|------------|
| Redis pub/sub message loss | LOW | Redis pub/sub is fire-and-forget. Polling fallback catches missed events. |
| SSE connection limits per browser | LOW | Max 6 per domain. One per job is fine. |
| Memory leak from unclosed SSE connections | MEDIUM | Close channel on job_completed/failed. Server-side timeout at 10min. |
| Celery event emission slows pipeline | LOW | Redis publish is < 1ms. Negligible overhead. |

## Security Considerations
- SSE endpoint requires authentication (JWT)
- Verify user owns the job before allowing subscription
- Rate limit SSE connections per user (prevent DoS)
- No sensitive data in SSE events (only progress, titles, previews)
