# Next.js 14 + TypeScript + Zustand Production Best Practices (2025)

**Research Date:** December 28, 2025
**Focus:** Component patterns, state management, security, performance, TypeScript strict typing

---

## 1. Component Patterns & Architecture

### Server vs Client Components (Default: Server)
- Next.js 14 uses **React Server Components (RSC) by default** - eliminate client-side JavaScript burden
- Server Components don't ship JS to browser, reducing bundle size automatically
- Use `'use client'` sparingly for interactive features only
- Reduces layout shift, improves hydration speed vs older Pages Router

### Functional Components & Hooks
- Use **functional components exclusively** (React 18+ best practice)
- Apply **Suspense boundaries** for streaming UI and data fetching
- Implement **error boundaries** for graceful error handling
- Lazy load components with `React.lazy()` for code splitting

### File Organization
```
app/
├── (routes)/
├── api/
├── layout.tsx
└── page.tsx
components/
├── ui/              # Reusable primitives
├── features/        # Feature-specific components
└── ErrorBoundary.tsx
hooks/
lib/
types/
```

---

## 2. State Management with Zustand + TypeScript

### Core Pattern
```typescript
interface StoreState {
  bears: number;
  increase: (by: number) => void;
}

const useStore = create<StoreState>()((set) => ({
  bears: 0,
  increase: (by) => set(state => ({ bears: state.bears + by })),
}));
```

### Key Principles (2025 Consensus)
- **Minimal API** - No boilerplate, no actions/reducers (~1kb gzipped)
- **No provider required** - Hook-based access, direct store access
- **Selector pattern for performance** - Select only needed state slices to prevent unnecessary re-renders
- **Middleware support** - Redux devtools, persist middleware with full TypeScript support

### Layered Architecture (Recommended)
- **Server State:** React Query/TanStack Query for data fetching
- **Client State:** Zustand for UI/workflow state
- **Workflow State:** XState for finite state machines in critical flows
- **Persistence:** Combine with Zustand persist middleware

### When to Use Zustand
✅ Small-to-medium apps with minimal setup
✅ Teams avoiding Redux learning curve
✅ Tight performance budgets (bundle-sensitive)
⚠️ Large enterprise apps may need Redux's structure (Zustand lacks strict patterns)

---

## 3. TypeScript Strict Mode & Typing

### Enable Strict Mode (`tsconfig.json`)
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true
  }
}
```

### Interface Patterns
- **Always type props explicitly** - Use interfaces/types for component props
- **Avoid `any` completely** - Use generics or `unknown` instead
- **Composition over inheritance** - Merge types instead of extending
- **Utility types for DRY:** `Partial<T>`, `Pick<T>`, `Omit<T>`, `Required<T>`

### Gradual Adoption
Enable strict flags one-at-a-time for existing projects; new projects should start strict.

---

## 4. Security Best Practices

### XSS Prevention
1. **Content Security Policy (CSP)** - Set in `next.config.js` headers
2. **Avoid `dangerouslySetInnerHTML`** - Use libraries like `dompurify` if needed
3. **HTTP-only cookies** - Session tokens unreachable by JavaScript
4. **Input sanitization** - Always sanitize user-generated content

### API Route Authentication
- **NextAuth.js 2025** - Standard for Next.js authentication
  - Signed JWTs ensure token integrity
  - CSRF tokens on every sign-in
  - Built-in defenses: replay attacks, clickjacking, OAuth state tampering
- **Verify all endpoints** - Use `getServerSession()` or JWT claims validation
- **Authorization != Authentication** - Confirm user permissions, not just identity
- **server-only package** - Prevent sensitive code/data leakage to client

### Additional Measures
- Set `SameSite=Strict` on all cookies, enforce HTTPS production-only
- Use Edge Middleware for rate limiting suspicious requests
- Log authentication events for breach detection

---

## 5. Performance Optimization

### Data Fetching & Caching (App Router)
- **Streaming:** Use React Suspense + loading UI to progressively send content
- **Parallel fetching:** Request data in parallel to avoid waterfalls
- **Revalidation:** Use `revalidatePath()` / `revalidateTag()` for smart cache invalidation
- **Next.js 14.2+** - Smarter integration between React cache and Next.js data cache

### Code Splitting & Loading
- Server Components enable **automatic code-splitting by route segment**
- Lazy load Client Components and third-party libraries where applicable
- **Partial Prerendering (PPR):** Compiler optimization for dynamic content with fast static response
- Use `@next/bundle-analyzer` to track bundle size

### Image & Font Optimization
- **Image Component:** Automatic optimization, modern format serving (WebP), responsive
- **Font Module:** Reduces layout shift (Cumulative Layout Shift)
- **Script Component:** Defers third-party scripts (prevents blocking)

### Core Web Vitals (LCP, INP, CLS)
Monitor using Next.js insights or third-party tools; focus on reducing JavaScript shipped to client.

---

## 6. Latest Updates (Next.js 16, October 2025)

- **Turbopack as default bundler** - Significant build speed improvements
- **Cache Components + PPR** - Instant navigation via cached components
- **React Compiler support** - Automatic memoization (stable in v16)
- **Typed routes** - Type-safe link navigation

---

## Key Takeaways

| Aspect | 2025 Best Practice |
|--------|-------------------|
| **Components** | Server Components by default; minimal Client Components |
| **State** | Zustand for client state, React Query for server state |
| **TypeScript** | Strict mode enabled; no `any`; utility types for DRY |
| **Security** | NextAuth.js + CSP headers; HTTP-only cookies; input sanitization |
| **Performance** | Streaming, PPR, automatic code-splitting, image optimization |

---

## Sources

- [Next.js Production Checklist](https://nextjs.org/docs/app/guides/production-checklist)
- [Zustand Documentation](https://zustand.docs.pmnd.rs/)
- [Next.js Security Guide 2025](https://www.turbostarter.dev/blog/complete-nextjs-security-guide-2025-authentication-api-protection-and-best-practices)
- [TypeScript Best Practices](https://www.w3schools.com/typescript/typescript_best_practices.php)
- [React & Next.js 2025 Best Practices](https://strapi.io/blog/react-and-nextjs-in-2025-modern-best-practices)

---

**Plan Directory:** `/Users/maz/Documents/GitHub/Research_Agent/plans/251228-1817-nextjs-14-typescript-zustand-2025/`
