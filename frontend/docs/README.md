# Frontend Documentation

Welcome to the Research Agent frontend documentation. This directory contains all guidelines, standards, and reference material for the React/Next.js application.

---

## Core Documents

### [Design System](./design-system.md)
Complete design token system and component usage standards.

**Read this for:**
- Color token naming and CSS variable system
- Component library rules (shadcn, Lucide, Spinner, Dialog)
- Touch target requirements and spacing scale
- Accessibility standards (WCAG AA)
- New component checklist

**Key sections:**
1. Color Tokens — CSS variables, semantic naming, surface scale, status colors
2. Component Usage Standards — Button, Card, Icons, Spinners, Modals, Loading
3. Spacing Scale — Compact (p-3), Default (p-4), Spacious (p-6)
4. Border Radius — Chips (rounded-full), Buttons (rounded-lg), Cards (rounded-xl)
5. Z-Index Scale — Named tokens (base, sticky, sidebar, header, overlay, modal, toast)
6. Touch Targets — 44x44px mobile minimum
7. Accessibility Standards — Focus management, ARIA labels, reduced motion
8. New Component Checklist — 14-point verification list
9. References — Component library, config files, utilities, icons

---

### [Code Standards](./code-standards.md)
Frontend-specific code quality and patterns.

**Read this for:**
- File naming conventions and directory structure
- TypeScript type safety requirements
- Component structure and hook usage patterns
- Tailwind styling conventions (mobile-first, CSS variables)
- Error handling and loading states
- API communication patterns
- Testing best practices
- Code review checklist

**Key sections:**
1. File & Naming Conventions — PascalCase, kebab-case, directory structure
2. TypeScript & Type Safety — Type hints, Props interfaces, avoid `any`
3. Component Structure — Functional components, hook ordering, component size
4. Styling — Tailwind-only, CSS variables, responsive design
5. Hooks & Custom Hooks — Hook naming, documentation, useCallback patterns
6. Error Handling — Try-catch, error boundaries, error states
7. API Communication — Typed requests/responses, loading states
8. Testing — Jest/RTL patterns, test structure, best practices
9. Commit Messages — Conventional commit format
10. Code Review Checklist — Pre-submission verification

---

## Quick Start

### For New Components
1. Check the [New Component Checklist](./design-system.md#8-new-component-checklist) (14 points)
2. Use shadcn Button/Card/Dialog (never raw elements)
3. Use Lucide icons (never inline SVGs)
4. Use CSS variables for colors (never hardcoded hex)
5. Verify touch targets ≥ 44px on mobile
6. Test with keyboard navigation and screen readers

### For Code Review
1. Run the [Code Review Checklist](./code-standards.md#10-code-review-checklist)
2. Verify TypeScript types are complete
3. Check Tailwind-only styling (no inline styles)
4. Confirm error handling is in place
5. Validate test coverage for happy & error paths

### For Questions
- **"What colors should I use?"** → [Color Tokens](./design-system.md#1-color-tokens)
- **"How do I build a button?"** → [Component Usage > Buttons](./design-system.md#2-component-usage-standards)
- **"How do I style this?"** → [Styling](./code-standards.md#4-styling)
- **"What's the folder structure?"** → [File Conventions](./code-standards.md#1-file--naming-conventions)
- **"How do I handle errors?"** → [Error Handling](./code-standards.md#6-error-handling)

---

## Key Principles

### Dark-Only Mode
The application uses dark mode exclusively. `forcedTheme="dark"` is set in `app/providers.tsx`.
No theme toggle. No light mode.

### Component Library Consolidation
- **Buttons:** shadcn `Button` only
- **Cards:** shadcn `Card` only
- **Icons:** Lucide React only
- **Spinners:** `<Spinner />` component only
- **Modals:** Radix Dialog / shadcn Dialog only
- **No:** Custom components, raw elements, inline SVGs, CSS spinners

### Accessibility First
- All interactive elements ≥ 44px on mobile
- All modals use Radix Dialog (focus traps built-in)
- All status indicators use icon + text (not color alone)
- All animations check `useReducedMotion()`
- All icon-only buttons have `aria-label`

### CSS Variables Only
Never hardcode colors. All colors use CSS custom properties:
```tsx
// ✅ Correct
<div className="bg-card text-foreground">Content</div>

// ❌ Wrong
<div className="bg-[#1a1a1a] text-[#f5f5f5]">Content</div>
```

### Type Safety
All functions have complete type hints. Props are interfaces. Avoid `any`.

```tsx
// ✅ Correct
interface AlertProps {
  message: string;
  onClose: () => void;
}

export function Alert({ message, onClose }: AlertProps) {
  // ...
}

// ❌ Wrong
export function Alert({ message, onClose }) {
  // ...
}
```

---

## Document Versions

| Document | Version | Updated | Status |
|----------|---------|---------|--------|
| Design System | 1.0.0 | 2026-04-03 | Active |
| Code Standards | 1.0.0 | 2026-04-03 | Active |

---

## Related Resources

### Component Library
- [shadcn/ui](https://ui.shadcn.com/) — UI component library
- [Lucide React](https://lucide.dev/) — Icon library
- [Radix UI](https://www.radix-ui.com/) — Primitives (Dialog, Dropdown, etc.)

### Styling & Configuration
- [Tailwind CSS](https://tailwindcss.com/) — Utility-first CSS
- `tailwind.config.ts` — Z-index and custom tokens
- `app/globals.css` — CSS variables
- `app/providers.tsx` — Theme configuration

### Tools & Utilities
- `hooks/use-reduced-motion.ts` — Accessibility hook
- `components/ui/spinner.tsx` — Spinner component
- `components/ui/skeleton.tsx` — Loading skeleton

### Framework Documentation
- [Next.js](https://nextjs.org/docs) — React framework
- [React](https://react.dev/) — JavaScript library
- [TypeScript](https://www.typescriptlang.org/docs/) — Type system

---

## Contributing

When adding new documentation:
1. Follow the structure of existing documents (sections, headers, code examples)
2. Include both ✅ correct and ❌ wrong examples
3. Link to related sections and external resources
4. Keep technical depth consistent with audience
5. Test code examples locally before documenting

---

**Last Updated:** 2026-04-03
**Maintained by:** Design & Development Team
