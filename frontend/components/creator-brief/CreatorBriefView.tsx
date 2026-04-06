/**
 * CreatorBriefView — Full-width hero component for the Creator Brief (Doc 3).
 *
 * Renders all Creator Brief sections: hooks, setup, twist, core facts,
 * analogy, personal stakes, cliffhanger, description sources, and disputed claims.
 *
 * Core facts are clickable for drill-down into provenance chain.
 */
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import DocumentHeader from '../common/DocumentHeader';
import {
  DisputedClaimBadge,
  SignificanceIndicator,
  SourceCitation,
} from '../common/ClaimIndicators';
import CopyButton from '../common/CopyButton';
import { useJobsStore } from '../../store/jobs';

// =============================================================================
// Types (matching backend CreatorBriefDocument model)
// =============================================================================

interface HookOption {
  hook_id: string;
  text: string;
  why_it_works: string;
  claim_id: string;
  source_id: string;
}

interface Setup {
  text: string;
  supporting_claim_ids: string[];
  supporting_source_ids: string[];
}

interface Twist {
  text: string;
  claim_id: string;
  source_id: string;
  framing: string;
}

interface CoreFact {
  fact_id: string;
  statement: string;
  say_it_like: string;
  significance: string;
  claim_id: string;
  source_id: string;
  speaker?: string;
}

interface Analogy {
  text: string;
  supporting_claim_ids: string[];
}

interface PersonalStakes {
  text: string;
  supporting_claim_ids: string[];
}

interface Cliffhanger {
  text: string;
  claim_id?: string;
  framing: string;
}

interface DescriptionSource {
  source_id: string;
  title: string;
  url?: string;
  creator?: string;
}

interface DisputedClaim {
  claim_id: string;
  statement: string;
  framing: string;
  speaker?: string;
  source_id: string;
}

interface CreatorBriefData {
  document_type: string;
  document_version: string;
  job_id: string;
  generated_at: string;
  topic: string;
  source_count: number;
  hook_options: HookOption[];
  setup: Setup;
  twist?: Twist | null;
  core_facts: CoreFact[];
  analogy?: Analogy | null;
  personal_stakes?: PersonalStakes | null;
  cliffhanger?: Cliffhanger | null;
  description_sources: DescriptionSource[];
  disputed_claims: DisputedClaim[];
}

// =============================================================================
// Props
// =============================================================================

