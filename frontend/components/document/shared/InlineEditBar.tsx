/**
 * InlineEditBar — Floating toolbar for inline section editing.
 *
 * Shows preset actions (Expand, Shorten, Change tone) and a freeform rewrite input.
 */

import { useState, useCallback } from 'react';

export interface InlineEditBarProps {
  jobId: string;
  docType: string;
  sectionId: string;
  onSubmit: (instruction: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function InlineEditBar({
  jobId,
  docType,
  sectionId,
  onSubmit,
  onCancel,
  isLoading = false,
}: InlineEditBarProps) {
  const [customInput, setCustomInput] = useState('');
  const [showCustom, setShowCustom] = useState(false);

  const handlePreset = useCallback((instruction: string) => {
    onSubmit(instruction);
  }, [onSubmit]);

  const handleCustomSubmit = useCallback(() => {
    if (customInput.trim()) {
      onSubmit(customInput.trim());
      setCustomInput('');
    }
  }, [customInput, onSubmit]);

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm border border-white/[0.1] rounded-lg p-2 shadow-xl">
      <div className="flex items-center gap-1.5 flex-wrap">
        <button
          onClick={() => setShowCustom(!showCustom)}
          disabled={isLoading}
          className="text-[11px] px-2.5 py-1 rounded-md bg-white/[0.08] text-white/70 hover:bg-white/[0.12] hover:text-white/90 transition-colors disabled:opacity-50"
        >
          Rewrite
        </button>
        <button
          onClick={() => handlePreset('Expand this section with more detail and examples')}
          disabled={isLoading}
          className="text-[11px] px-2.5 py-1 rounded-md bg-white/[0.08] text-white/70 hover:bg-white/[0.12] hover:text-white/90 transition-colors disabled:opacity-50"
        >
          Expand
        </button>
        <button
          onClick={() => handlePreset('Shorten this section — be more concise')}
          disabled={isLoading}
          className="text-[11px] px-2.5 py-1 rounded-md bg-white/[0.08] text-white/70 hover:bg-white/[0.12] hover:text-white/90 transition-colors disabled:opacity-50"
        >
          Shorten
        </button>
        <button
          onClick={() => handlePreset('Make this section more casual and conversational')}
          disabled={isLoading}
          className="text-[11px] px-2.5 py-1 rounded-md bg-white/[0.08] text-white/70 hover:bg-white/[0.12] hover:text-white/90 transition-colors disabled:opacity-50"
        >
          Casual
        </button>
        <button
          onClick={() => handlePreset('Make this section more formal and professional')}
          disabled={isLoading}
          className="text-[11px] px-2.5 py-1 rounded-md bg-white/[0.08] text-white/70 hover:bg-white/[0.12] hover:text-white/90 transition-colors disabled:opacity-50"
        >
          Formal
        </button>

        <div className="w-px h-4 bg-white/[0.1] mx-0.5" />

        <button
          onClick={onCancel}
          className="text-[11px] px-2 py-1 rounded-md text-white/40 hover:text-white/60 transition-colors"
        >
          Cancel
        </button>

        {isLoading && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="animate-spin text-white/40 ml-1">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.15" />
            <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
        )}
      </div>

      {showCustom && (
        <div className="mt-2 flex gap-1.5">
          <input
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCustomSubmit()}
            placeholder="Describe how to edit this section..."
            className="flex-1 text-[12px] px-2.5 py-1.5 rounded-md bg-white/[0.06] border border-white/[0.08] text-white/80 placeholder-white/30 focus:outline-none focus:border-white/[0.2]"
            autoFocus
          />
          <button
            onClick={handleCustomSubmit}
            disabled={!customInput.trim() || isLoading}
            className="text-[11px] px-3 py-1.5 rounded-md bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 transition-colors disabled:opacity-50"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
