/**
 * HookOptionCard — Visual card for opening hook options in Creator Brief.
 *
 * Replaces the plain-text HookCard with a richer visual treatment:
 * - Hook text rendered large and prominent
 * - Hook type badge with color coding (Question=blue, Contradiction=red, Stat-Lead=green, Story-Open=purple)
 * - Tone displayed in italic
 * - Source basis shown as CitationPills
 * - Copy button for quick clipboard access
 * - Selectable with highlighted border state
 */

import { useState, useCallback } from 'react';
import type { OpeningHook } from '@/types/documents';
import { CitationPill } from './shared/CitationPill';

interface HookOptionCardProps {
  hook: OpeningHook;
  index: number;
  isSelected: boolean;
  onSelect: (index: number) => void;
  showDetails?: boolean;
}

const HOOK_TYPE_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  question:      { bg: 'bg-blue-900/40',   text: 'text-blue-400',   border: 'border-blue-800/30' },
  contradiction: { bg: 'bg-red-900/40',    text: 'text-red-400',    border: 'border-red-800/30' },
  'stat-lead':   { bg: 'bg-green-900/40',  text: 'text-green-400',  border: 'border-green-800/30' },
  'stat_lead':   { bg: 'bg-green-900/40',  text: 'text-green-400',  border: 'border-green-800/30' },
  'story-open':  { bg: 'bg-purple-900/40', text: 'text-purple-400', border: 'border-purple-800/30' },
  'story_open':  { bg: 'bg-purple-900/40', text: 'text-purple-400', border: 'border-purple-800/30' },
};

const DEFAULT_STYLE = { bg: 'bg-muted/40', text: 'text-muted-foreground', border: 'border-border/30' };

function getHookTypeStyle(hookType: string) {
  const normalized = hookType.toLowerCase().replace(/[\s_]+/g, '-').trim();
  return HOOK_TYPE_STYLES[normalized] || HOOK_TYPE_STYLES[hookType.toLowerCase()] || DEFAULT_STYLE;
}

function formatHookTypeLabel(hookType: string): string {
  return hookType
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

export function HookOptionCard({ hook, index, isSelected, onSelect, showDetails = false }: HookOptionCardProps) {
  const [copied, setCopied] = useState(false);
  const typeStyle = getHookTypeStyle(hook.hook_type);

  const handleCopy = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(hook.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-secure contexts
      const textarea = document.createElement('textarea');
      textarea.value = hook.content;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [hook.content]);

  return (
    <button
      type="button"
      onClick={() => onSelect(index)}
      className={`
        relative w-full text-left rounded-lg border p-4 sm:p-5 transition-all duration-200
        bg-card/40 overflow-hidden group
        ${isSelected
          ? 'border-amber-500/60 ring-1 ring-amber-500/30 shadow-lg shadow-amber-900/10'
          : 'border-border/40 hover:border-border/60 hover:bg-card/60'
        }
      `}
    >
      {/* Selected indicator bar */}
      {isSelected && (
        <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-amber-500" />
      )}

      <div className={isSelected ? 'pl-2 sm:pl-3' : ''}>
        {/* Header: type badge + tone + copy button */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-caption px-2 py-0.5 rounded font-semibold uppercase tracking-wider ${typeStyle.bg} ${typeStyle.text} border ${typeStyle.border}`}>
              {formatHookTypeLabel(hook.hook_type)}
            </span>
            {hook.tone && (
              <span className="text-caption text-muted-foreground/70 italic">{hook.tone}</span>
            )}
          </div>

          {/* Copy button */}
          <button
            type="button"
            onClick={handleCopy}
            className={`
              flex-shrink-0 text-caption px-2 py-1 rounded transition-all duration-200
              ${copied
                ? 'bg-green-900/40 text-green-400 border border-green-800/30'
                : 'bg-muted/40 text-muted-foreground/70 border border-border/30 opacity-0 group-hover:opacity-100 hover:text-muted-foreground hover:bg-muted/60'
              }
            `}
            title="Copy hook text"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
        </div>

        {/* Hook content — the hero text */}
        <p className="text-[16px] text-foreground leading-relaxed font-medium">
          &ldquo;{hook.content}&rdquo;
        </p>

        {/* Source basis pills */}
        {hook.source_basis?.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-border/30">
            <span className="text-caption text-muted-foreground/60 uppercase tracking-wider mr-1">Sources</span>
            {hook.source_basis.map(sid => (
              <CitationPill key={sid} sourceId={sid} showDetails={showDetails} />
            ))}
          </div>
        )}
      </div>

      {/* Selection checkmark */}
      {isSelected && (
        <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
    </button>
  );
}
