# Phase 6: Supporting Pages — Settings, Usage, Transcripts, Admin, Landing, Login

## Context
- Plan: [plan.md](plan.md)
- Depends on: [Phase 2](phase-02-layout-system-sidebar-columns.md) (AppShell), [Phase 3](phase-03-core-pages-dashboard-queue.md) (stores)
- Current: 8 pages totaling ~2,600 lines across settings, usage, transcripts, admin (4 pages), landing, login

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P2 |
| Status | pending |
| Effort | 5h |
| Description | Migrate remaining pages to App Router with shadcn/ui redesign |

## Key Insights
- These pages are simpler than dashboard/job-detail — mostly forms and data tables
- Settings (367 lines) uses `components/settings/` (8 files) — well decomposed already
- Admin pages (4 total) share a layout — maps to `(admin)` route group from Phase 2
- Landing page (`index.tsx`) is just a redirect-if-authed page — minimal
- Login page (262 lines) has Google OAuth + magic link — straightforward shadcn form
- Transcripts page (420 lines) has YouTube URL input + transcript display
- Usage page (335 lines) shows API credits/stats

## Requirements
1. Settings page with shadcn/ui form components
2. Usage page with stats display
3. Transcripts page with input + display
4. Admin dashboard + 3 sub-pages
5. Landing page (redirect logic)
6. Login page (Google OAuth + magic link)

## Architecture

### Page Map
```
app/
├── page.tsx                    # Landing: redirect if authed
├── login/page.tsx              # Auth page
├── (app)/
│   ├── settings/page.tsx       # User preferences
│   ├── usage/page.tsx          # API usage/credits
│   └── transcripts/page.tsx    # YouTube transcripts
├── (admin)/
│   └── admin/
│       ├── page.tsx            # Admin dashboard
│       ├── errors/page.tsx     # Error logs
│       ├── jobs/page.tsx       # Job management
│       └── users/page.tsx      # User management
```

