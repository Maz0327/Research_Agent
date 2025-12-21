/**
 * Admin users management page.
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import AdminLayout from '../../components/AdminLayout';
import { AdminProtectedRoute } from '../../components/AuthProvider';
import { useAdminStore, AdminUser } from '../../store/admin';
import Skeleton from '../../components/ui/Skeleton';

function UserRow({ user, onBan, onUnban }: { user: AdminUser; onBan: () => Promise<void>; onUnban: () => Promise<void> }) {
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (action: () => Promise<void>) => {
    setIsLoading(true);
    try {
      await action();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="border-b border-gray-200 dark:border-gray-700"
    >
      <td className="px-4 py-3">
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{user.email}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">ID: {user.id.slice(0, 8)}...</p>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {new Date(user.created_at).toLocaleDateString()}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {user.last_sign_in_at ? new Date(user.last_sign_in_at).toLocaleDateString() : 'Never'}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{user.job_count}</td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          {user.is_admin && (
            <span className="inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
              Admin
            </span>
          )}
          {user.is_banned && (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
              Banned
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {!user.is_admin && (
          <button
            onClick={() => handleAction(user.is_banned ? onUnban : onBan)}
            disabled={isLoading}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
              user.is_banned
                ? 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300'
                : 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300'
            }`}
          >
            {isLoading ? '...' : user.is_banned ? 'Unban' : 'Ban'}
          </button>
        )}
      </td>
    </motion.tr>
  );
}

function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="rounded px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-700"
      >
        Previous
      </button>
      <span className="text-sm text-gray-600 dark:text-gray-400">
        Page {currentPage} of {totalPages}
      </span>
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="rounded px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50 dark:text-gray-400 dark:hover:bg-gray-700"
      >
        Next
      </button>
    </div>
  );
}

function AdminUsersContent() {
  const {
    users,
    isLoadingUsers,
    usersPage,
    totalUsers,
    pageSize,
    fetchUsers,
    banUser,
    unbanUser,
  } = useAdminStore();

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const totalPages = Math.ceil(totalUsers / pageSize);

  return (
    <AdminLayout title="Users">
      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Last Sign In
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Jobs
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoadingUsers ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">
                      <Skeleton height={20} width="80%" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton height={16} width="60%" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton height={16} width="60%" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton height={16} width="30%" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton height={20} width="50%" />
                    </td>
                    <td className="px-4 py-3">
                      <Skeleton height={24} width="60px" />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    No users found
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

        <Pagination currentPage={usersPage} totalPages={totalPages} onPageChange={fetchUsers} />
      </div>

      <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        Total: {totalUsers} users
      </p>
    </AdminLayout>
  );
}

export default function AdminUsersPage() {
  return (
    <AdminProtectedRoute>
      <AdminUsersContent />
    </AdminProtectedRoute>
  );
}
