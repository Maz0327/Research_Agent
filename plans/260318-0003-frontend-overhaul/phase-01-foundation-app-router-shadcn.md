# Phase 1: Foundation — App Router Scaffold + shadcn/ui Setup

## Context
- Plan: [plan.md](plan.md)
- Current: Pages Router (`pages/_app.tsx`), class-based dark mode, custom UI components
- Target: App Router (`app/layout.tsx`), CSS variable theming, shadcn/ui primitives

## Overview
| Field | Value |
|-------|-------|
| Date | 2026-03-18 |
| Priority | P1 — blocks all subsequent phases |
| Status | complete |
| Effort | 5h |
| Description | Initialize App Router structure, install shadcn/ui, set up theming and providers |

## Key Insights
- `pages/` and `app/` CAN coexist but we chose big-bang; `pages/` stays untouched until Phase 7 cleanup
- shadcn/ui uses `components.json` to configure paths, CSS variables, and aliases
- next-themes replaces custom `contexts/ThemeContext.tsx` entirely
- Tailwind config must add `content: ["./app/**/*.{ts,tsx}"]` and switch from `darkMode: 'class'` to CSS variable approach
- Current `globals.css` hardcodes `#0a0a0a` background — will be replaced by CSS variables

## Requirements
1. `app/` directory with root layout, global CSS, error/not-found pages
2. shadcn/ui initialized with `components.json`
3. CSS variables for light/dark themes (shadcn/ui default palette)
4. next-themes `ThemeProvider` wrapping the app
5. AuthProvider and ErrorBoundary migrated to root layout
6. 17 shadcn/ui base components installed
7. Tailwind config updated for CSS variables + `app/` content paths
8. `next.config.js` preserved (rewrites, security headers, standalone output)

## Architecture

### Root Layout (`app/layout.tsx`)
```
<html lang="en" suppressHydrationWarning>
  <body className={inter.className}>
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
      <ErrorBoundary>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ErrorBoundary>
    </ThemeProvider>
  </body>
</html>
```

### CSS Variables (`app/globals.css`)
shadcn/ui default structure:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root { /* light theme variables */ }
  .dark { /* dark theme variables — primary palette */ }
}
```

Map current dark palette to CSS variables:
- `--background`: #121212 (was dark-bg-primary)
- `--card`: #1a1a1a (was dark-bg-secondary)
- `--muted`: #262626 (was dark-bg-tertiary)
- `--border`: #333333 (was dark-border-primary)
- `--foreground`: #f5f5f5 (was dark-text-primary)
- `--accent-blue`, `--accent-purple`, `--accent-green`: preserved from current palette

### components.json
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

## Related Code Files
| File | Action | Notes |
|------|--------|-------|
| `pages/_app.tsx` | Reference only | Provider structure to replicate in `app/layout.tsx` |
| `styles/globals.css` | Replace with `app/globals.css` | New CSS variable system |
| `tailwind.config.js` | Modify | Add app/ paths, CSS variable mode |
| `contexts/ThemeContext.tsx` | Superseded | Replaced by next-themes |
| `components/ErrorBoundary.tsx` | Move | Wrap in root layout |
| `components/AuthProvider.tsx` | Move | Wrap in root layout, add 'use client' |
| `tsconfig.json` | Modify | Add `@/` path alias if not present |
| `next.config.js` | Preserve | Rewrites + security headers unchanged |
| `package.json` | Modify | Add next-themes, @tanstack/react-query, shadcn deps (tailwindcss-animate, class-variance-authority, clsx, tailwind-merge, lucide-react) |

## Implementation Steps

### 1.1 Install dependencies
```bash
npm install next-themes class-variance-authority clsx tailwind-merge lucide-react tailwindcss-animate @tanstack/react-query
```

### 1.2 Initialize shadcn/ui
```bash
npx shadcn@latest init
```
- Select: New York style, Zinc base color, CSS variables = yes
- Creates: `components.json`, updates `tailwind.config.js`, creates `lib/utils.ts`

### 1.3 Update tsconfig.json
Add path aliases:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### 1.4 Create app/globals.css
- Copy shadcn/ui CSS variable template
- Map current dark palette colors to CSS variables
- Preserve accessibility styles (focus-visible, reduced-motion)
- Remove hardcoded `#0a0a0a` backgrounds