### Component Organization
```
components/
├── settings/
│   ├── SettingsContent.tsx      # 'use client' orchestrator
│   ├── ProfileSection.tsx       # Name, email, avatar
│   ├── PreferencesSection.tsx   # Theme, default mode, niche
│   ├── ApiKeysSection.tsx       # API key management
│   ├── StyleGuidesSection.tsx   # Style guide CRUD
│   ├── VoiceProfilesSection.tsx # Voice profile CRUD
│   └── DangerZoneSection.tsx    # Account deletion
├── admin/
│   ├── AdminDashboard.tsx       # Stats overview
│   ├── ErrorLogTable.tsx        # Error list + filters
│   ├── JobManagementTable.tsx   # Job list + actions
│   └── UserManagementTable.tsx  # User list + roles
├── auth/
│   ├── LoginForm.tsx            # Google OAuth + magic link
│   └── AuthGuard.tsx            # Client-side auth check wrapper
└── landing/
    └── LandingHero.tsx          # Marketing landing (if unauthenticated)
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `pages/settings.tsx` | Decompose → app/(app)/settings/ | 367 lines |
| `pages/usage.tsx` | Decompose → app/(app)/usage/ | 335 lines |
| `pages/transcripts.tsx` | Decompose → app/(app)/transcripts/ | 420 lines |
| `pages/admin/index.tsx` | Migrate → app/(admin)/admin/ | Admin dashboard |
| `pages/admin/errors.tsx` | Migrate | Error logs |
| `pages/admin/jobs.tsx` | Migrate | Job management |
| `pages/admin/users.tsx` | Migrate | User management |
| `pages/index.tsx` | Migrate → app/page.tsx | Landing/redirect |
| `pages/login.tsx` | Migrate → app/login/page.tsx | Auth page, 262 lines |
| `components/settings/*` | Rebuild | 8 settings section components |
| `components/AdminLayout.tsx` | Superseded | Replaced by (admin)/layout.tsx |
| `store/settings.ts` | Preserve | Settings store |
| `store/admin.ts` | Preserve | Admin store |
| `store/style-guides.ts` | Preserve | Style guides store |
| `store/voice-profiles.ts` | Preserve | Voice profiles store |
| `lib/supabase.ts` | Preserve | Auth client |

## Implementation Steps

### 6.1 Landing page (`app/page.tsx`)
- Server component
- Check auth state (via cookies/headers)
- If authenticated: redirect to `/dashboard`
- If not: render LandingHero (marketing page or simple redirect to `/login`)

### 6.2 Login page (`app/login/page.tsx`)
- No AppShell layout (standalone page)
- LoginForm component ('use client'):
  - Google OAuth button (shadcn Button with Google icon)
  - Magic link input (shadcn Input + Button)
  - Loading states during auth flow
  - Error message display
  - Redirect to `/dashboard` on success
- Dark themed card centered on page

### 6.3 Settings page
- SettingsContent orchestrator with sections as Accordion or Card stack
- **ProfileSection**: name input, email display, avatar upload placeholder
- **PreferencesSection**: theme Select (dark/light/system), default mode Select, default niche Input
- **StyleGuidesSection**: list of style guides with create/edit/delete
- **VoiceProfilesSection**: list of voice profiles with create/edit/delete
- **ApiKeysSection**: API key display (masked) with regenerate button
- **DangerZoneSection**: destructive Card with delete account button + confirmation Dialog
- All use shadcn form components: Input, Select, Button, Dialog, Separator

### 6.4 Usage page
- Stats cards: total jobs, credits used, credits remaining
- Usage breakdown: by month or by job
- Simple table or list, no charting library needed (use Card + text)
- If charting desired later, stretch goal

### 6.5 Transcripts page
- YouTube URL input (shadcn Input + Button)
- Transcript list table
- Transcript detail view (collapsible or modal)
- Status indicators for processing transcripts

### 6.6 Admin dashboard
- Uses `(admin)/layout.tsx` from Phase 2
- Stats overview: total users, total jobs, error count, system health
- Cards with key metrics
- Links to sub-pages

### 6.7 Admin error logs page
- Table with: timestamp, error type, message, job ID, user ID
- Filters: date range, error type, severity
- Pagination
- Click to expand error details

### 6.8 Admin jobs page
- Table with: job ID, user, topic, status, created, source count
- Filters: status, date range
- Actions: view, cancel, delete
- Pagination

### 6.9 Admin users page
- Table with: user ID, email, name, role, created, job count
- Actions: view, change role
- Pagination

### 6.10 Verify all pages
- Navigate to each page, verify rendering
- Check sidebar active state matches current route
- Verify auth redirect for protected pages
- Test admin pages with admin user

## Todo
- [ ] 6.1 Landing page
- [ ] 6.2 Login page
- [ ] 6.3 Settings page (6 sections)
- [ ] 6.4 Usage page
- [ ] 6.5 Transcripts page
- [ ] 6.6 Admin dashboard
- [ ] 6.7 Admin error logs
- [ ] 6.8 Admin jobs management
- [ ] 6.9 Admin users management
- [ ] 6.10 Integration verification

## Success Criteria
- All 8 pages render correctly in App Router
- Settings forms save and load data correctly
- Login flow works (Google OAuth + magic link)
- Admin pages show data tables with working filters
- Transcripts page accepts YouTube URLs and shows transcripts
- Sidebar highlights correct active route on each page
- `npm run build` passes

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Settings save regression | Medium | Medium | Test each section's save independently |
| Admin table performance with many rows | Low | Low | Pagination handles this |
| OAuth redirect loop | Low | High | Test login flow carefully, check redirect URLs |
| Style guide/voice profile CRUD bugs | Medium | Medium | Preserve store logic exactly |

## Security Considerations
- Admin pages must enforce role check (middleware in Phase 7)
- API keys section must never expose full key in DOM
- Login page must validate redirect URLs (prevent open redirect)
- Settings delete account requires double confirmation

## Next Steps
Phase 7: Wire up auth middleware, migrate shared page, polish animations, accessibility, remove old pages/.
