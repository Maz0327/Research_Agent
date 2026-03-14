/**
 * ConfidenceBadge — Colored confidence level indicator.
 *
 * GREEN = high, YELLOW = medium, ORANGE = low.
 */

import type { ConfidenceLevel } from '@/types/documents';

interface ConfidenceBadgeProps {
  level: ConfidenceLevel | string;
  size?: 'sm' | 'md';
}

const styles: Record<string, { bg: string; text: string; dot: string }> = {
  high: { bg: 'bg-green-900/30', text: 'text-green-400', dot: 'bg-green-400' },
  medium: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', dot: 'bg-yellow-400' },
  low: { bg: 'bg-orange-900/30', text: 'text-orange-400', dot: 'bg-orange-400' },
};

export function ConfidenceBadge({ level, size = 'sm' }: ConfidenceBadgeProps) {
  const normalized = level?.toLowerCase() || 'unknown';
  const s = styles[normalized] || { bg: 'bg-gray-800/50', text: 'text-gray-400', dot: 'bg-gray-500' };

  const sizeClasses = size === 'sm'
    ? 'px-2 py-0.5 text-[11px]'
    : 'px-2.5 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${s.bg} ${s.text} ${sizeClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {normalized.charAt(0).toUpperCase() + normalized.slice(1)}
    </span>
  );
}
