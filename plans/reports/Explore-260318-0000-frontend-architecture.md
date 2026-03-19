# Frontend Architecture Exploration Report

**Date:** 2026-03-18  
**Scope:** Full frontend directory structure, framework, UI patterns, and component organization  
**Status:** Complete

---

## 1. FRAMEWORK & STACK

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js (Pages Router) | ^14.2.0 |
| React | React | ^18.3.1 |
| Styling | Tailwind CSS | ^3.4.19 |
| State Management | Zustand | ^4.5.0 |
| Authentication | Supabase | ^2.45.0 |
| Animation | Framer Motion | ^10.18.0 |
| Markdown | react-markdown + rehype plugins | ^10.1.0 |
| Export | docx, html2pdf.js | ^9.6.1, ^0.10.1 |
| Testing | Jest + React Testing Library | ^30.2.0, ^16.3.1 |

### Key Decisions:
- **Pages Router** (not App Router) - maintains traditional page-based structure
- **No component library** - custom Tailwind components only (no MUI, shadcn, etc.)
- **Zustand for state** - lightweight, no Redux complexity
- **Supabase for auth** - PostgreSQL + JWT-based authentication

---

## 2. OVERALL LAYOUT PATTERN

### Page Structure: Sidebar + Main Content

```
┌─────────────────────────────────────────┐
│          Mobile Header (lg:hidden)      │  56px height
├─────────────────────────────────────────┤
│ Sidebar │                               │
│ fixed   │     Main Content Area         │
│ left    │     (flex-1, overflow-y-auto) │
│ w-64    │                               │
│ (or     │                               │
│  w-16)  │                               │
├─────────────────────────────────────────┤
│   Mobile Bottom Nav (lg:hidden)         │  80px height
└─────────────────────────────────────────┘
```

**Layout Component:** `/components/Layout.tsx`
- **Responsive:** Mobile-first with hamburger menu
- **Sidebar states:**
  - Desktop: `w-64` (expanded, default) or `w-16` (collapsed)
  - Mobile: Fixed overlay with `-translate-x-full` / `translate-x-0`
- **Main margin:** Dynamic `lg:ml-64` or `lg:ml-16` based on sidebar collapse
- **Dark theme:** Background `#121212`, borders `#333333`

**Mobile Navigation:** Bottom nav + mobile header
- Top header: Logo + hamburger button (height: 56px)
- Bottom nav: Sticky navigation (height: 80px, `pb-20 lg:pb-0`)
- Overlay: `bg-black/50` when mobile sidebar open

---

## 3. COLOR SCHEME (Tailwind Dark Mode)

**Dark Mode Only** (class-based, not OS preference)

```javascript
// Primary Backgrounds
dark-bg-primary:    #121212  // Main background
dark-bg-secondary:  #1a1a1a  // Cards
dark-bg-tertiary:   #262626  // Elevated surfaces
dark-bg-hover:      #2d2d2d  // Hover states

// Borders
dark-border-primary:    #333333  // Default
dark-border-secondary:  #404040  // Hover
dark-border-accent:     #4a5568  // Active

// Text
dark-text-primary:    #f5f5f5  // Main text (15.4:1 contrast)
dark-text-secondary:  #d1d5db  // Secondary (10.5:1)
dark-text-muted:      #9ca3af  // Muted (7.5:1)
dark-text-disabled:   #6b7280  // Disabled (4.6:1)

// Accents
accent-blue:      #3b82f6
accent-blue-light: #60a5fa
accent-blue-dark:  #2563eb
accent-purple:    #8b5cf6
accent-green:     #22c55e
```

**WCAG 2.1 AA Compliant** - all text meets contrast ratios
**Animations:** shimmer, fade-in, slide-up, scale-in, gradient pulse

---

## 4. PAGE STRUCTURE (Pages Router)

```
/pages
├── _app.tsx                    # Root component (ErrorBoundary + AuthProvider)
├── index.tsx                   # Landing page (redirects to dashboard if authenticated)
├── login.tsx                   # Login page
├── dashboard.tsx               # Main dashboard (job creation + job grid)
├── queue.tsx                   # "My Jobs" - job queue/list view
├── transcripts.tsx             # Transcripts management page
├── usage.tsx                   # Usage stats/analytics
├── settings.tsx                # User settings & configuration
├── jobs
│   └── [id].tsx               # Job detail page (individual research job)
├── shared
│   └── [token].tsx            # Shared research document (public link)
└── admin
    ├── index.tsx              # Admin dashboard
    ├── errors.tsx             # Error logs
    ├── jobs.tsx               # Admin job management
    └── users.tsx              # User management
```

