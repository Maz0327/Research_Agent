# Research Agent: Product Vision

## Current State → Future State

**Current:** Local development tool with basic API and minimal frontend
**Future:** Modern SaaS research platform for documentary creators

---

## 1. Authentication & User Management

### Current Gap
- No authentication
- Single-user local tool
- No persistent user data

### Proposed Solution

```
┌─────────────────────────────────────────────────────┐
│  Authentication Layer                                │
├─────────────────────────────────────────────────────┤
│  • Supabase Auth (already have Supabase)            │
│  • Google OAuth (documentary creators use Google)    │
│  • Magic link email login                           │
│  • User profiles with preferences                    │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
- Use Supabase Auth (free tier: 50,000 MAUs)
- Store user preferences: default pipeline, API keys, Drive folder
- Row-level security in Supabase for job isolation

---

## 2. Project-Based Organization

### Current Gap
- Jobs are standalone, no grouping
- No way to organize research by documentary project

### Proposed Solution

```
User
 └── Projects (e.g., "Tesla Documentary")
      ├── Research Jobs
      │    ├── "Cybertruck Recall Investigation"
      │    ├── "Elon Musk Profile"
      │    └── "Tesla Safety Controversy"
      ├── Transcript Collections
      │    ├── "CEO Interviews"
      │    └── "Whistleblower Testimonies"
      ├── Source Library
      │    ├── Saved articles
      │    ├── Bookmarked videos
      │    └── Uploaded documents
      └── Export Packets
           ├── NotebookLM export
           └── Documentary blueprint
```

**New Database Tables:**
```sql
-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  name TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link jobs to projects
ALTER TABLE jobs ADD COLUMN project_id UUID REFERENCES projects(id);
```

---

## 3. Modern Frontend (Dashboard)

### Current Gap
- Single-page form submission
- No job history or management
- No progress visualization

### Proposed Solution: Full Dashboard

```
┌────────────────────────────────────────────────────────────────┐
│  Research Agent                            [User] [Settings]   │
├──────────┬─────────────────────────────────────────────────────┤
│          │                                                      │
│ Projects │  Tesla Documentary                                   │
│ ──────── │  ════════════════                                   │
│ + New    │                                                      │
│          │  [Research] [Transcripts] [Sources] [Exports]       │
│ Tesla    │                                                      │
│ ▸ SpaceX │  Recent Jobs                                        │
│   Crypto │  ┌─────────────────────────────────────────────┐    │
│          │  │ ● Cybertruck Recall    [Completed] [View]   │    │
│          │  │ ○ Elon Profile         [Running 67%]        │    │
│          │  │ ○ Safety Controversy   [Queued]             │    │
│          │  └─────────────────────────────────────────────┘    │
│          │                                                      │
│ Settings │  Quick Actions                                       │
│ Help     │  [+ New Research] [+ Extract Transcripts]           │
│          │  [+ Add Sources]  [Generate Export]                  │
│          │                                                      │
└──────────┴─────────────────────────────────────────────────────┘
```

**Tech Stack:**
- Next.js 14 App Router (upgrade from Pages)
- Tailwind CSS + shadcn/ui components
- React Query for data fetching
- Zustand for state management

---

## 4. Real-time Updates

### Current Gap
- Polling every 2 seconds for job status
- No live progress updates

### Proposed Solution

```
┌─────────────┐    WebSocket    ┌─────────────┐
│   Browser   │◄───────────────►│   Backend   │
└─────────────┘                 └─────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │   Celery    │
                               │   Worker    │
                               └─────────────┘
```

**Options:**
1. **Supabase Realtime** (easiest - already have Supabase)
   - Subscribe to job table changes
   - Built-in, no extra infrastructure

2. **Server-Sent Events (SSE)** (simpler than WebSockets)
   - `/jobs/{id}/stream` endpoint
   - Push progress updates

3. **WebSockets via FastAPI** (most flexible)
   - Bidirectional communication
   - Can send commands to running jobs

---

## 5. Cloud Deployment

### Current Gap
- Runs on localhost only
- No deployment configuration

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLOUDFLARE                          │
│                     (CDN + DDoS Protection)                 │
└────────────────────────────┬────────────────────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                      │
          ▼                                      ▼
┌─────────────────────┐              ┌─────────────────────┐
│   Vercel            │              │   Railway/Render    │
│   (Frontend)        │              │   (Backend API)     │
│                     │              │                     │
│   Next.js SSR       │◄────────────►│   FastAPI           │
│   Static Assets     │    API       │   Celery Workers    │
│   Edge Functions    │    Calls     │   Redis             │
└─────────────────────┘              └─────────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────────┐
                                     │   Supabase          │
                                     │   (Managed)         │
                                     │                     │
                                     │   PostgreSQL        │
                                     │   Auth              │
                                     │   Realtime          │
                                     │   Storage           │
                                     └─────────────────────┘
```

