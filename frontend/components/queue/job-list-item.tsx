'use client';

/**
 * Compact table-like row for a single job in the queue view.
 * Clicking navigates to the job detail page.
 */
import { useRouter } from 'next/navigation';
import { StatusBadge } from '@/components/job/status-badge';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { pipelineLabels } from '@/components/job-card/job-card-config';
import { formatRelativeTime } from '@/lib/time-utils';
import type { Job } from '@/store/jobs';

interface JobListItemProps {
  job: Job;
}

export function JobListItem({ job }: JobListItemProps) {
  const router = useRouter();
  const title = job.title || job.prompt;
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const isRunning = job.status === 'running';

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[#12121a] border border-[#27272a] hover:border-[#3f3f46] cursor-pointer transition-colors"
    >
      {/* Title */}
      <p className="flex-1 text-sm text-[#f5f5f5] truncate min-w-0">{title}</p>

      {/* Progress */}
      {isRunning && (
        <div className="w-24 shrink-0">
          <Progress value={job.progress_percent} className="h-1" />
        </div>
      )}

      {/* Mode badge */}
      <Badge variant="outline" className="text-xs text-[#a1a1aa] border-[#27272a] shrink-0 hidden sm:flex">
        {modeLabel}
      </Badge>

      {/* Status */}
      <StatusBadge status={job.status} className="shrink-0" />

      {/* Date */}
      <span className="text-xs text-[#71717a] shrink-0 hidden md:block w-20 text-right">
        {formatRelativeTime(job.created_at)}
      </span>
    </div>
  );
}