### 1.5 Create app/layout.tsx
- Import Inter font from `next/font/google`
- Add metadata export (title, description)
- Wrap with ThemeProvider (attribute="class", defaultTheme="dark")
- Wrap with QueryClientProvider (TanStack Query — create client in `lib/query-client.ts`)
- Wrap with ErrorBoundary (add 'use client' to ErrorBoundary)
- Wrap with AuthProvider (add 'use client' to AuthProvider)
- Keep env validation from `_app.tsx`

### 1.6 Create app/page.tsx
- Minimal landing page (redirect logic if authed)
- Server component that checks auth and redirects

### 1.7 Create app/not-found.tsx and app/error.tsx
- Basic error pages with shadcn/ui Card styling

### 1.8 Install shadcn/ui base components
```bash
npx shadcn@latest add button card badge tabs sheet collapsible accordion dialog input select separator scroll-area tooltip dropdown-menu avatar skeleton progress
```
These install to `components/ui/` — will coexist with existing custom UI components until Phase 2+

### 1.9 Update tailwind.config.js
- Add `"./app/**/*.{js,ts,jsx,tsx,mdx}"` to content array
- Add `tailwindcss-animate` plugin
- Preserve existing custom animations (shimmer, fade-in, slide-up, scale-in, gradient)
- Keep custom box-shadow definitions (glow-blue, glow-purple, glow-green)
- Merge shadcn/ui theme extensions with existing

### 1.10 Verify build
```bash
cd frontend && npm run build
```
Both `pages/` and `app/` should work during transition.

## Todo
- [x] 1.1 Install dependencies
- [x] 1.2 Initialize shadcn/ui (manual components.json + lib/utils.ts)
- [x] 1.3 Update tsconfig.json path aliases (already present)
- [x] 1.4 Create app/globals.css with CSS variables
- [x] 1.5 Create app/layout.tsx with providers (ThemeProvider + QueryClientProvider)
- [x] 1.6 Create app/page.tsx — SKIPPED (conflicts with pages/index.tsx; pages/index.tsx handles root)
- [x] 1.7 Create error + not-found pages
- [x] 1.8 Install 17 shadcn/ui components (progress added; 15 pre-existing + skeleton updated)
- [x] 1.9 Update tailwind.config.js (shadcn tokens + existing preserved)
- [x] 1.10 Verify build passes — PASS (0 errors, 16 pages/ routes + /_not-found app route)

## Implementation Notes
- app/page.tsx removed: conflicts with pages/index.tsx (Next.js enforces no dual ownership of `/`)
- AuthProvider excluded from app/providers.tsx: uses next/router (Pages Router only); App Router auth handled in Phase 3+ via server components
- ErrorBoundary excluded from app/providers.tsx: app/error.tsx serves this role in App Router
- skeleton.tsx extended with height/width props for backward compat with existing admin pages
- tailwind darkMode deduplication fixed (shadcn CLI added duplicate 'class' entry)

## Success Criteria
- `npm run build` passes with zero errors
- `app/layout.tsx` renders with dark theme by default
- shadcn/ui Button renders correctly in a test page
- CSS variables applied (inspect element shows `hsl(var(--background))`)
- No regressions in existing `pages/` routes (they still work)

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Tailwind config merge conflicts | Medium | Medium | Backup config before shadcn init, manual merge |
| CSS variable conflicts with existing classes | Low | Low | Existing classes remain, new components use vars |
| next-themes SSR flash | Low | Low | suppressHydrationWarning on html tag |
| Path alias conflicts | Low | High | Check tsconfig before adding @/ |

## Security Considerations
- `next.config.js` security headers preserved exactly
- No new external dependencies beyond shadcn/ui ecosystem (all are well-audited)
- `suppressHydrationWarning` only on `<html>` tag per next-themes docs

## Next Steps
Phase 2: Build sidebar navigation and 3-column layout system using the shadcn/ui components installed here.