**Recommended Stack:**
| Component | Service | Why |
|-----------|---------|-----|
| Frontend | Vercel | Free tier, edge deployment, Next.js native |
| Backend API | Railway | Easy Docker deploy, autoscaling |
| Workers | Railway | Background workers, cron jobs |
| Database | Supabase | Already using, managed Postgres |
| Redis | Upstash | Serverless Redis, pay-per-use |
| File Storage | Supabase Storage | For uploaded docs, exports |

**Cost Estimate (Hobby/Small Scale):**
- Vercel: Free
- Railway: ~$5-20/month
- Supabase: Free tier
- Upstash Redis: Free tier
- **Total: ~$5-20/month**

---

## 6. Mobile-Friendly Design

### Current Gap
- Desktop-only layout
- Not responsive

### Proposed Solution

**Responsive Breakpoints:**
- Mobile: Collapsible sidebar, stacked cards
- Tablet: Side panel for job details
- Desktop: Full dashboard layout

**Progressive Web App (PWA):**
- Install on phone home screen
- Offline job queue viewing
- Push notifications for job completion

---

## 7. Enhanced Research Features

### 7.1 Source Library

```
┌─────────────────────────────────────────────────────────────┐
│  Source Library                            [+ Add Source]   │
├─────────────────────────────────────────────────────────────┤
│  Filter: [All ▼] [YouTube ▼] [Articles ▼] [Dates ▼]        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🎥 Tesla Whistleblower Interview                    │    │
│  │    youtube.com • 45:32 • Added Dec 15               │    │
│  │    [Transcript ✓] [Claims: 12] [⭐ Starred]        │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ 📄 NHTSA Cybertruck Recall Notice                   │    │
│  │    nhtsa.gov • PDF • Added Dec 14                   │    │
│  │    [Extracted ✓] [Claims: 5]                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Save sources from research jobs
- Upload custom documents (PDF, DOCX)
- Star/tag important sources
- Full-text search across all sources

### 7.2 Claim Tracker

```
┌─────────────────────────────────────────────────────────────┐
│  Claim Tracker                                              │
├─────────────────────────────────────────────────────────────┤
│  "Tesla knew about the accelerator issue before recall"     │
│  ──────────────────────────────────────────────────────────│
│  Status: [Verified ✓]  Confidence: [High]                  │
│                                                             │
│  Evidence:                                                  │
│  ├─ 📄 Internal memo (2023-08-15) - Primary source         │
│  ├─ 🎥 Whistleblower interview - Corroborating             │
│  └─ 📰 Reuters article - Secondary source                  │
│                                                             │
│  Counter-evidence:                                          │
│  └─ 📄 Tesla press release - Denial                        │
│                                                             │
│  [Add Evidence] [Link to Source] [Export]                   │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Timeline Builder

Visual timeline of events for documentary narrative:

```
2023 ─────────────────────────────────────────────────────────
     │
     ├─ Aug 15: Internal memo about accelerator issue
     │
     ├─ Sep 3: First customer complaint filed
     │
     ├─ Nov 12: NHTSA opens investigation
     │
2024 ─────────────────────────────────────────────────────────
     │
     ├─ Jan 8: Tesla issues voluntary recall
     │
     └─ Present
```

---

## 8. Export & Integration

### 8.1 NotebookLM Integration

One-click export to NotebookLM-ready format:

