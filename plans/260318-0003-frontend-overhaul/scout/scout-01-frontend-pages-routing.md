# Scout: Frontend Pages & Routing

## Pages (14 total)

| Route | File | Description |
|-------|------|-------------|
| `/` | `index.tsx` | Landing — redirects to dashboard if authed |
| `/dashboard` | `dashboard.tsx` | Job list + creation form, tabbed input |
| `/login` | `login.tsx` | OAuth (Google) + email magic link |
| `/queue` | `queue.tsx` | Jobs hub with tabbed nav |
| `/settings` | `settings.tsx` | User settings + dark mode |
| `/usage` | `usage.tsx` | API usage + cost estimates |
| `/transcripts` | `transcripts.tsx` | YouTube transcript extractor |
| `/jobs/[id]` | `jobs/[id].tsx` | Job detail + artifacts + iterate |
| `/shared/[token]` | `shared/[token].tsx` | Public share (token-gated) |
| `/admin` | `admin/index.tsx` | Admin dashboard |
| `/admin/errors` | `admin/errors.tsx` | Error logs |
| `/admin/jobs` | `admin/jobs.tsx` | Job management |
| `/admin/users` | `admin/users.tsx` | User management |

## App-Level Setup

- `_app.tsx`: ErrorBoundary → AuthProvider → global CSS
- No `_document.tsx` — using defaults
- `next.config.js`: standalone output, `/api/:path*` → backend proxy, CSP headers

## Dependencies (Production)

```
@supabase/supabase-js ^2.45.0
docx ^9.6.1, dompurify ^3.3.1, html2pdf.js ^0.10.1
framer-motion ^10.18.0
next ^14.2.0, react ^18.3.1, react-dom ^18.3.1
react-markdown ^10.1.0, rehype-raw ^7.0.0, rehype-sanitize ^6.0.0, remark-gfm ^4.0.1
zustand ^4.5.0
```

## Dev Dependencies

```
tailwindcss ^3.4.19, autoprefixer, postcss
eslint, prettier, prettier-plugin-tailwindcss
jest ^30.2.0, @testing-library/react, ts-jest
typescript ^5.5.0
```
