#!/usr/bin/env bash
set -euo pipefail

echo "SERVICE_TYPE=${SERVICE_TYPE:-api}"

if [ "${SERVICE_TYPE:-api}" = "worker" ]; then
  echo "Starting Research Agent Worker (Celery)"

  # IMPORTANT: this must match your celery app object.
  # If your worker currently starts successfully in Railway, keep the -A target exactly like this.
  exec celery -A backend.worker worker -Q research --loglevel=INFO --concurrency=2

else
  echo "Starting Research Agent API (FastAPI)"
  # Railway provides PORT automatically. Default to 8000 for local runs.
  exec uvicorn backend.app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
