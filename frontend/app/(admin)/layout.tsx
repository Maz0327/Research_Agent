'use client';

/**
 * (admin) route group layout — admin shell matching 08-admin.html mockup.
 * Header: shield icon + "Admin Panel" + red "Admin" badge + "Back to Dashboard".
 * Sidebar: Jobs / Users / Errors tabs with active highlight and error count badge.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Shield, Briefcase, Users, AlertTriangle } from 'lucide-react';
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

function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-48 border-r border-border min-h-[calc(100vh-3.5rem)] p-3 flex flex-col gap-1 flex-shrink-0">
      {NAV.map(({ href, label, icon: Icon, badge }) => {
        const isActive = pathname === href || pathname?.startsWith(href + '/');
        return (
          <Link
            key={href}
            href={href}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border',
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
    </aside>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="flex items-center justify-between px-6 h-14">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-white" aria-hidden="true" />
            </div>
            <span className="text-sm font-semibold">Admin Panel</span>
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-red-500/10 text-red-400">
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
