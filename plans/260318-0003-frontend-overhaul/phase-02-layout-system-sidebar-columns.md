# Phase 2: Layout System — Sidebar Navigation + 3-Column Job Detail

## Context
- Plan: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-foundation-app-router-shadcn.md) (shadcn/ui components available)
- Current: `components/Layout.tsx` (simple wrapper), no sidebar, single-column pages
- Target: Fixed sidebar nav, 3-column job detail layout, pipeline status header

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 |
| Status | complete |
| Effort | 5h |
| Description | Build responsive app shell with sidebar, 3-column layout, pipeline header, circular gauges |

## Key Insights
- AI CMO inspiration: left context + center analytics + right feed — maps to job meta + documents + activity
- Sidebar should show: logo, nav links (Dashboard, Queue, Transcripts, Usage, Settings), admin section, user avatar
- Mobile: sidebar collapses to Sheet drawer (hamburger trigger), right panel becomes bottom Sheet
- Pipeline status header is a terminal-style bar showing current stage name, ETA, progress percentage
- Circular gauges use SVG with `stroke-dasharray` trick (radius 16, circumference ~100.5)

## Requirements
1. App shell layout for `(app)` route group with sidebar + main content area
2. Responsive sidebar: fixed 240px desktop, Sheet drawer on mobile (<768px)
3. 3-column layout component for job detail page (reusable)
4. Pipeline status header bar component
5. Circular gauge SVG component (confidence, quality, completion)
6. Mobile breakpoints: sidebar drawer, single column, bottom sheet for right panel
7. Admin shell layout for `(admin)` route group

## Architecture

### Route Group Layouts
```
app/
├── (app)/
│   └── layout.tsx          # Sidebar + main content area
├── (admin)/
│   └── layout.tsx          # Admin sidebar variant
├── login/page.tsx          # No shell (standalone)
└── shared/[token]/page.tsx # No shell (public)
```

### App Shell Layout (`(app)/layout.tsx`)
```
┌──────────────────────────────────────────────┐
│ ┌─────────┐ ┌──────────────────────────────┐ │
│ │ Sidebar  │ │     Main Content Area        │ │
│ │          │ │                              │ │
│ │ Logo     │ │  (children — page content)   │ │
│ │ ──────── │ │                              │ │
│ │ Dashboard│ │                              │ │
│ │ Queue    │ │                              │ │
│ │ Trans... │ │                              │ │
│ │ Usage    │ │                              │ │
│ │ Settings │ │                              │ │
│ │ ──────── │ │                              │ │
│ │ Admin    │ │                              │ │
│ │ ──────── │ │                              │ │
│ │ Avatar   │ │                              │ │
│ └─────────┘ └──────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### 3-Column Job Detail Layout (used in Phase 4)
```
┌──────────────────────────────────────────────────┐
│ Pipeline Status Header (terminal bar)            │
├────────────┬───────────────────┬─────────────────┤
│ Left Panel │  Center Content   │  Right Panel    │
│ (280px)    │  (flex-1)         │  (320px)        │
│            │                   │                 │
│ Job Meta   │  Document Tabs    │  Activity Log   │
│ Source Nav │  Active Document  │  [Chat Button]  │
│ Doc Nav    │  (Accordion)      │                 │
│            │                   │  Sheet overlay  │
│            │                   │  for iterate/   │
│            │                   │  brainstorm     │
├────────────┴───────────────────┴─────────────────┤
│ Mobile: single column, panels as Sheet drawers   │
└──────────────────────────────────────────────────┘
```

### Component Hierarchy
```
components/layout/
├── AppShell.tsx           # Sidebar + main area wrapper
├── Sidebar.tsx            # Navigation sidebar (desktop)
├── SidebarMobile.tsx      # Sheet-based sidebar (mobile)
├── SidebarNav.tsx         # Nav link list (shared)
├── ThreeColumnLayout.tsx  # Left + center + right panels
├── PipelineStatusBar.tsx  # Terminal-style header
├── UserMenu.tsx           # Avatar + dropdown
└── AdminShell.tsx         # Admin layout variant

components/pipeline/
├── CircularGauge.tsx      # SVG circular progress
├── StageProgress.tsx      # Pipeline stage indicator
└── ETADisplay.tsx         # Time remaining display
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `components/Layout.tsx` | Superseded | Replaced by AppShell |
| `components/MobileBottomNav.tsx` | Superseded | Replaced by SidebarMobile |
| `components/ui/StageIndicator.tsx` | Reference | Existing stage logic to preserve |
| `components/ui/ProgressRing.tsx` | Reference | Existing SVG ring, evaluate reuse vs CircularGauge |
| `lib/constants.ts` | Reference | Stage labels (40+), pipeline stage names |

## Implementation Steps

