'use client';

/**
 * AppShell — root layout wrapper for authenticated app pages.
 * Desktop: fixed sidebar (w-56) + scrollable main content area.
 * Mobile: top header bar (hamburger + logo + avatar) + Sheet sidebar.
 */

import Link from 'next/link';
import { Sidebar } from './sidebar';
import { SidebarMobile } from './sidebar-mobile';
import { UserMenu } from './user-menu';

interface AppShellProps {
  children: React.ReactNode;
  /** User email for sidebar UserMenu */
  email?: string | null;
  /** Show admin nav section */
  showAdmin?: boolean;
  /** Called on sign out */
  onSignOut?: () => void;
}

export function AppShell({
  children,
  email,
  showAdmin = false,
  onSignOut,
}: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar — hidden below md */}
      <Sidebar email={email} showAdmin={showAdmin} onSignOut={onSignOut} />

      {/* Right side: mobile header + main content */}
      <div className="flex flex-1 flex-col md:ml-56">
        {/* Mobile top header — visible below md only */}
        <header className="flex md:hidden h-14 items-center justify-between px-4 border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-20">
          <SidebarMobile
            email={email}
            showAdmin={showAdmin}
            onSignOut={onSignOut}
          />

          <Link
            href="/dashboard"
            className="text-sm font-bold bg-gradient-to-r from-accent-blue to-accent-purple bg-clip-text text-transparent"
          >
            Research Agent
          </Link>

          {/* Avatar shortcut on mobile header */}
          <div className="w-8">
            <UserMenu email={email} onSignOut={onSignOut} />
          </div>
        </header>

        {/* Main content area */}
        <main
          id="main-content"
          className="flex-1 overflow-auto"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
