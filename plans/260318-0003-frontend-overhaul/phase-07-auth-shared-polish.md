# Phase 7: Auth, Shared Page, Polish + Cleanup

## Context
- Plan: [plan.md](plan.md)
- Depends on: All previous phases (1-6)
- Current: Auth via `components/AuthProvider.tsx`, shared via `pages/shared/[token].tsx`, `pages/` directory still present

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 |
| Status | pending |
| Effort | 5h |
| Description | Complete auth middleware, migrate shared page, polish, accessibility, remove pages/ |

## Key Insights
- Auth middleware in Next.js App Router uses `middleware.ts` at project root
- Supabase auth checked server-side via `@supabase/ssr` (newer official package, replaces auth-helpers)
- Shared page (`/shared/[token]`) is PUBLIC — no auth, no sidebar, minimal layout
- Framer Motion page transitions work in App Router via `<AnimatePresence>` in layout
- Accessibility: focus management on route change, ARIA labels on interactive elements
- Cleanup: delete entire `pages/` directory, old `styles/globals.css`, old `contexts/ThemeContext.tsx`

## Requirements
1. Auth middleware protecting `(app)` and `(admin)` route groups
2. Admin role check in `(admin)` middleware
3. Public shared page migration
4. Framer Motion page transitions
5. WCAG 2.1 AA accessibility pass
6. Performance: code splitting, lazy loading heavy components
7. Remove old `pages/` directory and dead code
8. Update tests for new component locations

## Architecture

### Auth Flow
```
middleware.ts
  ├── /login, /shared/* → pass through (public)
  ├── /(app)/* → check Supabase session cookie
  │   ├── valid → continue
  │   └── invalid → redirect to /login
  └── /(admin)/* → check session + admin role
      ├── admin → continue
      └── not admin → redirect to /dashboard
```

### Shared Page
```
app/shared/[token]/
├── page.tsx           # Server: validate token, fetch job
└── SharedJobView.tsx  # Client: read-only document viewer (no iterate, no edit)
```

### Files to Delete (Cleanup)
```
DELETE:
├── pages/                     # Entire directory
├── styles/globals.css         # Replaced by app/globals.css
├── contexts/ThemeContext.tsx   # Replaced by next-themes
├── components/Layout.tsx      # Replaced by AppShell
├── components/MobileBottomNav.tsx  # Replaced by SidebarMobile
├── components/AdminLayout.tsx # Replaced by (admin)/layout.tsx
├── components/PublicHeader.tsx # Replaced by shared page layout

KEEP (adapt for new design system):
├── components/ui/GlowCard.tsx        # Keep — adapt for special emphasis cards

ARCHIVE (move to frontend/archive/):
├── components/ui/GradientText.tsx     # Replaced by shadcn styling
├── components/ui/FloatingActionButton.tsx  # Replaced by ChatToggle
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `pages/*` | Delete all | Replaced by app/ |
| `styles/globals.css` | Delete | Replaced by app/globals.css |
| `contexts/ThemeContext.tsx` | Delete | Replaced by next-themes |
| `components/Layout.tsx` | Delete | Replaced by AppShell |
| `components/AdminLayout.tsx` | Delete | Replaced by (admin)/layout.tsx |
| `components/MobileBottomNav.tsx` | Delete | Replaced by SidebarMobile |
| `components/PublicHeader.tsx` | Delete | Replaced by shared layout |
| `components/AuthProvider.tsx` | Modify | Ensure 'use client', works with root layout |
| `pages/shared/[token].tsx` | Reference → app/shared/[token]/ | Public page |
| `__tests__/*` | Update | Fix imports for new paths |

## Implementation Steps

### 7.1 Create middleware.ts
```typescript
import { createServerClient } from '@supabase/ssr';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { getAll: () => req.cookies.getAll(), setAll: (cookies) => cookies.forEach(({ name, value, options }) => res.cookies.set(name, value, options)) } }
  );
  const { data: { session } } = await supabase.auth.getSession();

  // Public routes: pass through
  if (req.nextUrl.pathname.startsWith('/login') ||
      req.nextUrl.pathname.startsWith('/shared')) {
    return res;
  }

  // No session: redirect to login
  if (!session) {
    return NextResponse.redirect(new URL('/login', req.url));
  }

  // Admin routes: check role
  if (req.nextUrl.pathname.startsWith('/admin')) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', session.user.id)
      .single();

    if (profile?.role !== 'admin') {
      return NextResponse.redirect(new URL('/dashboard', req.url));
    }
  }

  return res;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
```

### 7.2 Install @supabase/ssr
```bash
npm install @supabase/ssr
```

### 7.3 Migrate shared page
- `app/shared/[token]/page.tsx`: server component, extract token
- Fetch job data via public API endpoint (no auth required)
- Render `SharedJobView` — read-only DocumentViewer
- No sidebar, no iterate/brainstorm, no edit, no export (or limited export)
- Minimal layout: header with "Shared Research" branding + document content
- Handle invalid/expired tokens with friendly error

### 7.4 Add Framer Motion page transitions
- In `app/(app)/layout.tsx`, wrap children with AnimatePresence
- Page components export motion variants:
  ```tsx
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
    {children}
  </motion.div>
  ```
- Keep transitions subtle (opacity + slight Y translate, 200ms)
- Respect `prefers-reduced-motion`

### 7.5 Accessibility audit
- **Focus management**: auto-focus main content on route change
- **Skip link**: preserved from `components/SkipLink.tsx`
- **ARIA labels**: all interactive elements (buttons, links, inputs)
- **Keyboard navigation**: Tab order logical, Escape closes Sheet/Dialog
- **Color contrast**: CSS variables already WCAG compliant (from current palette)
- **Screen reader**: Accordion states announced, Badge content readable
- **Reduced motion**: Framer Motion respects media query, animate-pulse disabled
- Run automated check: `npx axe-cli http://localhost:3000/dashboard`

### 7.6 Performance optimization
- **Code splitting**: dynamic import for heavy renderers
  ```tsx
  const CreatorBriefRenderer = dynamic(() => import('./CreatorBriefRenderer'), {
    loading: () => <Skeleton className="h-96" />
  });
  ```
- **Lazy load**: document renderers loaded on tab switch, not all upfront
- **Image optimization**: next/image for any images
- **Bundle analysis**: `npm run build` check page sizes
- Target: First Load JS < 200kB per route

### 7.7 Remove old pages/ directory
- Delete `pages/` entirely
- Delete `styles/globals.css`
- Delete `contexts/ThemeContext.tsx`
- Delete `components/Layout.tsx`, `AdminLayout.tsx`, `MobileBottomNav.tsx`, `PublicHeader.tsx`
- Archive unused UI components to `frontend/archive/`
- Update `tailwind.config.js` content paths: remove `"./pages/**/*"`

