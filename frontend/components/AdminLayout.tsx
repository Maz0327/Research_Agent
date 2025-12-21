/**
 * Admin layout component with navigation sidebar.
 */
import { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from './Layout';

interface AdminLayoutProps {
  children: ReactNode;
  title: string;
}

const adminNavItems = [
  { href: '/admin', label: 'Dashboard', icon: 'chart' },
  { href: '/admin/users', label: 'Users', icon: 'users' },
  { href: '/admin/jobs', label: 'Jobs', icon: 'briefcase' },
  { href: '/admin/errors', label: 'Error Logs', icon: 'alert' },
];

const icons: Record<string, JSX.Element> = {
  chart: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  users: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
  briefcase: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  alert: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
};

export default function AdminLayout({ children, title }: AdminLayoutProps) {
  const router = useRouter();

  return (
    <Layout>
      <div className="flex gap-6">
        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0">
          <nav className="sticky top-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Admin Panel
            </h2>
            <ul className="space-y-1">
              {adminNavItems.map((item) => {
                const isActive = router.pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                          : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
                      }`}
                    >
                      {icons[item.icon]}
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>

            <div className="mt-6 border-t border-gray-200 pt-4 dark:border-gray-700">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to App
              </Link>
            </div>
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0">
          <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
          {children}
        </main>
      </div>
    </Layout>
  );
}
