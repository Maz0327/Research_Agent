'use client';

/**
 * DashboardJobCard — compact job card matching the mockup design.
 * Shows title, mode badge, source count, progress bar (running), status badge with pulse dot.
 * Navigates to /jobs/[id] on click.
 */
import { useRouter } from 'next/navigation';
import { pipelineLabels } from '@/components/job-card/job-card-config';
import { formatRelativeTime } from '@/lib/time-utils';
import type { Job } from '@/store/jobs';

interface DashboardJobCardProps {
  job: Job;
}

// Per-status badge styling matching mockup token palette
const STATUS_BADGE: Record<string, { label: string; className: string; pulse?: boolean }> = {
  running:                { label: 'Running',       className: 'text-green-500 bg-green-500/10', pulse: true },
  queued:                 { label: 'Queued',         className: 'text-muted-foreground bg-muted' },
  completed:              { label: 'Completed',      className: 'text-primary bg-primary/10' },
  completed_with_warnings:{ label: 'With Warnings',  className: 'text-amber-500 bg-amber-500/10' },
  failed:                 { label: 'Failed',         className: 'text-destructive bg-destructive/10' },
  failed_insufficient:    { label: 'Insufficient',   className: 'text-orange-500 bg-orange-500/10' },
  cancelled:              { label: 'Cancelled',      className: 'text-orange-500 bg-orange-500/10' },
  disambiguating:         { label: 'Needs Input',    className: 'text-amber-500 bg-amber-500/10' },
};

export function DashboardJobCard({ job }: DashboardJobCardProps) {
  const router = useRouter();
  const isRunning = job.status === 'running';
  const isFailed = job.status === 'failed' || job.status === 'failed_insufficient';
  const title = job.title || job.prompt || 'Untitled Job';
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const sourceCount = job.artifacts?.doc_urls?.length ?? 0;

  const badge = STATUS_BADGE[job.status] ?? STATUS_BADGE.queued;
  const borderClass = isFailed ? 'border-destructive/20 hover:border-destructive/40' : 'border-border hover:border-border';

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`bg-card border ${borderClass} rounded-xl p-4 cursor-pointer transition-all hover:shadow-[0_0_24px_rgba(59,130,246,0.08)]`}
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
            <span className="w-1.5 h-1.5 rounded-full bg-green-500 motion-safe:animate-pulse" />
          )}
          {badge.label}
        </span>
      </div>

      {/* Progress bar — running jobs only */}
      {isRunning && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
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
      <p className="text-[10px] text-muted-foreground">{formatRelativeTime(job.created_at)}</p>
    </div>
  );
}

export default DashboardJobCard;
