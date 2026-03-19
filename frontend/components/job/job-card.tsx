'use client';

/**
 * JobCard — clickable card for a single research job.
 * Shows title, status, pipeline mode, source count, date, and progress if running.
 */
import { useRouter } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { StatusBadge } from './status-badge';
import { pipelineLabels } from '@/components/job-card/job-card-config';
import { formatRelativeTime } from '@/lib/time-utils';
import type { Job } from '@/store/jobs';

interface JobCardProps {
  job: Job;
}

export function JobCard({ job }: JobCardProps) {
  const router = useRouter();
  const isRunning = job.status === 'running';
  const title = job.title || job.prompt;
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const sourceCount = (job.artifacts?.doc_urls?.length) ?? 0;

  return (
    <Card
      onClick={() => router.push(`/jobs/${job.id}`)}
      className="cursor-pointer bg-[#12121a] border-[#27272a] hover:border-[#3f3f46] transition-colors"
    >
      <CardContent className="p-4 flex flex-col gap-3">
        {/* Title */}
        <p className="text-sm font-medium text-[#f5f5f5] line-clamp-2 leading-snug">
          {title}
        </p>

        {/* Status + mode row */}
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={job.status} />
          <Badge variant="outline" className="text-xs text-[#a1a1aa] border-[#27272a]">
            {modeLabel}
          </Badge>
          {sourceCount > 0 && (
            <span className="text-xs text-[#71717a]">{sourceCount} source{sourceCount !== 1 ? 's' : ''}</span>
          )}
        </div>

        {/* Progress bar when running */}
        {isRunning && (
          <Progress value={job.progress_percent} className="h-1" />
        )}

        {/* Date */}
        <p className="text-xs text-[#71717a]">
          {formatRelativeTime(job.created_at)}
        </p>
      </CardContent>
    </Card>
  );
}
