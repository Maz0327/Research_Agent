/**
 * Shared time formatting utilities.
 *
 * Extracted from queue.tsx, DashboardJobCard.tsx, JobDetailHeader.tsx,
 * and RunSelector.tsx to eliminate duplication (Audit Fix 14.1).
 */

/** Format a date string as relative time (e.g., "2h ago", "3d ago") */
export function formatRelativeTime(dateString?: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/** Format elapsed time since a start time (e.g., "3m 42s") */
export function formatElapsedTime(startTime?: string): string {
  if (!startTime) return '-';
  const start = new Date(startTime);
  const now = new Date();
  const diffSec = Math.floor((now.getTime() - start.getTime()) / 1000);

  if (diffSec < 60) return `${diffSec}s`;
  const mins = Math.floor(diffSec / 60);
  const secs = diffSec % 60;
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

/** Estimate ETA based on progress percentage and elapsed time */
export function estimateETA(progress: number, startTime?: string): string {
  if (!startTime || progress <= 0 || progress >= 100) return '-';

  const start = new Date(startTime);
  const now = new Date();
  const elapsedMs = now.getTime() - start.getTime();

  const estimatedTotalMs = (elapsedMs / progress) * 100;
  const remainingMs = estimatedTotalMs - elapsedMs;

  if (remainingMs <= 0) return 'Soon';

  const remainingSec = Math.floor(remainingMs / 1000);
  if (remainingSec < 60) return `~${remainingSec}s`;
  const mins = Math.floor(remainingSec / 60);
  if (mins < 60) return `~${mins}m`;
  const hours = Math.floor(mins / 60);
  return `~${hours}h ${mins % 60}m`;
}
