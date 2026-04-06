/**
 * ClaimExtractorView - Dedicated output view for claim extraction jobs.
 *
 * Shows claims grouped by source, each with: text, confidence badge,
 * speaker, framing, and significance indicator. Uses ClaimIndicators
 * for consistent visual language.
 */
import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ConfidenceBadge,
  SignificanceIndicator,
  DisputedClaimBadge,
} from '../common/ClaimIndicators';

// =============================================================================
// Types
// =============================================================================

interface ClaimItem {
  claim_id?: string;
  statement: string;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
  speaker?: string;
  framing?: string;
  significance?: 'high' | 'medium' | 'low';
  anchor?: string;
  source_id?: string;
}

interface SourceGroup {
  source_id: string;
  title: string;
  url?: string;
  claims: ClaimItem[];
}

// =============================================================================
// Props
// =============================================================================

export interface ClaimExtractorViewProps {
  /** Raw claims document data (from API) */
  data: Record<string, unknown>;
  /** Optional markdown content */
  markdown?: string;
}

// =============================================================================
// Helpers
// =============================================================================

/** Parse the claims data into grouped format */
function parseClaimsData(data: Record<string, unknown>): SourceGroup[] {
  // Try different data shapes the backend might return
  const sources = (data.sources || data.source_groups || []) as Array<Record<string, unknown>>;

  if (sources.length > 0) {
    return sources.map((source) => ({
      source_id: (source.source_id || source.id || 'unknown') as string,
      title: (source.title || source.name || 'Untitled Source') as string,
      url: source.url as string | undefined,
      claims: ((source.claims || source.extracted_claims || []) as Array<Record<string, unknown>>).map((c) => ({
        claim_id: c.claim_id as string | undefined,
        statement: (c.statement || c.text || c.claim || '') as string,
        confidence: c.confidence as ClaimItem['confidence'],
        speaker: c.speaker as string | undefined,
        framing: c.framing as string | undefined,
        significance: c.significance as ClaimItem['significance'],
        anchor: c.anchor as string | undefined,
        source_id: (c.source_id || source.source_id) as string | undefined,
      })),
    }));
  }

  // Flat claims array — group by source_id
  const flatClaims = (data.claims || data.extracted_claims || []) as Array<Record<string, unknown>>;
  if (flatClaims.length > 0) {
    const grouped = new Map<string, ClaimItem[]>();
    for (const c of flatClaims) {
      const sid = (c.source_id || 'unknown') as string;
      if (!grouped.has(sid)) grouped.set(sid, []);
      grouped.get(sid)!.push({
        claim_id: c.claim_id as string | undefined,
        statement: (c.statement || c.text || c.claim || '') as string,
        confidence: c.confidence as ClaimItem['confidence'],
        speaker: c.speaker as string | undefined,
        framing: c.framing as string | undefined,
        significance: c.significance as ClaimItem['significance'],
        anchor: c.anchor as string | undefined,
        source_id: sid,
      });
    }

    return Array.from(grouped.entries()).map(([sid, claims]) => ({
      source_id: sid,
      title: sid,
      claims,
    }));
  }

  return [];
}

// =============================================================================
// Component
// =============================================================================

export function ClaimExtractorView({ data }: ClaimExtractorViewProps) {
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [confidenceFilter, setConfidenceFilter] = useState<string | null>(null);

  const sourceGroups = useMemo(() => parseClaimsData(data), [data]);

  const totalClaims = useMemo(
    () => sourceGroups.reduce((sum, g) => sum + g.claims.length, 0),
    [sourceGroups]
  );

  const toggleSource = (sourceId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else {
        next.add(sourceId);
      }
      return next;
    });
  };

  const expandAll = () => {
    setExpandedSources(new Set(sourceGroups.map((g) => g.source_id)));
  };

  const collapseAll = () => {
    setExpandedSources(new Set());
  };

  // Filter claims by confidence
  const filterClaims = (claims: ClaimItem[]): ClaimItem[] => {
    if (!confidenceFilter) return claims;
    return claims.filter((c) => c.confidence === confidenceFilter);
  };

  if (sourceGroups.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-background p-8 text-center">
        <p className="text-muted-foreground">No claims extracted yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-foreground">
            Extracted Claims
          </h3>
          <span className="text-sm text-muted-foreground">
            {totalClaims} claim{totalClaims !== 1 ? 's' : ''} from {sourceGroups.length} source{sourceGroups.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Confidence filter */}
          <select
            value={confidenceFilter || ''}
            onChange={(e) => setConfidenceFilter(e.target.value || null)}
            className="text-xs rounded-lg border border-border bg-card px-2 py-1 text-muted-foreground"
          >
            <option value="">All Confidence</option>
            <option value="HIGH">HIGH only</option>
            <option value="MEDIUM">MEDIUM only</option>
            <option value="LOW">LOW only</option>
          </select>
          <button onClick={expandAll} className="text-xs text-blue-400 hover:text-blue-300 transition">
            Expand All
          </button>
          <span className="text-muted-foreground/60">|</span>
          <button onClick={collapseAll} className="text-xs text-muted-foreground hover:text-muted-foreground transition">
            Collapse All
          </button>
        </div>
      </div>

      {/* Source groups */}
      {sourceGroups.map((group) => {
        const filteredClaims = filterClaims(group.claims);
        const isExpanded = expandedSources.has(group.source_id);

        return (
          <motion.div
            key={group.source_id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-background overflow-hidden"
          >
            {/* Source header */}
            <button
              onClick={() => toggleSource(group.source_id)}
              className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-card/50 transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-muted-foreground/70 font-mono text-xs">{group.source_id}</span>
                <span className="text-sm font-medium text-foreground truncate">{group.title}</span>
                <span className="text-xs text-muted-foreground/70 flex-shrink-0">
                  {filteredClaims.length} claim{filteredClaims.length !== 1 ? 's' : ''}
                </span>
              </div>
              <svg
                className={`w-4 h-4 text-muted-foreground/70 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Claims list */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-t border-border"
                >
                  <div className="divide-y divide-gray-800">
                    {filteredClaims.map((claim, i) => (
                      <div key={claim.claim_id || i} className="px-5 py-3.5">
                        <div className="flex items-start gap-3">
                          {/* Claim number */}
                          <span className="text-xs font-mono text-muted-foreground/60 mt-0.5 flex-shrink-0 w-6 text-right">
                            {i + 1}.
                          </span>

                          <div className="flex-1 min-w-0">
                            {/* Statement */}
                            <p className="text-sm text-foreground leading-relaxed">
                              {claim.statement}
                            </p>

                            {/* Metadata row */}
                            <div className="flex items-center gap-3 mt-2 flex-wrap">
                              {claim.confidence && (
                                <ConfidenceBadge level={claim.confidence} />
                              )}
                              {claim.significance && (
                                <SignificanceIndicator level={claim.significance} />
                              )}
                              {claim.speaker && (
                                <span className="text-xs text-muted-foreground">
                                  🗣️ {claim.speaker}
                                </span>
                              )}
                              {claim.framing && claim.framing !== 'factual' && (
                                <DisputedClaimBadge framing={claim.framing} />
                              )}
                            </div>

                            {/* Anchor quote */}
                            {claim.anchor && (
                              <div className="mt-2 pl-3 border-l-2 border-border">
                                <p className="text-xs text-muted-foreground/70 italic line-clamp-2">
                                  &ldquo;{claim.anchor}&rdquo;
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}

                    {filteredClaims.length === 0 && (
                      <div className="px-5 py-4 text-center">
                        <p className="text-xs text-muted-foreground/70">No claims match the current filter.</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}

export default ClaimExtractorView;
