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
      {/* Header - Always visible, touch-optimized */}
      <div
        className="cursor-pointer p-4 sm:p-6 touch-manipulation"
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
        <div className="flex items-start justify-between gap-3">
          {/* Checkbox for edit mode - 44px touch target */}
          {isEditMode && (
            <div
              className="flex items-center justify-center min-w-[44px] min-h-[44px] -ml-2"
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
            {/* Title - responsive text size */}
            <h3 className="text-base sm:text-lg font-semibold text-gray-100 truncate">
              {displayTitle}
            </h3>

            {/* Meta info - stack on mobile, inline on desktop */}
            <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs sm:text-sm text-gray-400">
              <span className="rounded-md bg-gray-800 px-2 py-0.5 text-xs font-medium text-gray-300">
                {pipelineLabel}
              </span>
              <span className="hidden sm:inline text-gray-600">&middot;</span>
              <span>{formatDate(job.created_at)}</span>
              {job.status === 'running' && eta && (
                <>
                  <span className="hidden sm:inline text-gray-600">&middot;</span>
                  <span className="text-blue-400">ETA: {eta}</span>
                </>
              )}
            </div>

            {/* Stage description for queued jobs only (running jobs show in progress bar) */}
            {job.status === 'queued' && (
              <p className="mt-2 text-sm text-gray-500">{stageDescription}</p>
            )}

            {/* Error preview for failed jobs */}
            {(job.status === 'failed' || job.status === 'failed_insufficient') && job.error && (
              <p className="mt-2 text-sm text-red-400 truncate">
                {job.error.length > 80 ? job.error.substring(0, 80) + '...' : job.error}
              </p>
            )}

            {/* Warning count for completed_with_warnings */}
            {job.status === 'completed_with_warnings' && job.warning_count && job.warning_count > 0 && (
              <p className="mt-2 text-sm text-yellow-400">
                {job.warning_count} warning{job.warning_count > 1 ? 's' : ''} during processing
              </p>
            )}
          </div>

          {/* Status + chevron - responsive gap */}
          <div className="flex items-center gap-2 sm:gap-3 ml-2 sm:ml-4 flex-shrink-0">
            <StatusBadge status={job.status} />

            <motion.svg
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.2 }}
              className="h-5 w-5 text-gray-500 flex-shrink-0"
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
          <ProgressBar progress={job.progress_percent} stageDescription={stageDescription} />
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
            {/* Responsive padding for expanded content */}
            <div className="border-t border-gray-800 px-4 sm:px-6 py-5 sm:py-6 space-y-5 sm:space-y-6">
              {/* Full prompt - collapsible section */}
              {job.title && job.prompt !== job.title && (
                <div className="pb-4 border-b border-gray-800/50">
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Original Prompt
                  </h4>
                  <p className="text-sm text-gray-300 leading-relaxed break-words whitespace-pre-wrap" style={{ overflowWrap: 'anywhere' }}>{job.prompt}</p>
                </div>
              )}

              {/* Time info - stack on mobile, inline on desktop */}
              <div className="flex flex-col sm:flex-row gap-2 sm:gap-8 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Elapsed:</span>
                  <span className="text-gray-300 font-medium">{elapsed}</span>
                </div>
                {eta && job.status === 'running' && (
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500">Remaining:</span>
                    <span className="text-blue-400 font-medium">{eta}</span>
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
                onRefresh={onRefresh}
                boosterStatus={job.booster_status}
                boosterError={job.booster_error}
                boosterProgressPercent={job.booster_progress_percent}
              />

              {/* Actions */}
              <JobActions
                jobId={job.id}
                status={job.status}
                driveFolderUrl={job.artifacts?.drive_folder_url}
                pipeline={job.pipeline}
                hasDocuments={!!(
                  job.artifacts?.source_ledger ||
                  job.artifacts?.jump_start ||
                  job.artifacts?.semantic_brief ||
                  job.artifacts?.doc_0_path ||
                  job.artifacts?.doc_1_path ||
                  job.artifacts?.doc_2_path
                )}
                onRefresh={onRefresh}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
