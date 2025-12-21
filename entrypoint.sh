#!/bin/bash
# Unified entrypoint for Research Agent services
# Set SERVICE_TYPE=worker to run Celery, otherwise runs API

set -e

SERVICE_TYPE="${SERVICE_TYPE:-api}"
PORT="${PORT:-8000}"

if [ "$SERVICE_TYPE" = "worker" ]; then
    echo "Starting Research Agent Worker (Celery)"

    # Start health endpoint in background for Railway healthchecks
    python3 -c "
import http.server
import socketserver
import os

PORT = int(os.environ.get('PORT', 8080))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{\"status\":\"ok\",\"service\":\"worker\"}')
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, format, *args):
        pass

with socketserver.TCPServer(('', PORT), HealthHandler) as httpd:
    httpd.serve_forever()
" &

    # Start Celery worker in foreground
    exec celery -A backend.worker worker --loglevel=INFO --concurrency=2
else
    echo "Starting Research Agent API (Uvicorn)"
    exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
fi
