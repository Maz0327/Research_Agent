/**
 * SearchApprovalView — Source approval and Quick Brief preview for search discovery.
 *
 * Split layout: Quick Brief preview (left/top) + source candidate cards (right/bottom).
 * User selects/deselects sources, then clicks "Run Full Research" to create a job.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/router';
import QuickBriefPreview from './QuickBriefPreview';
import { useJobsStore } from '../../store/jobs';
import type { SearchCandidate } from '../../types/run';

interface SearchApprovalViewProps {
  onBack: () => void;
}

/** Color for relevance score */
function getScoreColor(score: number): string {
  if (score >= 0.7) return 'text-green-400';
  if (score >= 0.5) return 'text-yellow-400';
  return 'text-gray-500';
}

/** Width for score bar */
function getScoreBarWidth(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Bar color for relevance score */
function getScoreBarColor(score: number): string {
  if (score >= 0.7) return 'bg-green-500';
  if (score >= 0.5) return 'bg-yellow-500';
  return 'bg-gray-600';
}

/** Badge for provider */
function getProviderBadge(provider: string): { label: string; color: string } {
  switch (provider) {
    case 'tavily': return { label: 'Tavily', color: 'text-blue-400 bg-blue-400/10' };
    case 'serper': return { label: 'Serper', color: 'text-purple-400 bg-purple-400/10' };
    default: return { label: provider, color: 'text-gray-400 bg-gray-400/10' };
  }
}

/** Badge for source type */
function getSourceTypeBadge(type?: string): { label: string; icon: string } {
  switch (type) {
    case 'video': return { label: 'Video', icon: '🎬' };
    case 'reddit': return { label: 'Reddit', icon: '💬' };
    case 'social': return { label: 'Social', icon: '📱' };
    case 'academic': return { label: 'Academic', icon: '🎓' };
    case 'news': return { label: 'News', icon: '📰' };
    default: return { label: 'Web', icon: '🌐' };
  }
}

export default function SearchApprovalView({ onBack }: SearchApprovalViewProps) {
  const router = useRouter();
  const {
    searchResults,
    quickBrief,
    isLoadingQuickBrief,
    error,
    fetchQuickBrief,
    approveSearchSources_v2,
    clearSearchResults,
  } = useJobsStore();

  const candidates = useMemo(() => searchResults?.candidates || [], [searchResults?.candidates]);
  const [selectedUrls, setSelectedUrls] = useState<Set<string>>(
    new Set(candidates.map((c) => c.url))
  );
  const [isApproving, setIsApproving] = useState(false);

  // Sync selected URLs when candidates change (e.g., re-search)
  useEffect(() => {
    setSelectedUrls(new Set(candidates.map((c) => c.url)));
  }, [candidates]);

  const toggleCandidate = useCallback((url: string) => {
    setSelectedUrls((prev) => {
      const next = new Set(prev);
      if (next.has(url)) {
        next.delete(url);
      } else {
        next.add(url);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedUrls(new Set(candidates.map((c) => c.url)));
  }, [candidates]);

  const deselectAll = useCallback(() => {
    setSelectedUrls(new Set());
  }, []);

  const handleGenerateQuickBrief = useCallback(async () => {
    if (!searchResults?.search_id) return;
    try {
      await fetchQuickBrief(searchResults.search_id);
    } catch {
      // Error handled in store
    }
  }, [searchResults?.search_id, fetchQuickBrief]);

  const handleApprove = useCallback(async () => {
    if (!searchResults?.search_id || selectedUrls.size === 0) return;
    setIsApproving(true);
    try {
      const result = await approveSearchSources_v2(
        searchResults.search_id,
        Array.from(selectedUrls)
      );
      // Navigate to the new job
      router.push(`/jobs/${result.job_id}`);
    } catch {
      setIsApproving(false);
    }
  }, [searchResults?.search_id, selectedUrls, approveSearchSources_v2, router]);

  const handleBack = useCallback(() => {
    clearSearchResults();
    onBack();
  }, [clearSearchResults, onBack]);

  if (!searchResults) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="space-y-5"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base sm:text-lg font-semibold text-gray-100">
            Sources for: <span className="text-blue-300 break-words">{searchResults.topic}</span>
          </h3>
          <p className="text-xs sm:text-sm text-gray-500 mt-0.5">
            Found {searchResults.total_found} source{searchResults.total_found !== 1 ? 's' : ''}
            {' · '}
            {selectedUrls.size} selected
          </p>
        </div>
        <button
          onClick={handleBack}
          className="text-sm text-gray-400 hover:text-gray-300 transition"
        >
          ← New Search
        </button>
      </div>

      {/* Two-column layout on desktop, stacked on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Quick Brief Preview */}
        <div className="space-y-3">
          {quickBrief ? (
            <QuickBriefPreview brief={quickBrief.brief} />
          ) : !isLoadingQuickBrief ? (
            <div className="rounded-xl border border-gray-700 bg-gray-900/50 p-5">
              <p className="text-sm text-gray-400 mb-3">
                Generate a Quick Brief preview to see what your research will look like before committing.
              </p>
              <button
                onClick={handleGenerateQuickBrief}
                disabled={isLoadingQuickBrief}
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600/20 border border-amber-500/30 px-4 py-2 text-sm font-medium text-amber-300 hover:bg-amber-600/30 transition disabled:opacity-50"
              >
                {isLoadingQuickBrief ? (
                  <>
                    <div className="animate-spin h-4 w-4 border-2 border-amber-400 border-t-transparent rounded-full" />
                    Generating…
                  </>
                ) : (
                  <>
                    <span>✨</span>
                    Generate Quick Brief
                  </>
                )}
              </button>
            </div>
          ) : null}

          {isLoadingQuickBrief && !quickBrief && (
            <QuickBriefPreview brief={{}} isLoading />
          )}
        </div>

        {/* Right: Source Candidates */}
        <div className="space-y-3">
          {/* Select all / deselect all */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">Sources</span>
            <div className="flex gap-1">
              <button
                onClick={selectAll}
                className="text-xs text-blue-400 hover:text-blue-300 transition px-2 py-1.5 min-h-[36px] touch-manipulation rounded"
              >
                Select All
              </button>
              <span className="text-gray-600 self-center">·</span>
              <button
                onClick={deselectAll}
                className="text-xs text-gray-400 hover:text-gray-300 transition px-2 py-1.5 min-h-[36px] touch-manipulation rounded"
              >
                Deselect All
              </button>
            </div>
          </div>

          {/* Candidate cards */}
          <div className="space-y-2 max-h-[60vh] sm:max-h-[500px] overflow-y-auto pr-1">
            <AnimatePresence>
              {candidates.map((candidate, i) => {
                const isSelected = selectedUrls.has(candidate.url);
                const providerBadge = getProviderBadge(candidate.provider);
                const sourceType = getSourceTypeBadge(candidate.source_type);

                return (
                  <motion.button
                    key={candidate.url}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => toggleCandidate(candidate.url)}
                    aria-label={`Toggle source: ${candidate.title || candidate.url}`}
                    className={`w-full text-left rounded-lg border p-3 transition-all touch-manipulation ${
                      isSelected
                        ? 'border-blue-500/50 bg-blue-500/5'
                        : 'border-gray-700/50 bg-gray-800/20 opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Checkbox */}
                      <div className={`mt-0.5 flex-shrink-0 h-5 w-5 rounded border-2 flex items-center justify-center transition ${
                        isSelected
                          ? 'border-blue-500 bg-blue-500'
                          : 'border-gray-600'
                      }`}>
                        {isSelected && (
                          <svg className="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-200 truncate">
                          {candidate.title || candidate.url}
                        </h4>
                        <p className="text-xs text-gray-500 truncate mt-0.5">{candidate.url}</p>
                        {candidate.snippet && (
                          <p className="text-xs text-gray-400 mt-1 line-clamp-2">{candidate.snippet}</p>
                        )}

                        {/* Meta badges */}
                        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mt-2">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${providerBadge.color}`}>
                            {providerBadge.label}
                          </span>
                          <span className="text-xs text-gray-500">
                            {sourceType.icon} {sourceType.label}
                          </span>
                          <span className={`text-xs ${getScoreColor(candidate.relevance_score)}`}>
                            {Math.round(candidate.relevance_score * 100)}%
                          </span>
                          {/* Score bar */}
                          <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden max-w-[60px]">
                            <div
                              className={`h-full rounded-full ${getScoreBarColor(candidate.relevance_score)}`}
                              style={{ width: getScoreBarWidth(candidate.relevance_score) }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.button>
                );
              })}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-700 bg-red-900/30 p-3">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
        <button
          onClick={handleApprove}
          disabled={isApproving || selectedUrls.size === 0}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-3.5 sm:py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-purple-500 hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none min-h-[48px] sm:min-h-0 touch-manipulation"
        >
          {isApproving ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Creating Job…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Run Full Research ({selectedUrls.size} source{selectedUrls.size !== 1 ? 's' : ''})
            </>
          )}
        </button>

        <button
          onClick={handleBack}
          disabled={isApproving}
          className="px-4 py-3 text-sm text-gray-400 hover:text-gray-300 transition touch-manipulation text-center"
        >
          Cancel
        </button>
      </div>
    </motion.div>
  );
}
