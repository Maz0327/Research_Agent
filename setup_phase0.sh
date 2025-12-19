#!/bin/bash
# Phase 0 Setup Script
# Run this script to set up the development environment

set -e  # Exit on error

echo "=========================================="
echo "Research Agent - Phase 0 Setup"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️  IMPORTANT: Edit .env and add your actual API keys before running the application!"
    echo ""
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Download spaCy model for entity extraction
echo "🔽 Downloading spaCy English model..."
python -m spacy download en_core_web_sm

# Check if Redis is running
echo "🔍 Checking Redis..."
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis is not running!"
    echo "Starting Redis server..."

    # Try to start Redis
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
        echo "✅ Redis started"
    else
        echo "❌ Redis not installed. Please install Redis:"
        echo "   Ubuntu/Debian: sudo apt-get install redis-server"
        echo "   macOS: brew install redis"
        echo "   Then run: redis-server --daemonize yes"
    fi
else
    echo "✅ Redis is already running"
fi

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

echo ""
echo "=========================================="
echo "✅ Phase 0 Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Verify Supabase access: python -c 'from backend.config import require_supabase; require_supabase()'"
echo "3. Start the backend: uvicorn backend.app.main:app --reload"
echo "4. Start the Celery worker: celery -A backend.worker worker --loglevel=info"
echo ""
echo "For Phase 1, you'll need to run database migrations."
echo "See EXECUTION_PLAN.md for details."
echo ""
