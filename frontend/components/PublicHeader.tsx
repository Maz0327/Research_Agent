/**
 * Public header component for landing and login pages.
 * Provides navigation and branding for unauthenticated users.
 */
import Link from 'next/link';

interface PublicHeaderProps {
  showHomeLink?: boolean;
}

export function PublicHeader({ showHomeLink = false }: PublicHeaderProps) {
  return (
    <header role="banner" className="relative z-10 border-b border-gray-800/50">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8"
      >
        <Link
          href="/"
          className="flex items-center gap-2 text-xl font-bold text-gray-100 transition-colors hover:text-blue-400"
        >
          <svg
            className="h-8 w-8 text-blue-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <span>Research Agent</span>
        </Link>

        <div className="flex items-center gap-4">
          {showHomeLink && (
            <Link
              href="/"
              className="text-sm font-medium text-gray-400 transition-colors hover:text-gray-100"
            >
              Home
            </Link>
          )}
          <Link
            href="/login"
            className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-gray-200 transition-all duration-200 hover:bg-gray-700"
          >
            Sign In
          </Link>
        </div>
      </nav>
    </header>
  );
}

export default PublicHeader;
