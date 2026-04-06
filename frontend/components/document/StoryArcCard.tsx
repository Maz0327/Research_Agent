/**
 * StoryArcCard — Renders a suggested story structure based on the Five-Act
 * Story Arc framework. Shows structure archetype, 5 beats with descriptions,
 * and a scripting preview.
 *
 * Phase 3B: Content Structure Suggestions
 */

import { useState } from 'react';
import { CardWrapper } from './shared/CardWrapper';
import type { StoryArc, StoryBeat } from '@/types/documents';

export type { StoryArc, StoryBeat };

interface StoryArcCardProps {
  arc: StoryArc;
}

const ARC_TYPE_COLORS: Record<string, { accent: string; bg: string; text: string }> = {
  cold_open: { accent: 'bg-red-500', bg: 'bg-red-900/20', text: 'text-red-400' },
  multiple_perspectives: { accent: 'bg-blue-500', bg: 'bg-blue-900/20', text: 'text-blue-400' },
  heros_journey: { accent: 'bg-amber-500', bg: 'bg-amber-900/20', text: 'text-amber-400' },
  discovery: { accent: 'bg-emerald-500', bg: 'bg-emerald-900/20', text: 'text-emerald-400' },
};

const ARC_TYPE_LABELS: Record<string, string> = {
  cold_open: 'Cold Open',
  multiple_perspectives: 'Multiple Perspectives',
  heros_journey: "Hero's Journey",
  discovery: 'Discovery',
};

export function StoryArcCard({ arc }: StoryArcCardProps) {
  const [showPreview, setShowPreview] = useState(false);
  const colors = ARC_TYPE_COLORS[arc.arc_type] || ARC_TYPE_COLORS.discovery;

  return (
    <CardWrapper accentColor={colors.accent}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-caption font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${colors.bg} ${colors.text} border border-current/20`}>
              {ARC_TYPE_LABELS[arc.arc_type] || arc.arc_type}
            </span>
          </div>
          <p className="text-body-lg font-semibold text-foreground">{arc.arc_name}</p>
          <p className="text-body-sm text-muted-foreground/70 mt-0.5">{arc.topic_fit_reason}</p>
        </div>
      </div>

      {/* Five beats */}
      <div className="space-y-0">
        {arc.beats.map((beat, idx) => {
          const isLast = idx === arc.beats.length - 1;
          return (
            <div key={beat.beat_number} className="relative flex gap-3">
              {/* Timeline connector */}
              {!isLast && (
                <div className={`absolute left-[7px] top-[20px] w-[2px] h-[calc(100%-4px)] ${colors.bg}`} />
              )}
              {/* Beat number dot */}
              <div className="relative z-10 flex-shrink-0 mt-[5px]">
                <div className={`w-[16px] h-[16px] rounded-full ${colors.bg} flex items-center justify-center`}>
                  <span className={`text-[9px] font-bold ${colors.text}`}>{beat.beat_number}</span>
                </div>
              </div>
              {/* Beat content */}
              <div className="pb-3 min-w-0">
                <p className="text-body-sm font-medium text-foreground">{beat.label}</p>
                <p className="text-body-sm text-muted-foreground mt-0.5">{beat.description}</p>
                {beat.mapped_ids && beat.mapped_ids.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {beat.mapped_ids.map((id) => (
                      <span key={id} className="text-caption px-1.5 py-0.5 rounded bg-card text-muted-foreground/70 border border-border/50">
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Scripting preview toggle */}
      <button
        onClick={() => setShowPreview(!showPreview)}
        className="mt-3 text-body-sm text-muted-foreground/70 hover:text-muted-foreground transition-colors flex items-center gap-1"
      >
        <svg
          className={`w-3 h-3 transition-transform ${showPreview ? 'rotate-90' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        {showPreview ? 'Hide' : 'Show'} scripting preview
      </button>

      {showPreview && (
        <div className="mt-2 p-3 rounded-lg bg-card/60 border border-border/30">
          <p className="text-body-sm text-muted-foreground/70 font-medium mb-1 uppercase tracking-wider">If you were scripting this...</p>
          <p className="text-body-sm text-muted-foreground italic leading-relaxed">{arc.scripting_preview}</p>
        </div>
      )}
    </CardWrapper>
  );
}