### 7.8 Update tests
- Fix import paths in `__tests__/`
- Update component references
- Add smoke tests for new pages:
  - Dashboard renders
  - Queue renders
  - Job detail renders with mock data
  - Settings renders
  - Login renders
- Run full test suite: `npm test`

### 7.9 Update package.json scripts
- Ensure `dev`, `build`, `start`, `lint` all work
- Add `"test:e2e"` script placeholder for future Playwright tests

### 7.10 Final verification
- `npm run lint` — zero errors
- `npm run build` — zero errors
- `npm test` — all pass
- Manual smoke test: full user journey (login > dashboard > create job > view job > iterate > export > settings > logout)
- Mobile responsive check at 375px, 768px, 1280px

## Todo
- [ ] 7.1 Create middleware.ts with auth checks
- [ ] 7.2 Install Supabase auth helpers
- [ ] 7.3 Migrate shared page
- [ ] 7.4 Framer Motion page transitions
- [ ] 7.5 Accessibility audit + fixes
- [ ] 7.6 Performance optimization (code splitting, lazy loading)
- [ ] 7.7 Remove pages/ directory and dead code
- [ ] 7.8 Update tests
- [ ] 7.9 Update package.json scripts
- [ ] 7.10 Final verification (lint, build, test, smoke test)

## Success Criteria
- Unauthenticated users redirected to /login
- Admin routes protected by role check
- Shared page renders publicly without auth
- Page transitions animate smoothly
- axe accessibility check: zero critical/serious violations
- `npm run lint` — zero errors
- `npm run build` — zero errors, bundle size < 200kB first load per route
- `npm test` — all tests pass
- No files remaining in `pages/` directory
- Full user journey works end-to-end

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auth middleware breaks all routes | High | Critical | Test with real Supabase session first, fallback to pass-through |
| Deleting pages/ breaks build | Medium | Critical | Verify app/ routes cover 100% before deletion |
| Test failures from import changes | High | Medium | Fix imports systematically, run tests after each file move |
| Bundle size regression | Medium | Medium | Run bundle analyzer, dynamic import heavy components |
| Framer Motion SSR issues | Low | Low | Use 'use client' on animated components |

## Security Considerations
- Middleware MUST check auth server-side (not just client-side)
- Admin role check must query database, not trust client-provided role
- Shared page token validation must be server-side
- Remove any hardcoded tokens or credentials during cleanup
- Ensure CSP headers still work with new route structure

## Resolved Questions
1. ~~Auth package~~ → Using `@supabase/ssr` (validated decision)
2. Shared page export → TBD (minor, decide during implementation)
3. ~~E2E tests~~ → Deferred to separate effort (validated decision)
