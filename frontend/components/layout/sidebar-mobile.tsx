'use client';

/**
 * SidebarMobile — Sheet-based sidebar for mobile (<md breakpoint).
 * Hamburger button triggers a left-side Sheet containing SidebarNav.
 * Auto-closes when pathname changes (navigation event).
 */

import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { Menu, Plus } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { SidebarNav } from './sidebar-nav';
import { UserMenu } from './user-menu';

interface SidebarMobileProps {
  email?: string | null;
  showAdmin?: boolean;
  onSignOut?: () => void;
}

export function SidebarMobile({
  email,
  showAdmin = false,
  onSignOut,
}: SidebarMobileProps) {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close sheet on navigation
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <button
          className="p-3 text-muted-foreground hover:text-foreground transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </SheetTrigger>

      <SheetContent side="left" className="w-56 p-0 bg-background border-border flex flex-col">
        <SheetHeader className="flex h-14 flex-row items-center px-4 border-b border-border space-y-0">
          <SheetTitle asChild>
            <Link
              href="/dashboard"
              className="flex items-center gap-3 min-w-0"
              onClick={() => setOpen(false)}
            >
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
              <span className="text-sm font-semibold tracking-tight">
                Research Agent
              </span>
            </Link>
          </SheetTitle>
        </SheetHeader>

        {/* Nav */}
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <SidebarNav
            showAdmin={showAdmin}
            onNavigate={() => setOpen(false)}
          />
        </div>

        {/* Bottom */}
        <div className="flex flex-col gap-2 p-3 border-t border-border flex-shrink-0">
          <Button
            asChild
            size="sm"
            className="w-full bg-gradient-to-r from-accent-blue to-accent-purple hover:opacity-90 text-white transition-opacity"
          >
            <Link href="/queue/new" onClick={() => setOpen(false)}>
              <Plus className="mr-1.5 h-4 w-4" aria-hidden="true" />
              New Research
            </Link>
          </Button>

          <Separator />

          <UserMenu email={email} onSignOut={onSignOut} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
