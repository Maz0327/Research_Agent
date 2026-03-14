/**
 * JobDetailHeader - Header component for job detail page
 * Shows back navigation, title, status, and action buttons.
 */
import Link from 'next/link';
import { StatusBadge } from '../job-card/StatusBadge';
import type { JobStatus } from '../job-card/job-card-config';
import { formatRelativeTime } from '../../lib/time-utils';

export interface JobDetailHeaderProps {
  /** Job ID */
  jobId: string;
  /** Job title (AI-generated or prompt snippet) */
  title: string;
  /** Current job status */
  status: JobStatus;
  /** Job creation timestamp (ISO format) */
  createdAt: string;
  /** Archive button handler */
  onArchive: () => void;
  /** Delete button handler */
  onDelete: () => void;
  /** Whether actions are disabled */
  actionsDisabled?: boolean;
}

export function JobDetailHeader({
  jobId,
  title,
  status,
  createdAt,
  onArchive,
  onDelete,
  actionsDisabled = false,
}: JobDetailHeaderProps) {
  return (
    <header className="border-b border-gray-800 pb-4 sm:pb-6 mb-4 sm:mb-6">
      {/* Back navigation */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-3 sm:mb-4 transition-colors min-h-[44px] touch-manipulation"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span className="text-sm sm:text-base">Back to Dashboard</span>
      </Link>

      {/* Title row */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold text-white truncate" title={title}>
            {title || 'Untitled Job'}
          </h1>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 mt-1.5 sm:mt-2">
            <StatusBadge status={status} />
            <span className="text-xs sm:text-sm text-gray-400">
              Created {formatRelativeTime(createdAt)}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={onArchive}
            disabled={actionsDisabled}
            className="px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[40px] touch-manipulation"
          >
            Archive
          </button>
          <button
            onClick={onDelete}
            disabled={actionsDisabled}
            className="px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[40px] touch-manipulation"
          >
            Delete
          </button>
        </div>
      </div>
    </header>
  );
}

export default JobDetailHeader;