```
┌─────────────────────────────────────────────────────────────┐
│  Export to NotebookLM                                       │
├─────────────────────────────────────────────────────────────┤
│  Project: Tesla Documentary                                 │
│                                                             │
│  Include:                                                   │
│  [✓] Research summaries                                    │
│  [✓] Transcripts (12 videos)                               │
│  [✓] Key claims with evidence                              │
│  [✓] Timeline of events                                    │
│  [ ] Raw source content                                     │
│                                                             │
│  Format: [Google Docs ▼]                                   │
│                                                             │
│  [Generate Export Package]                                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Documentary Blueprint

AI-generated documentary structure:

```markdown
# Documentary Blueprint: Tesla's Hidden Crisis

## Act 1: The Promise (0:00 - 15:00)
- Opening: Cybertruck reveal hype
- Suggested clips: [Launch event, Twitter reactions]
- Key talking points: Innovation narrative

## Act 2: The Cracks (15:00 - 35:00)
- First complaints emerge
- Whistleblower introduction
- Suggested clips: [Customer videos, interview segments]
- Key claims to address: [Claim 1, Claim 2]

## Act 3: The Reckoning (35:00 - 50:00)
- NHTSA investigation
- Recall announcement
- Expert analysis
- Suggested clips: [News coverage, expert interviews]

## Conclusion (50:00 - 55:00)
- Current status
- Broader implications
- Call to action
```

---

## 9. API & Integrations

### 9.1 Public API

```yaml
# OpenAPI spec for public API
paths:
  /v1/projects:
    get: List user projects
    post: Create project

  /v1/projects/{id}/research:
    post: Start research job
    get: List research jobs

  /v1/transcripts:
    post: Extract transcripts

  /v1/sources:
    post: Add source to library
    get: Search sources

  /v1/exports:
    post: Generate export package
```

### 9.2 Integrations

| Integration | Purpose |
|-------------|---------|
| Notion | Export research to Notion pages |
| Airtable | Sync claims/sources to Airtable base |
| Zapier | Automate workflows (job complete → Slack) |
| Google Drive | Already have - primary export target |
| Descript | Export transcripts for editing |

---

## 10. Monetization (Optional)

### Freemium Model

| Tier | Price | Features |
|------|-------|----------|
| Free | $0 | 3 projects, 10 jobs/month, 5 transcripts/month |
| Pro | $29/mo | Unlimited projects, 100 jobs/month, Whisper enabled |
| Team | $79/mo | Collaboration, shared libraries, priority processing |
| Enterprise | Custom | API access, custom integrations, dedicated support |

### Usage-Based Add-ons
- Whisper transcription: $0.006/min (pass-through)
- Extended research: $5 per deep-dive job
- Priority processing: $2 per job

---

## 11. Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)
- [ ] Supabase Auth integration
- [ ] User profiles and preferences
- [ ] Docker deployment config
- [ ] Deploy to Railway/Render

### Phase 2: Dashboard (2-3 weeks)
- [ ] New frontend with App Router
- [ ] Job management dashboard
- [ ] Real-time progress updates
- [ ] Responsive design

### Phase 3: Projects & Organization (2 weeks)
- [ ] Projects CRUD
- [ ] Source library
- [ ] Job grouping by project

### Phase 4: Enhanced Features (3-4 weeks)
- [ ] Claim tracker
- [ ] Timeline builder
- [ ] NotebookLM export
- [ ] Documentary blueprint generator

### Phase 5: Polish & Scale (2 weeks)
- [ ] PWA support
- [ ] Performance optimization
- [ ] Rate limiting
- [ ] Usage analytics

---

## 12. Quick Wins (Can Do Now)

These require minimal changes and provide immediate value:

1. **Docker Compose** - Containerize everything for easy deployment
2. **Basic Auth** - Add Supabase Auth to protect endpoints
3. **Job History Page** - List all past jobs with status
4. **Vercel Deployment** - Deploy frontend to Vercel today
5. **Environment Configs** - Production vs development settings

---

## Summary

Transform from:
```
Local CLI Tool → Modern SaaS Research Platform
```

Key differentiators:
- **Documentary-focused**: Built for video creators, not general research
- **AI-powered**: Claim extraction, validation, blueprint generation
- **Integrated**: Direct export to NotebookLM, Google Docs, Descript
- **Accessible**: Use from anywhere, any device

The infrastructure is already there (Supabase, Redis, Google APIs). The main work is:
1. Authentication layer
2. Modern frontend
3. Cloud deployment
4. Enhanced organization features
