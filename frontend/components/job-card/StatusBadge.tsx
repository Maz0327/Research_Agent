/**
 * Status badge component for displaying job status.
 */
import { statusConfig, JobStatus } from './job-card-config';

interface StatusBadgeProps {
  status: JobStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${config.bgColor} ${config.textColor}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${config.dotColor} ${status === 'running' ? 'animate-pulse' : ''}`}
      />
      {config.label}
    </span>
  );
}

export default StatusBadge;
