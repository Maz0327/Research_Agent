# Design Guidelines (Convenience Summary)

> **Authoritative spec lives at `docs/authoritative/INDEX.md`.**
> This document is a **non-authoritative convenience summary** for UI/UX patterns only.

**Version**: 1.0.0
**Last Updated**: 2025-12-26

---

## 1. Brand Identity

### Name & Tagline
- **Product Name**: Research Agent
- **Tagline**: AI-powered research for documentary creators
- **Personality**: Professional, intelligent, trustworthy, efficient

### Logo Usage
- Primary: Gradient text "Research Agent" (blue-to-purple)
- Minimum width: 120px
- Clear space: 16px around logo

---

## 2. Color System

### Dark Mode Palette (Primary)

```css
/* Background Colors */
--bg-primary: #121212;      /* Main background */
--bg-secondary: #1a1a1a;    /* Card backgrounds */
--bg-tertiary: #262626;     /* Elevated surfaces */
--bg-hover: #2d2d2d;        /* Hover states */

/* Border Colors */
--border-primary: #333333;   /* Default borders */
--border-secondary: #404040; /* Hover borders */
--border-accent: #4a5568;    /* Active borders */

/* Text Colors */
--text-primary: #f5f5f5;     /* Primary text - 15.4:1 ratio */
--text-secondary: #d1d5db;   /* Secondary text - 10.5:1 ratio */
--text-muted: #9ca3af;       /* Muted text - 7.5:1 ratio */
--text-disabled: #6b7280;    /* Disabled - 4.6:1 ratio */
```

### Accent Colors

```css
/* Blue - Primary Actions */
--blue-default: #3b82f6;
--blue-light: #60a5fa;
--blue-dark: #2563eb;

/* Purple - Gradient & Highlights */
--purple-default: #8b5cf6;
--purple-light: #a78bfa;
--purple-dark: #7c3aed;

/* Green - Success States */
--green-default: #22c55e;
--green-light: #4ade80;
--green-dark: #16a34a;

/* Red - Error States */
--red-default: #ef4444;
--red-light: #f87171;
--red-dark: #dc2626;

/* Orange - Warning States */
--orange-default: #f97316;
--orange-light: #fb923c;
--orange-dark: #ea580c;
```

### Gradients

```css
/* Primary Gradient (CTA buttons, headings) */
--gradient-primary: linear-gradient(to right, #3b82f6, #8b5cf6);

/* Background Glow Effects */
--glow-blue: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
--glow-purple: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 70%);
```

### Status Colors

| Status | Background | Text | Dot |
|--------|------------|------|-----|
| Queued | `bg-gray-800` | `text-gray-300` | `bg-gray-400` |
| Running | `bg-blue-900/50` | `text-blue-300` | `bg-blue-400` |
| Completed | `bg-green-900/50` | `text-green-300` | `bg-green-400` |
| Failed | `bg-red-900/50` | `text-red-300` | `bg-red-400` |
| Cancelled | `bg-orange-900/50` | `text-orange-300` | `bg-orange-400` |

---

## 3. Typography

### Font Families

```css
/* Primary Font - Google Fonts */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Monospace - Code & IDs */
font-family: 'JetBrains Mono', 'Fira Code', monospace;
```

**Note**: Inter has full Vietnamese language support.

### Type Scale

| Name | Size | Line Height | Usage |
|------|------|-------------|-------|
| xs | 12px (0.75rem) | 16px (1rem) | Labels, captions |
| sm | 14px (0.875rem) | 20px (1.25rem) | Body small, buttons |
| base | 16px (1rem) | 26px (1.625rem) | Body text |
| lg | 18px (1.125rem) | 28px (1.75rem) | Lead text |
| xl | 20px (1.25rem) | 30px (1.875rem) | Section titles |
| 2xl | 24px (1.5rem) | 32px (2rem) | Page titles |
| 3xl | 30px (1.875rem) | 36px (2.25rem) | Hero headings |
| 4xl | 36px (2.25rem) | 40px (2.5rem) | Landing hero |

### Font Weights

- Regular (400): Body text
- Medium (500): Buttons, labels
- Semibold (600): Headings, emphasis
- Bold (700): Hero text, strong emphasis

---

## 4. Spacing System

### Base Unit
- **4px** base grid unit

### Scale

| Token | Value | Tailwind | Usage |
|-------|-------|----------|-------|
| space-1 | 4px | `p-1` | Inline spacing |
| space-2 | 8px | `p-2` | Tight padding |
| space-3 | 12px | `p-3` | Default gap |
| space-4 | 16px | `p-4` | Component padding |
| space-5 | 20px | `p-5` | Card padding |
| space-6 | 24px | `p-6` | Section padding |
| space-8 | 32px | `p-8` | Page margins |
| space-10 | 40px | `p-10` | Large spacing |
| space-12 | 48px | `p-12` | Section gaps |
| space-16 | 64px | `p-16` | Hero spacing |

---

## 5. Border Radius

