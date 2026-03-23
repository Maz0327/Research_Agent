'use client';

/**
 * UserManagementTable — mockup-aligned users table.
 * Columns: User (avatar + name + email) | Role | Jobs | Spend | Last Active
 * Avatar: colored circle with initials. Role badge: red for admin, gray for user.
 */
import { useEffect, useState } from 'react';
import { AlertCircle, Users } from 'lucide-react';
import { useAdminStore, type AdminUser } from '@/store/admin';

const AVATAR_COLORS = [
  'bg-blue-500/20 text-blue-400',
  'bg-purple-500/20 text-purple-400',
  'bg-green-500/20 text-green-400',
  'bg-orange-500/20 text-orange-400',
  'bg-pink-500/20 text-pink-400',
];

function initials(email: string): string {
  const parts = email.split('@')[0].split(/[._-]/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return email.slice(0, 2).toUpperCase();
}

function avatarColor(email: string): string {
  const idx = email.charCodeAt(0) % AVATAR_COLORS.length;
  return AVATAR_COLORS[idx];
}

function relativeTime(iso: string | null): string {
  if (!iso) return 'Never';
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  if (h < 1) return 'Now';
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function UserRow({ user, onBan, onUnban }: { user: AdminUser; onBan: () => Promise<void>; onUnban: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const inits = initials(user.email);
  const color = avatarColor(user.email);

  const handle = async (fn: () => Promise<void>) => {
    setBusy(true);
    try { await fn(); } finally { setBusy(false); }
  };

  return (
    <tr className="border-b border-border hover:bg-accent/30 transition-colors">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${color}`}>
            {inits}
          </div>
          <div>
            <p className="text-sm font-medium">{user.email.split('@')[0]}</p>
            <p className="text-[10px] text-muted-foreground">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        {user.is_admin ? (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 font-medium">Admin</span>
        ) : (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium">User</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-muted-foreground">{user.job_count}</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">—</td>
      <td className="px-4 py-3 text-xs text-muted-foreground">{relativeTime(user.last_sign_in_at)}</td>
      {!user.is_admin && (
        <td className="px-4 py-3">
          <button
            onClick={() => handle(user.is_banned ? onUnban : onBan)}
            disabled={busy}
            className={`text-[10px] transition-colors disabled:opacity-50 ${
              user.is_banned ? 'text-green-400 hover:text-green-300' : 'text-muted-foreground hover:text-red-400'
            }`}
          >
            {busy ? '…' : user.is_banned ? 'Unban' : 'Ban'}
          </button>
        </td>
      )}
      {user.is_admin && <td className="px-4 py-3" />}
    </tr>
  );
}

export function UserManagementTable() {
  const { users, isLoadingUsers, usersPage, totalUsers, pageSize, fetchUsers, banUser, unbanUser, error } = useAdminStore();
  const totalPages = Math.ceil(totalUsers / pageSize);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  if (error && !isLoadingUsers && users.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center p-6">
        <AlertCircle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm font-medium text-foreground">Failed to load users</p>
        <p className="text-xs text-muted-foreground mt-1">{error}</p>
        <button
          onClick={() => fetchUsers()}
          className="mt-4 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (isLoadingUsers && users.length === 0) {
    return (
      <div className="p-6 space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 rounded-lg bg-muted motion-safe:animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold">Users</h1>
        <button className="px-3 py-1.5 rounded-lg text-xs bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors">
          Invite User
        </button>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              {['User', 'Role', 'Jobs', 'Spend', 'Last Active', ''].map((h) => (
                <th key={h} className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoadingUsers ? (
              [...Array(3)].map((_, i) => (
                <tr key={i} className="border-b border-border">
                  {[...Array(6)].map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-3 rounded bg-muted motion-safe:animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <Users className="h-8 w-8 text-muted-foreground/40 mb-3" />
                    <p className="text-sm text-muted-foreground">No users found</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">Users will appear here when they sign up</p>
                  </div>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <UserRow
                  key={user.id}
                  user={user}
                  onBan={() => banUser(user.id)}
                  onUnban={() => unbanUser(user.id)}
                />
              ))
            )}
          </tbody>
        </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-border">
            <button
              onClick={() => fetchUsers(usersPage - 1)}
              disabled={usersPage === 1}
              className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-muted-foreground">Page {usersPage} of {totalPages}</span>
            <button
              onClick={() => fetchUsers(usersPage + 1)}
              disabled={usersPage === totalPages}
              className="text-xs px-3 py-1 rounded text-muted-foreground hover:bg-accent disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
