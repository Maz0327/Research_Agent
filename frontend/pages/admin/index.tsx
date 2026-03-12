/**
 * Admin dashboard with system statistics.
 */
import { useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import AdminLayout from '../../components/AdminLayout';
import { AdminProtectedRoute, useAuth } from '../../components/AuthProvider';
import { useAdminStore } from '../../store/admin';
import Skeleton from '../../components/ui/Skeleton';

function StatCard({
  label,
  value,
  icon,
  color,
  href,
}: {
  label: string;
  value: number | string;
  icon: JSX.Element;
  color: string;
  href?: string;
}) {
  const content = (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border p-6 ${color} transition-shadow hover:shadow-md`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-400">{label}</p>
          <p className="mt-1 text-3xl font-bold text-white">{value}</p>
        </div>
        <div className="rounded-full bg-gray-800/80 p-3">{icon}</div>
      </div>
    </motion.div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

function AdminDashboardContent() {
  const { stats, isLoadingStats, fetchStats } = useAdminStore();
  const { user, isAdmin } = useAuth();

  // Gate data fetching on auth completion
  useEffect(() => {
    if (user && isAdmin) {
      fetchStats();
    }
  }, [fetchStats, user, isAdmin]);

  const statCards = [
    {
      label: 'Total Users',
      value: stats?.total_users ?? '-',
      icon: (
        <svg className="h-8 w-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ),
      color: 'border-blue-800 bg-blue-900/20',
      href: '/admin/users',
    },
    {
      label: 'Total Jobs',
      value: stats?.total_jobs ?? '-',
      icon: (
        <svg className="h-8 w-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
      color: 'border-green-800 bg-green-900/20',
      href: '/admin/jobs',
    },
    {
      label: 'Jobs Today',
      value: stats?.jobs_today ?? '-',
      icon: (
        <svg className="h-8 w-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      color: 'border-purple-800 bg-purple-900/20',
    },
    {
      label: 'Running Now',
      value: stats?.jobs_running ?? '-',
      icon: (
        <svg className="h-8 w-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
      color: 'border-yellow-800 bg-yellow-900/20',
    },
    {
      label: 'Failed Today',
      value: stats?.jobs_failed_today ?? '-',
      icon: (
        <svg className="h-8 w-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      color: 'border-red-800 bg-red-900/20',
    },
    {
      label: 'Unresolved Errors',
      value: stats?.unresolved_errors ?? '-',
      icon: (
        <svg className="h-8 w-8 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: 'border-orange-800 bg-orange-900/20',
      href: '/admin/errors',
    },
  ];

  return (
    <AdminLayout title="Dashboard">
      {isLoadingStats ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="rounded-lg border border-gray-700 bg-gray-800 p-6">
              <Skeleton height={16} width="40%" className="mb-2" />
              <Skeleton height={36} width="60%" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {statCards.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      )}

      {/* Quick actions */}
      <div className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-white">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/admin/jobs?status=running"
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            View Running Jobs
          </Link>
          <Link
            href="/admin/errors?resolved=false"
            className="inline-flex items-center gap-2 rounded-md bg-orange-600 px-4 py-2 text-sm font-medium text-white hover:bg-orange-700"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            View Unresolved Errors
          </Link>
        </div>
      </div>
    </AdminLayout>
  );
}

export default function AdminDashboardPage() {
  return (
    <AdminProtectedRoute>
      <AdminDashboardContent />
    </AdminProtectedRoute>
  );
}
