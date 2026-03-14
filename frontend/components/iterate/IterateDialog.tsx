/**
 * IterateDialog — Unified 5-mode iteration dialog.
 *
 * Replaces the old 3-mode IterationDialog. Supports:
 * - Deep Dive: find gaps and search directions (Doc 1)
 * - Expand Sources: add more sources (Doc 0/1/2/3)
 * - Go Deeper: re-extract with more detail (Doc 0/1/2/3)
 * - Different Angle: same data, new perspective (Doc 2/3)
 * - Custom: user-defined instructions (varies)
 *
 * Submits to POST /jobs/{job_id}/iterate via store.iterateJob().
 */
import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { IterateMode, IterateRequest } from '../../types/run';
import { ITERATE_MODE_CONFIG } from '../../types/run';
import { useJobsStore } from '../../store/jobs';

// =============================================================================
// Mode colors for Tailwind
// =============================================================================

const MODE_COLORS: Record<string, {
  border: string;
  bg: string;
  bgSelected: string;
  text: string;
}> = {
  blue: { border: 'border-blue-600', bg: 'bg-blue-900/10', bgSelected: 'bg-blue-900/30', text: 'text-blue-400' },
  green: { border: 'border-green-600', bg: 'bg-green-900/10', bgSelected: 'bg-green-900/30', text: 'text-green-400' },
  purple: { border: 'border-purple-600', bg: 'bg-purple-900/10', bgSelected: 'bg-purple-900/30', text: 'text-purple-400' },
  orange: { border: 'border-orange-600', bg: 'bg-orange-900/10', bgSelected: 'bg-orange-900/30', text: 'text-orange-400' },
  gray: { border: 'border-gray-600', bg: 'bg-gray-800/50', bgSelected: 'bg-gray-800', text: 'text-gray-300' },
};

// =============================================================================
// Props
// =============================================================================

export interface IterateDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Job ID to iterate */
  jobId: string;
  /** Optional pre-selected mode */
  defaultMode?: IterateMode;
  /** Callback after successful iteration start */
  onIterateStarted?: (iterateId: string) => void;
}

// =============================================================================
// Component
// =============================================================================

const MODES: IterateMode[] = ['deep_dive', 'expand_sources', 'deeper', 'different_angle', 'custom'];