**Protected Routes:**
- Dashboard, queue, transcripts, usage, settings → `<ProtectedRoute>`
- Admin pages → `<AdminProtectedRoute>`
- Login, index, shared → Public

---

## 5. COMPONENT ORGANIZATION

### Top-Level Components (Root Layout)
```
/components
├── Layout.tsx                  # Main sidebar + content layout
├── AdminLayout.tsx             # Admin-specific layout variant
├── AuthProvider.tsx            # Auth context + hooks + HOCs
├── ErrorBoundary.tsx           # Error boundary wrapper
├── PublicHeader.tsx            # Landing page header
├── SkipLink.tsx                # A11y skip link
├── MobileBottomNav.tsx         # Mobile bottom navigation
├── JobCard.tsx                 # Reusable job card component
└── ThemeToggle.tsx             # Dark/light mode toggle
```

### Feature Component Folders

| Folder | Purpose | Key Files |
|--------|---------|-----------|
| `ui/` | Base UI components | AnimatedButton, GlowCard, ProgressRing, Spinner, Skeleton, StageIndicator |
| `common/` | Shared utilities | ClaimIndicators, CopyButton, DocumentHeader, MarkdownRenderer |
| `dashboard/` | Dashboard page components | DashboardJobCard, JobTable, StartInput, ViewToggle |
| `job-card/` | Job results card components (18 files) | DocumentAccordion, DocumentCard, QuoteList, GapAnalysisView, ResearchStarterView, ExportButton, ShareButton, etc. |
| `job-detail/` | Job detail page components | JobDetailHeader, ArtifactCardGrid, JobProgressPanel, DocumentAccordion, ReadingGuide |
| `document/` | Document renderers | CreatorBriefRenderer, SemanticBriefRenderer, JumpStartRenderer, SourceLedgerRenderer, ExportToolbar, SocialKitRenderer, ScriptRenderer, BlogPostRenderer |
| `unified-input/` | Unified research input system | Research mode selector, source collection interface |
| `search/` | Search & source discovery | SearchApprovalView - manual source curation |
| `iterate/` | Iteration/refinement UI | IterateDialog, RefinePanel - re-analysis controls |
| `brainstorm/` | Research angle exploration | BrainstormPanel, AngleCard - gap analysis & search directions |
| `claim-extractor/` | Claim extraction tool | ClaimExtractorView - standalone claims analysis |
| `creator-analysis/` | Creator style profile | CreatorAnalysisInput, CreatorStyleProfileRenderer - voice mimicry analysis |
| `creator-brief/` | Creator brief document | CreatorBriefView - doc display |
| `document-drawer/` | Document drawer/modal | Side panel document view |
| `settings/` | Settings page components | AccountSection, PipelineSection, NotificationsSection, DisplaySection, StyleGuideSection, PipelineSection |

---

## 6. STATE MANAGEMENT (Zustand Stores)

Located in `/store/` directory

### Store Architecture
```
/store
├── jobs.ts                     # Job data, job lifecycle, artifacts
├── settings.ts                 # User settings, preferences, API keys
├── admin.ts                    # Admin operations (users, errors, jobs)
├── style-guides.ts             # Saved style guides (creator analysis)
├── voice-profiles.ts           # Voice profile data (creator mimicry)
└── ui-preferences.ts           # UI preferences (theme, layout)
```

**jobs.ts** (Largest, ~59KB)
- `useJobsStore` - Zustand store
- Types: `Job`, `JobArtifacts`, `Clip`, `Quote`, `JobPreview`, `Interpretation`
- Methods: `setJobs()`, `addJob()`, `updateJob()`, `fetchJob()`, `clearJobs()`
- Data: Job lifecycle, artifacts (docs, clips, quotes), producer packet results

**No Redux** - Zustand provides lightweight state without complexity

---

## 7. KEY PAGES IN DETAIL

### Dashboard (pages/dashboard.tsx)
- **Purpose:** Main hub for research job creation + job list
- **Components:**
  - `UnifiedInputPanel` - Research request entry (5 modes)
  - `SearchApprovalView` - Manual source curation
  - `BrainstormPanel` - Gap analysis & angle suggestions
  - `DashboardJobCard` - Job preview cards
  - `FloatingActionButton` - Quick actions
- **States:** 6 job modes (none, topic, research, claims, transcripts, creator_analysis)
- **Features:** Job preview, form validation, category selection, source type filtering

