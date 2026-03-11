/**
 * RunSelector - Dropdown to select run/iteration version
 *
 * Supports both V2 runs (run_0, run_1) and V1 iterations (it_0001).
 * Shows baseline and all completed runs for switching document views.
 *
 * Badge colors:
 * - baseline: gray
 * - expand: blue
 * - refine: orange
 * - regenerate: red
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { IterationBundle } from '../../store/jobs';
import type { Run, RunType } from '../../types/run';
import {
  RUN_TYPE_LABELS,
  RUN_TYPE_ICONS,
  normalizeRunType,
  isV2Run,
} from '../../types/run';

/** Format relative time */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/** V1 Mode labels for legacy iterations */
const MODE_LABELS: Record<string, string> = {
  more_sources: 'More sources',
  deeper: 'Deeper analysis',
  different_angle: 'Different angle',
  custom: 'Custom',
};

/** Get badge CSS class for a run type */
function getRunTypeBadgeClass(runType: RunType): string {
  const canonical = normalizeRunType(runType);
  const colors: Record<string, string> = {
    baseline: 'bg-gray-600 text-gray-200',
    expand: 'bg-blue-600 text-blue-100',
    refine: 'bg-orange-600 text-orange-100',
    regenerate: 'bg-red-600 text-red-100',
  };
  return colors[canonical] || 'bg-gray-600 text-gray-200';
}

export interface RunSelectorProps {
  /** V2 runs (preferred) */
  runs?: Run[];
  /** V1 iterations (legacy) */
  iterations?: IterationBundle[];
  /** Currently selected version ('baseline', 'run_0', 'run_1', 'it_0001', etc.) */
  selectedVersion: string;
  /** Handler when version changes */
  onSelectVersion: (version: string) => void;
}

export function RunSelector({
  runs = [],
  iterations = [],
  selectedVersion,
  onSelectVersion,
}: RunSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter to completed items
  const completedRuns = runs.filter(r => r.status === 'completed' && r.run_type !== 'baseline');
  const completedIterations = iterations.filter(it => it.status === 'completed');
  const hasV2Runs = runs.length > 0;

  // Get selected label
  const getSelectedLabel = () => {
    if (selectedVersion === 'baseline' || selectedVersion === 'run_0') {
      return 'Baseline (original)';
    }

    // Check V2 runs first
    if (isV2Run(selectedVersion)) {
      const run = runs.find(r => r.run_id === selectedVersion);
      if (run) {
        const icon = RUN_TYPE_ICONS[run.run_type] || '○';
        const label = RUN_TYPE_LABELS[run.run_type] || run.run_type;
        return `${icon} ${run.run_id} - ${label}`;
      }
    }

    // Fall back to V1 iterations
    const iteration = iterations.find(it => it.iteration_id === selectedVersion);
    if (iteration) {
      return `${iteration.iteration_id} - ${MODE_LABELS[iteration.request.mode] || iteration.request.mode}`;
    }

    return 'Baseline (original)';
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Viewing:</span>
          <span className="text-white font-medium">{getSelectedLabel()}</span>
        </div>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-20 w-full mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden max-h-80 overflow-y-auto"
          >
            {/* Baseline option */}
            <button
              onClick={() => {
                onSelectVersion(hasV2Runs ? 'run_0' : 'baseline');
                setIsOpen(false);
              }}
              className={`
                w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors
                flex items-center justify-between
                ${selectedVersion === 'baseline' || selectedVersion === 'run_0' ? 'bg-gray-700' : ''}
              `}
            >
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 text-xs rounded ${getRunTypeBadgeClass('baseline')}`}>
                  {RUN_TYPE_ICONS.baseline}
                </span>
                <div>
                  <p className="text-white font-medium">Baseline (original)</p>
                  <p className="text-sm text-gray-400">Initial research results</p>
                </div>
              </div>
              {(selectedVersion === 'baseline' || selectedVersion === 'run_0') && (
                <span className="text-green-400">✓</span>
              )}
            </button>

            {/* V2 Runs Section */}
            {completedRuns.length > 0 && (
              <>
                <div className="px-4 py-2 text-xs text-gray-500 bg-gray-900/50 border-t border-gray-700">
                  RUNS
                </div>
                {completedRuns.map(run => {
                  const canonical = normalizeRunType(run.run_type);
                  return (
                    <button
                      key={run.run_id}
                      onClick={() => {
                        onSelectVersion(run.run_id);
                        setIsOpen(false);
                      }}
                      className={`
                        w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors border-t border-gray-700
                        flex items-center justify-between
                        ${selectedVersion === run.run_id ? 'bg-gray-700' : ''}
                      `}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-0.5 text-xs rounded ${getRunTypeBadgeClass(run.run_type)}`}>
                          {RUN_TYPE_ICONS[run.run_type] || '○'}
                        </span>
                        <div>
                          <p className="text-white font-medium">
                            {run.run_id} - {RUN_TYPE_LABELS[run.run_type] || canonical}
                          </p>
                          <p className="text-sm text-gray-400">
                            {formatRelativeTime(run.completed_at || run.created_at)}
                            {run.request.user_prompt && (
                              <span className="ml-2 text-gray-500">
                                • &quot;{run.request.user_prompt.slice(0, 25)}{run.request.user_prompt.length > 25 ? '...' : ''}&quot;
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                      {selectedVersion === run.run_id && (
                        <span className="text-green-400">✓</span>
                      )}
                    </button>
                  );
                })}
              </>
            )}

            {/* V1 Iterations Section (legacy) */}
            {completedIterations.length > 0 && (
              <>
                <div className="px-4 py-2 text-xs text-gray-500 bg-gray-900/50 border-t border-gray-700">
                  LEGACY ITERATIONS
                </div>
                {completedIterations.map(iteration => (
                  <button
                    key={iteration.iteration_id}
                    onClick={() => {
                      onSelectVersion(iteration.iteration_id);
                      setIsOpen(false);
                    }}
                    className={`
                      w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors border-t border-gray-700
                      flex items-center justify-between
                      ${selectedVersion === iteration.iteration_id ? 'bg-gray-700' : ''}
                    `}
                  >
                    <div>
                      <p className="text-white font-medium">
                        {iteration.iteration_id} - {MODE_LABELS[iteration.request.mode] || iteration.request.mode}
                      </p>
                      <p className="text-sm text-gray-400">
                        {formatRelativeTime(iteration.completed_at || iteration.created_at)}
                        {iteration.request.user_prompt && (
                          <span className="ml-2 text-gray-500">
                            • &quot;{iteration.request.user_prompt.slice(0, 25)}{iteration.request.user_prompt.length > 25 ? '...' : ''}&quot;
                          </span>
                        )}
                      </p>
                    </div>
                    {selectedVersion === iteration.iteration_id && (
                      <span className="text-green-400">✓</span>
                    )}
                  </button>
                ))}
              </>
            )}

            {/* No runs message */}
            {completedRuns.length === 0 && completedIterations.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400 border-t border-gray-700">
                No completed runs or iterations yet
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default RunSelector;
