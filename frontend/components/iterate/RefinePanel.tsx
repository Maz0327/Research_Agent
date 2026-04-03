/**
 * RefinePanel — Natural language iteration dialog.
 *
 * Replaces the technical 5-mode IterateDialog with a simple text input
 * plus contextual suggestion chips. Users describe what they want;
 * the system infers the correct iteration mode via keyword matching.
 *
 * Users never see mode names like "deep_dive" or "expand_sources".
 */

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import type { IterateRequest } from '../../types/run';
import { useJobsStore } from '../../store/jobs';
import { inferIterateMode, generateSuggestions } from '../../lib/iterate-intent';
import { Spinner } from '@/components/ui/Spinner';

interface RefinePanelProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  /** Job data for generating contextual suggestions */
  job?: { title?: string; artifacts?: Record<string, unknown> };
  onIterateStarted?: (iterateId: string) => void;
}

export function RefinePanel({
  isOpen,
  onClose,
  jobId,
  job,
  onIterateStarted,
}: RefinePanelProps) {
  const [userInput, setUserInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const iterateJob = useJobsStore((s) => s.iterateJob);
  const prefersReducedMotion = useReducedMotion();

  // Generate contextual suggestions
  const suggestions = job ? generateSuggestions(job) : [
    'Find more sources on this topic',
    'Go deeper on the key findings',
    'What am I missing?',
    'Try a more casual tone',
  ];

  // Reset when dialog opens
  useEffect(() => {
    if (isOpen) {
      setUserInput('');
      setError(null);
    }
  }, [isOpen]);

  // Body scroll lock (Radix handles Escape and focus trap)
  useEffect(() => {
    if (!isOpen) return;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  const handleSubmit = useCallback(async () => {
    const trimmed = userInput.trim();
    if (!trimmed || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const inferred = inferIterateMode(trimmed);
      const request: IterateRequest = {
        mode: inferred.mode,
        ...(inferred.angle && { angle: inferred.angle }),
        ...(inferred.userPrompt && { user_prompt: inferred.userPrompt }),
      };

      const result = await iterateJob(jobId, request);
      onIterateStarted?.(result.iterate_id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start refinement');
    } finally {
      setSubmitting(false);
    }
  }, [userInput, submitting, jobId, iterateJob, onIterateStarted, onClose]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  // Show what mode was detected (subtle feedback)
  const inferred = userInput.trim() ? inferIterateMode(userInput.trim()) : null;

  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <AnimatePresence>
          {isOpen && (
            <>
              {/* Backdrop */}
              <DialogPrimitive.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 bg-black/50 z-[55]"
                  onClick={onClose}
                />
              </DialogPrimitive.Overlay>

              {/* Dialog */}
              <DialogPrimitive.Content asChild aria-labelledby="refine-panel-title">
                <motion.div
                  initial={prefersReducedMotion ? false : { opacity: 0, scale: 0.95, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={prefersReducedMotion ? {} : { opacity: 0, scale: 0.95, y: 20 }}
                  transition={prefersReducedMotion ? { duration: 0 } : { type: 'spring', damping: 25, stiffness: 300 }}
                  className="fixed inset-x-4 top-1/2 -translate-y-1/2 sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full sm:max-w-lg bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl z-[60] overflow-hidden"
                >
            {/* Header */}
            <div className="border-b border-gray-800 px-6 py-4">
              <div className="flex items-center justify-between">
                <h2 id="refine-panel-title" className="text-lg font-semibold text-gray-100">
                  Improve Research
                </h2>
                <button
                  onClick={onClose}
                  className="p-2.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
                  aria-label="Close"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-5 space-y-4">
              {/* Suggestion chips */}
              <div>
                <p className="text-xs text-gray-500 mb-2">Quick actions</p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setUserInput(suggestion)}
                      className={`
                        text-xs px-3 py-1.5 rounded-full border transition-all
                        ${userInput === suggestion
                          ? 'border-blue-500/50 bg-blue-900/20 text-blue-300'
                          : 'border-gray-700 bg-gray-800/50 text-gray-400 hover:border-gray-600 hover:text-gray-300'
                        }
                      `}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Text input */}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">
                  What would you like to improve?
                </label>
                <textarea
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="e.g., Find more sources about the economic impact..."
                  rows={3}
                  className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  style={{ fontSize: '16px' }}
                  autoFocus
                />
              </div>

              {/* Mode hint */}
              {inferred && userInput.trim() && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xs text-gray-500"
                >
                  {getModeHint(inferred.mode)}
                </motion.p>
              )}

              {/* Error */}
              {error && (
                <div className="rounded-lg bg-red-900/20 border border-red-800/50 px-4 py-2">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-gray-800 px-6 py-4">
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors min-h-[44px]"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!userInput.trim() || submitting}
                  className={`
                    px-5 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px]
                    ${userInput.trim() && !submitting
                      ? 'bg-blue-600 hover:bg-blue-500 text-white'
                      : 'bg-gray-800 text-gray-600 cursor-not-allowed'
                    }
                  `}
                >
                  {submitting ? (
                    <span className="flex items-center gap-2">
                      <Spinner size="sm" />
                      Starting...
                    </span>
                  ) : (
                    'Improve'
                  )}
                </button>
              </div>
            </div>
                </motion.div>
              </DialogPrimitive.Content>
            </>
          )}
        </AnimatePresence>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function getModeHint(mode: string): string {
  switch (mode) {
    case 'expand_sources': return 'Will search for and add new sources to your research';
    case 'different_angle': return 'Will re-analyze your data from a new perspective';
    case 'deeper': return 'Will extract more detail from your existing sources';
    case 'deep_dive': return 'Will identify gaps and suggest new research directions';
    case 'custom': return 'Will apply your custom instructions to the research';
    default: return '';
  }
}

export default RefinePanel;
