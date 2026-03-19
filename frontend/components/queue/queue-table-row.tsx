'use client';

/**
 * Single row in the queue table.
 * Running: full opacity, stop button.
 * Queued: opacity-60, X button, position number.
 * Completed: opacity-40, green progress bar, no action.
 */
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
    return <span className="text-xs text-[#52525b]">Done</span>;
  }
  if (!stage || status === 'queued') {
    return <span className="text-xs text-[#52525b]">—</span>;
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
    return <span className="text-[10px] text-[#52525b]">Position #{queuePosition}</span>;
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
        <div className="flex-1 h-1.5 rounded-full bg-surface-3 overflow-hidden">
          <div
            className="h-full rounded-full bg-accent-blue"
            style={{ width: `${job.progress_percent ?? 0}%` }}
          />
        </div>
        <span className="text-[10px] text-[#71717a] w-8">{job.progress_percent ?? 0}%</span>
      </div>
    );
  }

  return null;
}

function StatusCell({ status }: { status: Job['status'] }) {
  if (status === 'running') {
    return (
      <span className="flex items-center gap-1.5 text-[10px] font-medium text-accent-green">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
        Running
      </span>
    );
  }
  if (status === 'queued') {
    return <span className="text-[10px] font-medium text-[#71717a]">Queued</span>;
  }
  if (status === 'completed' || status === 'completed_with_warnings') {
    return <span className="text-[10px] font-medium text-accent-green">Completed</span>;
  }
  if (status === 'failed' || status === 'failed_insufficient') {
    return <span className="text-[10px] font-medium text-accent-red">Failed</span>;
  }
  if (status === 'cancelled') {
    return <span className="text-[10px] font-medium text-[#71717a]">Cancelled</span>;
  }
  return <span className="text-[10px] font-medium text-[#71717a]">{status}</span>;
}

export function QueueTableRow({ job, queuePosition }: QueueTableRowProps) {
  const router = useRouter();
  const title = job.title || job.prompt;
  const modeLabel = pipelineLabels[job.pipeline] ?? job.pipeline;
  const isRunning = job.status === 'running';
  const isQueued = job.status === 'queued';
  const isCompleted = job.status === 'completed' || job.status === 'completed_with_warnings';

  const rowOpacity = isCompleted ? 'opacity-40' : isQueued ? 'opacity-60' : '';

  return (
    <tr
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`border-b border-border hover:bg-[#2a2a38] transition-colors cursor-pointer ${rowOpacity}`}
    >
      {/* Drag handle */}
      <td className="px-4 py-3 w-8">
        {!isCompleted && (
          <GripVertical className="w-4 h-4 text-[#52525b] cursor-grab" />
        )}
      </td>

      {/* Job title + meta */}
      <td className="px-4 py-3">
        <p className="text-sm font-medium truncate max-w-[250px]">{title}</p>
        <p className="text-[10px] text-[#71717a]">
          {modeLabel}
          {job.status === 'running' || job.status === 'completed' || job.status === 'completed_with_warnings'
            ? ''
            : ' · Pending'}
        </p>
      </td>

      {/* Mode */}
      <td className="px-4 py-3">
        <span className="text-xs text-[#a1a1aa]">{modeLabel}</span>
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
          <button className="text-[#52525b] hover:text-accent-red transition-colors">
            <Square className="w-4 h-4" />
          </button>
        )}
        {isQueued && (
          <button className="text-[#52525b] hover:text-accent-red transition-colors">
            <X className="w-4 h-4" />
          </button>
        )}
      </td>
    </tr>
  );
}
