'use client';

/**
 * Sidebar — desktop fixed sidebar (w-56, hidden below md breakpoint).
 * Contains: logo, SidebarNav (scrollable), "New Research" CTA, UserMenu.
 */

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { SidebarNav } from './sidebar-nav';
import { UserMenu } from './user-menu';
import { ThemeToggleButton } from './theme-toggle-button';

interface SidebarProps {
  /** User email for UserMenu initials */
  email?: string | null;
  /** Show admin nav section */
  showAdmin?: boolean;
  /** Called on logout */
  onSignOut?: () => void;
}

export function Sidebar({ email, showAdmin = false, onSignOut }: SidebarProps) {
  return (
    <aside
      className="hidden md:flex flex-col fixed inset-y-0 left-0 z-30 w-56 border-r border-border bg-surface-0"
      aria-label="Sidebar navigation"
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 px-4 border-b border-border flex-shrink-0">
        <Link href="/dashboard" className="flex items-center gap-3 min-w-0">
          <div className="flex h-8 w-8 flex-shrink-0 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple items-center justify-center">
            <svg
              className="h-4 w-4 text-white"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 14.5"
              />
            </svg>
          </div>
          <span className="text-sm font-semibold tracking-tight truncate">
            Research Agent
          </span>
        </Link>
      </div>

      {/* Nav — scrollable */}
      <ScrollArea className="flex-1 px-3 py-3">
        <SidebarNav showAdmin={showAdmin} />
      </ScrollArea>

      {/* Bottom section */}
      <div className="flex flex-col gap-2 p-3 border-t border-border flex-shrink-0">
        <Button
          asChild
          size="sm"
          className="w-full bg-gradient-to-r from-accent-blue to-accent-purple hover:opacity-90 text-white transition-opacity"
        >
          <Link href="/queue/new">
            <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
            New Research
          </Link>
        </Button>

        <Separator />

        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0">
            <UserMenu email={email} onSignOut={onSignOut} />
          </div>
          <ThemeToggleButton />
        </div>
      </div>
    </aside>
  );
}
