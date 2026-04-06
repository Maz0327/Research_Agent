'use client';

/**
 * DashboardJobCard — compact job card matching the mockup design.
 * Shows title, mode badge, source count, progress bar (running), status badge with pulse dot.
 * Navigates to /jobs/[id] on click.
 */
import React from 'react';
import { useRouter } from 'next/navigation';
import { pipelineLabels, statusConfig } from '@/components/job-card/job-card-config';
import { formatRelativeTime } from '@/lib/time-utils';
import type { Job } from '@/store/jobs';

interface DashboardJobCardProps {
  job: Job;
}

// Derive compact badge styles from canonical statusConfig (single source of truth).
// running = blue (in-progress standard), completed = green.
const STATUS_BADGE: Record<string, { label: string; className: string; pulse?: boolean }> = Object.fromEntries(
  Object.entries(statusConfig).map(([key, cfg]) => [
    key,
    {
      label: cfg.label,
      className: `${cfg.textColor} ${cfg.bgColor}`,
      pulse: key === 'running',
    },
  ])
);

export function DashboardJobCard({ job }: DashboardJobCardProps) {
  const router = useRouter();
  const isRunning = job.status === 'running';
  const isFailed = job.status === 'failed' || job.status === 'failed_insufficient';
  const title = job.title || job.prompt || 'Untitled Job';
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const sourceCount = job.artifacts?.doc_urls?.length ?? 0;

  const badge = STATUS_BADGE[job.status] ?? STATUS_BADGE.queued;
  const borderClass = isFailed ? 'border-destructive/20 hover:border-destructive/40' : 'border-border hover:border-border';

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      router.push(`/jobs/${job.id}`);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => router.push(`/jobs/${job.id}`)}
      onKeyDown={handleKeyDown}
      className={`bg-card border ${borderClass} rounded-xl p-4 cursor-pointer transition-all hover:shadow-[0_0_24px_rgba(59,130,246,0.08)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring`}
    >
      {/* Title row + status badge */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground truncate">{title}</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {modeLabel}
            {sourceCount > 0 && <> &middot; {sourceCount} source{sourceCount !== 1 ? 's' : ''}</>}
          </p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${badge.className}`}>
          {badge.pulse && (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 motion-safe:animate-pulse" />
          )}
          {badge.label}
        </span>
      </div>

      {/* Progress bar — running jobs only */}
      {isRunning && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-caption text-muted-foreground mb-1">
            <span>{job.stage ?? 'Processing'}</span>
            <span>{job.progress_percent ?? 0}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary to-purple-500 transition-all duration-500"
              style={{ width: `${job.progress_percent ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message — failed jobs */}
      {isFailed && job.error && (
        <p className="text-xs text-destructive/80 mb-2 line-clamp-1">{job.error}</p>
      )}

      {/* Footer: time ago */}
      <p className="text-caption text-muted-foreground">{formatRelativeTime(job.created_at)}</p>
    </div>
  );
}

export default DashboardJobCard;
