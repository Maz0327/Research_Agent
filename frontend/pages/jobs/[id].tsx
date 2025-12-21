/**
 * Job detail page showing full job information and progress.
 */
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { motion } from 'framer-motion';
import Layout from '../../components/Layout';
import { ProtectedRoute } from '../../components/AuthProvider';
import { getAccessToken } from '../../lib/supabase';
import useETA from '../../hooks/useETA';
import ErrorDisplay from '../../components/ErrorDisplay';

interface JobDetail {
  id: string;
  prompt: string;
  pipeline: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  artifacts?: {
    drive_folder_url?: string;
    doc_urls?: string[];
  };
  error?: string;
  created_at: string;
}

const statusConfig = {
  queued: {
    label: 'Queued',
    bgColor: 'bg-gray-100',
    textColor: 'text-gray-700',
  },
  running: {
    label: 'Running',
    bgColor: 'bg-blue-100',
    textColor: 'text-blue-700',
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-green-100',
    textColor: 'text-green-700',
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-red-100',
    textColor: 'text-red-700',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-700',
  },
};

const pipelineLabels: Record<string, string> = {
  quick: 'Quick',
  full: 'Full',
  breaking_news: 'Breaking News',
  investigation: 'Investigation',
  profile: 'Profile',
  controversy: 'Controversy',
};

