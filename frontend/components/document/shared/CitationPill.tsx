/**
 * CitationPill — Inline source reference badge.
 *
 * Renders a compact pill like [S1] or [Source 1] depending on mode.
 * Used inline within key points, claims, and other semantic units.
 */

import { formatInternalId } from '@/lib/document-formatters';

interface CitationPillProps {
  sourceId: string;
  showDetails?: boolean;
}

export function CitationPill({ sourceId, showDetails = false }: CitationPillProps) {
  // Short form: S1, KP1 etc. Long form: Source 1, Key Point 1
  const shortLabel = sourceId.replace('SRC_', 'S').replace(/^KP_/i, 'KP');
  const longLabel = formatInternalId(sourceId);
  const label = showDetails ? `${longLabel} (${sourceId})` : shortLabel;

  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-gray-700/60 text-gray-400 border border-gray-600/40 whitespace-nowrap"
      title={longLabel}
    >
      {label}
    </span>
  );
}
