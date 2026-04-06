/**
 * source-map-utils — Extracts source_id → {url, title, type} map from Doc 0 (Source Ledger).
 * Used by document renderers to make citation pills clickable.
 */

import type { SourceLedgerData } from '@/types/documents';

export interface SourceInfo {
  url?: string;
  title?: string;
  sourceType?: string;
  creator?: string | null;
}

/** Maps source_id → SourceInfo for quick lookup by citation pills */
export type SourceMap = Record<string, SourceInfo>;

/**
 * Build a source map from raw Doc 0 content.
 * Returns empty map if data is missing or malformed.
 */
export function buildSourceMap(doc0Content: Record<string, unknown> | null | undefined): SourceMap {
  if (!doc0Content) return {};

  const data = doc0Content as unknown as SourceLedgerData;
  const sources = data?.sources;

  if (!Array.isArray(sources)) return {};

  const map: SourceMap = {};
  for (const source of sources) {
    if (source.source_id) {
      map[source.source_id] = {
        url: source.url || undefined,
        title: source.title || undefined,
        sourceType: source.source_type || undefined,
        creator: source.creator ?? null,
      };
    }
  }

  return map;
}

/**
 * Format tooltip text for a source entry.
 * Example: "YouTube: 'The Dark Side of AI' by TechAltar"
 */
export function formatSourceTooltip(info: SourceInfo): string {
  const parts: string[] = [];

  if (info.sourceType) {
    const type = info.sourceType.charAt(0).toUpperCase() + info.sourceType.slice(1).toLowerCase();
    parts.push(type + ':');
  }

  if (info.title) {
    parts.push(`'${info.title}'`);
  }

  if (info.creator) {
    parts.push(`by ${info.creator}`);
  }

  return parts.length > 0 ? parts.join(' ') : 'View source';
}
