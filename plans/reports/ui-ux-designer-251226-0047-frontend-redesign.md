# Research Agent Frontend UI/UX Redesign Proposal

**Document ID**: ui-ux-designer-251226-0047-frontend-redesign
**Date**: 2025-12-26
**Status**: Proposal
**Scope**: Complete frontend redesign with accessibility compliance

---

## Executive Summary

This document outlines a comprehensive UI/UX redesign for the Research Agent frontend application. The current implementation has a solid dark-mode foundation but lacks semantic landmarks, skip-links, and proper navigation hierarchy. This proposal addresses accessibility compliance (WCAG 2.1 AA), information architecture improvements, and visual design enhancements optimized for documentary researcher workflows.

---

## 1. Current State Analysis

### 1.1 Screenshots Reviewed
- **Landing Page**: `/frontend-20251226-004059.png`
- **Login Page**: `/login-page.png`

### 1.2 Files Analyzed
| File | Purpose | Lines |
|------|---------|-------|
| `pages/index.tsx` | Landing page | 198 |
| `pages/login.tsx` | Authentication | 189 |
| `pages/dashboard.tsx` | Job management | 266 |
| `pages/settings.tsx` | User preferences | 627 |
| `components/Layout.tsx` | Main layout with sidebar | 92 |
| `components/JobCard.tsx` | Job status display | 345 |

### 1.3 Current Strengths
- **Visual Design**: Dark mode with gradient accents (blue-purple) is modern and professional
- **Animation**: Good use of Framer Motion for micro-interactions
- **Component Library**: Existing UI components (AnimatedButton, GlowCard, ProgressRing)
- **Color System**: Defined dark palette in tailwind.config.js
- **Job Cards**: Expandable cards with clear status indicators

### 1.4 Critical Issues Identified

