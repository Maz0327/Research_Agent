/**
 * SourceReviewPanel - Shows search candidates awaiting user approval.
 *
 * Displayed when an EXPAND run with auto-search enters AWAITING_REVIEW status.
 * Users can approve or reject individual search candidates before processing continues.
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
      <div className="p-4 bg-blue-900/20 border border-blue-700/50 rounded-lg">
        <div className="flex items-center gap-2 text-blue-300 text-sm">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading search candidates...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
        <p className="text-red-300 text-sm">{error}</p>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="p-4 bg-gray-700/50 border border-gray-600/50 rounded-lg">
        <p className="text-gray-400 text-sm">No search candidates found.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-blue-900/10 border border-blue-700/30 rounded-xl p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-blue-300 flex items-center gap-2">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Review Search Results ({candidates.length} found)
        </h4>
        <div className="flex gap-2 text-xs">
          <button onClick={selectAll} className="text-blue-400 hover:text-blue-300 transition">
            Select All
          </button>
          <span className="text-gray-600">|</span>
          <button onClick={deselectAll} className="text-blue-400 hover:text-blue-300 transition">
            Deselect All
          </button>
        </div>
      </div>

      <p className="text-xs text-gray-400 mb-3">
        Select the sources you want to add to your research. Unchecked sources will be skipped.
      </p>

      {/* Candidate list */}
      <div className="space-y-2 max-h-[300px] overflow-y-auto mb-4">
        {candidates.map((candidate) => (
          <label
            key={candidate.url}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition ${
              selectedUrls.has(candidate.url)
                ? 'border-blue-500/50 bg-blue-500/5'
                : 'border-gray-700 bg-gray-800/50 opacity-60'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedUrls.has(candidate.url)}
              onChange={() => toggleCandidate(candidate.url)}
              className="mt-1 h-4 w-4 rounded border-gray-600 text-blue-500 focus:ring-blue-500 bg-gray-700"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-200 truncate">
                  {candidate.title || 'Untitled'}
                </span>
                {candidate.relevance_score >= 0.8 && (
                  <span className="text-xs px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded">
                    High match
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{candidate.snippet}</p>
              <p className="text-xs text-gray-500 mt-1 truncate font-mono">{candidate.url}</p>
            </div>
          </label>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={handleApprove}
          disabled={isSubmitting || selectedUrls.size === 0}
          className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 disabled:cursor-not-allowed rounded-lg transition"
        >
          {isSubmitting
            ? 'Processing...'
            : `Approve ${selectedUrls.size} Source${selectedUrls.size !== 1 ? 's' : ''}`}
        </button>
      </div>
    </motion.div>
  );
}
