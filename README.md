# Research Agent - Phase 1 Skeleton

A cloud-based research backend for aggregating content from Reddit, Twitter, articles, YouTube, and more.

## Phase 1: Project Skeleton

This phase provides a minimal working skeleton with:
- FastAPI HTTP API
- Celery worker with stub research job task
- Playwright scraper stub for Reddit
- Configuration management with Pydantic
- Basic job queuing and status tracking

## Prerequisites

- Python 3.11+
- Redis (for Celery broker/backend)
- Virtual environment (recommended)

## Setup

### 1. Create and activate virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

### 4. Configure environment

Copy the example environment file and edit as needed:

```bash
cp .env.example .env
```

Edit `.env` to set your Redis URL and other configuration. For Phase 1, the defaults should work if Redis is running locally.

### 5. Start Redis

Make sure Redis is running on `localhost:6379` (or update `REDIS_URL` in `.env`):

```bash
# macOS (with Homebrew)
brew services start redis

# Or run directly
redis-server
```

### 6. Start Celery worker

In a separate terminal:

```bash
celery -A backend.worker worker --loglevel=INFO
```

### 7. Start the API server

In another terminal:

```bash
uvicorn backend.app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) at: `http://localhost:8000/docs`

## Testing Phase 1

### 1. Health check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "environment": "dev"
}
```

### 2. Create a research job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"topic": "Test topic"}'
```

Expected response:
```json
{
  "job_id": "uuid-here",
  "topic": "Test topic",
  "status": "queued",
  "result": null
}
```

### 3. Check job status

```bash
curl http://localhost:8000/jobs/{job_id}
```

Replace `{job_id}` with the UUID returned from the previous request.

## Project Structure

```
Research_Agent/
├── backend/
│   ├── __init__.py
│   ├── config.py              # Settings loader with Pydantic
│   ├── state.py               # Shared job state management
│   ├── worker.py              # Celery app and tasks
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py            # FastAPI application
│   └── scrapers/
│       ├── __init__.py
│       └── reddit_scraper.py  # Playwright scraper stub
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Future Phases

- **Phase 2:** Planner + YouTube + transcript pipeline (OpenAI Whisper + YouTube)
- **Phase 3:** Reddit/Twitter/Article scraping via Playwright, plus JSON structuring
- **Phase 4:** Packet assembly + Google Drive upload + basic front-end dashboard

## Notes

- Job state is currently stored in-memory (`JOB_STORE` dict in `backend/state.py`). This will be replaced with Supabase/Postgres in later phases.
- The Celery task returns a stub result. Real research pipeline logic will be added in later phases.
- The Reddit scraper is a placeholder. Full implementation will come in Phase 3.

