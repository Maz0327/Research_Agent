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
  running:                { label: 'Running',       className: 'text-[#22c55e] bg-[#22c55e]/10', pulse: true },
  queued:                 { label: 'Queued',         className: 'text-[#71717a] bg-[#222230]' },
  completed:              { label: 'Completed',      className: 'text-[#3b82f6] bg-[#3b82f6]/10' },
  completed_with_warnings:{ label: 'With Warnings',  className: 'text-[#f59e0b] bg-[#f59e0b]/10' },
  failed:                 { label: 'Failed',         className: 'text-[#ef4444] bg-[#ef4444]/10' },
  failed_insufficient:    { label: 'Insufficient',   className: 'text-[#f97316] bg-[#f97316]/10' },
  cancelled:              { label: 'Cancelled',      className: 'text-[#f97316] bg-[#f97316]/10' },
  disambiguating:         { label: 'Needs Input',    className: 'text-[#f59e0b] bg-[#f59e0b]/10' },
};

export function DashboardJobCard({ job }: DashboardJobCardProps) {
  const router = useRouter();
  const isRunning = job.status === 'running';
  const isFailed = job.status === 'failed' || job.status === 'failed_insufficient';
  const title = job.title || job.prompt || 'Untitled Job';
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const sourceCount = job.artifacts?.doc_urls?.length ?? 0;

  const badge = STATUS_BADGE[job.status] ?? STATUS_BADGE.queued;
  const borderClass = isFailed ? 'border-[#ef4444]/20 hover:border-[#ef4444]/40' : 'border-[#27272a] hover:border-[#3f3f46]';

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`bg-[#12121a] border ${borderClass} rounded-xl p-4 cursor-pointer transition-all hover:shadow-[0_0_24px_rgba(59,130,246,0.08)]`}
    >
      {/* Title row + status badge */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[#f5f5f5] truncate">{title}</h3>
          <p className="text-xs text-[#71717a] mt-0.5">
            {modeLabel}
            {sourceCount > 0 && <> &middot; {sourceCount} source{sourceCount !== 1 ? 's' : ''}</>}
          </p>
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${badge.className}`}>
          {badge.pulse && (
            <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] animate-pulse" />
          )}
          {badge.label}
        </span>
      </div>

      {/* Progress bar — running jobs only */}
      {isRunning && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-[10px] text-[#71717a] mb-1">
            <span>{job.stage ?? 'Processing'}</span>
            <span>{job.progress_percent ?? 0}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-[#222230] overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#3b82f6] to-[#8b5cf6] transition-all duration-500"
              style={{ width: `${job.progress_percent ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Error message — failed jobs */}
      {isFailed && job.error && (
        <p className="text-xs text-[#ef4444]/80 mb-2 line-clamp-1">{job.error}</p>
      )}

      {/* Footer: time ago */}
      <p className="text-[10px] text-[#71717a]">{formatRelativeTime(job.created_at)}</p>
    </div>
  );
}

export default DashboardJobCard;
