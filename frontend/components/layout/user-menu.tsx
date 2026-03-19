'use client';

/**
 * UserMenu — avatar with dropdown for theme toggle and logout.
 * Reads user from Supabase auth context (pages/ AuthProvider is incompatible
 * with App Router; we read the session via a simple hook or prop here).
 */

import { useTheme } from 'next-themes';
import { LogOut, Sun, Moon } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface UserMenuProps {
  /** User email or display name — used to derive initials */
  email?: string | null;
  /** Called on logout click */
  onSignOut?: () => void;
}

/** Derive 1–2 letter initials from email or name string */
function getInitials(email?: string | null): string {
  if (!email) return 'U';
  const local = email.split('@')[0];
  const parts = local.split(/[._-]/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return local.slice(0, 2).toUpperCase();
}

export function UserMenu({ email, onSignOut }: UserMenuProps) {
  const { theme, setTheme } = useTheme();
  const initials = getInitials(email);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex items-center gap-2 rounded-lg px-2 py-1.5 w-full hover:bg-surface-hover transition-colors"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8 flex-shrink-0">
            <AvatarFallback className="bg-surface-3 border border-border text-xs font-semibold text-muted-foreground">
              {initials}
            </AvatarFallback>
          </Avatar>
          <span className="flex-1 truncate text-left text-sm text-muted-foreground">
            {email ?? 'User'}
          </span>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" side="top" className="w-48">
        <DropdownMenuItem
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        >
          {theme === 'dark' ? (
            <Sun className="mr-2 h-4 w-4" aria-hidden="true" />
          ) : (
            <Moon className="mr-2 h-4 w-4" aria-hidden="true" />
          )}
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={onSignOut}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
