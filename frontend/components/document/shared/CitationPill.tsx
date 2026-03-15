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
  const friendlyLabel = formatInternalId(sourceId);
  // Default: show friendly label ("Source 1"). Debug: show both ("Source 1 (SRC_1)")
  const label = showDetails ? `${friendlyLabel} (${sourceId})` : friendlyLabel;

  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-gray-700/60 text-gray-400 border border-gray-600/40 whitespace-nowrap"
      title={showDetails ? sourceId : friendlyLabel}
    >
      {label}
    </span>
  );
}
