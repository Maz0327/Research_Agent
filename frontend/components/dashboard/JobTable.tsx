/**
 * JobTable - Table view for job list with expandable rows.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Job } from '../../store/jobs';
import { statusConfig, StatusBadge, ProgressBar } from '../job-card';
import useETA from '../../hooks/useETA';

interface JobTableProps {
  jobs: Job[];
  onRefresh: () => void;
  isEditMode: boolean;
  selectedJobIds: Set<string>;
  onToggleSelect: (jobId: string) => void;
}

// Format date for display
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Table row component with ETA hook
function JobTableRow({
  job,
  isEditMode,
  isSelected,
  isExpanded,
  onToggleSelect,
  onToggleExpand,
}: {
  job: Job;
  isEditMode: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onToggleSelect: () => void;
  onToggleExpand: () => void;
}) {
  const canSelect = !['running', 'queued'].includes(job.status);
  const config = statusConfig[job.status] || statusConfig.queued;

  const { eta, stageDescription } = useETA({
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
    (job.prompt.length > 40 ? job.prompt.substring(0, 40) + '...' : job.prompt);

  return (
    <>
      <tr
        onClick={onToggleExpand}
        className={`border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors ${
          isExpanded ? 'bg-gray-800/30' : ''
        }`}
      >
        {/* Checkbox (edit mode) */}
        {isEditMode && (
          <td className="px-3 py-3 w-10" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              disabled={!canSelect}
              className="h-4 w-4 rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
            />
          </td>
        )}

        {/* Title */}
        <td className="px-3 py-3">
          <div className="flex items-center gap-2">
            <motion.svg
              animate={{ rotate: isExpanded ? 90 : 0 }}
              transition={{ duration: 0.2 }}
              className="h-4 w-4 text-gray-500 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </motion.svg>
            <span className="text-sm font-medium text-gray-100 truncate">{displayTitle}</span>
          </div>
        </td>

        {/* Status */}
        <td className="px-3 py-3 w-28">
          <StatusBadge status={job.status} />
        </td>

        {/* Created */}
        <td className="px-3 py-3 w-32 text-sm text-gray-400 hidden sm:table-cell">
          {formatDate(job.created_at)}
        </td>

        {/* ETA */}
        <td className="px-3 py-3 w-20 text-sm text-blue-400 hidden md:table-cell">
          {job.status === 'running' && eta ? eta : '-'}
        </td>

        {/* Progress (visual) */}
        <td className="px-3 py-3 w-24 hidden lg:table-cell">
          {job.status === 'running' && (
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-purple-600 transition-all"
                style={{ width: `${job.progress_percent}%` }}
              />
            </div>
          )}
        </td>
      </tr>

      {/* Expanded row content */}
      <AnimatePresence>
        {isExpanded && (
          <tr>
            <td colSpan={isEditMode ? 6 : 5} className="p-0">
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className={`p-4 border-b ${config.borderColor} bg-gray-900/50`}>
                  {/* Full prompt */}
                  <div className="mb-3">
                    <p className="text-xs text-gray-500 mb-1">Prompt</p>
                    <p className="text-sm text-gray-300">{job.prompt}</p>
                  </div>

                  {/* Stage description */}
                  {(job.status === 'running' || job.status === 'queued') && stageDescription && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1">Stage</p>
                      <p className="text-sm text-gray-300">{stageDescription}</p>
                    </div>
                  )}

                  {/* Progress bar for running jobs */}
                  {job.status === 'running' && (
                    <div className="mb-3">
                      <ProgressBar progress={job.progress_percent} stageDescription={stageDescription} />
                    </div>
                  )}

                  {/* Error for failed jobs */}
                  {(job.status === 'failed' || job.status === 'failed_insufficient') && job.error && (
                    <div className="mb-3">
                      <p className="text-xs text-gray-500 mb-1">Error</p>
                      <p className="text-sm text-red-400">{job.error}</p>
                    </div>
                  )}

                  {/* Quick actions */}
                  <div className="flex items-center gap-2 mt-3">
                    {job.artifacts?.drive_folder_url && (
                      <a
                        href={job.artifacts.drive_folder_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-900/20 border border-blue-700/50 rounded-md hover:bg-blue-900/40 transition"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                        View Results
                      </a>
                    )}
                  </div>
                </div>
              </motion.div>
            </td>
          </tr>
        )}
      </AnimatePresence>
    </>
  );
}

export function JobTable({
  jobs,
  onRefresh,
  isEditMode,
  selectedJobIds,
  onToggleSelect,
}: JobTableProps) {
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-800/50 border-b border-gray-700">
            <tr>
              {isEditMode && <th className="px-3 py-3 w-10" />}
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Title
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-28">
                Status
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-32 hidden sm:table-cell">
                Created
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-20 hidden md:table-cell">
                ETA
              </th>
              <th className="px-3 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-24 hidden lg:table-cell">
                Progress
              </th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <JobTableRow
                key={job.id}
                job={job}
                isEditMode={isEditMode}
                isSelected={selectedJobIds.has(job.id)}
                isExpanded={expandedJobId === job.id}
                onToggleSelect={() => onToggleSelect(job.id)}
                onToggleExpand={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default JobTable;
