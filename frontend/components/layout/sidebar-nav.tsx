'use client';

/**
 * SidebarNav — shared navigation link list used by both desktop Sidebar and mobile Sheet.
 * Uses usePathname() for active route highlighting.
 * Icons: lucide-react
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ListTodo,
  FileText,
  BarChart3,
  Settings,
  Shield,
} from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

const mainNavItems: NavItem[] = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/queue', label: 'Queue', icon: ListTodo },
  { href: '/transcripts', label: 'Transcripts', icon: FileText },
  { href: '/usage', label: 'Usage', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

const adminNavItems: NavItem[] = [
  { href: '/admin', label: 'Admin Dashboard', icon: Shield },
];

interface SidebarNavProps {
  /** Show admin section — controlled by caller based on user role */
  showAdmin?: boolean;
  /** Called after link click (used to close mobile Sheet) */
  onNavigate?: () => void;
}

/**
 * Nav link item — active state via pathname match.
 */
function NavLink({
  item,
  isActive,
  onNavigate,
}: {
  item: NavItem;
  isActive: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={isActive ? 'page' : undefined}
      onClick={onNavigate}
      className={cn(
        'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        isActive
          ? 'bg-accent-blue/10 text-accent-blue'
          : 'text-muted-foreground hover:bg-surface-hover hover:text-foreground'
      )}
    >
      <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
      <span>{item.label}</span>
    </Link>
  );
}

export function SidebarNav({ showAdmin = false, onNavigate }: SidebarNavProps) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-1" aria-label="Main navigation">
      {mainNavItems.map((item) => (
        <NavLink
          key={item.href}
          item={item}
          isActive={pathname === item.href || (pathname?.startsWith(item.href + '/') ?? false)}
          onNavigate={onNavigate}
        />
      ))}

      {showAdmin && (
        <>
          <Separator className="my-2" />
          <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Admin
          </p>
          {adminNavItems.map((item) => (
            <NavLink
              key={item.href}
              item={item}
              isActive={pathname === item.href || (pathname?.startsWith(item.href + '/') ?? false)}
              onNavigate={onNavigate}
            />
          ))}
        </>
      )}
    </nav>
  );
}
