/**
 * Status badge component for displaying job status.
 */
import { statusConfig, JobStatus } from './job-card-config';

interface StatusBadgeProps {
  status: JobStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  // Fallback to queued for unknown statuses
  const config = statusConfig[status] || statusConfig.queued;

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium ${config.bgColor} ${config.textColor}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${config.dotColor} ${status === 'running' ? 'animate-pulse' : ''}`}
        style={{ boxShadow: status === 'running' ? '0 0 8px currentColor' : undefined }}
      />
      {config.label}
    </span>
  );
}

export default StatusBadge;
