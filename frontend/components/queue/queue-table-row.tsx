'use client';

/**
 * Single row in the queue table.
 * Running: full opacity, stop button.
 * Queued: opacity-60, X button, position number.
 * Completed: opacity-40, green progress bar, no action.
 */
import React from 'react';
import { useRouter } from 'next/navigation';
import { GripVertical, Square, X } from 'lucide-react';
import { pipelineLabels } from '@/components/job-card/job-card-config';
import type { Job } from '@/store/jobs';

interface QueueTableRowProps {
  job: Job;
  queuePosition?: number; // 1-based, only for queued jobs
}

const STAGE_LABEL: Record<string, string> = {
  ingestion: 'Ingestion',
  extraction: 'Extraction',
  validation: 'Validation',
  synthesis: 'Synthesis',
  assembly: 'Assembly',
};

function StageCell({ stage, status }: { stage?: string; status: Job['status'] }) {
  if (status === 'completed' || status === 'completed_with_warnings') {
    return <span className="text-xs text-muted-foreground/60">Done</span>;
  }
  if (!stage || status === 'queued') {
    return <span className="text-xs text-muted-foreground/60">—</span>;
  }
  const label = STAGE_LABEL[stage.toLowerCase()] ?? stage;
  return <span className="text-xs text-accent-blue font-medium">{label}</span>;
}

function ProgressCell({
  job,
  queuePosition,
}: {
  job: Job;
  queuePosition?: number;
}) {
  const isCompleted = job.status === 'completed' || job.status === 'completed_with_warnings';
  const isRunning = job.status === 'running';

  if (job.status === 'queued') {
    return <span className="text-[10px] text-muted-foreground/60">Position #{queuePosition}</span>;
  }

  if (isCompleted) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-accent-green/20 overflow-hidden">
          <div className="h-full rounded-full bg-accent-green w-full" />
        </div>
        <span className="text-[10px] text-accent-green w-8">Done</span>
      </div>
    );
  }

  if (isRunning) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className="h-full rounded-full bg-accent-blue"
            style={{ width: `${job.progress_percent ?? 0}%` }}
          />
        </div>
        <span className="text-[10px] text-muted-foreground w-8">{job.progress_percent ?? 0}%</span>
      </div>
    );
  }

  return null;
}

function StatusCell({ status }: { status: Job['status'] }) {
  if (status === 'running') {
    return (
      <span className="flex items-center gap-1.5 text-[10px] font-medium text-accent-green">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-green motion-safe:animate-pulse" />
        Running
      </span>
    );
  }
  if (status === 'queued') {
    return <span className="text-[10px] font-medium text-muted-foreground">Queued</span>;
  }
  if (status === 'completed' || status === 'completed_with_warnings') {
    return <span className="text-[10px] font-medium text-accent-green">Completed</span>;
  }
  if (status === 'failed' || status === 'failed_insufficient') {
    return <span className="text-[10px] font-medium text-destructive">Failed</span>;
  }
  if (status === 'cancelled') {
    return <span className="text-[10px] font-medium text-muted-foreground">Cancelled</span>;
  }
  return <span className="text-[10px] font-medium text-muted-foreground">{status}</span>;
}

export function QueueTableRow({ job, queuePosition }: QueueTableRowProps) {
  const router = useRouter();
  const title = job.title || job.prompt;
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const isRunning = job.status === 'running';
  const isQueued = job.status === 'queued';
  const isCompleted = job.status === 'completed' || job.status === 'completed_with_warnings';

  const rowOpacity = isCompleted ? 'opacity-40' : isQueued ? 'opacity-60' : '';

  const handleRowKeyDown = (e: React.KeyboardEvent<HTMLTableRowElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      router.push(`/jobs/${job.id}`);
    }
  };

  return (
    <tr
      onClick={() => router.push(`/jobs/${job.id}`)}
      onKeyDown={handleRowKeyDown}
      role="button"
      tabIndex={0}
      className={`border-b border-border hover:bg-accent transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${rowOpacity}`}
    >
      {/* Drag handle */}
      <td className="px-4 py-3 w-8">
        {!isCompleted && (
          <GripVertical className="w-4 h-4 text-muted-foreground/60 cursor-grab" />
        )}
      </td>

      {/* Job title + meta */}
      <td className="px-4 py-3">
        <p className="text-sm font-medium truncate max-w-[250px]">{title}</p>
        <p className="text-[10px] text-muted-foreground">
          {modeLabel}
          {job.status === 'running' || job.status === 'completed' || job.status === 'completed_with_warnings'
            ? ''
            : ' · Pending'}
        </p>
      </td>

      {/* Mode */}
      <td className="px-4 py-3">
        <span className="text-xs text-muted-foreground">{modeLabel}</span>
      </td>

      {/* Stage */}
      <td className="px-4 py-3">
        <StageCell stage={job.stage} status={job.status} />
      </td>

      {/* Progress */}
      <td className="px-4 py-3 w-36">
        <ProgressCell job={job} queuePosition={queuePosition} />
      </td>

      {/* Status */}
      <td className="px-4 py-3">
        <StatusCell status={job.status} />
      </td>

      {/* Action */}
      <td className="px-4 py-3 w-10" onClick={(e) => e.stopPropagation()}>
        {isRunning && (
          <button
            aria-label="Stop job"
            className="text-muted-foreground/60 hover:text-destructive transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            <Square className="w-4 h-4" />
          </button>
        )}
        {isQueued && (
          <button
            aria-label="Remove from queue"
            className="text-muted-foreground/60 hover:text-destructive transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </td>
    </tr>
  );
}