export function IterateDialog({
  isOpen,
  onClose,
  jobId,
  defaultMode,
  onIterateStarted,
}: IterateDialogProps) {
  const [selectedMode, setSelectedMode] = useState<IterateMode | null>(defaultMode || null);
  const [userPrompt, setUserPrompt] = useState('');
  const [angle, setAngle] = useState('');
  const [sourceUrls, setSourceUrls] = useState('');
  const [maxNewSources, setMaxNewSources] = useState(4);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const iterateJob = useJobsStore((s) => s.iterateJob);

  // Reset form when dialog opens
  const resetForm = useCallback(() => {
    if (!defaultMode) setSelectedMode(null);
    setUserPrompt('');
    setAngle('');
    setSourceUrls('');
    setMaxNewSources(4);
    setError(null);
  }, [defaultMode]);

  // Reset when dialog opens (not on exit)
  useEffect(() => {
    if (isOpen) resetForm();
  }, [isOpen, resetForm]);

  // Escape key + body scroll lock
  useEffect(() => {
    if (!isOpen) return;
    document.body.style.overflow = 'hidden';
    const handleEscape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  // Build request based on selected mode
  const buildRequest = (): IterateRequest | null => {
    if (!selectedMode) return null;

    const request: IterateRequest = { mode: selectedMode };

    switch (selectedMode) {
      case 'expand_sources':
        if (sourceUrls.trim()) {
          request.new_source_urls = sourceUrls
            .split(/[\n,]/)
            .map((u) => u.trim())
            .filter((u) => u.length > 0);
        }
        request.max_new_sources = maxNewSources;
        break;
      case 'deeper':
        if (userPrompt.trim()) {
          request.user_prompt = userPrompt.trim();
        }
        break;
      case 'different_angle':
        if (!angle.trim()) return null; // Required
        request.angle = angle.trim();
        break;
      case 'custom':
        if (!userPrompt.trim()) return null; // Required
        request.user_prompt = userPrompt.trim();
        break;
      // deep_dive needs no extra params
    }

    return request;
  };

  // Check if form is valid for submission
  const isValid = (): boolean => {
    if (!selectedMode) return false;
    if (selectedMode === 'different_angle' && !angle.trim()) return false;
    if (selectedMode === 'custom' && !userPrompt.trim()) return false;
    return true;
  };

  // Submit
  const handleSubmit = async () => {
    const request = buildRequest();
    if (!request) return;

    setSubmitting(true);
    setError(null);

    try {
      const result = await iterateJob(jobId, request);
      onIterateStarted?.(result.iterate_id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start iteration');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-[55]"
            onClick={onClose}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-x-3 sm:inset-x-4 top-[5vh] sm:top-auto sm:inset-auto sm:left-1/2 sm:top-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-full sm:max-w-lg bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl z-[60] max-h-[90vh] sm:max-h-[80vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-labelledby="iterate-dialog-title"
          >
            {/* Header */}
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 rounded-t-2xl z-10">
              <div className="flex items-center justify-between">
                <h2 id="iterate-dialog-title" className="text-lg font-semibold text-gray-100">
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

            {/* Mode selection */}
            <div className="px-6 py-4 space-y-2">
              {MODES.map((mode) => {
                const config = ITERATE_MODE_CONFIG[mode];
                const colors = MODE_COLORS[config.color];
                const isSelected = selectedMode === mode;

                return (
                  <motion.button
                    key={mode}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={() => setSelectedMode(mode)}
                    className={`
                      w-full text-left rounded-xl border-2 p-3 sm:p-4 transition-all duration-150 touch-manipulation
                      ${isSelected
                        ? `${colors.border} ${colors.bgSelected}`
                        : `border-gray-700 ${colors.bg} hover:border-gray-600`
                      }
                    `}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{config.icon}</span>
                      <div className="flex-1">
                        <p className={`font-medium ${isSelected ? colors.text : 'text-gray-200'}`}>
                          {config.label}
                        </p>
                        <p className="text-xs text-gray-500">
                          {config.description}
                        </p>
                      </div>
                      <span className="text-xs text-gray-600">{config.docsAffected}</span>
                    </div>
                  </motion.button>
                );
              })}
            </div>

            {/* Mode-specific inputs */}
            <AnimatePresence mode="wait">
              {selectedMode && (
                <motion.div
                  key={selectedMode}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="px-6 pb-4"
                >
                  {/* Expand Sources: URL input + max sources slider */}
                  {selectedMode === 'expand_sources' && (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">
                          Source URLs <span className="text-gray-600">(optional — or auto-discover)</span>
                        </label>
                        <textarea
                          value={sourceUrls}
                          onChange={(e) => setSourceUrls(e.target.value)}
                          placeholder="Paste URLs, one per line..."
                          rows={3}
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 font-mono focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">
                          Max new sources: {maxNewSources}
                        </label>
                        <input
                          type="range"
                          min={1}
                          max={10}
                          value={maxNewSources}
                          onChange={(e) => setMaxNewSources(Number(e.target.value))}
                          className="w-full accent-green-500"
                        />
                        <div className="flex justify-between text-xs text-gray-600">
                          <span>1</span>
                          <span>10</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Deeper: optional user prompt */}
                  {selectedMode === 'deeper' && (
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">
                        Focus areas <span className="text-gray-600">(optional)</span>
                      </label>
                      <textarea
                        value={userPrompt}
                        onChange={(e) => setUserPrompt(e.target.value)}
                        placeholder="Any specific areas to focus on..."
                        rows={2}
                        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      />
                    </div>
                  )}

                  {/* Different Angle: required angle text */}
                  {selectedMode === 'different_angle' && (
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">
                        New angle or perspective <span className="text-red-400">*</span>
                      </label>
                      <textarea
                        value={angle}
                        onChange={(e) => setAngle(e.target.value)}
                        placeholder="e.g., Focus on economic implications..."
                        rows={2}
                        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
                      />
                    </div>
                  )}

                  {/* Custom: required user prompt */}
                  {selectedMode === 'custom' && (
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">
                        Your instructions <span className="text-red-400">*</span>
                      </label>
                      <textarea
                        value={userPrompt}
                        onChange={(e) => setUserPrompt(e.target.value)}
                        placeholder="Describe what you want to change or improve..."
                        rows={3}
                        className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500"
                      />
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error */}
            {error && (
              <div className="px-6 pb-3">
                <div className="rounded-lg bg-red-900/20 border border-red-800/50 px-4 py-2">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="sticky bottom-0 z-10 bg-gray-900 border-t border-gray-800 px-6 py-4 rounded-b-2xl">
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors min-h-[44px] touch-manipulation"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!isValid() || submitting}
                  className={`
                    px-5 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px] touch-manipulation
                    ${isValid() && !submitting
                      ? 'bg-amber-600 hover:bg-amber-500 text-white'
                      : 'bg-gray-800 text-gray-600 cursor-not-allowed'
                    }
                  `}
                >
                  {submitting ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Starting...
                    </span>
                  ) : (
                    'Start Iteration'
                  )}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default IterateDialog;