// Progress section with ETA
function ProgressSection({
  job,
  onCancel,
  isCancelling,
  cancelError,
}: {
  job: JobDetail;
  onCancel: () => void;
  isCancelling: boolean;
  cancelError: string | null;
}) {
  const { eta, elapsed, isCalculating } = useETA({
    progress: job.progress_percent,
    status: job.status,
    createdAt: job.created_at,
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
    >
      <h2 className="mb-4 text-lg font-medium text-gray-900 dark:text-gray-100">Progress</h2>

      {/* Progress bar */}
      <div className="mb-2 flex justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">
          {job.status === 'queued' ? 'Waiting to start...' : 'Processing...'}
        </span>
        <span className="font-medium text-gray-900 dark:text-gray-100">{job.progress_percent}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <motion.div
          className="h-full rounded-full bg-blue-600"
          initial={{ width: 0 }}
          animate={{ width: `${job.progress_percent}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* ETA and elapsed time */}
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          Elapsed: {elapsed}
        </span>
        {isCalculating && eta && (
          <span className="text-blue-600 dark:text-blue-400">
            ETA: ~{eta}
          </span>
        )}
      </div>

      {/* Cancel button */}
      <div className="mt-6 border-t border-gray-100 pt-4 dark:border-gray-700">
        {cancelError && (
          <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
            {cancelError}
          </div>
        )}
        <button
          onClick={onCancel}
          disabled={isCancelling}
          className="inline-flex items-center rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 shadow-sm hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-700 dark:bg-gray-800 dark:text-red-400 dark:hover:bg-red-900/20"
        >
          {isCancelling ? (
            <>
              <motion.svg
                className="-ml-1 mr-2 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
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
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </motion.svg>
              Cancelling...
            </>
          ) : (
            <>
              <svg
                className="-ml-1 mr-2 h-4 w-4"
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
      </div>
    </motion.div>
  );
}

function JobDetailContent() {
  const router = useRouter();
  const { id } = router.query;
  const [job, setJob] = useState<JobDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const fetchJob = useCallback(async () => {
    if (!id) return;

    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${id}`, { headers });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Job not found');
        }
        throw new Error('Failed to fetch job');
      }

      const data = await response.json();
      setJob({
        id: data.id,
        prompt: data.prompt,
        pipeline: data.pipeline,
        status: data.status,
        progress_percent: data.progress_percent,
        artifacts: data.artifacts,
        error: data.error,
        created_at: data.created_at,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch job');
    } finally {
      setIsLoading(false);
    }
  }, [id, API_URL]);

  const handleCancel = async () => {
    if (!id || !job) return;

    const confirmed = window.confirm(
      'Are you sure you want to cancel this job? This action cannot be undone.'
    );
    if (!confirmed) return;

    setIsCancelling(true);
    setCancelError(null);

    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${id}/cancel`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to cancel job');
      }

      // Update local job state
      setJob({ ...job, status: 'cancelled' });
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Failed to cancel job');
    } finally {
      setIsCancelling(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // Polling for running jobs
  useEffect(() => {
    if (!job || (job.status !== 'running' && job.status !== 'queued')) return;

    const interval = setInterval(fetchJob, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [job, fetchJob]);

  if (isLoading) {
    return (
      <Layout>
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="text-lg text-gray-600">Loading...</div>
        </div>
      </Layout>
    );
  }

  if (error || !job) {
    return (
      <Layout>
        <div className="mx-auto max-w-3xl">
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
            <h2 className="text-lg font-medium text-red-800">
              {error || 'Job not found'}
            </h2>
            <Link
              href="/dashboard"
              className="mt-4 inline-block text-sm font-medium text-red-600 hover:text-red-700"
            >
              &larr; Back to Dashboard
            </Link>
          </div>
        </div>
      </Layout>
    );
  }

  const config = statusConfig[job.status];
  const pipelineLabel = pipelineLabels[job.pipeline] || job.pipeline;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        {/* Back link */}
        <div className="mb-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-900"
          >
            <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Dashboard
          </Link>
          {(job.status === 'running' || job.status === 'queued') && (
            <span className="ml-2 text-sm text-gray-500">(job continues in background)</span>
          )}
        </div>

        {/* Job Header */}
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{job.prompt}</h1>
              <div className="mt-2 flex items-center gap-3 text-sm text-gray-500">
                <span className="rounded bg-gray-100 px-2 py-0.5 font-medium">
                  {pipelineLabel}
                </span>
                <span>&middot;</span>
                <span>{formatDate(job.created_at)}</span>
              </div>
            </div>

            {/* Status badge */}
            <span
              className={`inline-flex items-center rounded-full px-4 py-2 text-sm font-medium ${config.bgColor} ${config.textColor}`}
            >
              {config.label}
            </span>
          </div>
        </div>

        {/* Progress (for running jobs) */}
        {(job.status === 'running' || job.status === 'queued') && (
          <ProgressSection job={job} onCancel={handleCancel} isCancelling={isCancelling} cancelError={cancelError} />
        )}

        {/* Error (for failed jobs) */}
        {job.status === 'failed' && job.error && (
          <div className="mb-6">
            <ErrorDisplay error={job.error} showTechnical />
          </div>
        )}

        {/* Cancelled (for cancelled jobs) */}
        {job.status === 'cancelled' && (
          <div className="mb-6 rounded-lg border border-orange-200 bg-orange-50 p-6">
            <h2 className="mb-2 text-lg font-medium text-orange-800">Job Cancelled</h2>
            <p className="text-sm text-orange-700">
              This job was cancelled by the user. Any partial results may have been saved.
            </p>
          </div>
        )}

        {/* Artifacts (for completed jobs) */}
        {job.status === 'completed' && job.artifacts && (
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-medium text-gray-900">Results</h2>

            <div className="space-y-4">
              {job.artifacts.drive_folder_url && (
                <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                  <div className="flex items-center gap-3">
                    <svg
                      className="h-8 w-8 text-yellow-500"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                    <div>
                      <p className="font-medium text-gray-900">Google Drive Folder</p>
                      <p className="text-sm text-gray-500">Contains all research documents</p>
                    </div>
                  </div>
                  <a
                    href={job.artifacts.drive_folder_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
                  >
                    Open Folder
                  </a>
                </div>
              )}

              {job.artifacts.doc_urls && job.artifacts.doc_urls.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-700">Documents</h3>
                  <ul className="space-y-2">
                    {job.artifacts.doc_urls.map((url, index) => (
                      <li key={index}>
                        <a
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 text-blue-600 hover:text-blue-700"
                        >
                          <svg
                            className="h-5 w-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                          </svg>
                          Document {index + 1}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

export default function JobDetailPage() {
  return (
    <ProtectedRoute>
      <JobDetailContent />
    </ProtectedRoute>
  );
}
