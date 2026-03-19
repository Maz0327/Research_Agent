'use client';

/**
 * (app) route group layout — wraps all authenticated dashboard pages
 * with the AppShell (sidebar + mobile header).
 *
 * Auth state is managed by pages/ AuthProvider (incompatible with App Router).
 * For now the shell renders without a user object; Phase 3 will wire up
 * the Supabase server client to pass email as a prop.
 */

import { AppShell } from '@/components/layout/app-shell';

interface AppLayoutProps {
  children: React.ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <AppShell>
      {children}
    </AppShell>
  );
}
