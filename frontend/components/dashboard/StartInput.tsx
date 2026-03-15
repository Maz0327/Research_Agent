/**
 * StartInput — Unified smart input for starting any research job.
 *
 * Replaces the 4-card grid with a single text input that detects intent:
 * - Plain topic → search discovery flow
 * - URLs → own sources flow
 * - Claims language → claim extraction
 * - Creator + style → creator analysis (Phase 3)
 *
 * Power user links below for explicit mode selection.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { detectIntent, type DetectedIntent } from '../../lib/intent-router';

const PLACEHOLDER_EXAMPLES = [
  'What topic is your next video about?',
  'Paste a YouTube URL to analyze...',
  'The rise of AI agents in 2026',
  'Boeing safety culture collapse timeline',
  'Why are so many fast food chains closing?',
];

interface StartInputProps {
  /** Called when user submits with detected intent */
  onSubmit: (input: string, intent: DetectedIntent) => void;
  /** Whether a submission is in progress */
  isLoading?: boolean;
  /** Called when user clicks a power-user mode link */
  onModeSelect?: (mode: 'sources' | 'claims' | 'transcripts') => void;
}

export function StartInput({ onSubmit, isLoading = false, onModeSelect }: StartInputProps) {
  const [value, setValue] = useState('');
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Rotate placeholder text every 4 seconds
  useEffect(() => {
    if (isFocused || value) return;
    const interval = setInterval(() => {
      setPlaceholderIndex(i => (i + 1) % PLACEHOLDER_EXAMPLES.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [isFocused, value]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;

    const result = detectIntent(trimmed);
    onSubmit(trimmed, result.intent);
  }, [value, isLoading, onSubmit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  // Detect intent in real-time for visual feedback
  const detected = value.trim() ? detectIntent(value.trim()) : null;
  const intentHint = detected ? getIntentHint(detected.intent) : null;

  return (
    <div className="space-y-3">
      {/* Main input area */}
      <div className={`
        relative rounded-xl border-2 transition-all duration-200
        ${isFocused
          ? 'border-blue-500/60 shadow-lg shadow-blue-500/10'
          : 'border-gray-700 hover:border-gray-600'
        }
      `}>
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={PLACEHOLDER_EXAMPLES[placeholderIndex]}
          disabled={isLoading}
          rows={2}
          className="w-full resize-none rounded-xl bg-gray-800/50 px-4 py-4 pr-24 text-[15px] text-gray-100 placeholder-gray-500 focus:outline-none disabled:opacity-50"
          style={{ fontSize: '16px' }} // Prevent iOS zoom
        />

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading}
          className={`
            absolute right-3 bottom-3 flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all
            ${value.trim() && !isLoading
              ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-md'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }
          `}
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          )}
          Go
        </button>
      </div>

      {/* Intent hint (shows what the system detected) */}
      {intentHint && value.trim() && (
        <motion.p
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs text-gray-500 px-1"
        >
          {intentHint.icon} {intentHint.text}
        </motion.p>
      )}

      {/* Power user links */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-1">
        <span className="text-xs text-gray-600">or:</span>
        <button
          onClick={() => onModeSelect?.('sources')}
          className="text-xs text-gray-500 hover:text-blue-400 transition-colors"
        >
          paste my own sources
        </button>
        <button
          onClick={() => onModeSelect?.('claims')}
          className="text-xs text-gray-500 hover:text-purple-400 transition-colors"
        >
          extract claims
        </button>
        <button
          onClick={() => onModeSelect?.('transcripts')}
          className="text-xs text-gray-500 hover:text-amber-400 transition-colors"
        >
          get transcripts
        </button>
      </div>
    </div>
  );
}

function getIntentHint(intent: DetectedIntent): { icon: string; text: string } | null {
  switch (intent) {
    case 'sources':
      return { icon: '📎', text: "URLs detected — we'll analyze these sources directly" };
    case 'claims':
      return { icon: '📋', text: "Claim extraction mode — we'll pull out claims with confidence scores" };
    case 'creator_analysis':
      return { icon: '🎨', text: "Creator analysis — we'll break down their style and approach" };
    case 'topic':
      return null; // Default, no hint needed
    default:
      return null;
  }
}