#### Accessibility (A11y)
| Issue | Location | WCAG Criteria | Severity |
|-------|----------|---------------|----------|
| Missing `<header>` landmark | All pages | 1.3.1 Info & Relationships | High |
| Missing `<nav>` landmark | Landing/Login | 1.3.1 Info & Relationships | High |
| Missing `<main>` landmark | Login page | 1.3.1 Info & Relationships | High |
| No skip-link | All pages | 2.4.1 Bypass Blocks | High |
| Pure black bg (#0a0a0a) | All pages | Potential halation | Medium |
| Missing aria-labels | Icon buttons | 1.1.1 Text Alternatives | Medium |
| Focus indicators insufficient | Sidebar nav | 2.4.7 Focus Visible | Medium |

#### Information Architecture
- No global navigation on landing/login pages
- No breadcrumbs in authenticated views
- Settings page is 627 lines (too long, needs refactoring)
- No search functionality for jobs

#### User Experience
- No onboarding flow for new users
- No empty state guidance beyond "Create your first job"
- No keyboard shortcuts
- Mobile sidebar not implemented (fixed width 264px)

---

## 2. Information Architecture

### 2.1 Proposed Site Map

```
Research Agent
|
+-- Landing (/)
|   +-- Hero Section
|   +-- Features Section
|   +-- How It Works
|   +-- Pricing/Plans (future)
|   +-- Footer with links
|
+-- Authentication
|   +-- Login (/login)
|   +-- Register (/register) -- future
|   +-- Magic Link Confirmation
|
+-- App (authenticated)
    +-- Dashboard (/dashboard)
    |   +-- Quick Actions
    |   +-- Active Jobs
    |   +-- Recent Completed
    |   +-- Job Search/Filter
    |
    +-- Jobs (/jobs)
    |   +-- Job List (paginated)
    |   +-- Job Detail (/jobs/[id])
    |
    +-- Transcripts (/transcripts)
    |
    +-- Settings (/settings)
        +-- Account
        +-- Google Drive
        +-- Pipeline Defaults
        +-- Notifications
        +-- Display
```

### 2.2 Navigation Structure

#### Public Navigation (Landing/Login)
```
+---------------------------------------------------------------+
| [Logo]                              [Features] [Pricing] [Login] |
+---------------------------------------------------------------+
```

#### Authenticated Navigation
```
+-------------------+--------------------------------------------+
| Research Agent    | [Search]              [Notifications] [User]|
+-------------------+--------------------------------------------+
| Dashboard         |                                            |
| Jobs              |            MAIN CONTENT AREA               |
| Transcripts       |                                            |
| Settings          |                                            |
+-------------------+--------------------------------------------+
| [User Info]       |                                            |
| Sign Out          |                                            |
+-------------------+--------------------------------------------+
```

---

## 3. Accessibility Improvements

### 3.1 Semantic HTML Structure

**Current (`index.tsx`):**
```tsx
<main className="min-h-screen">
  <div>Hero</div>
  <div>Features</div>
  <footer>...</footer>
</main>
```

**Proposed:**
```tsx
<>
  <a href="#main-content" className="skip-link">Skip to main content</a>
  <header role="banner">
    <nav aria-label="Main navigation">...</nav>
  </header>
  <main id="main-content" role="main">
    <section aria-labelledby="hero-heading">...</section>
    <section aria-labelledby="features-heading">...</section>
  </main>
  <footer role="contentinfo">...</footer>
</>
```

### 3.2 Skip-Link Component

```tsx
// components/SkipLink.tsx
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
    >
      Skip to main content
    </a>
  );
}
```

### 3.3 Color Contrast Fixes

| Element | Current | Proposed | Ratio |
|---------|---------|----------|-------|
| Background | #0a0a0a | #121212 | - |
| Gray text | text-gray-400 (#9ca3af) | text-gray-300 (#d1d5db) | 7.5:1 vs 10.5:1 |
| Gray subtle | text-gray-500 (#6b7280) | text-gray-400 (#9ca3af) | 4.6:1 vs 7.5:1 |
| Border | border-gray-800 | border-gray-700 | Improved |

### 3.4 Focus States

```css
/* globals.css additions */
:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.nav-item:focus-visible {
  background: rgba(59, 130, 246, 0.2);
  outline: 2px solid #3b82f6;
  outline-offset: -2px;
}
```

### 3.5 ARIA Improvements

```tsx
// Icon buttons need labels
<button
  aria-label="Expand job details"
  aria-expanded={isExpanded}
>
  <ChevronIcon aria-hidden="true" />
</button>

// Status badges need context
<span
  role="status"
  aria-live="polite"
  className={statusClasses}
>
  {status}
</span>
```

---

## 4. Component Hierarchy

### 4.1 Atomic Design Structure

```
components/
├── atoms/
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Badge.tsx
│   ├── Icon.tsx
│   ├── Spinner.tsx
│   └── SkipLink.tsx
│
├── molecules/
│   ├── FormField.tsx
│   ├── SearchBar.tsx
│   ├── StatusBadge.tsx
│   ├── NavItem.tsx
│   └── UserMenu.tsx
│
├── organisms/
│   ├── Header.tsx
│   ├── Sidebar.tsx
│   ├── Footer.tsx
│   ├── JobCard.tsx
│   ├── JobForm.tsx
│   └── SettingsSection.tsx
│
├── templates/
│   ├── PublicLayout.tsx
│   ├── AppLayout.tsx
│   └── AuthLayout.tsx
│
└── pages/ (Next.js pages remain in /pages)
```

### 4.2 New Components Required

| Component | Purpose | Priority |
|-----------|---------|----------|
| `SkipLink` | Accessibility bypass | P0 |
| `Header` | Public page header | P0 |
| `PublicLayout` | Layout for landing/login | P0 |
| `SearchBar` | Job search | P1 |
| `Breadcrumbs` | Navigation context | P1 |
| `EmptyState` | Guided empty states | P1 |
| `MobileSidebar` | Responsive nav | P1 |
| `KeyboardShortcuts` | Power user UX | P2 |
| `OnboardingModal` | New user flow | P2 |

---

## 5. Visual Design Specifications

### 5.1 Color Palette (WCAG-Compliant Dark Mode)

```js
// tailwind.config.js extension
colors: {
  dark: {
    bg: {
      primary: '#121212',    // Main background (softer than #0a0a0a)
      secondary: '#1a1a1a',  // Card backgrounds
      tertiary: '#262626',   // Elevated surfaces
      hover: '#2d2d2d',      // Hover states
    },
    border: {
      primary: '#333333',    // Default borders
      secondary: '#404040',  // Hover borders
      accent: '#4a5568',     // Active borders
    },
    text: {
      primary: '#f5f5f5',    // Primary text (15.4:1 ratio)
      secondary: '#d1d5db',  // Secondary text (10.5:1)
      muted: '#9ca3af',      // Muted text (7.5:1)
      disabled: '#6b7280',   // Disabled (4.6:1)
    },
  },
  accent: {
    blue: {
      DEFAULT: '#3b82f6',
      light: '#60a5fa',
      dark: '#2563eb',
    },
    purple: {
      DEFAULT: '#8b5cf6',
      light: '#a78bfa',
      dark: '#7c3aed',
    },
    green: {
      DEFAULT: '#22c55e',
      light: '#4ade80',
      dark: '#16a34a',
    },
  },
}
```

### 5.2 Typography Scale

```js
// Using Inter font family (Google Fonts, Vietnamese support)
typography: {
  fonts: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'monospace'],
  },
  sizes: {
    xs: ['0.75rem', { lineHeight: '1rem' }],      // 12px
    sm: ['0.875rem', { lineHeight: '1.25rem' }],  // 14px
    base: ['1rem', { lineHeight: '1.625rem' }],   // 16px, 1.625 for readability
    lg: ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
    xl: ['1.25rem', { lineHeight: '1.875rem' }],  // 20px
    '2xl': ['1.5rem', { lineHeight: '2rem' }],    // 24px
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }], // 36px
  },
}
```

### 5.3 Spacing System

```js
spacing: {
  // Base: 4px
  px: '1px',
  0: '0',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  2: '0.5rem',      // 8px
  3: '0.75rem',     // 12px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  8: '2rem',        // 32px
  10: '2.5rem',     // 40px
  12: '3rem',       // 48px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
}
```

### 5.4 Border Radius

```js
borderRadius: {
  none: '0',
  sm: '0.25rem',    // 4px - subtle
  DEFAULT: '0.5rem', // 8px - buttons, inputs
  md: '0.625rem',   // 10px - cards (current: 12px)
  lg: '0.75rem',    // 12px - modals
  xl: '1rem',       // 16px - large cards
  full: '9999px',   // Pills, avatars
}
```

---

## 6. Wireframes

### 6.1 Landing Page (Desktop)

```
+------------------------------------------------------------------+
| [Skip to content]                                                 |
+------------------------------------------------------------------+
| HEADER                                                            |
| [Logo: Research Agent]              [Features] [Pricing] [Sign In]|
+------------------------------------------------------------------+
|                                                                   |
|                     HERO SECTION                                  |
|                                                                   |
|           Research Agent                                          |
|           for Documentary Creators                                |
|                                                                   |
|     AI-powered research tool that aggregates content from         |
|     YouTube, articles, Reddit, and more.                          |
|                                                                   |
|         [Get Started - Primary]    [Watch Demo - Secondary]       |
|                                                                   |
+------------------------------------------------------------------+
|                                                                   |
|                     FEATURES SECTION                              |
|                                                                   |
|   +----------------+  +----------------+  +----------------+      |
|   | [Icon]         |  | [Icon]         |  | [Icon]         |      |
|   | Transcript     |  | Claim          |  | Research       |      |
|   | Extraction     |  | Validation     |  | Packets        |      |
|   |                |  |                |  |                |      |
|   | Extract from   |  | AI-powered     |  | NotebookLM     |      |
|   | YouTube...     |  | fact checking  |  | ready docs     |      |
|   +----------------+  +----------------+  +----------------+      |
|                                                                   |
+------------------------------------------------------------------+
|                                                                   |
|                     HOW IT WORKS (NEW)                            |
|                                                                   |
|   1. Enter Topic  -->  2. AI Researches  -->  3. Get Documents    |
|                                                                   |
+------------------------------------------------------------------+
| FOOTER                                                            |
| [Logo]  About | Privacy | Terms | Contact        (c) 2025         |
+------------------------------------------------------------------+
```

### 6.2 Landing Page (Mobile)

```
+--------------------------------+
| [Skip link - hidden]           |
+--------------------------------+
| [=Menu]   Research Agent       |
+--------------------------------+
|                                |
|    Research Agent              |
|    for Documentary             |
|    Creators                    |
|                                |
|  AI-powered research tool...   |
|                                |
| [     Get Started      ]       |
| [     Watch Demo       ]       |
|                                |
+--------------------------------+
|        FEATURES                |
|                                |
| +----------------------------+ |
| | Transcript Extraction      | |
| | Extract from YouTube...    | |
| +----------------------------+ |
|                                |
| +----------------------------+ |
| | Claim Validation           | |
| | AI-powered fact checking   | |
| +----------------------------+ |
|                                |
+--------------------------------+
| FOOTER                         |
| (c) 2025 Research Agent        |
+--------------------------------+
```

### 6.3 Dashboard (Desktop)

```
+------------------------------------------------------------------+
| [Skip to content]                                                 |
+------------------------------------------------------------------+
| SIDEBAR              |  HEADER                                    |
|                      |  [Search jobs...]        [Bell] [Avatar v] |
| Research Agent       +--------------------------------------------+
|                      |                                            |
| [*] Dashboard        |  Dashboard                                 |
| [ ] Jobs             |  Create and manage research jobs           |
| [ ] Transcripts      |                                            |
| [ ] Settings         +--------------------------------------------+
|                      |  NEW RESEARCH JOB                          |
|                      |  +-----------------------------------------+
|                      |  | Research Topic                          |
|                      |  | [Enter your research topic...]          |
|                      |  |                                         |
|                      |  | Pipeline Mode                           |
|                      |  | [Breaking] [Investigation*] [Profile]   |
|                      |  | [Controversy] [Quick] [Full]            |
|                      |  |                                         |
|                      |  | [Start Research]                        |
|                      |  +-----------------------------------------+
|                      |                                            |
|                      |  YOUR JOBS                                 |
|                      |  [All] [Running] [Completed] [Failed]      |
| +------------------+ |                                            |
| | Avatar           | |  +----------------------------------------+|
| | user@email.com   | |  | [>] AI Ethics Investigation            ||
| | Sign out         | |  |     Investigation | Dec 25 | Running   ||
| +------------------+ |  |     [=========>          ] 45%         ||
+----------------------+  +----------------------------------------+|
                          |  +----------------------------------------+
                          |  | [v] Tesla Cybertruck Controversy      |
                          |  |     Controversy | Dec 24 | Completed  |
                          |  +----------------------------------------+
```

### 6.4 Login Page

```
+------------------------------------------------------------------+
| [Skip to content]                                                 |
+------------------------------------------------------------------+
| HEADER                                                            |
| [Logo: Research Agent]                                   [Home]   |
+------------------------------------------------------------------+
|                                                                   |
|                        MAIN CONTENT                               |
|                                                                   |
|              +------------------------------------+                |
|              |                                    |                |
|              |       Research Agent               |                |
|              |       Sign in to your account      |                |
|              |                                    |                |
|              |  [G] Continue with Google          |                |
|              |                                    |                |
|              |  ----------- or -----------        |                |
|              |                                    |                |
|              |  Email address                     |                |
|              |  [you@example.com              ]   |                |
|              |                                    |                |
|              |  [    Send Magic Link          ]   |                |
|              |                                    |                |
|              |  By signing in, you agree to our   |                |
|              |  Terms of Service and Privacy      |                |
|              |                                    |                |
|              +------------------------------------+                |
|                                                                   |
+------------------------------------------------------------------+
```

---

## 7. Implementation Plan

### Phase 1: Accessibility Foundation (Week 1)

| Task | File(s) | Priority |
|------|---------|----------|
| Add SkipLink component | `components/SkipLink.tsx` | P0 |
| Create PublicLayout with header | `components/PublicLayout.tsx` | P0 |
| Update index.tsx with semantic landmarks | `pages/index.tsx` | P0 |
| Update login.tsx with semantic landmarks | `pages/login.tsx` | P0 |
| Fix color contrast in tailwind.config | `tailwind.config.js` | P0 |
| Add focus-visible styles | `styles/globals.css` | P0 |
| Add aria-labels to icon buttons | All components | P0 |

### Phase 2: Navigation & Layout (Week 2)

| Task | File(s) | Priority |
|------|---------|----------|
| Refactor Layout.tsx with proper landmarks | `components/Layout.tsx` | P1 |
| Add mobile sidebar drawer | `components/MobileSidebar.tsx` | P1 |
| Create AppHeader component | `components/AppHeader.tsx` | P1 |
| Implement SearchBar | `components/SearchBar.tsx` | P1 |
| Add breadcrumbs | `components/Breadcrumbs.tsx` | P1 |

### Phase 3: Component Refactoring (Week 3)

| Task | File(s) | Priority |
|------|---------|----------|
| Split settings.tsx into sections | `pages/settings/*.tsx` | P1 |
| Create EmptyState component | `components/EmptyState.tsx` | P1 |
| Standardize form components | `components/forms/*` | P2 |
| Add keyboard shortcuts hook | `hooks/useKeyboardShortcuts.ts` | P2 |

### Phase 4: Polish & Testing (Week 4)

| Task | File(s) | Priority |
|------|---------|----------|
| Add loading skeletons | All pages | P2 |
| Implement OnboardingModal | `components/OnboardingModal.tsx` | P2 |
| Accessibility audit with axe-core | - | P1 |
| Cross-browser testing | - | P1 |
| Mobile responsive testing | - | P1 |

---

## 8. Design Guidelines Document

The following content should be added to `/docs/design-guidelines.md`:

```markdown
# Research Agent Design Guidelines

## Brand

- **Name**: Research Agent
- **Tagline**: AI-powered research for documentary creators
- **Personality**: Professional, intelligent, trustworthy

## Colors

### Dark Mode (Primary)
- Background Primary: #121212
- Background Secondary: #1a1a1a
- Background Tertiary: #262626
- Text Primary: #f5f5f5
- Text Secondary: #d1d5db
- Text Muted: #9ca3af

### Accent Colors
- Blue (Primary Action): #3b82f6
- Purple (Gradient): #8b5cf6
- Green (Success): #22c55e
- Red (Error): #ef4444
- Orange (Warning): #f97316

## Typography

- **Primary Font**: Inter (Google Fonts, Vietnamese support)
- **Monospace**: JetBrains Mono
- **Base Size**: 16px
- **Line Height**: 1.625 (body), 1.25 (headings)

## Spacing

- Grid: 4px base unit
- Component spacing: 16px (4 units)
- Section spacing: 32px (8 units)
- Page margin: 32px desktop, 16px mobile

## Components

### Buttons
- Primary: Blue gradient, white text
- Secondary: Gray border, gray text
- Min height: 44px (touch target)
- Border radius: 8px

### Cards
- Background: #1a1a1a
- Border: 1px solid #333333
- Border radius: 12px
- Padding: 24px

### Forms
- Input height: 44px
- Border radius: 8px
- Focus: 2px blue outline

## Accessibility

- Minimum contrast: 4.5:1 (normal text), 3:1 (large text)
- Touch targets: 44x44px minimum
- Focus visible on all interactive elements
- Skip links on all pages
- Semantic HTML landmarks
```

---

## 9. Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Lighthouse Accessibility | Unknown | 95+ | Lighthouse audit |
| WCAG 2.1 AA Compliance | Partial | Full | axe-core audit |
| Mobile Usability | Limited | Full | Manual testing |
| Time to First Job | Unknown | < 60s | Analytics |
| User Satisfaction | Unknown | > 4.5/5 | User feedback |

---

## 10. References

### Design Inspiration
- [Muzli Dashboard Inspiration](https://muz.li/inspiration/dashboard-inspiration/)
- [Dribbble Dashboard UI](https://dribbble.com/tags/dashboard-ui)
- [Behance Dashboard Projects](https://www.behance.net/search/projects/dashboard%20ui%20design)
- [Holo AI Dashboard Design](https://www.behance.net/gallery/238954891/Holo-AI-Branding-UX-UI-Dashboard-Design)

### Accessibility Standards
- [WCAG 2.1 Official Guidelines](https://www.w3.org/TR/WCAG21/)
- [Dark Mode A11y Best Practices](https://dubbot.com/dubblog/2023/dark-mode-a11y.html)
- [Color Contrast WCAG 2025 Guide](https://www.allaccessible.org/blog/color-contrast-accessibility-wcag-guide-2025)
- [BrowserStack WCAG Checklist](https://www.browserstack.com/guide/wcag-compliance-checklist)

### Dashboard Design Principles
- [20 Best Dashboard UI/UX Principles 2025](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795)
- [16 Best Dashboard Design Examples](https://www.eleken.co/blog-posts/dashboard-design-examples-that-catch-the-eye)

---

## Unresolved Questions

1. **Light mode support**: Should the app support light mode toggle, or remain dark-only?
2. **Pricing page**: Is a pricing/plans page needed for the landing page?
3. **Notification system**: What notifications should be shown in the app header?
4. **Job search scope**: Should search include job content or just titles?
5. **Mobile priority**: What percentage of users are on mobile vs desktop?
6. **Onboarding depth**: How many steps should the onboarding flow include?
7. **Keyboard shortcuts**: Which actions should have shortcuts?
