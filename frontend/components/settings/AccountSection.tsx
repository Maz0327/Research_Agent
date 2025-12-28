/**
 * Account settings section component.
 * Handles username, email display, and user info.
 */
import { User } from '@supabase/supabase-js';
import SettingsSection from './SettingsSection';

interface AccountSectionProps {
  user: User | null;
  username: string;
  setUsername: (value: string) => void;
  isCheckingUsername: boolean;
  usernameCheck: { available: boolean; error?: string | null } | null;
  currentUsername?: string | null;
}

export function AccountSection({
  user,
  username,
  setUsername,
  isCheckingUsername,
  usernameCheck,
  currentUsername,
}: AccountSectionProps) {
  const handleUsernameChange = (value: string) => {
    // Only allow lowercase letters, numbers, and underscores
    setUsername(value.toLowerCase().replace(/[^a-z0-9_]/g, ''));
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <SettingsSection title="Account" delay={0.1}>
      <div className="space-y-4">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Username
          </label>
          <div className="mt-1.5 flex gap-2">
            <input
              type="text"
              value={username}
              onChange={(e) => handleUsernameChange(e.target.value)}
              placeholder="Choose a username"
              maxLength={30}
              className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            {isCheckingUsername && (
              <span className="flex items-center text-sm text-gray-500">
                <svg
                  className="animate-spin h-4 w-4 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Checking...
              </span>
            )}
          </div>
          {username.length >= 3 && usernameCheck && (
            <p
              className={`mt-1.5 text-sm ${
                usernameCheck.available ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {usernameCheck.available
                ? 'Username available'
                : usernameCheck.error || 'Username taken'}
            </p>
          )}
          {username.length > 0 && username.length < 3 && (
            <p className="mt-1.5 text-sm text-gray-500">
              Username must be at least 3 characters
            </p>
          )}
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Email
          </label>
          <p className="mt-1 text-gray-200">{user?.email || 'Not set'}</p>
        </div>

        {/* User ID */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            User ID
          </label>
          <p className="mt-1 font-mono text-sm text-gray-500">
            {user?.id || 'Not set'}
          </p>
        </div>

        {/* Last Sign In */}
        <div>
          <label className="block text-sm font-medium text-gray-400">
            Last Sign In
          </label>
          <p className="mt-1 text-gray-200">
            {user?.last_sign_in_at ? formatDate(user.last_sign_in_at) : 'Unknown'}
          </p>
        </div>
      </div>
    </SettingsSection>
  );
}

export default AccountSection;
