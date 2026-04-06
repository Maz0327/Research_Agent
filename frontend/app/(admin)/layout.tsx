'use client';

/**
 * (admin) route group layout — admin shell matching 08-admin.html mockup.
 * Desktop: fixed sidebar (w-48) with Jobs / Users / Errors nav.
 * Mobile: top header with hamburger Sheet, sidebar hidden.
 */

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Shield, Briefcase, Users, AlertTriangle, Menu, X } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

const NAV: NavItem[] = [
  { href: '/admin/jobs',   label: 'Jobs',   icon: Briefcase },
  { href: '/admin/users',  label: 'Users',  icon: Users },
  { href: '/admin/errors', label: 'Errors', icon: AlertTriangle, badge: 3 },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {NAV.map(({ href, label, icon: Icon, badge }) => {
        const isActive = pathname === href || pathname?.startsWith(href + '/');
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border min-h-[44px]',
              isActive
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                : 'text-muted-foreground hover:bg-accent border-transparent'
            )}
          >
            <Icon className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span>{label}</span>
            {badge && (
              <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded-full bg-red-500 text-white font-bold">
                {badge}
              </span>
            )}
          </Link>
        );
      })}
    </>
  );
}

function AdminSidebar() {
  return (
    <aside className="hidden md:flex w-48 border-r border-border min-h-[calc(100vh-3.5rem)] p-3 flex-col gap-1 flex-shrink-0">
      <NavLinks />
    </aside>
  );
}

function MobileAdminHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="md:hidden sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="flex items-center justify-between px-4 h-14">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <button
              className="flex items-center justify-center w-11 h-11 rounded-lg text-muted-foreground hover:bg-accent transition-colors"
              aria-label="Open admin navigation"
            >
              {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </SheetTrigger>
          <SheetContent side="left" className="w-56 p-3 flex flex-col gap-1 pt-14">
            <NavLinks onNavigate={() => setOpen(false)} />
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center flex-shrink-0">
            <Shield className="w-3.5 h-3.5 text-white" aria-hidden="true" />
          </div>
          <span className="text-sm font-semibold">Admin Panel</span>
          <span className="text-caption font-medium px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
            Admin
          </span>
        </div>

        <Link
          href="/dashboard"
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Dashboard
        </Link>
      </div>
    </header>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Desktop header */}
      <header className="hidden md:block sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-white" aria-hidden="true" />
            </div>
            <span className="text-sm font-semibold">Admin Panel</span>
            <span className="text-caption font-medium px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
              Admin
            </span>
          </div>
          <Link
            href="/dashboard"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Back to Dashboard
          </Link>
        </div>
      </header>

      {/* Mobile header */}
      <MobileAdminHeader />

      {/* Body */}
      <div className="flex flex-1">
        <AdminSidebar />
        <main id="main-content" className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