### 2.1 Create `components/layout/SidebarNav.tsx`
- Nav items array: Dashboard, Queue, Transcripts, Usage, Settings
- Admin section (conditionally shown based on user role)
- Active link highlight using `usePathname()`
- Icons from lucide-react (LayoutDashboard, ListTodo, Video, BarChart3, Settings, Shield)
- `'use client'` — uses pathname hook

### 2.2 Create `components/layout/Sidebar.tsx`
- Desktop: fixed left, w-60, border-right, dark card background
- Logo at top, nav in middle, user menu at bottom
- Separator between sections
- ScrollArea for overflow

### 2.3 Create `components/layout/SidebarMobile.tsx`
- Uses shadcn/ui Sheet (side="left")
- Triggered by hamburger Button in mobile header
- Same SidebarNav content
- Closes on navigation (listen to pathname changes)

### 2.4 Create `components/layout/UserMenu.tsx`
- Avatar with user initials or image
- DropdownMenu: Profile, Theme toggle, Logout
- `'use client'` — uses auth state and signOut

### 2.5 Create `components/layout/AppShell.tsx`
- Combines Sidebar (desktop) + SidebarMobile (mobile) + main content
- Responsive: `flex` container, sidebar hidden below md breakpoint
- Mobile: top header bar with hamburger + logo + user avatar
- Main content: `flex-1 overflow-auto`

### 2.6 Create `app/(app)/layout.tsx`
- Import AppShell, wrap children
- This is a client component (needs auth check for sidebar user menu)

### 2.7 Create `components/layout/ThreeColumnLayout.tsx`
- Props: `leftPanel`, `centerContent`, `rightPanel`, `statusBar`
- Desktop: CSS grid `grid-cols-[280px_1fr_320px]`
- Tablet (< 1024px): hide right panel, show as Sheet
- Mobile (< 768px): single column, left panel as collapsible, right as bottom Sheet
- Center column gets ScrollArea

### 2.8 Create `components/layout/PipelineStatusBar.tsx`
- Terminal-style: dark bg, monospace font, border-bottom
- Shows: stage icon, stage name, progress %, ETA
- Pulsing dot animation for active stages
- Uses stage labels from `lib/constants.ts`
- Variants: running (animated), completed (green), failed (red), queued (gray)

### 2.9 Create `components/pipeline/CircularGauge.tsx`
- SVG component, radius 16, viewBox="0 0 36 36"
- Props: `value` (0-100), `label`, `size` (sm/md/lg), `color` (from theme)
- stroke-dasharray = `${value} ${100 - value}`
- Center text shows value or label
- Animated on mount (Framer Motion)

### 2.10 Create `components/pipeline/StageProgress.tsx`
- Horizontal stepper showing pipeline stages
- Completed/active/pending states
- Maps to: INGESTION > EXTRACTION > VALIDATION > SYNTHESIS > ASSEMBLY
- Compact variant for sidebar/header use

### 2.11 Create `app/(admin)/layout.tsx`
- Admin variant of AppShell
- Different sidebar nav: Dashboard, Errors, Jobs, Users
- Admin role check (redirect if not admin)

### 2.12 Responsive testing + polish
- Test at 375px (mobile), 768px (tablet), 1280px (desktop)
- Verify sidebar collapse/expand
- Verify Sheet transitions
- Check focus management for keyboard nav

## Todo
- [x] 2.1 SidebarNav component
- [x] 2.2 Sidebar desktop component
- [x] 2.3 SidebarMobile Sheet component
- [x] 2.4 UserMenu dropdown
- [x] 2.5 AppShell wrapper
- [x] 2.6 (app) route group layout
- [x] 2.7 ThreeColumnLayout component
- [x] 2.8 PipelineStatusBar component
- [x] 2.9 CircularGauge SVG component
- [x] 2.10 StageProgress component
- [x] 2.11 (admin) route group layout
- [ ] 2.12 Responsive testing (manual, browser)

## Success Criteria
- Sidebar renders on desktop, Sheet on mobile
- Navigation links highlight correctly on active route
- ThreeColumnLayout renders 3 columns on desktop, collapses on mobile
- PipelineStatusBar shows stage + progress + ETA
- CircularGauge renders with correct value and animation
- `npm run build` passes
- No layout shifts on resize

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Layout shift on hydration | Medium | Medium | Use fixed widths, avoid dynamic layout calc on server |
| Mobile Sheet z-index conflicts | Low | Low | shadcn/ui handles z-index via portal |
| Sidebar state persistence | Low | Medium | Use Zustand ui-preferences store for collapsed state |
| Admin role check timing | Medium | Medium | Use middleware.ts (Phase 7), layout shows skeleton until auth resolves |

## Security Considerations
- Admin layout must validate role server-side (middleware), not just hide UI
- UserMenu logout must clear all tokens (Supabase signOut)
- Navigation links should not expose admin routes to non-admin users

## Next Steps
Phase 3: Migrate Dashboard and Queue pages into the AppShell layout, wire up job creation and Zustand stores.
