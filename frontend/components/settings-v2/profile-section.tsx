'use client';

/**
 * ProfileSection — username input, email display (read-only).
 * Part of the settings-v2 module for App Router.
 */

interface ProfileSectionProps {
  userEmail: string | null;
  username: string;
  setUsername: (value: string) => void;
  isCheckingUsername: boolean;
  usernameCheck: { available: boolean; error?: string | null } | null;
  currentUsername?: string | null;
}

export function ProfileSection({
  userEmail,
  username,
  setUsername,
  isCheckingUsername,
  usernameCheck,
  currentUsername,
}: ProfileSectionProps) {
  const handleUsernameChange = (value: string) => {
    setUsername(value.toLowerCase().replace(/[^a-z0-9_]/g, ''));
  };

  return (
    <div className="rounded-xl border border-border bg-background p-6">
      <div className="flex items-center gap-2 mb-4">
        <svg className="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
        <h2 className="text-lg font-semibold text-foreground">Account</h2>
      </div>

      <div className="space-y-4">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1.5">Username</label>
          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={username}
              onChange={(e) => handleUsernameChange(e.target.value)}
              placeholder="Choose a username"
              maxLength={30}
              className="flex-1 rounded-lg border border-border bg-card px-4 py-2.5 text-sm text-foreground placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {isCheckingUsername && (
              <svg className="animate-spin h-4 w-4 text-muted-foreground/70" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
          </div>
          {username.length >= 3 && usernameCheck && !isCheckingUsername && (
            <p className={`mt-1.5 text-sm ${usernameCheck.available ? 'text-green-400' : 'text-red-400'}`}>
              {usernameCheck.available ? 'Username available' : usernameCheck.error || 'Username taken'}
            </p>
          )}
          {username.length > 0 && username.length < 3 && (
            <p className="mt-1.5 text-sm text-muted-foreground/70">Username must be at least 3 characters</p>
          )}
        </div>

        {/* Email (read-only) */}
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1.5">Email</label>
          <p className="text-foreground">{userEmail || 'Not set'}</p>
        </div>
      </div>
    </div>
  );
}
