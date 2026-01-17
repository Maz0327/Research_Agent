/**
 * Expandable job card component for displaying job status in the dashboard.
 * Uses modular sub-components for better maintainability.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Job } from '../store/jobs';
import useETA from '../hooks/useETA';
import {
  statusConfig,
  pipelineLabels,
  StatusBadge,
  ProgressBar,
  JobResults,
  JobActions,
  DisambiguationPanel,
} from './job-card';

interface JobCardProps {
  job: Job;
  onRefresh?: () => void;
  isEditMode?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function JobCard({ job, onRefresh, isEditMode = false, isSelected = false, onToggleSelect }: JobCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const canSelect = !['running', 'queued'].includes(job.status);

  // Fallback to queued config for unknown statuses (e.g., deleted, archived)
  const config = statusConfig[job.status] || statusConfig.queued;
  const pipelineLabel = pipelineLabels[job.pipeline] || job.pipeline;

  const { eta, elapsed, stageDescription } = useETA({
    progress: job.progress_percent,
    status: job.status,
    stage: job.stage,
    stageStartedAt: job.stage_started_at,
    passDetail: job.pass_detail,
    pipeline: job.pipeline,
    createdAt: job.created_at,
  });

  const displayTitle =
    job.title ||
    (job.prompt.length > 50 ? job.prompt.substring(0, 50) + '...' : job.prompt);

  return (
    <motion.div
      layout
      className={`rounded-xl border ${config.borderColor} bg-gray-900 shadow-lg transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/5`}
    >
      {/* Header - Always visible */}
      <div
        className="cursor-pointer p-5"
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        aria-label={`Job: ${displayTitle}. Status: ${job.status}. Click to ${isExpanded ? 'collapse' : 'expand'} details.`}
        onClick={() => setIsExpanded(!isExpanded)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setIsExpanded(!isExpanded);
          }
        }}
      >
        <div className="flex items-start justify-between">
          {/* Checkbox for edit mode */}
          {isEditMode && (
            <div
              className="mr-3 flex items-center"
              onClick={(e) => e.stopPropagation()}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={onToggleSelect}
                disabled={!canSelect}
                className="h-5 w-5 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-100 truncate">
              {displayTitle}
            </h3>

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

            {(job.status === 'running' || job.status === 'queued') && (
              <p className="mt-2 text-sm text-gray-500">{stageDescription}</p>
            )}
          </div>

          <div className="flex items-center gap-3 ml-4">
            <StatusBadge status={job.status} />

            <motion.svg
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="h-5 w-5 text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </motion.svg>
          </div>
        </div>

        {job.status === 'running' && (
          <ProgressBar progress={job.progress_percent} />
        )}

        {/* Disambiguation panel - always visible when needed */}
        {job.status === 'disambiguating' && job.interpretations && (
          <div onClick={(e) => e.stopPropagation()}>
            <DisambiguationPanel
              jobId={job.id}
              interpretations={job.interpretations}
            />
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
                  <p className="text-sm text-gray-300 break-words whitespace-pre-wrap" style={{ overflowWrap: 'anywhere' }}>{job.prompt}</p>
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

              {/* Results display */}
              <JobResults
                jobId={job.id}
                status={job.status}
                driveFolderUrl={job.artifacts?.drive_folder_url}
                error={job.error}
                pipeline={job.pipeline}
                artifacts={job.artifacts}
              />

              {/* Actions */}
              <JobActions
                jobId={job.id}
                status={job.status}
                driveFolderUrl={job.artifacts?.drive_folder_url}
                pipeline={job.pipeline}
                hasDocuments={!!(job.artifacts?.source_ledger || job.artifacts?.jump_start || job.artifacts?.semantic_brief)}
                onRefresh={onRefresh}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