### Job Detail (pages/jobs/[id].tsx)
- **Purpose:** Full view of a single research job
- **Components:**
  - `JobDetailHeader` - Title, status, metadata
  - `ArtifactCardGrid` - Doc cards (Doc 0-3, iterations)
  - `JobProgressPanel` - Stage tracking
  - `CreatorBriefView` - Hero document display
  - `RefinePanel` - Iteration controls
  - `DocumentAccordion` - Expandable doc sections
- **Behavior:** Real-time polling for job completion, document versioning

### Settings (pages/settings.tsx)
- **Purpose:** User configuration & preferences
- **Sections:**
  - AccountSection - Email, auth settings
  - PipelineSection - API keys, model selection
  - NotificationsSection - Email alerts
  - DisplaySection - UI theme, preferences
  - StyleGuideSection - Saved style templates

---

## 8. AUTHENTICATION & AUTHORIZATION

**Provider:** `/components/AuthProvider.tsx`
- **Context:** `AuthContext` provides `{user, session, loading, isAdmin, signOut()}`
- **Backend:** Supabase (PostgreSQL + JWT)
- **Dev Bypass:** `NEXT_PUBLIC_DISABLE_AUTH=true` for local development
- **Admin Check:** `GET /admin/check` endpoint validates admin status

**Protected Routes:**
```javascript
export function ProtectedRoute({ children }) { /* redirects to /login */ }
export function AdminProtectedRoute({ children }) { /* redirects to /dashboard */ }
```

**Global Auth Checks:**
- `_app.tsx` validates `NEXT_PUBLIC_API_URL` in production
- Routes automatically redirect on auth state change

---

## 9. STYLING APPROACH

**Tailwind CSS only** - no component library

### Theme System
- `tailwind.config.js` extends theme with custom colors & animations
- **Dark mode:** `darkMode: 'class'` (manual toggle, not OS preference)
- **Custom animations:** shimmer, fade-in, slide-up, scale-in, gradient pulse
- **Shadow effects:** glow-blue, glow-purple, glow-green

### Global Styles (`styles/globals.css`)
- Tailwind directives (base, components, utilities)
- Focus-visible states (blue outline, 2px)
- Reduced motion support (@media prefers-reduced-motion)
- Mobile optimizations:
  - Safe area insets for notched devices
  - Scrollbar hiding (`.scrollbar-hide`)
  - iOS smooth scrolling
  - Tap highlight colors
  - 16px font size on inputs (prevents iOS zoom)

### Class Utilities
- Custom tree-list styling for branch graphics
- `.nav-item` - navigation link states
- `.safe-area-inset-*` - notch support
- `.scrollbar-hide` - hide scrollbars

---

## 10. RESPONSIVE DESIGN

**Mobile-First Breakpoints** (Tailwind defaults)
```
sm: 640px
md: 768px
lg: 1024px
xl: 1280px
2xl: 1536px
```

**Key Responsive Behaviors:**
- **Sidebar:** Hidden on mobile, shown in overlay with hamburger
- **Mobile header:** 56px fixed top (`lg:hidden`)
- **Mobile bottom nav:** 80px fixed bottom (`lg:hidden`)
- **Main content:** `pt-14 lg:pt-0` (adjust for fixed headers)
- **Grid layouts:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- **Padding:** `p-4 sm:p-6 lg:p-8`

**Viewport Settings:**
```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
```

---

## 11. ACCESSIBILITY FEATURES

**WCAG 2.1 AA Compliant**
- ✓ Focus-visible states (blue outline)
- ✓ Semantic landmarks (`<main role="main">`, `<nav aria-label>`)
- ✓ Skip link (`SkipLink.tsx`) to main content
- ✓ Contrast ratios ≥ 4.5:1 for text
- ✓ Reduced motion support
- ✓ ARIA labels on interactive elements
- ✓ Proper heading hierarchy (h1, h2, h3)
- ✓ Error boundary for error recovery

**Components:**
- `SkipLink` - Skip to main content link
- `ErrorBoundary` - Graceful error handling
- Semantic HTML (nav, main, section, article, aside)
- Image alt text (inline SVGs with aria-hidden)

---

## 12. LIBRARY CHOICES RATIONALE

| Choice | Alternative | Why Selected |
|--------|-----------|---------|
| Zustand | Redux, Context API | Lightweight, minimal boilerplate, good for medium state |
| Tailwind | MUI, styled-components | Utility-first → consistent spacing/colors, smaller bundle |
| Framer Motion | React Spring, Animate.css | Declarative, great for page transitions, good DX |
| Supabase | Firebase, Auth0 | Open source, PostgreSQL, strong developer experience |
| Custom UI | shadcn, MUI | Full control, Tailwind-native, no dependency lock-in |

