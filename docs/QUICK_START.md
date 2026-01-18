# Research Agent Quick Start

Get up and running with the Research Agent in 10 minutes.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Redis server
- API Keys:
  - Google API Key (Gemini 2.5)
  - Supadata API Key (optional, for transcripts)
  - Supabase project (for production)

---

## Local Development Setup

### 1. Clone and Setup Backend

```bash
# Clone repository
git clone https://github.com/your-org/Research_Agent.git
cd Research_Agent

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your API keys:

```bash
# Required
REDIS_URL=redis://localhost:6379
GOOGLE_API_KEY=your-gemini-api-key

# Optional (for transcripts)
SUPADATA_API_KEY=your-supadata-key

# Production only
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. Start Services

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
source venv/bin/activate
celery -A backend.worker worker --loglevel=INFO

# Terminal 3: Start API Server
source venv/bin/activate
uvicorn backend.app.main:app --reload
```

API available at `http://localhost:8000/docs` (Swagger UI)

### 4. Frontend (Optional)

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:3000`

---

## Creating Your First Job

### Video Analysis

```bash
curl -X POST http://localhost:8000/jobs/video-analysis \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://youtube.com/watch?v=YOUR_VIDEO_ID"}'
```

### Text Input

```bash
curl -X POST http://localhost:8000/jobs/text-input \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Research Notes",
    "content": "Your text content here...",
    "platform_hint": "notes"
  }'
```

### Check Job Status

```bash
curl http://localhost:8000/jobs/{job_id}
```

### Get Documents

```bash
# Source Ledger (Doc 0)
curl http://localhost:8000/jobs/{job_id}/documents/doc_0

# Jump-Start Directions (Doc 1)
curl http://localhost:8000/jobs/{job_id}/documents/doc_1

# Semantic Brief (Doc 2)
curl http://localhost:8000/jobs/{job_id}/documents/doc_2
```

---

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest backend/tests/ -v

# Expected: 948 tests passing

# Run specific test file
pytest backend/tests/test_semantic_models.py -v

# Run with coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

## Key Concepts

### Analysis Modes

| Mode | Source Type | Confidence Ceiling |
|------|-------------|-------------------|
| `transcript_grounded` | YouTube + transcript | HIGH |
| `caption_grounded` | YouTube + captions | MEDIUM |
| `video_only` | YouTube, no text | LOW |
| `text_provided` | User-pasted text | MEDIUM |
| `ocr_extracted` | Screenshot | MEDIUM |
| `article_fetched` | Web article | HIGH |

### Output Documents

- **Doc 0 (Source Ledger)**: Raw data, full transcripts, metadata
- **Doc 1 (Jump-Start)**: Gaps, research directions, next steps
- **Doc 2 (Semantic Brief)**: Themes, key points, tensions
- **Doc 3 (Producer Packet)**: Creative interpretation (optional)

### Pipeline Flow

```
Source Identity → Extraction → Validation → Synthesis → Assembly
```

Each source is extracted in a **separate LLM call** (source isolation).

---

## Common Commands

```bash
# Backend
uvicorn backend.app.main:app --reload         # API server
celery -A backend.worker worker --loglevel=INFO  # Worker
pytest backend/tests/ -v                      # Tests

# Frontend
cd frontend && npm run dev                    # Dev server
npm run build && npm run lint                 # Build + lint
```

---

## Next Steps

- Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Read [API_Endpoint_Spec.md](../API_Endpoint_Spec.md) for full API documentation
- Read [RASS.md](authoritative/spec/RASS.md) for system specification
