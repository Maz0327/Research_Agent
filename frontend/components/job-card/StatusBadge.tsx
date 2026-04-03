/**
 * Status badge component for displaying job status.
 * Includes Lucide icon + colored dot + label for non-color-only identification (WCAG M2).
 */
import { Check, X, Loader2, Clock, Ban, AlertTriangle, HelpCircle } from 'lucide-react';
import { statusConfig, JobStatus } from './job-card-config';

interface StatusBadgeProps {
  status: JobStatus;
}

/** Maps job status to a Lucide icon component */
function StatusIcon({ status }: { status: JobStatus }) {
  const iconClass = 'h-3.5 w-3.5 flex-shrink-0';
  switch (status) {
    case 'completed':
      return <Check className={iconClass} />;
    case 'failed':
    case 'failed_insufficient':
      return <X className={iconClass} />;
    case 'running':
      return <Loader2 className={`${iconClass} animate-spin`} />;
    case 'queued':
      return <Clock className={iconClass} />;
    case 'cancelled':
      return <Ban className={iconClass} />;
    case 'completed_with_warnings':
      return <AlertTriangle className={iconClass} />;
    case 'disambiguating':
      return <HelpCircle className={iconClass} />;
    default:
      return null;
  }
}

export function StatusBadge({ status }: StatusBadgeProps) {
  // Fallback to queued for unknown statuses
  const config = statusConfig[status] || statusConfig.queued;

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium ${config.bgColor} ${config.textColor}`}
    >
      <StatusIcon status={status} />
      <span
        className={`h-2 w-2 rounded-full ${config.dotColor} ${status === 'running' ? 'animate-pulse' : ''}`}
        style={{ boxShadow: status === 'running' ? '0 0 8px currentColor' : undefined }}
      />
      {config.label}
    </span>
  );
}

export default StatusBadge;
