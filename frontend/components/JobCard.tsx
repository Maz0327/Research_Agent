/**
 * Expandable job card component for displaying job status in the dashboard.
 * Replaces the separate job detail page with inline expandable content.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useJobsStore, Job } from '../store/jobs';
import useETA from '../hooks/useETA';
import { getAccessToken } from '../lib/supabase';

interface JobCardProps {
  job: Job;
  onRefresh?: () => void;
}

const statusConfig = {
  queued: {
    label: 'Queued',
    bgColor: 'bg-gray-800',
    textColor: 'text-gray-300',
    dotColor: 'bg-gray-400',
    borderColor: 'border-gray-700',
  },
  running: {
    label: 'Running',
    bgColor: 'bg-blue-900/50',
    textColor: 'text-blue-300',
    dotColor: 'bg-blue-400',
    borderColor: 'border-blue-500/50',
  },
  completed: {
    label: 'Completed',
    bgColor: 'bg-green-900/50',
    textColor: 'text-green-300',
    dotColor: 'bg-green-400',
    borderColor: 'border-green-500/50',
  },
  failed: {
    label: 'Failed',
    bgColor: 'bg-red-900/50',
    textColor: 'text-red-300',
    dotColor: 'bg-red-400',
    borderColor: 'border-red-500/50',
  },
  cancelled: {
    label: 'Cancelled',
    bgColor: 'bg-orange-900/50',
    textColor: 'text-orange-300',
    dotColor: 'bg-orange-400',
    borderColor: 'border-orange-500/50',
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

export default function JobCard({ job, onRefresh }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const config = statusConfig[job.status];
  const pipelineLabel = pipelineLabels[job.pipeline] || job.pipeline;

  // Use the enhanced ETA hook
  const { eta, elapsed, stageDescription, isCalculating } = useETA({
    progress: job.progress_percent,
    status: job.status,
    stage: job.stage,
    stageStartedAt: job.stage_started_at,
    pipeline: job.pipeline,
    createdAt: job.created_at,
  });

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleCancel = useCallback(async () => {
    if (isCancelling) return;

    setIsCancelling(true);
    setCancelError(null);

    try {
      const token = await getAccessToken();
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_URL}/jobs/${job.id}/cancel`, {
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
  }, [job.id, isCancelling, onRefresh]);

  // Display title if available, otherwise truncated prompt
  const displayTitle = job.title || (job.prompt.length > 50 ? job.prompt.substring(0, 50) + '...' : job.prompt);

  return (
    <motion.div
      layout
      className={`rounded-xl border ${config.borderColor} bg-gray-900 shadow-lg transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/5`}
    >
      {/* Header - Always visible */}
      <div
        className="cursor-pointer p-5"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            {/* Title */}
            <h3 className="text-lg font-semibold text-gray-100 truncate">
              {displayTitle}
            </h3>

            {/* Subtitle info */}
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-gray-400">
              <span className="rounded-md bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-300">
                {pipelineLabel}
              </span>
              <span className="text-gray-600">&middot;</span>
              <span>{formatDate(job.created_at)}</span>
              {job.status === 'running' && eta && (
                <>
                  <span className="text-gray-600">&middot;</span>
                  <span className="text-blue-400">ETA: {eta}</span>
                </>
              )}
            </div>

            {/* Stage description for running jobs */}
            {(job.status === 'running' || job.status === 'queued') && (
              <p className="mt-2 text-sm text-gray-500">{stageDescription}</p>
            )}
          </div>

          {/* Status badge and expand icon */}
          <div className="flex items-center gap-3 ml-4">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${config.bgColor} ${config.textColor}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${config.dotColor} ${job.status === 'running' ? 'animate-pulse' : ''}`}></span>
              {config.label}
            </span>

            {/* Expand/collapse icon */}
            <motion.svg
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="h-5 w-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </motion.svg>
          </div>
        </div>

        {/* Progress bar for running jobs */}
        {job.status === 'running' && (
          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-gray-500">Progress</span>
              <span className="font-medium text-gray-300">{job.progress_percent}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-800">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-blue-400"
                initial={{ width: 0 }}
                animate={{ width: `${job.progress_percent}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="border-t border-gray-800 px-5 py-4 space-y-4">
              {/* Full prompt */}
              {job.title && job.prompt !== job.title && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                    Original Prompt
                  </h4>
                  <p className="text-sm text-gray-300">{job.prompt}</p>
                </div>
              )}

              {/* Time info */}
              <div className="flex gap-6">
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                    Elapsed
                  </h4>
                  <p className="text-sm text-gray-300">{elapsed}</p>
                </div>
                {eta && job.status === 'running' && (
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                      Remaining
                    </h4>
                    <p className="text-sm text-gray-300">{eta}</p>
                  </div>
                )}
              </div>

              {/* Error display for failed jobs */}
              {job.status === 'failed' && job.error && (
                <div className="rounded-lg border border-red-800 bg-red-900/30 p-4">
                  <h4 className="text-sm font-medium text-red-400 mb-1">Error</h4>
                  <p className="text-sm text-red-300">{job.error}</p>
                </div>
              )}

              {/* Cancelled message */}
              {job.status === 'cancelled' && (
                <div className="rounded-lg border border-orange-800 bg-orange-900/30 p-4">
                  <p className="text-sm text-orange-300">
                    This job was cancelled. Any partial results may have been saved.
                  </p>
                </div>
              )}

              {/* Results for completed jobs */}
              {job.status === 'completed' && job.artifacts?.drive_folder_url && (
                <div className="rounded-lg border border-green-800 bg-green-900/30 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-green-800/50 rounded-lg">
                        <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-green-300">Research Complete</p>
                        <p className="text-sm text-green-400/70">Your documents are ready</p>
                      </div>
                    </div>
                    <a
                      href={job.artifacts.drive_folder_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Open in Drive
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3 pt-2">
                {/* Cancel button for running/queued jobs */}
                {(job.status === 'running' || job.status === 'queued') && (
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
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Cancelling...
                      </>
                    ) : (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Cancel Job
                      </>
                    )}
                  </button>
                )}

                {cancelError && (
                  <span className="text-sm text-red-400">{cancelError}</span>
                )}

                {/* Drive link for completed jobs (secondary) */}
                {job.status === 'completed' && job.artifacts?.drive_folder_url && (
                  <a
                    href={job.artifacts.drive_folder_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-400 hover:text-gray-300 transition"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Open folder in new tab
                  </a>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
