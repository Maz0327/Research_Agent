/**
 * Job action buttons component (cancel, view results, etc.).
 */
import { useState, useCallback } from 'react';
import { getAccessToken } from '../../lib/supabase';
import { JobStatus } from './job-card-config';

interface JobActionsProps {
  jobId: string;
  status: JobStatus;
  driveFolderUrl?: string;
  onRefresh?: () => void;
}

export function JobActions({
  jobId,
  status,
  driveFolderUrl,
  onRefresh,
}: JobActionsProps) {
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const handleCancel = useCallback(async () => {
    if (isCancelling) return;

    setIsCancelling(true);
    setCancelError(null);

    try {
      const token = await getAccessToken();
      const API_URL =
        process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_URL}/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }

      onRefresh?.();
    } catch (error) {
      setCancelError(error instanceof Error ? error.message : 'Failed to cancel');
    } finally {
      setIsCancelling(false);
    }
  }, [jobId, isCancelling, onRefresh]);

  const canCancel = status === 'running' || status === 'queued';
  const hasResults = status === 'completed' && driveFolderUrl;

  return (
    <div className="flex items-center gap-3 pt-2">
      {canCancel && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCancel();
          }}
          disabled={isCancelling}
          className="inline-flex items-center gap-2 rounded-lg border border-red-700 px-4 py-2 text-sm font-medium text-red-400 transition hover:bg-red-900/30 disabled:opacity-50"
        >
          {isCancelling ? (
            <>
              <svg
                className="animate-spin h-4 w-4"
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
              Cancelling...
            </>
          ) : (
            <>
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              Cancel Job
            </>
          )}
        </button>
      )}

      {cancelError && (
        <span className="text-sm text-red-400">{cancelError}</span>
      )}

      {hasResults && (
        <a
          href={driveFolderUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-400 hover:text-gray-300 transition"
          onClick={(e) => e.stopPropagation()}
        >
          Open folder in new tab
        </a>
      )}
    </div>
  );
}

export default JobActions;