export interface CreatorBriefViewProps {
  /** Job ID to fetch the Creator Brief for */
  jobId: string;
  /** Optional pre-loaded data (avoids re-fetch) */
  data?: CreatorBriefData;
  /** Callback when user clicks a core fact for drill-down */
  onFactClick?: (fact: CoreFact) => void;
  /** Callback for contextual navigation to other documents */
  onNavigateToDoc?: (docType: string) => void;
  /** Whether this is a preview (Quick Brief) */
  isPreview?: boolean;
  /** Optional className */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function CreatorBriefView({
  jobId,
  data: preloadedData,
  onFactClick,
  onNavigateToDoc,
  isPreview = false,
  className = '',
}: CreatorBriefViewProps) {
  const [brief, setBrief] = useState<CreatorBriefData | null>(preloadedData || null);
  const [loading, setLoading] = useState(!preloadedData);
  const [error, setError] = useState<string | null>(null);
  const [selectedHook, setSelectedHook] = useState<string>('HOOK_A');
  const fetchDocumentByVersion = useJobsStore((s) => s.fetchDocumentByVersion);

  // Fetch Creator Brief data
  useEffect(() => {
    if (preloadedData) {
      setBrief(preloadedData);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const fetchBrief = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await fetchDocumentByVersion(jobId, 'doc_3');
        if (!cancelled && result.data) {
          setBrief(result.data as unknown as CreatorBriefData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load Creator Brief');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchBrief();
    return () => { cancelled = true; };
  }, [jobId, preloadedData, fetchDocumentByVersion]);

  // Build description sources text for copy
  const buildSourcesText = useCallback(() => {
    if (!brief?.description_sources?.length) return '';
    return brief.description_sources
      .map((s) => {
        const parts = [s.title];
        if (s.creator) parts.push(`by ${s.creator}`);
        if (s.url) parts.push(s.url);
        return parts.join(' — ');
      })
      .join('\n');
  }, [brief]);

  // Loading state
  if (loading) {
    return (
      <div className={`max-w-4xl mx-auto px-4 py-8 ${className}`}>
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-card rounded w-1/3" />
          <div className="h-4 bg-card rounded w-2/3" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="h-32 bg-card rounded-xl" />
            <div className="h-32 bg-card rounded-xl" />
          </div>
          <div className="h-24 bg-card rounded-xl" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-card rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`max-w-4xl mx-auto px-4 py-8 ${className}`}>
        <div className="rounded-xl border border-red-800/50 bg-red-900/20 p-6 text-center">
          <p className="text-red-400 font-medium">Failed to load Creator Brief</p>
          <p className="text-sm text-red-300/70 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!brief) return null;

  return (
    <div className={`max-w-4xl mx-auto px-4 py-6 ${className}`}>
      {/* Preview badge */}
      {isPreview && (
        <div className="mb-4 px-3 py-1.5 bg-yellow-900/30 border border-yellow-700/50 rounded-lg inline-flex items-center gap-2">
          <span className="text-yellow-400 text-xs font-semibold uppercase tracking-wide">Preview</span>
          <span className="text-yellow-300/70 text-xs">This is a preview — run full research for the complete brief</span>
        </div>
      )}

      {/* Header */}
      <DocumentHeader
        docType="doc_3"
        title="Creator Brief"
        subtitle={brief.topic}
        sourceCount={brief.source_count}
        date={brief.generated_at}
        isHero={!isPreview}
      />

      {/* Hook Options */}
      {brief.hook_options?.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Hook Options
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {brief.hook_options.map((hook) => (
              <motion.div
                key={hook.hook_id}
                whileHover={{ scale: 1.01 }}
                onClick={() => setSelectedHook(hook.hook_id)}
                className={`
                  rounded-xl border-2 p-4 cursor-pointer transition-all duration-200
                  ${selectedHook === hook.hook_id
                    ? 'border-amber-500 bg-amber-900/20'
                    : 'border-border bg-card/50 hover:border-border'
                  }
                `}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-amber-400 uppercase">
                    {hook.hook_id.replace('_', ' ')}
                  </span>
                  {selectedHook === hook.hook_id && (
                    <span className="text-amber-400 text-xs">Selected</span>
                  )}
                </div>
                <p className="text-foreground text-sm leading-relaxed italic">
                  &ldquo;{hook.text}&rdquo;
                </p>
                <p className="text-xs text-muted-foreground/70 mt-2">
                  {hook.why_it_works}
                </p>
                <SourceCitation sourceId={hook.source_id} className="mt-2" />
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Setup */}
      {brief.setup && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Setup
          </h3>
          <div className="rounded-xl bg-card/50 border border-border p-5">
            <p className="text-foreground leading-relaxed">{brief.setup.text}</p>
            {brief.setup.supporting_source_ids?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {brief.setup.supporting_source_ids.map((sid) => (
                  <SourceCitation key={sid} sourceId={sid} onClick={onNavigateToDoc ? () => onNavigateToDoc('doc_0') : undefined} />
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Twist */}
      {brief.twist && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            The Twist
          </h3>
          <div className="rounded-xl bg-orange-900/10 border border-orange-800/30 p-5">
            <div className="flex items-start gap-3">
              <span className="text-orange-400 text-xl mt-0.5" aria-hidden="true">↩️</span>
              <div className="flex-1">
                <p className="text-foreground leading-relaxed">{brief.twist.text}</p>
                <div className="flex items-center gap-3 mt-3">
                  <DisputedClaimBadge framing={brief.twist.framing} />
                  <SourceCitation sourceId={brief.twist.source_id} />
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Core Facts */}
      {brief.core_facts?.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Core Facts
          </h3>
          <div className="space-y-3">
            {brief.core_facts.map((fact) => (
              <motion.div
                key={fact.fact_id}
                whileHover={onFactClick ? { scale: 1.005 } : {}}
                onClick={() => onFactClick?.(fact)}
                className={`
                  rounded-xl border border-border bg-card/50 p-5 transition-all
                  ${onFactClick ? 'cursor-pointer hover:border-amber-600/50 hover:bg-card' : ''}
                `}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    {/* Statement */}
                    <p className="text-foreground font-medium leading-relaxed">
                      {fact.statement}
                    </p>
                    {/* Say-it-like */}
                    <p className="text-sm text-amber-300/80 mt-2 italic">
                      Say it like: &ldquo;{fact.say_it_like}&rdquo;
                    </p>
                    {/* Metadata row */}
                    <div className="flex flex-wrap items-center gap-3 mt-3">
                      <SignificanceIndicator level={fact.significance} />
                      {fact.speaker && (
                        <span className="text-xs text-muted-foreground">
                          — {fact.speaker}
                        </span>
                      )}
                      <SourceCitation
                        sourceId={fact.source_id}
                        onClick={onNavigateToDoc ? () => onNavigateToDoc('doc_0') : undefined}
                      />
                    </div>
                  </div>
                  {/* Drill-down indicator */}
                  {onFactClick && (
                    <span className="text-muted-foreground/60 text-sm flex-shrink-0 mt-1" aria-label="Click for details">
                      →
                    </span>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Analogy */}
      {brief.analogy && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Analogy
          </h3>
          <div className="rounded-xl bg-blue-900/10 border border-blue-800/30 p-5">
            <div className="flex items-start gap-3">
              <span className="text-blue-400 text-xl" aria-hidden="true">💡</span>
              <p className="text-foreground leading-relaxed">{brief.analogy.text}</p>
            </div>
          </div>
        </section>
      )}

      {/* Personal Stakes */}
      {brief.personal_stakes && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Why This Matters
          </h3>
          <div className="rounded-xl bg-purple-900/10 border border-purple-800/30 p-5">
            <p className="text-foreground leading-relaxed">{brief.personal_stakes.text}</p>
          </div>
        </section>
      )}

      {/* Cliffhanger */}
      {brief.cliffhanger && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Cliffhanger
          </h3>
          <div className="rounded-xl bg-card/80 border border-border p-5">
            <div className="flex items-start gap-3">
              <span className="text-muted-foreground text-xl" aria-hidden="true">🎯</span>
              <div className="flex-1">
                <p className="text-foreground leading-relaxed italic">{brief.cliffhanger.text}</p>
                <DisputedClaimBadge framing={brief.cliffhanger.framing} className="mt-2" />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Disputed Claims */}
      {brief.disputed_claims?.length > 0 && (
        <section className="mb-8">
          <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wide mb-3">
            ⚠️ Disputed Claims
          </h3>
          <div className="space-y-2">
            {brief.disputed_claims.map((claim) => (
              <div
                key={claim.claim_id}
                className="rounded-lg bg-red-900/10 border border-red-800/30 p-5"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-1">
                    <p className="text-muted-foreground text-sm">{claim.statement}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <DisputedClaimBadge framing={claim.framing} />
                      {claim.speaker && (
                        <span className="text-xs text-muted-foreground/70">— {claim.speaker}</span>
                      )}
                      <SourceCitation sourceId={claim.source_id} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Description Sources */}
      {brief.description_sources?.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Sources for Description
            </h3>
            <CopyButton text={buildSourcesText()} label="Copy" copiedLabel="Copied!" size="sm" />
          </div>
          <div className="rounded-xl bg-card/50 border border-border p-5">
            <ul className="space-y-2">
              {brief.description_sources.map((source) => (
                <li key={source.source_id} className="flex items-start gap-2 text-sm">
                  <span className="text-muted-foreground/70 flex-shrink-0">•</span>
                  <div className="flex-1 min-w-0">
                    <span className="text-foreground">{source.title}</span>
                    {source.creator && (
                      <span className="text-muted-foreground/70"> by {source.creator}</span>
                    )}
                    {source.url && (
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-blue-400 hover:text-blue-300 text-xs truncate mt-0.5"
                      >
                        {source.url}
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {/* Contextual Navigation */}
      {onNavigateToDoc && (
        <section className="mt-10 pt-6 border-t border-border">
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => onNavigateToDoc('doc_2')}
              className="px-4 py-2.5 rounded-lg bg-purple-900/20 border border-purple-700/50 text-purple-300 text-sm font-medium hover:bg-purple-900/30 transition-colors"
            >
              📊 View Research
            </button>
            <button
              onClick={() => onNavigateToDoc('doc_1')}
              className="px-4 py-2.5 rounded-lg bg-blue-900/20 border border-blue-700/50 text-blue-300 text-sm font-medium hover:bg-blue-900/30 transition-colors"
            >
              🚀 Go Deeper
            </button>
            <button
              onClick={() => onNavigateToDoc('doc_0')}
              className="px-4 py-2.5 rounded-lg bg-card border border-border text-muted-foreground text-sm font-medium hover:bg-muted transition-colors"
            >
              📋 View Sources
            </button>
            <button
              disabled
              className="px-4 py-2.5 rounded-lg bg-background border border-border text-muted-foreground/60 text-sm font-medium cursor-not-allowed"
              title="Coming in v2"
            >
              🔒 Generate Script
            </button>
          </div>
        </section>
      )}
    </div>
  );
}

export default CreatorBriefView;
