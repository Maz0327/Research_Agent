/**
 * Expandable job card component for displaying job status in the dashboard.
 * Uses modular sub-components for better maintainability.
 *
 * Progressive Disclosure Levels:
 * - Level 0 (Collapsed): Title + Status + ETA + TaskBadges
 * - Level 1 (Quick View): + Progress + Inline actions
 *
 * Clicking navigates to /jobs/[id] detail page for full view.
 */
import { useState, useCallback } from 'react';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import { Job } from '../store/jobs';
import useETA from '../hooks/useETA';
import {
  statusConfig,
  pipelineLabels,
  StatusBadge,
  ProgressBar,
  DisambiguationPanel,
} from './job-card';
import { QuickActions } from './job-card/QuickActions';
import { TaskBadges } from './job-card/TaskBadges';

// Expansion levels for progressive disclosure (Level 2 moved to detail page)
type ExpansionLevel = 0 | 1;

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
  const router = useRouter();
  const [expansionLevel, setExpansionLevel] = useState<ExpansionLevel>(0);
  const canSelect = !['running', 'queued'].includes(job.status);

  // Handle card header click - toggle Level 0/1 or navigate
  const handleHeaderClick = useCallback(() => {
    setExpansionLevel((prev) => (prev === 0 ? 1 : 0));
  }, []);

  // Navigate to job detail page
  const navigateToDetail = useCallback(() => {
    router.push(`/jobs/${job.id}`);
  }, [router, job.id]);

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
        aria-expanded={expansionLevel > 0}
        aria-label={`Job: ${displayTitle}. Status: ${job.status}. Click to ${expansionLevel > 0 ? 'collapse' : 'expand'} details.`}
        onClick={handleHeaderClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleHeaderClick();
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

            {/* Task badges for secondary tasks */}
            <TaskBadges
              boosterStatus={job.booster_status}
              boosterProgressPercent={job.booster_progress_percent}
              iterationStatus={job.iteration_status}
              iterationId={job.iteration_id}
              iterationProgressPercent={job.iteration_progress_percent}
              iterationCount={job.artifacts?.iterations?.filter((it) => it.status === 'completed').length}
              hasProducerPacket={!!(job.artifacts?.doc_3_path || job.artifacts?.creator_brief_md)}
            />
          </div>

          {/* Status + chevron - responsive gap */}
          <div className="flex items-center gap-2 sm:gap-3 ml-2 sm:ml-4 flex-shrink-0">
            <StatusBadge status={job.status} />

            <motion.svg
              animate={{ rotate: expansionLevel > 0 ? 180 : 0 }}
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

        {/* Level 1: Show progress bar when expanded */}
        {(expansionLevel >= 1 || job.status === 'running') && (
          <ProgressBar progress={job.progress_percent} stageDescription={stageDescription} />
        )}

        {/* Level 1: Quick Actions */}
        {expansionLevel === 1 && (
          <QuickActions
            jobId={job.id}
            status={job.status}
            driveFolderUrl={job.artifacts?.drive_folder_url}
            onExpandDetails={navigateToDetail}
          />
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

    </motion.div>
  );
}
