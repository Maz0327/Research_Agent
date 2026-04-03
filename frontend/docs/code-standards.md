# Frontend Code Standards

**Version:** 1.0.0
**Last Updated:** 2026-04-03
**Scope:** React/Next.js frontend application

---

## Overview

This document defines code standards specific to the frontend application. Combined with the design system documentation (`design-system.md`), it ensures consistent, maintainable, and accessible code across all React components.

---

## 1. File & Naming Conventions

### File Naming
```
Components:   PascalCase.tsx          (MyComponent.tsx)
Hooks:        kebab-case.ts           (use-pagination.ts)
Utils:        kebab-case.ts           (format-date.ts)
Types:        kebab-case.ts           (api-response.ts)
Styles:       kebab-case.module.css   (card-styles.module.css)
Tests:        [name].test.tsx         (MyComponent.test.tsx)
```

### Directory Structure
```
frontend/
├── app/                    # Next.js app directory
│   ├── (dashboard)/       # Route groups
│   ├── api/               # API routes
│   └── providers.tsx      # Global providers
├── components/
│   ├── ui/                # shadcn components
│   └── [feature]/         # Feature components
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities & helpers
├── types/                 # TypeScript definitions
├── public/                # Static assets
└── docs/                  # Documentation
```

---

## 2. TypeScript & Type Safety

### Type Hints Required
All functions must have complete type hints:

```tsx
// ✅ Correct
interface JobFormProps {
  onSubmit: (data: JobInput) => Promise<void>;
  isLoading?: boolean;
}

export function JobForm({ onSubmit, isLoading = false }: JobFormProps) {
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await onSubmit(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  return <form onSubmit={handleSubmit}>...</form>;
}

// ❌ Wrong: Missing type hints
export function JobForm({ onSubmit, isLoading }) {
  const [error, setError] = useState(null);
  // ...
}
```

### Props Interface Pattern
Always define Props as a separate interface:

```tsx
interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  onClose?: () => void;
}

export function Alert({ title, message, severity, onClose, ...props }: AlertProps) {
  return <div {...props}>{message}</div>;
}
```

### Avoid `any`
Never use `any` type — use `unknown` and type-guard instead:

```tsx
// ❌ Wrong
const handleResponse = (data: any) => {
  return data.results;
};

// ✅ Correct
const handleResponse = (data: unknown) => {
  if (typeof data === 'object' && data !== null && 'results' in data) {
    return (data as { results: unknown }).results;
  }
  throw new Error('Invalid response format');
};
```

---

## 3. Component Structure

### Functional Components Only
Always use functional components with hooks:

```tsx
interface CardProps {
  title: string;
  children: React.ReactNode;
}

export function Card({ title, children }: CardProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleToggle = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <button
        onClick={handleToggle}
        className="text-lg font-semibold text-foreground"
        aria-expanded={isOpen}
      >
        {title}
      </button>
      {isOpen && <div className="mt-4">{children}</div>}
    </div>
  );
}
```

### Hook Usage Order
Hooks should follow this order:
1. State (`useState`)
2. Side effects (`useEffect`)
3. Callbacks (`useCallback`, `useMemo`)
4. Refs (`useRef`)
5. Context (`useContext`)

```tsx
export function MyComponent() {
  // 1. State
  const [count, setCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  // 2. Effects
  useEffect(() => {
    // Setup
    return () => {
      // Cleanup
    };
  }, [count]);

  // 3. Callbacks
  const handleIncrement = useCallback(() => {
    setCount(prev => prev + 1);
  }, []);

  // 4. Render
  return <button onClick={handleIncrement}>{count}</button>;
}
```

### Avoid Large Components
Keep components under 150 lines. If longer, extract sub-components:

```tsx
// ❌ Too large
export function Dashboard() {
  // 200+ lines of JSX
  return <div>...</div>;
}

// ✅ Better: Split into smaller components
export function Dashboard() {
  return (
    <div className="space-y-6">
      <DashboardHeader />
      <JobsList />
      <RecentActivity />
      <SettingsPanel />
    </div>
  );
}
```

---

## 4. Styling

### Tailwind Classes Only
Use Tailwind utility classes — never CSS-in-JS or inline styles:

```tsx
// ✅ Correct
<div className="flex items-center gap-4 rounded-lg bg-card p-4 text-foreground">
  <span>Content</span>
</div>

// ❌ Wrong: Inline styles
<div style={{ display: 'flex', gap: '16px', backgroundColor: '#1a1a1a' }}>
  <span>Content</span>
</div>

// ❌ Wrong: CSS-in-JS
const styles = css`
  display: flex;
  gap: 16px;
`;
```

### CSS Variables for Colors
Never hardcode color hex values — use CSS variables:

```tsx
// ✅ Correct
<div className="bg-card text-foreground border-border">Content</div>

// ❌ Wrong: Hardcoded colors
<div className="bg-[#1a1a1a] text-[#f5f5f5] border-[#333333]">Content</div>
```

### Responsive Design
Use Tailwind breakpoints (mobile-first):

