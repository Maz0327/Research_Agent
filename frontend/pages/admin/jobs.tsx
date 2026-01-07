/**
 * Admin jobs management page.
 */
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { motion } from 'framer-motion';
import AdminLayout from '../../components/AdminLayout';
import { AdminProtectedRoute, useAuth } from '../../components/AuthProvider';
import { useAdminStore, AdminJob } from '../../store/admin';
import Skeleton from '../../components/ui/Skeleton';

const statusConfig: Record<string, { label: string; color: string }> = {
  queued: { label: 'Queued', color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
  running: { label: 'Running', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
  completed_with_warnings: { label: 'Completed (Warnings)', color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300' },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
  failed_insufficient: { label: 'Insufficient Data', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  cancelled: { label: 'Cancelled', color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
};

function JobRow({
  job,
  onCancel,
  onDelete,
}: {
  job: AdminJob;
  onCancel: () => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [isLoading, setIsLoading] = useState<'cancel' | 'delete' | null>(null);

  const handleAction = async (action: () => Promise<void>, type: 'cancel' | 'delete') => {
    if (type === 'delete' && !confirm('Are you sure you want to delete this job?')) return;
    setIsLoading(type);
    try {
      await action();
    } finally {
      setIsLoading(null);
    }
  };

  const config = statusConfig[job.status] || statusConfig.queued;

  return (
    <motion.tr
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="border-b border-gray-200 dark:border-gray-700"
    >
      <td className="px-4 py-3">
        <Link href={`/jobs/${job.id}`} className="font-medium text-blue-600 hover:underline dark:text-blue-400">
          {job.prompt.length > 50 ? job.prompt.slice(0, 50) + '...' : job.prompt}
        </Link>
        <p className="text-xs text-gray-500 dark:text-gray-400">ID: {job.id.slice(0, 8)}...</p>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {job.user_email}
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {job.progress_percent}%
      </td>
      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
        {new Date(job.created_at).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          {(job.status === 'running' || job.status === 'queued') && (
            <button
              onClick={() => handleAction(onCancel, 'cancel')}
              disabled={isLoading !== null}
              className="rounded bg-orange-100 px-2 py-1 text-xs font-medium text-orange-700 hover:bg-orange-200 disabled:opacity-50 dark:bg-orange-900/30 dark:text-orange-300"
            >
              {isLoading === 'cancel' ? '...' : 'Cancel'}
            </button>
          )}
          <button
            onClick={() => handleAction(onDelete, 'delete')}
            disabled={isLoading !== null}
            className="rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-200 disabled:opacity-50 dark:bg-red-900/30 dark:text-red-300"
          >
            {isLoading === 'delete' ? '...' : 'Delete'}
          </button>
        </div>
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
    <div className="flex items-center justify-center gap-2 p-4">
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

function AdminJobsContent() {
  const router = useRouter();
  const { user, isAdmin } = useAuth();
  const {
    jobs,
    isLoadingJobs,
    jobsPage,
    totalJobs,
    pageSize,
    fetchJobs,
    cancelJob,
    deleteJob,
  } = useAdminStore();

  const [statusFilter, setStatusFilter] = useState<string>(
    (router.query.status as string) || ''
  );

  // Gate data fetching on auth completion
  useEffect(() => {
    if (user && isAdmin) {
      fetchJobs(1, { status: statusFilter || undefined });
    }
  }, [fetchJobs, statusFilter, user, isAdmin]);

  const handlePageChange = (page: number) => {
    fetchJobs(page, { status: statusFilter || undefined });
  };

  const totalPages = Math.ceil(totalJobs / pageSize);

  return (
    <AdminLayout title="Jobs">
      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="completed_with_warnings">Completed (Warnings)</option>
          <option value="failed">Failed</option>
          <option value="failed_insufficient">Insufficient Data</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Job
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Progress
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Created
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoadingJobs ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3"><Skeleton height={20} width="80%" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="60%" /></td>
                    <td className="px-4 py-3"><Skeleton height={20} width="60px" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="40%" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="70%" /></td>
                    <td className="px-4 py-3"><Skeleton height={24} width="80px" /></td>
                  </tr>
                ))
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    No jobs found
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <JobRow
                    key={job.id}
                    job={job}
                    onCancel={() => cancelJob(job.id)}
                    onDelete={() => deleteJob(job.id)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        <Pagination currentPage={jobsPage} totalPages={totalPages} onPageChange={handlePageChange} />
      </div>

      <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        Total: {totalJobs} jobs
      </p>
    </AdminLayout>
  );
}

export default function AdminJobsPage() {
  return (
    <AdminProtectedRoute>
      <AdminJobsContent />
    </AdminProtectedRoute>
  );
}
