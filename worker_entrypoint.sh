#!/bin/bash
# Worker entrypoint that runs Celery with a health endpoint for Railway

# Start a simple health server in the background
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
        pass  # Suppress logs

with socketserver.TCPServer(('', PORT), HealthHandler) as httpd:
    httpd.serve_forever()
" &

# Start Celery worker in foreground
exec celery -A backend.worker worker --loglevel=INFO --concurrency=2
