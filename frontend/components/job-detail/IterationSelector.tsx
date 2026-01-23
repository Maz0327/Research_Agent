/**
 * IterationSelector - Dropdown to select iteration version
 * Shows baseline and all completed iterations for switching document views.
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { IterationBundle } from '../../store/jobs';

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

/** Mode labels for display */
const MODE_LABELS: Record<string, string> = {
  more_sources: 'More sources',
  deeper: 'Deeper analysis',
  different_angle: 'Different angle',
  custom: 'Custom',
};

export interface IterationSelectorProps {
  /** Available iterations */
  iterations: IterationBundle[];
  /** Currently selected version ('baseline' or iteration_id like 'it_0001') */
  selectedVersion: string;
  /** Handler when version changes */
  onSelectVersion: (version: string) => void;
}

export function IterationSelector({
  iterations,
  selectedVersion,
  onSelectVersion,
}: IterationSelectorProps) {
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

  // Filter to completed iterations only
  const completedIterations = iterations.filter(it => it.status === 'completed');

  // Get selected label
  const getSelectedLabel = () => {
    if (selectedVersion === 'baseline') {
      return 'Baseline (original)';
    }
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
            className="absolute z-20 w-full mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl overflow-hidden"
          >
            {/* Baseline option */}
            <button
              onClick={() => {
                onSelectVersion('baseline');
                setIsOpen(false);
              }}
              className={`
                w-full px-4 py-3 text-left hover:bg-gray-700 transition-colors
                flex items-center justify-between
                ${selectedVersion === 'baseline' ? 'bg-gray-700' : ''}
              `}
            >
              <div>
                <p className="text-white font-medium">● Baseline (original)</p>
                <p className="text-sm text-gray-400">Initial research results</p>
              </div>
              {selectedVersion === 'baseline' && (
                <span className="text-green-400">✓</span>
              )}
            </button>

            {/* Completed iterations */}
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
                        • &quot;{iteration.request.user_prompt.slice(0, 30)}{iteration.request.user_prompt.length > 30 ? '...' : ''}&quot;
                      </span>
                    )}
                  </p>
                </div>
                {selectedVersion === iteration.iteration_id && (
                  <span className="text-green-400">✓</span>
                )}
              </button>
            ))}

            {/* No iterations message */}
            {completedIterations.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400 border-t border-gray-700">
                No completed iterations yet
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default IterationSelector;
