/**
 * Admin error logs viewer page.
 */
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import AdminLayout from '../../components/AdminLayout';
import { AdminProtectedRoute } from '../../components/AuthProvider';
import { useAdminStore, ErrorLog } from '../../store/admin';
import Skeleton from '../../components/ui/Skeleton';

const categoryColors: Record<string, string> = {
  api_error: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  memory: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  timeout: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  validation: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  auth: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  external_service: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
  database: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
};

function ErrorRow({ error, onResolve }: { error: ErrorLog; onResolve: () => Promise<void> }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isResolving, setIsResolving] = useState(false);

  const handleResolve = async () => {
    setIsResolving(true);
    try {
      await onResolve();
    } finally {
      setIsResolving(false);
    }
  };

  const categoryColor = categoryColors[error.error_category] || categoryColors.unknown;

  return (
    <>
      <motion.tr
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className={`border-b border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750 ${
          error.resolved ? 'opacity-60' : ''
        }`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <motion.svg
              className="h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              animate={{ rotate: isExpanded ? 90 : 0 }}
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </motion.svg>
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${categoryColor}`}>
              {error.error_category}
            </span>
          </div>
        </td>
        <td className="px-4 py-3 text-sm text-gray-900 dark:text-white max-w-xs truncate">
          {error.user_message}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
          {error.user_email || 'System'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
          {error.stage || '-'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
          {new Date(error.created_at).toLocaleString()}
        </td>
        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
          {error.resolved ? (
            <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Resolved
            </span>
          ) : (
            <button
              onClick={handleResolve}
              disabled={isResolving}
              className="rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-200 disabled:opacity-50 dark:bg-green-900/30 dark:text-green-300"
            >
              {isResolving ? '...' : 'Resolve'}
            </button>
          )}
        </td>
      </motion.tr>

      {/* Expanded details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.tr
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <td colSpan={6} className="bg-gray-50 px-4 py-4 dark:bg-gray-900">
              <div className="space-y-3">
                <div>
                  <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                    Technical Message
                  </h4>
                  <p className="mt-1 font-mono text-sm text-gray-900 dark:text-white break-all">
                    {error.technical_message}
                  </p>
                </div>

                {error.stack_trace && (
                  <div>
                    <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      Stack Trace
                    </h4>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-gray-800 p-3 font-mono text-xs text-gray-300">
                      {error.stack_trace}
                    </pre>
                  </div>
                )}

                {error.job_id && (
                  <div>
                    <h4 className="text-xs font-medium uppercase text-gray-500 dark:text-gray-400">
                      Related Job
                    </h4>
                    <a
                      href={`/jobs/${error.job_id}`}
                      className="mt-1 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
                    >
                      {error.job_id}
                    </a>
                  </div>
                )}
              </div>
            </td>
          </motion.tr>
        )}
      </AnimatePresence>
    </>
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

function AdminErrorsContent() {
  const router = useRouter();
  const {
    errorLogs,
    isLoadingErrors,
    errorsPage,
    totalErrors,
    pageSize,
    fetchErrorLogs,
    resolveError,
  } = useAdminStore();

  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [resolvedFilter, setResolvedFilter] = useState<string>(
    router.query.resolved === 'false' ? 'false' : ''
  );

  useEffect(() => {
    const filters: { category?: string; resolved?: boolean } = {};
    if (categoryFilter) filters.category = categoryFilter;
    if (resolvedFilter) filters.resolved = resolvedFilter === 'true';
    fetchErrorLogs(1, filters);
  }, [fetchErrorLogs, categoryFilter, resolvedFilter]);

  const handlePageChange = (page: number) => {
    const filters: { category?: string; resolved?: boolean } = {};
    if (categoryFilter) filters.category = categoryFilter;
    if (resolvedFilter) filters.resolved = resolvedFilter === 'true';
    fetchErrorLogs(page, filters);
  };

  const totalPages = Math.ceil(totalErrors / pageSize);

  return (
    <AdminLayout title="Error Logs">
      {/* Filters */}
      <div className="mb-4 flex gap-4">
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">All Categories</option>
          <option value="api_error">API Error</option>
          <option value="memory">Memory</option>
          <option value="timeout">Timeout</option>
          <option value="validation">Validation</option>
          <option value="auth">Auth</option>
          <option value="external_service">External Service</option>
          <option value="database">Database</option>
          <option value="unknown">Unknown</option>
        </select>

        <select
          value={resolvedFilter}
          onChange={(e) => setResolvedFilter(e.target.value)}
          className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">All Status</option>
          <option value="false">Unresolved</option>
          <option value="true">Resolved</option>
        </select>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Category
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Message
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  User
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Stage
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Time
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoadingErrors ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3"><Skeleton height={20} width="80px" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="80%" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="60%" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="50%" /></td>
                    <td className="px-4 py-3"><Skeleton height={16} width="70%" /></td>
                    <td className="px-4 py-3"><Skeleton height={24} width="60px" /></td>
                  </tr>
                ))
              ) : errorLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    No error logs found
                  </td>
                </tr>
              ) : (
                errorLogs.map((error) => (
                  <ErrorRow
                    key={error.id}
                    error={error}
                    onResolve={() => resolveError(error.id)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        <Pagination currentPage={errorsPage} totalPages={totalPages} onPageChange={handlePageChange} />
      </div>

      <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
        Total: {totalErrors} errors
      </p>
    </AdminLayout>
  );
}

export default function AdminErrorsPage() {
  return (
    <AdminProtectedRoute>
      <AdminErrorsContent />
    </AdminProtectedRoute>
  );
}
