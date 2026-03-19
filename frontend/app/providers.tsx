'use client';

/**
 * Client-side providers for the App Router root layout.
 * Only includes providers that are App Router–compatible:
 * - ThemeProvider (next-themes): dark mode class on <html>
 * - QueryClientProvider (TanStack Query): data fetching
 *
 * NOTE: AuthProvider and ErrorBoundary are NOT included here.
 * - AuthProvider uses next/router (Pages Router only) — incompatible with App Router.
 *   App Router pages handle auth via server components + Supabase server client (Phase 3+).
 * - ErrorBoundary is a class component; App Router uses app/error.tsx for the same purpose.
 * Both continue to work in pages/ via pages/_app.tsx unchanged.
 */

import { useState } from 'react';
import { ThemeProvider } from 'next-themes';
import { QueryClientProvider } from '@tanstack/react-query';
import { makeQueryClient } from '@/lib/query-client';

interface ProvidersProps {
  children: React.ReactNode;
}

export default function Providers({ children }: ProvidersProps) {
  // useState ensures QueryClient is created once per component lifecycle,
  // not recreated on every render, while staying SSR-safe.
  const [queryClient] = useState(() => makeQueryClient());

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    </ThemeProvider>
  );
}
