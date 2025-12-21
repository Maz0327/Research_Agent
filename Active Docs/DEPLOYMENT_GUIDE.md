# Research Agent Deployment Guide

**Version:** 1.1
**Date:** December 21, 2024
**Status:** Deployed to Production

This guide provides step-by-step instructions for deploying the Research Agent to production using Vercel (frontend) and Railway (backend).

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Architecture Overview](#2-architecture-overview)
3. [Prepare for Deployment](#3-prepare-for-deployment)
4. [Deploy Backend to Railway](#4-deploy-backend-to-railway)
5. [Deploy Frontend to Vercel](#5-deploy-frontend-to-vercel)
6. [Configure Environment Variables](#6-configure-environment-variables)
7. [Verify Deployment](#7-verify-deployment)
8. [Post-Deployment Checklist](#8-post-deployment-checklist)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

### Required Accounts

- [ ] **GitHub Account** - Repository hosting
- [ ] **Railway Account** - Backend hosting (https://railway.app)
- [ ] **Vercel Account** - Frontend hosting (https://vercel.com)
- [ ] **Supabase Project** - Database already configured

### Required API Keys (Already Configured)

- [x] `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- [x] `SUPABASE_JWT_SECRET`
- [x] `OPENAI_API_KEY`
- [x] `PERPLEXITY_API_KEY`
- [x] `GOOGLE_OAUTH_*` credentials

### Local Tools

```bash
# Install Railway CLI
npm install -g @railway/cli

# Install Vercel CLI
npm install -g vercel

# Verify installations
railway --version
vercel --version
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐         ┌─────────────────────────────────┐│
│  │    VERCEL       │         │           RAILWAY               ││
│  │                 │         │                                 ││
│  │  ┌───────────┐  │  HTTPS  │  ┌─────────┐    ┌───────────┐  ││
│  │  │  Next.js  │◄─┼────────►│  │   API   │◄──►│   Redis   │  ││
│  │  │  Frontend │  │         │  │ FastAPI │    │           │  ││
│  │  └───────────┘  │         │  └────┬────┘    └───────────┘  ││
│  │                 │         │       │                         ││
│  └─────────────────┘         │  ┌────▼────┐                    ││
│                              │  │  Worker │                    ││
│                              │  │  Celery │                    ││
│                              │  └─────────┘                    ││
│                              └─────────────────────────────────┘│
│                                         │                        │
│                              ┌──────────▼──────────┐            │
│                              │     SUPABASE        │            │
│                              │   (PostgreSQL)      │            │
│                              └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Services

| Service | Platform | Resources | Purpose |
|---------|----------|-----------|---------|
| Frontend | Vercel | Auto-scaled | Next.js web app |
| API | Railway | 512 MB | FastAPI REST API |
| Worker | Railway | 2 GB | Celery job processor |
| Redis | Railway | 512 MB | Message broker |
| Database | Supabase | Existing | PostgreSQL storage |

### Current Production Deployment

| Service | Status | URL/Details |
|---------|--------|-------------|
| **API** | ✅ Live | https://api-production-1c52.up.railway.app |
| **Worker** | ✅ Live | Running Celery with 2 concurrent workers |
| **Redis** | ✅ Live | redis.railway.internal:6379 |
| **Frontend** | 🔄 Pending | Vercel deployment |

**Railway Project ID:** `9d40e7f3-4b60-4456-8a56-9ade9a9c3321`

---

## 3. Prepare for Deployment

### Step 3.1: Push Code to GitHub

```bash
# Ensure all changes are committed
git add .
git commit -m "Prepare for production deployment"
git push origin main
```

### Step 3.2: Verify Docker Files Exist

```bash
# Check Docker files are present
ls -la Dockerfile entrypoint.sh docker-compose.yml frontend/Dockerfile
```

Expected output:
```
-rw-r--r--  Dockerfile           # Unified container for API and Worker
-rw-r--r--  entrypoint.sh        # Service type selector script
-rw-r--r--  docker-compose.yml
-rw-r--r--  frontend/Dockerfile
```

**Note:** We use a unified Dockerfile approach. The `entrypoint.sh` script checks the `SERVICE_TYPE` environment variable to determine whether to run the API (Uvicorn) or Worker (Celery).

### Step 3.3: Create .dockerignore

```bash
cat > .dockerignore << 'EOF'
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/
.coverage

# Environment
.env
.env.local
.env*.local

# Node
node_modules/
.next/

# IDE
.vscode/
.idea/

# Git
.git/
.gitignore

# Documentation
*.md
docs/

# Tests
tests/
*_test.py
test_*.py
EOF
```

### Step 3.4: Create Railway Configuration

```bash
cat > railway.toml << 'EOF'
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
EOF
```

### Step 3.5: Create Vercel Configuration

```bash
cat > vercel.json << 'EOF'
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
EOF
mv vercel.json frontend/
```

---

## 4. Deploy Backend to Railway

### Step 4.1: Login to Railway

```bash
railway login
```

This opens a browser for authentication.

### Step 4.2: Create New Project

```bash
# Create new Railway project
railway init

# When prompted:
# - Project Name: research-agent
# - Select: Empty Project
```

### Step 4.3: Add Redis Service

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Open your `research-agent` project
3. Click **"+ New"** → **"Database"** → **"Add Redis"**
4. Wait for Redis to deploy
5. Click Redis service → **"Variables"** tab
6. Copy the `REDIS_URL` value (you'll need it later)

### Step 4.4: Deploy API Service

```bash
# Link to project
railway link

# Create new service for API
railway service create api

# Deploy API
railway up --service api

# Wait for build to complete (5-10 minutes first time)
```

### Step 4.5: Deploy Worker Service

The Worker uses the **same Dockerfile** as the API but runs Celery instead of Uvicorn. This is controlled by the `SERVICE_TYPE` environment variable.

```bash
# Create worker service
railway service create worker

# Set SERVICE_TYPE to run Celery instead of API
railway variables --set "SERVICE_TYPE=worker" --service worker

# The worker will automatically use the same Dockerfile
# but entrypoint.sh will start Celery based on SERVICE_TYPE=worker

# Deploy worker (or it auto-deploys from GitHub)
railway up --service worker
```

**How It Works:**
- `SERVICE_TYPE=api` (default) → runs `uvicorn backend.app.main:app`
- `SERVICE_TYPE=worker` → runs `celery -A backend.worker worker` with a health endpoint

### Step 4.6: Configure API Environment Variables

Go to Railway Dashboard → `api` service → **Variables** tab:

```bash
# Required - Copy these values from your local .env
ENVIRONMENT=production
REDIS_URL=${REDIS_URL}  # Use Railway reference
SUPABASE_URL=https://lmkqozgsrwisozebskzd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...  # Your full key
SUPABASE_JWT_SECRET=puGTEjHQ...  # Your full secret
OPENAI_API_KEY=sk-proj-...  # Your full key
PERPLEXITY_API_KEY=pplx-...  # Your full key
GOOGLE_OAUTH_CLIENT_ID=263123928563-...
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
GOOGLE_OAUTH_REFRESH_TOKEN=1//05RU-...
FRONTEND_ORIGINS=https://your-app.vercel.app  # Update after Vercel deploy
```

### Step 4.7: Configure Worker Environment Variables

Go to Railway Dashboard → `worker` service → **Variables** tab:

Copy the **same variables** from API service, plus the SERVICE_TYPE variable:

```bash
# Required: This tells entrypoint.sh to run Celery
SERVICE_TYPE=worker

# Copy all other env vars from API service:
# - REDIS_URL
# - SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
# - OPENAI_API_KEY, PERPLEXITY_API_KEY
# - GOOGLE_OAUTH_* credentials
# Use Railway's "Reference" feature to copy from api service
```

### Step 4.8: Configure Worker Resources

Go to Railway Dashboard → `worker` service → **Settings**:

1. **Memory:** Set to 2048 MB (2 GB)
2. **Restart Policy:** On Failure
3. **Health Check:** `/health` endpoint works (entrypoint.sh runs a health server on PORT)

### Step 4.9: Get API URL

After deployment completes:

1. Go to Railway Dashboard → `api` service
2. Click **"Settings"** → **"Networking"**
3. Click **"Generate Domain"**
4. Copy the URL

**Current Production URL:** `https://api-production-1c52.up.railway.app`

---

## 5. Deploy Frontend to Vercel

### Step 5.1: Login to Vercel

```bash
cd frontend
vercel login
```

### Step 5.2: Deploy to Vercel

```bash
# Deploy (first time setup)
vercel

# When prompted:
# - Set up and deploy? Yes
# - Which scope? Select your account
# - Link to existing project? No
# - Project name? research-agent-frontend
# - Directory? ./
# - Override settings? No
```

### Step 5.3: Configure Environment Variables

Go to [Vercel Dashboard](https://vercel.com/dashboard):

1. Select `research-agent-frontend` project
2. Go to **Settings** → **Environment Variables**
3. Add the following variables:

| Key | Value | Environment |
|-----|-------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://lmkqozgsrwisozebskzd.supabase.co` | Production |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGci...` (anon key) | Production |
| `NEXT_PUBLIC_API_URL` | `https://research-agent-api.up.railway.app` | Production |

### Step 5.4: Redeploy with Environment Variables

```bash
# Trigger production deployment
vercel --prod
```

### Step 5.5: Get Frontend URL

After deployment:
- Your frontend URL will be: `https://research-agent-frontend.vercel.app`
- Or a custom domain if configured

---

## 6. Configure Environment Variables

### Step 6.1: Update Railway CORS Settings

Now that you have the Vercel URL, update Railway:

1. Go to Railway Dashboard → `api` service → **Variables**
2. Update `FRONTEND_ORIGINS`:

```bash
FRONTEND_ORIGINS=https://research-agent-frontend.vercel.app
```

3. Railway will auto-redeploy

### Step 6.2: Verify All Variables

**Railway API Service:**
```
ENVIRONMENT=production
REDIS_URL=${REDIS_URL}
SUPABASE_URL=https://lmkqozgsrwisozebskzd.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_JWT_SECRET=puGTEjHQ...
OPENAI_API_KEY=sk-proj-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_OAUTH_CLIENT_ID=263123928563-...
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
GOOGLE_OAUTH_REFRESH_TOKEN=1//05RU-...
FRONTEND_ORIGINS=https://research-agent-frontend.vercel.app
```

**Railway Worker Service:**
```
(Same as API service)
```

**Vercel Frontend:**
```
NEXT_PUBLIC_SUPABASE_URL=https://lmkqozgsrwisozebskzd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_API_URL=https://research-agent-api.up.railway.app
```

---

## 7. Verify Deployment

### Step 7.1: Test API Health

```bash
# Health check
curl https://api-production-1c52.up.railway.app/health

# Expected response:
# {"status":"ok","environment":"production"}
```

### Step 7.2: Test API Docs

Open in browser:
```
https://api-production-1c52.up.railway.app/docs
```

You should see the Swagger documentation.

### Step 7.3: Test Frontend

Open in browser:
```
https://research-agent-frontend.vercel.app
```

You should see the Research Agent dashboard.

### Step 7.4: Test Authentication

1. Go to the frontend
2. Click "Sign In"
3. Complete authentication via Supabase
4. Verify you're redirected back and logged in

### Step 7.5: Test Job Creation

```bash
# Create a test job
curl -X POST https://api-production-1c52.up.railway.app/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"prompt": "Test research topic", "pipeline": "quick"}'

# Expected response:
# {"job_id": "uuid-here"}
```

### Step 7.6: Monitor Worker Logs

1. Go to Railway Dashboard → `worker` service
2. Click **"Logs"** tab
3. Watch for job processing:

```
[INFO] Stage 1: Initializing job abc-123
[INFO] Stage 2: Planning research
[INFO] Starting claim extraction from X transcripts and Y web sources
[INFO] Memory optimization: max_chunks=100, batch_size=10
...
```

---

## 8. Post-Deployment Checklist

### Security

- [x] HTTPS enabled (automatic with Railway/Vercel)
- [x] JWT secret is 32+ characters
- [x] Rate limiting enabled
- [x] CORS configured for production domain only
- [x] Security headers configured
- [x] RLS policies applied in Supabase

### Performance

- [x] Worker has 2GB memory
- [x] Memory optimization enabled (max_chunks=100)
- [x] Redis connected
- [x] Health checks configured

### Monitoring

- [ ] Set up error tracking (Sentry recommended)
- [ ] Configure log aggregation
- [ ] Set up uptime monitoring
- [ ] Configure alerting for failures

### Backups

- [ ] Supabase database backups enabled
- [ ] Document recovery procedures

---

## 9. Troubleshooting

### Issue: API Returns 502 Bad Gateway

**Cause:** API service crashed or hasn't started

**Solution:**
1. Check Railway logs for errors
2. Verify environment variables are set
3. Ensure Redis is healthy
4. Redeploy: `railway up --service api`

### Issue: Worker Gets Killed (SIGKILL)

**Cause:** Memory exhaustion

**Solution:**
1. Verify worker has 2GB memory in Railway settings
2. Check logs for "Reached max_chunks limit" - this is expected
3. If still crashing, reduce `max_chunks` from 100 to 75

### Issue: CORS Errors in Browser

**Cause:** FRONTEND_ORIGINS not set correctly

**Solution:**
1. Verify `FRONTEND_ORIGINS` matches exactly your Vercel URL
2. Include protocol: `https://your-app.vercel.app`
3. Redeploy API after changing

### Issue: Frontend Can't Connect to API

**Cause:** Wrong API URL or CORS

**Solution:**
1. Verify `NEXT_PUBLIC_API_URL` in Vercel matches Railway URL
2. Test API health directly: `curl https://api-url/health`
3. Check browser console for specific errors

### Issue: Jobs Stuck in "queued"

**Cause:** Worker not running or Redis disconnected

**Solution:**
1. Check worker logs in Railway
2. Verify Redis is healthy (green status)
3. Verify `REDIS_URL` is set in worker service
4. Restart worker: Railway Dashboard → worker → Restart

### Issue: Google Drive Upload Fails

**Cause:** OAuth credentials expired or incorrect

**Solution:**
1. Verify all three Google OAuth env vars are set
2. Refresh token may have expired - regenerate if needed
3. Check worker logs for specific error message

---

## Cost Summary

### Railway (Monthly)

| Service | Resources | Cost |
|---------|-----------|------|
| API | 512 MB, shared CPU | ~$5 |
| Worker | 2 GB, shared CPU | ~$10 |
| Redis | 512 MB | ~$5 |
| **Total** | | **~$20** |

### Vercel (Monthly)

| Plan | Cost |
|------|------|
| Hobby (free tier) | $0 |
| Pro (if needed) | $20 |

### API Costs (Estimated)

| Service | Usage | Cost |
|---------|-------|------|
| OpenAI | 10-20 jobs/day | ~$10-20 |
| Perplexity | 10-20 jobs/day | ~$10-20 |
| YouTube API | Free tier | $0 |
| Google Drive | Free | $0 |

### Total Monthly Cost

- **Infrastructure:** ~$20-40
- **API Usage:** ~$20-40
- **Grand Total:** ~$40-80/month

---

## Quick Reference Commands

```bash
# Railway (Project ID: 9d40e7f3-4b60-4456-8a56-9ade9a9c3321)
railway link -p 9d40e7f3-4b60-4456-8a56-9ade9a9c3321  # Link to project
railway service API              # Switch to API service
railway service Worker           # Switch to Worker service
railway logs -n 50               # View last 50 logs
railway variables                # List variables
railway variables --set "KEY=value"  # Set variable
railway status                   # Check project status

# Vercel
vercel login                     # Authenticate
vercel                          # Deploy preview
vercel --prod                   # Deploy production
vercel logs                     # View logs
vercel env ls                   # List variables

# Testing (Production)
curl https://api-production-1c52.up.railway.app/health  # Health check
curl https://api-production-1c52.up.railway.app/docs    # API docs (browser)
```

---

## Support

For issues with:
- **Railway:** https://docs.railway.app
- **Vercel:** https://vercel.com/docs
- **Supabase:** https://supabase.com/docs
- **This Project:** Create issue in GitHub repository

---

**Deployment Guide Complete**

Your Research Agent is now ready for production deployment. Follow the steps above to deploy to Railway and Vercel. Expected deployment time: 30-60 minutes.
