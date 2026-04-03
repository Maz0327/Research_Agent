# Design System

**Version:** 1.0.0
**Last Updated:** 2026-04-03
**Scope:** Frontend React/Next.js application

---

## Overview

This document defines the design system conventions for the Research Agent frontend. It ensures consistency across all UI components, maintains WCAG AA accessibility standards, and provides guidelines for extending the design system.

---

## 1. Color Tokens

### CSS Variable System
All colors use CSS custom properties. Never hardcode hex colors in components.

```css
/* In globals.css or app.css */
:root {
  --bg-primary: #121212;
  --bg-secondary: #1a1a1a;
  --bg-tertiary: #262626;
  --border-border: #333333;
  --text-foreground: #f5f5f5;
  --text-muted-foreground: #9ca3af;
  /* ... others */
}
```

### Semantic Naming Convention
- `bg-*` — Background colors (primary, secondary, tertiary)
- `text-*` — Foreground/text colors (foreground, muted-foreground, disabled)
- `border-*` — Border colors (border, secondary)
- `surface-*` — Layered backgrounds (surface-0 through surface-4)

### Surface Scale (Layering)
Use for layered UI elements without changing base colors:
```
--surface-0: Main background (#121212)
--surface-1: Slightly elevated (#1a1a1a)
--surface-2: Card level (#262626)
--surface-3: Modal overlay (#2d2d2d)
--surface-4: Tooltip/popover (#333333)
```

### Status Colors
Status indicators must use both color AND icon/text differentiation:

| Status | Background | Text | Icon | Use Case |
|--------|------------|------|------|----------|
| Running | `bg-blue-900/50` | `text-blue-300` | ✦ (pulse) | Job in progress |
| Completed | `bg-green-900/50` | `text-green-300` | ✓ (check) | Job succeeded |
| Failed | `bg-red-900/50` | `text-red-300` | ✕ (x) | Job error |
| Queued | `bg-gray-800` | `text-gray-300` | ↻ (clock) | Waiting |
| Cancelled | `bg-orange-900/50` | `text-orange-300` | ⊗ (block) | User cancelled |

### Dark-Only Mode
The application uses dark-only mode exclusively. ThemeToggle components have been removed.

**Provider configuration** (`app/providers.tsx`):
```tsx
<ThemeProvider attribute="class" defaultTheme="dark" forcedTheme="dark">
  {children}
</ThemeProvider>
```

---

## 2. Component Usage Standards

### Buttons
Use **shadcn Button only** — never raw `<button>` elements.

```tsx
import { Button } from '@/components/ui/button';

// Basic button
<Button onClick={handleClick}>Click me</Button>

// With loading state
<Button disabled={isLoading}>
  {isLoading && <Spinner size="sm" />}
  {isLoading ? 'Processing...' : 'Submit'}
</Button>

// Variants
<Button variant="default">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
```

**Never:**
```tsx
// ❌ Raw button
<button onClick={handleClick}>Click</button>

// ❌ Inline onClick without Spinner
<button disabled={isLoading}>{isLoading ? 'Loading' : 'Submit'}</button>
```

### Cards
Use **shadcn Card only** — never raw `<div>` with custom styling.

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Subtitle or description</CardDescription>
  </CardHeader>
  <CardContent>Content here</CardContent>
</Card>
```

### Icons
Use **Lucide React only** — never inline SVGs or custom icon components.

```tsx
import { Search, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

// Icon button with aria-label
<Button variant="ghost" size="icon" aria-label="Search">
  <Search className="h-4 w-4" />
</Button>

// Status icons
<CheckCircle className="text-green-400" />
<AlertCircle className="text-red-400" />
```

**Icon sizes:**
- `h-4 w-4` — Inline/button icons (16px)
- `h-5 w-5` — Form labels (20px)
- `h-6 w-6` — List items (24px)
- `h-8 w-8` — Page headers (32px)

### Spinners
Use **`<Spinner />` component only** — never CSS spinners or inline SVGs.

```tsx
import { Spinner } from '@/components/ui/spinner';

// Default spinner
<Spinner />

// Sized spinners
<Spinner size="sm" />    // 16px
<Spinner size="md" />    // 24px (default)
<Spinner size="lg" />    // 32px

// In buttons
<Button disabled={isLoading}>
  {isLoading && <Spinner size="sm" />}
  Loading...
</Button>
```

**Never:**
```tsx
// ❌ CSS spinner
<div className="border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin" />

// ❌ Inline SVG
<svg>...</svg>
```

### Modals/Dialogs
Use **Radix Dialog / shadcn Dialog only** — never raw fixed overlays.

All modals automatically include:
- Focus trap (keyboard tab confinement)
- Escape key handling
- Backdrop click to close
- Proper z-index stacking

```tsx
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';

<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>Are you sure?</DialogDescription>
    </DialogHeader>
    <Button onClick={handleConfirm}>Confirm</Button>
  </DialogContent>
</Dialog>
```

**Never:**
```tsx
// ❌ Raw fixed overlay
<div className="fixed inset-0 bg-black/50 z-50">
  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
    Dialog content
  </div>
</div>
```

### Loading States
Use **Skeleton** for page/section loads, **Spinner** for inline actions.

```tsx
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';

// Page-level loading (use Skeleton)
export default function JobsPage({ isLoading }) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }
  return <div>Jobs list</div>;
}

