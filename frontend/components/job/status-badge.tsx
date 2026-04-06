'use client';

/**
 * Status badge for a research job — uses shadcn Badge.
 * Running status shows an animated pulse dot.
 */
import { Badge } from '@/components/ui/badge';
import type { Job } from '@/store/jobs';

type JobStatus = Job['status'];

interface StatusConfig {
  label: string;
  className: string;
  showPulse?: boolean;
}

const STATUS_CONFIG: Record<JobStatus, StatusConfig> = {
  running: {
    label: 'Running',
    className: 'bg-green-900/50 text-green-300 border-green-700',
    showPulse: true,
  },
  queued: {
    label: 'Queued',
    className: 'bg-card text-muted-foreground border-border',
  },
  completed: {
    label: 'Completed',
    className: 'bg-blue-900/50 text-blue-300 border-blue-700',
  },
  completed_with_warnings: {
    label: 'With Warnings',
    className: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  },
  failed: {
    label: 'Failed',
    className: 'bg-red-900/50 text-red-300 border-red-700',
  },
  failed_insufficient: {
    label: 'Insufficient',
    className: 'bg-orange-900/50 text-orange-300 border-orange-700',
  },
  cancelled: {
    label: 'Cancelled',
    className: 'bg-orange-900/50 text-orange-300 border-orange-700',
  },
  disambiguating: {
    label: 'Needs Input',
    className: 'bg-yellow-900/50 text-yellow-300 border-yellow-700',
  },
};

interface StatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.queued;

  return (
    <Badge
      variant="outline"
      className={`inline-flex items-center gap-1.5 ${config.className} ${className ?? ''}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === 'running'
            ? 'bg-green-400 animate-pulse'
            : status === 'completed'
            ? 'bg-blue-400'
            : status === 'failed' || status === 'failed_insufficient'
            ? 'bg-red-400'
            : status === 'cancelled'
            ? 'bg-orange-400'
            : 'bg-muted-foreground'
        }`}
      />
      {config.label}
    </Badge>
  );
}
