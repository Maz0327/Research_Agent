/**
 * Job results display component for completed/failed/cancelled jobs.
 */
import { JobStatus } from './job-card-config';

interface JobResultsProps {
  status: JobStatus;
  driveFolderUrl?: string;
  error?: string;
}

export function JobResults({ status, driveFolderUrl, error }: JobResultsProps) {
  if (status === 'failed' && error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/30 p-4">
        <h4 className="text-sm font-medium text-red-400 mb-1">Error</h4>
        <p className="text-sm text-red-300 break-words" style={{ overflowWrap: 'anywhere' }}>{error}</p>
      </div>
    );
  }

  if (status === 'cancelled') {
    return (
      <div className="rounded-lg border border-orange-800 bg-orange-900/30 p-4">
        <p className="text-sm text-orange-300">
          This job was cancelled. Any partial results may have been saved.
        </p>
      </div>
    );
  }

  if (status === 'completed' && driveFolderUrl) {
    return (
      <div className="rounded-lg border border-green-800 bg-green-900/30 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-800/50 rounded-lg">
              <svg
                className="h-6 w-6 text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
            </div>
            <div>
              <p className="font-medium text-green-300">Research Complete</p>
              <p className="text-sm text-green-400/70">
                Your documents are ready
              </p>
            </div>
          </div>
          <a
            href={driveFolderUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
            onClick={(e) => e.stopPropagation()}
          >
            Open in Drive
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
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        </div>
      </div>
    );
  }

  return null;
}

export default JobResults;