---

## 13. DIRECTORY STRUCTURE SUMMARY

```
frontend/
├── pages/                  # Next.js pages (routing)
│   ├── _app.tsx           # App root with providers
│   ├── index.tsx          # Landing
│   ├── dashboard.tsx      # Main hub
│   ├── jobs/[id].tsx      # Job detail
│   ├── queue.tsx          # Job list
│   ├── transcripts.tsx    # Transcripts page
│   ├── usage.tsx          # Usage analytics
│   ├── settings.tsx       # User settings
│   ├── login.tsx          # Auth
│   ├── shared/[token].tsx # Public share link
│   └── admin/             # Admin pages
├── components/            # React components (organized by feature)
│   ├── Layout.tsx         # Main layout wrapper
│   ├── AuthProvider.tsx   # Auth context
│   ├── ui/                # Base UI components
│   ├── common/            # Shared utilities
│   ├── dashboard/         # Dashboard-specific
│   ├── job-card/          # Job result cards
│   ├── job-detail/        # Detail page components
│   ├── document/          # Document renderers
│   ├── settings/          # Settings sections
│   └── [other features]/  # Feature-specific folders
├── store/                 # Zustand stores
│   ├── jobs.ts           # Job state
│   ├── settings.ts       # Settings
│   ├── admin.ts          # Admin state
│   └── [other stores]/   # Feature stores
├── lib/                   # Utility functions
│   ├── api-client.ts     # API wrapper
│   ├── constants.ts      # App constants
│   ├── document-formatters.ts
│   ├── docx-export.ts    # Word export
│   ├── intent-router.ts  # Input intent detection
│   └── [other utils]/
├── types/                 # TypeScript types
│   ├── documents.ts
│   ├── run.ts
│   └── [other types]/
├── styles/               # Global styles
│   └── globals.css       # Tailwind + custom CSS
├── contexts/             # React contexts
│   └── ThemeContext.tsx  # Theme management
├── hooks/                # Custom hooks
│   └── useETA.ts        # ETA calculation
└── __tests__/            # Jest tests
```

---

## 14. CURRENT ARCHITECTURE PATTERNS

### Component Patterns
1. **Layout wrapper pattern:** `<Layout>` wraps all authenticated pages
2. **Feature folders:** Self-contained feature components (job-card, document, etc.)
3. **Store integration:** Zustand hooks used directly in components (`useJobsStore()`)
4. **Responsive containers:** Mobile-first grid layouts with Tailwind utilities
5. **Framer animations:** Page transitions, accordion animations, modal reveals

### Data Flow
```
Supabase Auth ──→ AuthProvider ──→ useAuth() hook
                     ↓
              ProtectedRoute HOC
                     ↓
         Page component ──→ useJobsStore() ──→ API calls
                     ↓
         Child components receive props from store/API
```

### Page Lifecycle
1. Auth check (redirect if not authenticated)
2. Fetch initial data from API
3. Poll for updates (jobs in progress)
4. Render page with data
5. Handle user actions (create job, export, etc.)

---

## 15. KEY OBSERVATIONS

### Strengths
- ✓ Clean separation of concerns (pages, components, stores, utils)
- ✓ WCAG 2.1 AA compliance built-in
- ✓ Mobile-first responsive design
- ✓ No component library lock-in (full Tailwind flexibility)
- ✓ Lightweight state management (Zustand)
- ✓ Feature-folder organization scales well

### Current State
- ✓ Production-ready dark mode implementation
- ✓ Full authentication with admin checks
- ✓ 14 pages covering all user workflows
- ✓ 27 component folders with organized features
- ✓ Comprehensive export capabilities (DOCX, PDF)
- ✓ Document versioning support
- ✓ Real-time job polling

### Considerations for Extension
- Large pages (dashboard.tsx: 42KB, job-detail: 15KB) could benefit from component extraction
- Document renderers folder is large (12 files) - could be organized further
- Type definitions spread across `/types/` - could consolidate related types
- Store files getting large (jobs.ts: 59KB) - could split by feature area

---

## 16. UNRESOLVED QUESTIONS

1. **Build Performance:** Current bundle size for production build?
2. **Component Library:** Any plans to migrate from custom Tailwind to shadcn/ui?
3. **State Persistence:** Are stores persisted to localStorage for offline access?
4. **Testing Coverage:** Current test coverage percentage across components?
5. **API Integration:** How many API endpoints do frontend components call?
6. **Mobile Native:** Any plans for React Native or mobile app version?
7. **Document Syncing:** How are document iterations versioned - in DB or file storage?