```tsx
// ✅ Mobile-first approach
<div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
  {items.map(item => <Card key={item.id}>{item.name}</Card>)}
</div>

// ❌ Wrong: Desktop-first
<div className="grid grid-cols-3 lg:grid-cols-1">
  {/* Confusing breakpoint logic */}
</div>
```

---

## 5. Hooks & Custom Hooks

### Custom Hook Naming
Custom hooks must start with `use`:

```tsx
// ✅ Correct
export function usePagination(items: unknown[], pageSize: number) {
  const [page, setPage] = useState(1);
  const start = (page - 1) * pageSize;
  return {
    page,
    setPage,
    paginatedItems: items.slice(start, start + pageSize),
  };
}

// ❌ Wrong: Doesn't follow hook naming
export function pagination(items: unknown[], pageSize: number) {
  // ...
}
```

### Hook Documentation
Document custom hooks with JSDoc:

```tsx
/**
 * Manages pagination state and returns paginated items.
 *
 * @param items - Array of items to paginate
 * @param pageSize - Number of items per page
 * @returns Object with pagination state and utilities
 *
 * @example
 * const { page, setPage, paginatedItems } = usePagination(jobs, 10);
 */
export function usePagination<T>(items: T[], pageSize: number) {
  // Implementation
}
```

### useCallback for Event Handlers
Use `useCallback` for handlers passed to child components:

```tsx
// ✅ Correct
const handleDelete = useCallback((id: string) => {
  setItems(prev => prev.filter(item => item.id !== id));
}, []);

return <ItemList onDelete={handleDelete} />;

// ❌ Wrong: New function reference on every render
return <ItemList onDelete={(id) => setItems(...)} />;
```

---

## 6. Error Handling

### Try-Catch with Typed Errors
Always handle errors gracefully:

```tsx
const handleSubmit = async (data: FormData) => {
  try {
    setError(null);
    const response = await fetch('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    setSuccess(true);
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    setError(message);
  }
};
```

### Error Boundaries
Wrap major sections with error boundaries:

```tsx
// app/layout.tsx
<ErrorBoundary>
  <DashboardContent />
</ErrorBoundary>
```

---

## 7. API Communication

### Typed API Calls
Define types for all API requests/responses:

```tsx
// types/job.ts
export interface JobInput {
  title: string;
  sources: string[];
}

export interface JobResponse {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  createdAt: string;
}

// lib/api.ts
export async function createJob(input: JobInput): Promise<JobResponse> {
  const response = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.status}`);
  }

  return response.json();
}
```

### Loading States
Always handle loading and error states:

```tsx
export function JobForm() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: FormData) => {
    setIsLoading(true);
    setError(null);

    try {
      await createJob(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <Alert severity="error">{error}</Alert>}
      <Button disabled={isLoading}>
        {isLoading && <Spinner size="sm" />}
        {isLoading ? 'Loading...' : 'Submit'}
      </Button>
    </form>
  );
}
```

---

## 8. Testing

### Test Structure
Place tests next to components:

```
components/
├── JobForm.tsx
├── JobForm.test.tsx
└── __tests__/
    └── JobForm.integration.test.tsx
```

### Testing Best Practices
```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { JobForm } from './JobForm';

describe('JobForm', () => {
  it('should submit form data', async () => {
    const handleSubmit = jest.fn();
    render(<JobForm onSubmit={handleSubmit} />);

    fireEvent.change(screen.getByLabelText('Title'), {
      target: { value: 'Test Job' },
    });

    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Test Job' })
      );
    });
  });

  it('should display error message on failure', async () => {
    const handleSubmit = jest.fn().mockRejectedValue(new Error('API error'));
    render(<JobForm onSubmit={handleSubmit} />);

    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(screen.getByText('API error')).toBeInTheDocument();
    });
  });
});
```

---

## 9. Commit Messages

Use conventional commits format:

```
feat(jobs): add job creation form
fix(dashboard): resolve loading state issue
docs(design-system): update component guidelines
refactor(api): simplify error handling
test(jobs): add form validation tests
chore: update dependencies
```

---

## 10. Code Review Checklist

Before submitting code for review:

- [ ] All TypeScript types are complete (no `any`)
- [ ] Props have a defined interface
- [ ] Components use Tailwind classes only (no inline styles)
- [ ] Colors use CSS variables only
- [ ] Buttons use shadcn Button
- [ ] Icons use Lucide React
- [ ] Loading states show Spinner
- [ ] Errors are handled and displayed
- [ ] Tests pass and cover happy/error paths
- [ ] No console errors or warnings
- [ ] Accessibility checks pass (a11y)
- [ ] Commit messages follow conventional format

---

## References

- **React Docs:** https://react.dev/
- **Next.js Docs:** https://nextjs.org/docs
- **Tailwind CSS:** https://tailwindcss.com/
- **shadcn Components:** https://ui.shadcn.com/
- **Lucide Icons:** https://lucide.dev/
- **TypeScript:** https://www.typescriptlang.org/docs/

---

## Changelog

### v1.0.0 (2026-04-03)
- Initial frontend code standards
- TypeScript guidelines
- Component structure patterns
- Tailwind styling conventions
- Hook usage standards
- Error handling patterns
- API communication guidelines
