/**
 * QuickActions - Compact inline actions for Level 1 (Quick View) expansion.
 * Provides essential actions without full expansion.
 */
import { useState, useCallback } from 'react';
import { JobStatus } from './job-card-config';
import { useJobsStore } from '../../store/jobs';

interface QuickActionsProps {
  jobId: string;
  status: JobStatus;
  driveFolderUrl?: string;
  onExpandDetails: () => void;
}

export function QuickActions({ jobId, status, driveFolderUrl, onExpandDetails }: QuickActionsProps) {
  const [isCancelling, setIsCancelling] = useState(false);
  const cancelJob = useJobsStore((state) => state.cancelJob);

  const handleCancel = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isCancelling) return;
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
    } catch {
      // Error handling in store
    } finally {
      setIsCancelling(false);
    }
  }, [jobId, isCancelling, cancelJob]);

  const canCancel = status === 'running' || status === 'queued';
  const hasResults = (status === 'completed' || status === 'completed_with_warnings') && driveFolderUrl;

  return (
    <div className="flex items-center gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
      {/* Cancel for running jobs */}
      {canCancel && (
        <button
          onClick={handleCancel}
          disabled={isCancelling}
          className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-xs font-medium text-red-400 bg-red-900/20 border border-red-700/50 hover:bg-red-900/40 disabled:opacity-50 transition touch-manipulation min-h-[44px] min-w-[44px]"
        >
          {isCancelling ? (
            <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
          Cancel
        </button>
      )}

      {/* View Drive folder for completed jobs */}
      {hasResults && (
        <a
          href={driveFolderUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-xs font-medium text-blue-400 bg-blue-900/20 border border-blue-700/50 hover:bg-blue-900/40 transition touch-manipulation min-h-[44px] min-w-[44px]"
        >
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          Drive
        </a>
      )}

      {/* View details button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onExpandDetails();
        }}
        className="inline-flex items-center gap-1 rounded-md px-3 py-2 text-xs font-medium text-gray-400 bg-gray-800 border border-gray-700 hover:bg-gray-700 hover:text-gray-300 transition touch-manipulation min-h-[44px] min-w-[44px]"
      >
        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Details
      </button>
    </div>
  );
}

export default QuickActions;
