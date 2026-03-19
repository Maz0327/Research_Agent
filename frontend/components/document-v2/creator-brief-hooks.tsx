/**
 * creator-brief-hooks — Opening Hooks grid for Creator Brief (Doc 3).
 * Reuses HookOptionCard pattern with shadcn Badge for hook type.
 */

'use client';

import { useState, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { CitationPill } from './shared/citation-pill';
import type { OpeningHook } from '@/types/documents';

const HOOK_TYPE_STYLES: Record<string, string> = {
  question:      'bg-blue-900/40 text-blue-400 border-blue-800/30',
  contradiction: 'bg-red-900/40 text-red-400 border-red-800/30',
  'stat-lead':   'bg-green-900/40 text-green-400 border-green-800/30',
  stat_lead:     'bg-green-900/40 text-green-400 border-green-800/30',
  'story-open':  'bg-purple-900/40 text-purple-400 border-purple-800/30',
  story_open:    'bg-purple-900/40 text-purple-400 border-purple-800/30',
};

function formatHookType(t: string) {
  return t.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function HookCard({ hook, index, isSelected, onSelect }: {
  hook: OpeningHook;
  index: number;
  isSelected: boolean;
  onSelect: (i: number) => void;
}) {
  const [copied, setCopied] = useState(false);
  const typeKey = (hook.hook_type ?? '').toLowerCase().replace(/\s+/g, '-');
  const typeStyle = HOOK_TYPE_STYLES[typeKey] ?? 'bg-zinc-700/40 text-zinc-400 border-zinc-600/30';

  const handleCopy = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(hook.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }, [hook.content]);

  return (
    <button
      type="button"
      onClick={() => onSelect(isSelected ? -1 : index)}
      className={`relative w-full text-left rounded-lg border p-4 transition-all duration-200 bg-zinc-800/40 overflow-hidden group
        ${isSelected
          ? 'border-amber-500/60 ring-1 ring-amber-500/30'
          : 'border-border hover:border-zinc-600/60 hover:bg-zinc-800/60'
        }`}
    >
      {isSelected && <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-amber-500" />}
      <div className={isSelected ? 'pl-3' : ''}>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 font-semibold uppercase tracking-wider ${typeStyle}`}>
              {formatHookType(hook.hook_type ?? '')}
            </Badge>
            {hook.tone && <span className="text-[11px] text-zinc-500 italic">{hook.tone}</span>}
          </div>
          <button
            type="button"
            onClick={handleCopy}
            className={`flex-shrink-0 text-[10px] px-2 py-0.5 rounded transition-all
              ${copied
                ? 'bg-green-900/40 text-green-400 border border-green-800/30'
                : 'bg-zinc-700/40 text-zinc-500 border border-zinc-600/30 opacity-0 group-hover:opacity-100 hover:text-zinc-300'
              }`}
          >
            {copied ? '✓' : 'Copy'}
          </button>
        </div>
        <p className="text-[15px] text-zinc-100 leading-relaxed font-medium">&ldquo;{hook.content}&rdquo;</p>
        {hook.source_basis?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-border">
            {hook.source_basis.map((sid: string) => <CitationPill key={sid} id={sid} />)}
          </div>
        )}
      </div>
      {isSelected && (
        <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-amber-500 flex items-center justify-center">
          <svg className="w-3 h-3 text-zinc-900" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
    </button>
  );
}

interface HooksSectionProps {
  hooks: OpeningHook[];
}

export function HooksSection({ hooks }: HooksSectionProps) {
  const [selectedIndex, setSelectedIndex] = useState(-1);

  if (!hooks?.length) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {hooks.map((hook, i) => (
        <HookCard
          key={i}
          hook={hook}
          index={i}
          isSelected={selectedIndex === i}
          onSelect={setSelectedIndex}
        />
      ))}
    </div>
  );
}