// Button action loading (use Spinner)
<Button disabled={isLoading}>
  {isLoading && <Spinner size="sm" />}
  {isLoading ? 'Submitting...' : 'Submit'}
</Button>
```

---

## 3. Spacing Scale

Consistent spacing maintains visual hierarchy and improves readability.

```
Compact:  p-3 / gap-2  (12px)
Default:  p-4 / gap-3  (16px)
Spacious: p-6 / gap-4  (24px)
```

### Usage Guidelines
```tsx
// Card content (default)
<Card className="p-4 space-y-3">
  <h3>{title}</h3>
  <p>{description}</p>
</Card>

// Dense list (compact)
<div className="space-y-2">
  {items.map(item => <div key={item.id}>{item.name}</div>)}
</div>

// Section spacing (spacious)
<div className="space-y-6">
  <Section />
  <Section />
</div>
```

---

## 4. Border Radius

Different border radii create visual hierarchy:

```
Chips/Pills:     rounded-full  (9999px)
Buttons/Inputs:  rounded-lg    (8px)
Cards:           rounded-xl    (12px)
Modals/Overlays: rounded-2xl   (16px)
```

### Examples
```tsx
// Chip
<span className="rounded-full bg-blue-900/50 px-3 py-1">Status</span>

// Button (rounded-lg is default in Button component)
<Button>Click me</Button>

// Card (rounded-xl is default in Card component)
<Card className="rounded-xl">Content</Card>

// Modal (rounded-2xl is default in Dialog component)
<DialogContent>Content</DialogContent>
```

---

## 5. Z-Index Scale

Consistent z-index stacking prevents overlap issues and improves accessibility.

```
0        — base (default)
10       — sticky header/footer
20       — sidebar
30       — header/navbar
40       — overlay/tooltip
50       — modal/dialog
60       — toast/notification
100      — skip link
```

**Tailwind config** (`tailwind.config.ts`):
```ts
zIndex: {
  base: '0',
  sticky: '10',
  sidebar: '20',
  header: '30',
  overlay: '40',
  modal: '50',
  toast: '60',
  skipLink: '100',
}
```

**Usage:**
```tsx
<div className="z-modal">Modal</div>
<div className="z-toast">Toast</div>
<div className="z-overlay">Overlay</div>
```

**Never use arbitrary z-index values:**
```tsx
// ❌ Wrong
<div className="z-[45]">Not allowed</div>

// ✅ Correct
<div className="z-overlay">Correct</div>
```

---

## 6. Touch Targets

All interactive elements must meet WCAG AA standards for touch targets.

### Size Requirements
- **Minimum:** 44x44px on mobile (mobile-first design)
- **Desktop:** 36x36px acceptable via responsive sizing

### Responsive Pattern
```tsx
// Standard pattern: 44px mobile, 36px desktop
<Button className="h-11 sm:h-9">Click me</Button>

// Icon button
<Button
  variant="ghost"
  size="icon"
  className="h-11 sm:h-9 w-11 sm:w-9"
  aria-label="Menu"
>
  <Menu className="h-4 w-4" />
</Button>

// Small button (use with caution)
<Button className="h-10 sm:h-8">Small</Button>
```

### Spacing Between Targets
Maintain at least 16px spacing between interactive elements on mobile to prevent accidental clicks.

```tsx
// ✅ Correct: 16px gap
<div className="flex gap-4">
  <Button>Button 1</Button>
  <Button>Button 2</Button>
