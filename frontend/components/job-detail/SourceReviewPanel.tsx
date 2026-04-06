/**
 * SourceReviewPanel - Card-based UI for reviewing search candidates.
 *
 * Displayed when an EXPAND run with auto-search enters AWAITING_REVIEW status.
 * Users can approve or reject individual search candidates before processing continues.
 * Each candidate is shown as a card with title, URL, quality score, and snippet.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useJobsStore } from '../../store/jobs';
import type { SearchCandidate } from '../../types/run';

interface SourceReviewPanelProps {
  jobId: string;
  runId: string;
  onComplete: () => void;
}

/** Quality score color based on relevance */
function getScoreColor(score: number): string {
  if (score >= 0.7) return 'text-green-400';
  if (score >= 0.5) return 'text-yellow-400';
  return 'text-muted-foreground';
}

/** Quality score bar width */
function getScoreWidth(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Quality score bg color for bar */
function getScoreBarColor(score: number): string {
  if (score >= 0.7) return 'bg-green-500';
  if (score >= 0.5) return 'bg-yellow-500';
  return 'bg-gray-500';
}

/** Source type badge from provider */
function getProviderBadge(provider: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    google: { label: 'Web', color: 'bg-blue-900/40 text-blue-300' },
    news: { label: 'News', color: 'bg-purple-900/40 text-purple-300' },
    youtube: { label: 'Video', color: 'bg-red-900/40 text-red-300' },
    reddit: { label: 'Reddit', color: 'bg-orange-900/40 text-orange-300' },
  };
  return map[provider] || { label: provider, color: 'bg-muted text-muted-foreground' };
}

export function SourceReviewPanel({ jobId, runId, onComplete }: SourceReviewPanelProps) {
  const { getSearchCandidates, approveSearchSources, actionInProgress } = useJobsStore();

  const [candidates, setCandidates] = useState<SearchCandidate[]>([]);
  const [selectedUrls, setSelectedUrls] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load candidates on mount
  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      try {
        const results = await getSearchCandidates(jobId, runId);
        setCandidates(results);
        // Select all by default
        setSelectedUrls(new Set(results.map((c) => c.url)));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load candidates');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [jobId, runId, getSearchCandidates]);

  const toggleCandidate = (url: string) => {
    setSelectedUrls((prev) => {
      const next = new Set(prev);
      if (next.has(url)) {
        next.delete(url);
      } else {
        next.add(url);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelectedUrls(new Set(candidates.map((c) => c.url)));
  };

  const deselectAll = () => {
    setSelectedUrls(new Set());
  };

  const handleApprove = async () => {
    if (selectedUrls.size === 0) return;
    try {
      await approveSearchSources(jobId, runId, Array.from(selectedUrls));
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve sources');
    }
  };

  const isSubmitting = actionInProgress === 'iteration';

  if (isLoading) {
    return (
      <div className="p-6 bg-blue-900/10 border border-blue-700/30 rounded-xl">
        <div className="flex items-center gap-3 text-blue-300 text-sm">
          <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          Discovering sources…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-xl">
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="p-4 bg-muted/50 border border-border/50 rounded-xl">
        <p className="text-muted-foreground text-sm">No search candidates found.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-blue-900/10 border border-blue-700/30 rounded-xl overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-blue-700/20">
        <div>
          <h4 className="text-sm font-semibold text-blue-300 flex items-center gap-2">
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Review Sources
          </h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            {candidates.length} source{candidates.length !== 1 ? 's' : ''} found — select which ones to include
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <button
            onClick={selectAll}
            className="px-2 py-1 rounded text-blue-400 hover:text-blue-300 hover:bg-blue-900/30 transition"
          >
            Select All
          </button>
          <button
            onClick={deselectAll}
            className="px-2 py-1 rounded text-muted-foreground hover:text-muted-foreground hover:bg-card transition"
          >
            Deselect All
          </button>
        </div>
      </div>

      {/* Source cards */}
      <div className="p-4 space-y-2 max-h-[400px] overflow-y-auto">
        {candidates.map((candidate, index) => {
          const isSelected = selectedUrls.has(candidate.url);
          const badge = getProviderBadge(candidate.provider);

          return (
            <motion.button
              key={candidate.url}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => toggleCandidate(candidate.url)}
              className={`
                w-full text-left rounded-xl border-2 p-4 transition-all duration-150
                ${isSelected
                  ? 'border-blue-500/50 bg-blue-500/5'
                  : 'border-border bg-card/30 opacity-50'
                }
              `}
            >
              <div className="flex items-start gap-3">
                {/* Toggle indicator */}
                <div className={`
                  mt-0.5 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                  ${isSelected
                    ? 'border-blue-500 bg-blue-500'
                    : 'border-border bg-card'
                  }
                `}>
                  {isSelected && (
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-foreground truncate">
                      {candidate.title || 'Untitled'}
                    </span>
                    <span className={`text-caption px-1.5 py-0.5 rounded-full font-medium ${badge.color}`}>
                      {badge.label}
                    </span>
                  </div>

                  {/* Snippet */}
                  <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{candidate.snippet}</p>

                  {/* Bottom row: URL + quality score */}
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-caption text-muted-foreground/70 truncate font-mono flex-1">
                      {candidate.url}
                    </span>

                    {/* Quality score bar */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${getScoreBarColor(candidate.relevance_score)}`}
                          style={{ width: getScoreWidth(candidate.relevance_score) }}
                        />
                      </div>
                      <span className={`text-caption font-mono ${getScoreColor(candidate.relevance_score)}`}>
                        {Math.round(candidate.relevance_score * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-between px-5 py-4 border-t border-blue-700/20 bg-background/50">
        <span className="text-xs text-muted-foreground">
          {selectedUrls.size} of {candidates.length} selected
        </span>
        <button
          onClick={handleApprove}
          disabled={isSubmitting || selectedUrls.size === 0}
          className={`
            px-5 py-2 rounded-lg text-sm font-medium transition-all
            ${selectedUrls.size > 0 && !isSubmitting
              ? 'bg-blue-600 hover:bg-blue-500 text-white'
              : 'bg-card text-muted-foreground/60 cursor-not-allowed'
            }
          `}
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Processing…
            </span>
          ) : (
            `Approve ${selectedUrls.size} Source${selectedUrls.size !== 1 ? 's' : ''}`
          )}
        </button>
      </div>
    </motion.div>
  );
}

export default SourceReviewPanel;
