/**
 * DashboardJobCard - Compact job status card for dashboard overview.
 * Shows job status, progress, ETA, and elapsed time.
 * Clicks navigate to appropriate tab in Jobs page.
 */
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import { statusConfig, pipelineLabels } from '../job-card/job-card-config';
import type { Job } from '../../store/jobs';
import { getStageLabel } from '../../lib/constants';
import { formatRelativeTime, formatElapsedTime, estimateETA } from '../../lib/time-utils';

interface DashboardJobCardProps {
  job: Job;
  /** Animation delay for staggered entrance */
  delay?: number;
}

export function DashboardJobCard({ job, delay = 0 }: DashboardJobCardProps) {
  const router = useRouter();
  const [elapsedTime, setElapsedTime] = useState(formatElapsedTime(job.stage_started_at || job.created_at));
  const [eta, setEta] = useState(estimateETA(job.progress_percent, job.stage_started_at || job.created_at));
  
  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.queued;
  const isActive = job.status === 'running' || job.status === 'queued';
  const isCompleted = job.status === 'completed' || job.status === 'completed_with_warnings';
  const isFailed = job.status === 'failed' || job.status === 'failed_insufficient' || job.status === 'cancelled';
  
  // Update elapsed time every second for running jobs
  useEffect(() => {
    if (!isActive) return;
    
    const interval = setInterval(() => {
      setElapsedTime(formatElapsedTime(job.stage_started_at || job.created_at));
      setEta(estimateETA(job.progress_percent, job.stage_started_at || job.created_at));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isActive, job.progress_percent, job.stage_started_at, job.created_at]);

  // Always navigate to job detail page
  const handleClick = () => {
    router.push(`/jobs/${job.id}`);
  };

  // Left accent border color by status
  const leftBorder = isActive
    ? job.status === 'running' ? 'border-l-blue-500' : 'border-l-yellow-500'
    : isCompleted ? 'border-l-green-500'
    : 'border-l-red-600';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay * 0.05, duration: 0.2 }}
      onClick={handleClick}
      className={`relative py-3.5 px-3 bg-gray-900 rounded-lg border border-l-2 ${leftBorder} ${config.borderColor} hover:border-gray-600 cursor-pointer transition-all group`}
    >
      <div className="flex items-center gap-3">
        {/* Status indicator */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center`}>
          {isActive ? (
            <div className={`w-3 h-3 rounded-full ${config.dotColor} ${job.status === 'running' ? 'animate-pulse' : ''}`} />
          ) : isCompleted ? (
            <svg className={`w-4 h-4 ${config.textColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className={`w-4 h-4 ${config.textColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          )}
        </div>
        
        {/* Job info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium text-gray-100 truncate">
              {job.title || job.prompt || 'Untitled Job'}
            </h4>
            <span className={`flex-shrink-0 px-1.5 py-0.5 text-xs rounded ${config.bgColor} ${config.textColor}`}>
              {config.label}
            </span>
          </div>
          
          {/* Progress details for active jobs */}
          {isActive && (
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              <span>{job.pass_detail || getStageLabel(job.stage)}</span>
            </div>
          )}
          
          {/* Time info for completed jobs */}
          {isCompleted && (
            <div className="text-xs text-gray-500 mt-0.5">
              {formatRelativeTime(job.created_at)}
              {job.status === 'completed_with_warnings' && job.warning_count && (
                <span className="ml-2 text-yellow-400">
                  {job.warning_count} warning{job.warning_count > 1 ? 's' : ''}
                </span>
              )}
            </div>
          )}
          
          {/* Error for failed jobs */}
          {isFailed && job.error && (
            <p className="text-xs text-red-400 truncate mt-0.5">{job.error}</p>
          )}
        </div>
        
        {/* Progress/time info */}
        <div className="flex-shrink-0 text-right">
          {isActive && (
            <div className="text-right">
              <span className={`text-sm font-mono ${config.textColor}`}>{job.progress_percent}%</span>
              <div className="text-xs text-gray-500 mt-0.5">
                {job.status === 'running' && job.progress_percent > 0 ? (
                  <span>ETA: {eta}</span>
                ) : (
                  <span>{elapsedTime}</span>
                )}
              </div>
            </div>
          )}
          
          {/* Arrow indicator */}
          <svg
            className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors mt-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </div>
      
      {/* Progress bar for active jobs */}
      {isActive && (
        <div className="mt-2 h-1 bg-gray-800 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${job.progress_percent}%` }}
            transition={{ duration: 0.5 }}
            className={`h-full rounded-full ${job.status === 'running' ? 'bg-blue-500' : 'bg-yellow-500'}`}
          />
        </div>
      )}
    </motion.div>
  );
}

export default DashboardJobCard;
