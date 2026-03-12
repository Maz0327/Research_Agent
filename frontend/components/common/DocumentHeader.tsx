/**
 * DocumentHeader — Shared header component for all document views.
 *
 * Provides consistent color-coded badge, title, subtitle, and metadata
 * across Creator Brief, Semantic Brief, Jump-Start, Source Ledger, and Producer Packet.
 */

import { formatTimestamp } from '../../lib/document-formatters';

/** Document type color configuration */
const DOC_COLORS: Record<string, {
  badge: string;
  badgeText: string;
  accent: string;
  border: string;
}> = {
  doc_0: {
    badge: 'bg-gray-700',
    badgeText: 'text-gray-200',
    accent: 'text-gray-400',
    border: 'border-gray-700',
  },
  doc_1: {
    badge: 'bg-blue-900/60',
    badgeText: 'text-blue-200',
    accent: 'text-blue-400',
    border: 'border-blue-800/50',
  },
  doc_2: {
    badge: 'bg-purple-900/60',
    badgeText: 'text-purple-200',
    accent: 'text-purple-400',
    border: 'border-purple-800/50',
  },
  doc_3: {
    badge: 'bg-amber-900/60',
    badgeText: 'text-amber-200',
    accent: 'text-amber-400',
    border: 'border-amber-800/50',
  },
  doc_4: {
    badge: 'bg-green-900/60',
    badgeText: 'text-green-200',
    accent: 'text-green-400',
    border: 'border-green-800/50',
  },
  booster: {
    badge: 'bg-indigo-900/60',
    badgeText: 'text-indigo-200',
    accent: 'text-indigo-400',
    border: 'border-indigo-800/50',
  },
};

/** Document type display labels */
const DOC_LABELS: Record<string, string> = {
  doc_0: 'DOC 0',
  doc_1: 'DOC 1',
  doc_2: 'DOC 2',
  doc_3: 'DOC 3',
  doc_4: 'DOC 4',
  booster: 'DEEP RESEARCH',
};

export interface DocumentHeaderProps {
  /** Document type identifier (doc_0, doc_1, doc_2, doc_3, doc_4, booster) */
  docType: string;
  /** Document title (e.g., "Creator Brief") */
  title: string;
  /** Document subtitle (e.g., "Your hero document") */
  subtitle?: string;
  /** Current version number */
  version?: number;
  /** Number of sources in the research */
  sourceCount?: number;
  /** Number of claims extracted */
  claimCount?: number;
  /** Document creation/last-updated date (ISO string) */
  date?: string;
  /** Whether to show the hero badge (star icon for Creator Brief) */
  isHero?: boolean;
  /** Additional className */
  className?: string;
}

export function DocumentHeader({
  docType,
  title,
  subtitle,
  version,
  sourceCount,
  claimCount,
  date,
  isHero = false,
  className = '',
}: DocumentHeaderProps) {
  const colors = DOC_COLORS[docType] || DOC_COLORS.doc_0;
  const docLabel = DOC_LABELS[docType] || docType.toUpperCase();

  return (
    <div className={`border-b ${colors.border} pb-4 mb-6 ${className}`}>
      {/* Top row: badge + version + date */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-1 rounded-md text-xs font-bold tracking-wide ${colors.badge} ${colors.badgeText}`}>
            {docLabel}
          </span>
          {isHero && (
            <span className="text-amber-400 text-sm" title="Hero Document">
              ⭐
            </span>
          )}
          {version != null && (
            <span className="text-xs text-gray-500 font-mono">
              v{version}
            </span>
          )}
        </div>
        {date && (
          <span className="text-xs text-gray-500">
            {formatTimestamp(date)}
          </span>
        )}
      </div>

      {/* Title + subtitle */}
      <h2 className="text-xl font-semibold text-gray-100">{title}</h2>
      {subtitle && (
        <p className={`text-sm mt-0.5 ${colors.accent}`}>{subtitle}</p>
      )}

      {/* Stats row */}
      {(sourceCount != null || claimCount != null) && (
        <div className="flex items-center gap-4 mt-3">
          {sourceCount != null && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className="text-gray-500">📋</span>
              <span>{sourceCount} source{sourceCount !== 1 ? 's' : ''}</span>
            </div>
          )}
          {claimCount != null && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <span className="text-gray-500">📊</span>
              <span>{claimCount} claim{claimCount !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentHeader;