</div>

// ❌ Wrong: Too close together
<div className="flex gap-2">
  <Button>Button 1</Button>
  <Button>Button 2</Button>
</div>
```

---

## 7. Accessibility Standards

All components must meet WCAG AA (minimum) standards.

### Focus Management
All interactive elements are automatically focusable. Use `:focus-visible` for focus styling:

```css
:focus-visible {
  outline: 2px solid var(--text-foreground);
  outline-offset: 2px;
}
```

### Aria Labels
Icon-only buttons require `aria-label`:

```tsx
// ✅ Correct
<Button variant="ghost" size="icon" aria-label="Search">
  <Search className="h-4 w-4" />
</Button>

// ❌ Wrong: Missing aria-label
<Button variant="ghost" size="icon">
  <Search className="h-4 w-4" />
</Button>
```

### Dynamic Content
Dynamic content requires proper ARIA attributes:

```tsx
// Status updates (read by screen readers)
<div aria-live="polite" aria-atomic="true">
  {status === 'complete' && 'Processing complete'}
</div>

// Alerts
<div role="alert" className="bg-red-900/50 p-4 rounded-lg">
  Error: Something went wrong
</div>

// Loading state indication
<Button disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Loading...' : 'Submit'}
</Button>
```

### Status Indicators
Status badges must use non-color differentiation (icon + text):

```tsx
// ✅ Correct: Icon + color + text
<div className="flex items-center gap-2 rounded-lg bg-green-900/50 px-3 py-2 text-green-300">
  <CheckCircle className="h-4 w-4" />
  <span>Completed</span>
</div>

// ❌ Wrong: Color only
<div className="bg-green-900/50 px-3 py-2">
  Completed
</div>
```

### Motion & Animation
All animations must respect the `prefers-reduced-motion` preference:

```tsx
import { useReducedMotion } from '@/hooks/use-reduced-motion';

export function AnimatedCard() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      animate={{ opacity: 1 }}
      transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.3 }}
    >
      Content
    </motion.div>
  );
}
```

---

## 8. New Component Checklist

When creating a new component, verify ALL of the following:

- [ ] **Colors:** Uses only CSS variable tokens (no hardcoded hex colors)
- [ ] **Buttons:** Uses shadcn `Button` component (never raw `<button>`)
- [ ] **Cards:** Uses shadcn `Card` component (never raw `<div>`)
- [ ] **Icons:** Uses Lucide React (never inline SVGs or custom icon files)
- [ ] **Loading:** Uses `Spinner` for inline actions, `Skeleton` for page loads
- [ ] **Modals:** Uses Radix Dialog / shadcn Dialog (never fixed overlays)
- [ ] **Touch Target:** Interactive elements >= 44px on mobile
- [ ] **Spacing:** Uses predefined scale (p-3, p-4, p-6 / gap-2, gap-3, gap-4)
- [ ] **Border Radius:** Uses semantic tokens (rounded-lg, rounded-xl, rounded-2xl)
- [ ] **Z-Index:** Uses named tokens only (z-modal, z-toast, not arbitrary z-[45])
- [ ] **Accessibility:** Icon-only buttons have `aria-label`
- [ ] **Accessibility:** Dynamic content uses `aria-live="polite"`
- [ ] **Accessibility:** Status indicators have icon + text differentiation
- [ ] **Animations:** Checks `useReducedMotion()` hook

---

## 9. References

### Component Library
- **Button:** `components/ui/button.tsx`
- **Card:** `components/ui/card.tsx`
- **Dialog:** `components/ui/dialog.tsx`
- **Spinner:** `components/ui/spinner.tsx`
- **Skeleton:** `components/ui/skeleton.tsx`

### Configuration Files
- **Tailwind:** `tailwind.config.ts`
- **CSS Variables:** `app/globals.css`
- **Theme Provider:** `app/providers.tsx`

### Utilities
- **Reduced Motion Hook:** `hooks/use-reduced-motion.ts`

### Icon Library
- **Lucide React:** https://lucide.dev/

---

## 10. Changelog

### v1.0.0 (2026-04-03)
- Initial design system documentation
- Color token consolidation (dark-only mode)
- Component usage standards established
- WCAG AA compliance guidelines
- Touch target requirements
- Accessibility standards defined