| Token | Value | Tailwind | Usage |
|-------|-------|----------|-------|
| radius-sm | 4px | `rounded-sm` | Subtle rounding |
| radius | 8px | `rounded-lg` | Buttons, inputs |
| radius-md | 10px | `rounded-lg` | Small cards |
| radius-lg | 12px | `rounded-xl` | Cards, modals |
| radius-xl | 16px | `rounded-2xl` | Large cards |
| radius-full | 9999px | `rounded-full` | Pills, avatars |

---

## 6. Shadows

```css
/* Card shadows */
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
--shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);

/* Glow shadows */
--glow-blue: 0 0 20px rgba(59, 130, 246, 0.3);
--glow-purple: 0 0 20px rgba(139, 92, 246, 0.3);
--glow-green: 0 0 20px rgba(34, 197, 94, 0.3);
```

---

## 7. Components

### Buttons

#### Primary Button
```jsx
<button className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed">
  Button Text
</button>
```

#### Secondary Button
```jsx
<button className="rounded-lg border border-gray-700 bg-gray-800/50 px-6 py-3 font-medium text-gray-300 transition-all hover:bg-gray-800 hover:text-gray-100">
  Button Text
</button>
```

#### Specs
- Min height: 44px (touch target)
- Border radius: 8px
- Padding: 12px 24px (py-3 px-6)
- Font weight: 500 (medium)

### Cards

```jsx
<div className="rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg transition-all hover:border-gray-700 hover:shadow-xl">
  {/* Card content */}
</div>
```

#### Specs
- Background: `#1a1a1a` (bg-gray-900)
- Border: 1px solid `#333333` (border-gray-800)
- Border radius: 12px
- Padding: 24px (p-6)

### Form Inputs

```jsx
<input
  type="text"
  className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
/>
```

#### Specs
- Height: 44px
- Border radius: 8px
- Border: 1px solid `#404040`
- Focus: Blue ring with 2px outline

### Status Badges

```jsx
<span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium bg-green-900/50 text-green-300">
  <span className="h-1.5 w-1.5 rounded-full bg-green-400"></span>
  Completed
</span>
```

---

## 8. Layout

### Page Structure

```jsx
<>
  <SkipLink />
  <header role="banner">
    <nav aria-label="Main navigation">...</nav>
  </header>
  <main id="main-content" role="main">
    <section aria-labelledby="section-heading">...</section>
  </main>
  <footer role="contentinfo">...</footer>
</>
```

### Breakpoints

| Name | Width | Usage |
|------|-------|-------|
| sm | 640px | Mobile landscape |
| md | 768px | Tablets |
| lg | 1024px | Desktop |
| xl | 1280px | Large desktop |
| 2xl | 1536px | Extra large |

### Max Widths

- Content: `max-w-5xl` (1024px)
- Forms: `max-w-3xl` (768px)
- Cards: `max-w-md` (448px)

### Sidebar

- Width: 256px (w-64)
- Fixed position on desktop
- Drawer on mobile

---

## 9. Accessibility (WCAG 2.1 AA)

### Color Contrast Requirements

- Normal text: 4.5:1 minimum
- Large text (18px+ or 14px+ bold): 3:1 minimum
- UI components & graphics: 3:1 minimum

### Focus States

```css
:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
```

### Touch Targets

- Minimum: 44x44px
- Recommended: 48x48px

### Skip Links

Always include on every page:

```jsx
<a
  href="#main-content"
  className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-blue-600 focus:text-white focus:px-4 focus:py-2 focus:rounded-lg"
>
  Skip to main content
</a>
```

### ARIA Labels

- All icon-only buttons must have `aria-label`
- Interactive elements need clear labels
- Status updates use `aria-live="polite"`

---

## 10. Animation

### Duration

| Speed | Duration | Usage |
|-------|----------|-------|
| Fast | 150ms | Hover states |
| Normal | 200ms | Most transitions |
| Slow | 300ms | Page transitions |
| Slower | 500ms | Complex animations |

### Easing

```css
/* Default easing */
transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);

/* Enter easing */
transition-timing-function: cubic-bezier(0, 0, 0.2, 1);

/* Exit easing */
transition-timing-function: cubic-bezier(0.4, 0, 1, 1);
```

### Motion Preferences

Always respect `prefers-reduced-motion`:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 11. Icons

### Source
Use [Heroicons](https://heroicons.com/) (outline style by default)

### Sizes

| Size | Pixels | Tailwind | Usage |
|------|--------|----------|-------|
| xs | 16px | `h-4 w-4` | Inline icons |
| sm | 20px | `h-5 w-5` | Buttons |
| md | 24px | `h-6 w-6` | Navigation |
| lg | 32px | `h-8 w-8` | Feature icons |
| xl | 48px | `h-12 w-12` | Empty states |

### Usage

```jsx
<svg
  className="h-5 w-5 text-gray-400"
  fill="none"
  stroke="currentColor"
  viewBox="0 0 24 24"
  aria-hidden="true"
>
  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="..." />
</svg>
```

---

## 12. Patterns

### Loading States

- Use skeleton loaders for content
- Use spinners for actions
- Show progress for long operations

### Empty States

- Clear illustration or icon
- Helpful message
- Call-to-action button

### Error States

- Red border/background tint
- Clear error message
- Suggested resolution

### Success States

- Green border/background tint
- Confirmation message
- Next steps or dismissal

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-26 | Initial design system |
