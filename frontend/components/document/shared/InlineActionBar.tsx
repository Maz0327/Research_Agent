/**
 * InlineActionBar — Quick action buttons for document sections.
 *
 * Provides one-click iteration triggers directly on document content,
 * bypassing the RefinePanel for common actions like "Dig deeper"
 * or "Copy for script".
 */

import { useState, useCallback } from 'react';
import { useJobsStore } from '../../../store/jobs';
import type { IterateRequest } from '../../../types/run';

interface InlineActionBarProps {
  jobId: string;
  /** Section context passed to the iteration prompt */
  sectionContext?: string;
  /** Called after iteration starts */
  onIterateStarted?: () => void;
}

export function InlineActionBar({ jobId, sectionContext, onIterateStarted }: InlineActionBarProps) {
  const [loading, setLoading] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const iterateJob = useJobsStore((s) => s.iterateJob);

  const handleIterate = useCallback(async (mode: string, extra?: Partial<IterateRequest>) => {
    setLoading(mode);
    try {
      const request: IterateRequest = {
        mode: mode as IterateRequest['mode'],
        ...(sectionContext && { user_prompt: sectionContext }),
        ...extra,
      };
      await iterateJob(jobId, request);
      onIterateStarted?.();
    } catch (err) {
      console.error('Inline iterate failed:', err);
    } finally {
      setLoading(null);
    }
  }, [jobId, sectionContext, iterateJob, onIterateStarted]);

  const handleCopy = useCallback(async () => {
    // Find the parent card wrapper and copy its text content
    const el = document.activeElement?.closest('[data-section-content]');
    if (el) {
      await navigator.clipboard.writeText(el.textContent || '');
    } else if (sectionContext) {
      await navigator.clipboard.writeText(sectionContext);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [sectionContext]);

  return (
    <div className="flex items-center gap-1.5 mt-3 pt-2.5 border-t border-gray-700/30">
      <button
        onClick={() => handleIterate('deeper')}
        disabled={!!loading}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-gray-400 hover:text-blue-300 hover:bg-blue-900/20 transition-colors disabled:opacity-50"
      >
        {loading === 'deeper' ? (
          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
            <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        ) : (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        )}
        Dig deeper
      </button>

      <button
        onClick={handleCopy}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-gray-400 hover:text-green-300 hover:bg-green-900/20 transition-colors"
      >
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        {copied ? 'Copied!' : 'Copy for script'}
      </button>

      <button
        onClick={() => handleIterate('different_angle', { angle: sectionContext })}
        disabled={!!loading}
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-gray-400 hover:text-purple-300 hover:bg-purple-900/20 transition-colors disabled:opacity-50"
      >
        {loading === 'different_angle' ? (
          <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
            <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        ) : (
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        )}
        Different angle
      </button>
    </div>
  );
}
