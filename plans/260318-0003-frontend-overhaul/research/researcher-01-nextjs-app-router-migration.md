# Next.js App Router Migration & shadcn/ui Integration Research

**Date:** 2026-03-18
**Focus:** Pages Router → App Router (v14), shadcn/ui setup, Zustand integration, dashboard patterns

---

## 1. Migration Strategy: Pages → App Router

### File Structure Mapping
| Pages Router | App Router | Notes |
|---|---|---|
| `pages/_app.tsx` | `app/layout.tsx` (root) | Combines _app + _document |
| `pages/_document.tsx` | `app/layout.tsx` | HTML structure via root layout |
| `pages/dashboard/[id].tsx` | `app/dashboard/[id]/page.tsx` | Routes become directories |
| `pages/api/users.ts` | `app/api/users/route.ts` | API Routes → Route Handlers |
| `pages/404.js` | `app/not-found.js` | Granular error handling |
| `pages/_error.js` | `app/error.js` | Per-segment error boundaries |

### Root Layout Replacement (`app/layout.tsx`)
```tsx
// Replaces _app.tsx + _document.tsx
export default function RootLayout({ children }) {
  return (
    <html>
      <body>{children}</body>
    </html>
  )
}
```

### Migration Path (Incremental)
- Both `pages/` and `app/` can coexist during transition
- Start with `_app.tsx` and `_document.tsx` replacement first
- Migrate routes page-by-page; App Router takes precedence if conflict
- getServerSideProps/getStaticProps → server components or API routes

---

## 2. shadcn/ui + App Router Setup

### Installation & Configuration
```json
{
  "style": "new-york",
  "rsc": true,
  "cssVariables": true,
  "tailwind": { "cssVariables": true }
}
```

### Dark Mode with CSS Variables
1. **Enable in components.json:** `"cssVariables": true`
2. **Wrap app in ThemeProvider** (typically in root layout):
```tsx
import { ThemeProvider } from "next-themes"

export default function RootLayout({ children }) {
  return (
    <html suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class">
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
```

3. **CSS Variables** (app/globals.css):
```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
}
.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 0 0% 100%;
}
```

### Key Components for Dashboards
- **Card** — content containers
- **Tabs** — multi-section navigation
- **Sheet/Sidebar** — collapsible navigation drawer
- **Dialog** — modals for actions
- **Badge** — status indicators
- **Progress** — task/upload progress
- **Collapsible** — expandable sections

All work out-of-box with CSS variable theming; no per-component tweaks needed.

---

## 3. Zustand + App Router Best Practices

### Store Isolation Rule
**⚠️ Critical:** Stores must be per-request, not global. Shared global state = state leakage across users.

```tsx
// ❌ WRONG: Global store
const store = create(() => ({}))

// ✅ RIGHT: Create per request
const createStore = () => create(() => ({}))
```

### Client/Server Split Pattern
```tsx
// app/store.ts (client only)
'use client'
import { create } from 'zustand'

export const useAppStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user })
}))

// app/layout.tsx (server, passes data to client)
export default async function Layout({ children }) {
  const user = await fetchUser() // server-side
  return <AppInitializer initialUser={user}>{children}</AppInitializer>
}

// app/components/AppInitializer.tsx (client)
'use client'
export function AppInitializer({ initialUser, children }) {
  const setUser = useAppStore((s) => s.setUser)
  useEffect(() => setUser(initialUser), [initialUser])
  return children
}
```

### Key Rules
- **RSCs cannot** read/write stores (no hooks allowed)
- **Client components** wrap stores in 'use client'
- **Fetch on server**, pass data to client components
- **Never define stores as module-level globals** in shared files

---

## 4. 3-Column Dashboard Layout Pattern

### Route Groups Structure
```
app/
├── (dashboard)/
│   ├── layout.tsx         # Main dashboard layout
│   ├── (main)/            # Route group for main content
│   │   ├── page.tsx       # Overview
│   │   ├── users/
│   │   │   └── page.tsx
│   └── (sidebar)/         # Parallel route for sidebar
│       └── page.tsx
├── layout.tsx             # Root layout (providers, theme)
```

### Layout Component
```tsx
// app/(dashboard)/layout.tsx
import { Sheet, SheetContent } from '@/components/ui/sheet'

export default function DashboardLayout({ children }) {
  return (
    <div className="grid grid-cols-[250px_1fr_300px] h-screen">
      <aside>{/* Sidebar navigation */}</aside>
      <main>{children}</main>
      <aside>{/* Right panel: details/preview */}</aside>
    </div>
  )
}
```

### For Responsive
- Collapse sidebar on mobile using `Sheet` component
- Use `hidden md:block` Tailwind classes
- Store open/close state in Zustand client store (mobile drawer state only)

---

## 5. Common Migration Pitfalls

| Pitfall | Solution |
|---------|----------|
| **RSC state management** | Don't use Zustand in RSCs; pass server data as props |
| **_app logic loss** | Move middleware → `middleware.ts`; providers → root layout |
| **CSS-in-JS conflicts** | Use CSS modules or Tailwind; avoid styled-components in RSCs |
| **API route differences** | Route Handlers don't have req.query; use dynamic segments instead |
| **Hydration mismatch** | Add `suppressHydrationWarning` to `<html>` if using theme detection |
| **Confidence ceiling** | Keep layouts lightweight; heavy logic in `app/api` or async server components |

---

## Unresolved Questions

1. **Parallel routes for 3-column layout** — Verify if route groups alone suffice or if parallel routes (`@sidebar/@main`) needed for independent navigation
2. **shadcn/ui with custom CSS variable schemes** — Can you add brand-specific colors beyond Tailwind defaults?
3. **Zustand + Server Component Data** — Should AppInitializer live in root layout or per-route?

---

## Sources

- [Next.js App Router Migration Guide](https://nextjs.org/docs/app/guides/migrating/app-router-migration)
- [Next.js Upgrading: App Router Migration](https://nextjs.org/docs/14/app/building-your-application/upgrading/app-router-migration)
- [shadcn/ui Theming](https://ui.shadcn.com/docs/theming)
- [shadcn/ui Dark Mode](https://ui.shadcn.com/docs/dark-mode)
- [Zustand with Next.js Setup Guide](https://zustand.docs.pmnd.rs/learn/guides/nextjs)
- [Medium: Zustand with Next.js App Router](https://medium.com/@mak-dev/zustand-with-next-js-14-server-components-da9c191b73df)
- [Medium: Next.js File Structure Best Practices 2025](https://medium.com/better-dev-nextjs-react/inside-the-app-router-best-practices-for-next-js-file-and-directory-structure-2025-edition-ed6bc14a8da3)
