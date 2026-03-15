/**
 * AngleCard — Visual card for a brainstorm narrative angle.
 *
 * Displays title, description, hook preview, collapsible story arc,
 * content type + depth badges, and selected state with checkmark.
 */

import { useState } from 'react';

interface StoryArc {
  hook: string;
  conflict: string;
  build: string;
  resolution: string;
  cta: string;
}

export interface BrainstormAngleData {
  angle_id: string;
  title: string;
  description: string;
  hook_preview: string;
  story_arc: StoryArc;
  content_type: string;
  estimated_depth: string;
}

interface AngleCardProps {
  angle: BrainstormAngleData;
  isSelected: boolean;
  onToggle: (angleId: string) => void;
}

const CONTENT_TYPE_COLORS: Record<string, string> = {
  investigation: 'bg-red-900/40 text-red-400 border-red-800/30',
  explainer: 'bg-blue-900/40 text-blue-400 border-blue-800/30',
  story: 'bg-purple-900/40 text-purple-400 border-purple-800/30',
  analysis: 'bg-green-900/40 text-green-400 border-green-800/30',
  comparison: 'bg-amber-900/40 text-amber-400 border-amber-800/30',
  profile: 'bg-pink-900/40 text-pink-400 border-pink-800/30',
  controversy: 'bg-orange-900/40 text-orange-400 border-orange-800/30',
  tutorial: 'bg-cyan-900/40 text-cyan-400 border-cyan-800/30',
};

const DEPTH_LABELS: Record<string, string> = {
  quick: '5-10 min',
  medium: '10-20 min',
  deep: '20+ min',
};

const ARC_LABELS = [
  { key: 'hook', label: 'Hook', icon: '🎣' },
  { key: 'conflict', label: 'Conflict', icon: '⚡' },
  { key: 'build', label: 'Build', icon: '📈' },
  { key: 'resolution', label: 'Resolution', icon: '✅' },
  { key: 'cta', label: 'CTA', icon: '🎯' },
] as const;

export function AngleCard({ angle, isSelected, onToggle }: AngleCardProps) {
  const [showArc, setShowArc] = useState(false);

  const typeStyle = CONTENT_TYPE_COLORS[angle.content_type] || CONTENT_TYPE_COLORS.analysis;

  return (
    <button
      type="button"
      onClick={() => onToggle(angle.angle_id)}
      className={`
        relative w-full text-left rounded-lg border p-4 sm:p-5 transition-all duration-200
        bg-gray-800/40 overflow-hidden group
        ${isSelected
          ? 'border-blue-500/60 ring-1 ring-blue-500/30 shadow-lg shadow-blue-900/10'
          : 'border-gray-700/40 hover:border-gray-600/60 hover:bg-gray-800/60'
        }
      `}
    >
      {/* Selected indicator */}
      {isSelected && (
        <div className="absolute top-0 left-0 bottom-0 w-1 rounded-l-lg bg-blue-500" />
      )}

      <div className={isSelected ? 'pl-2 sm:pl-3' : ''}>
        {/* Badges */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase tracking-wider border ${typeStyle}`}>
            {angle.content_type}
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded bg-gray-700/40 text-gray-500 border border-gray-600/30">
            {DEPTH_LABELS[angle.estimated_depth] || angle.estimated_depth}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-[16px] font-semibold text-gray-100 mb-1">{angle.title}</h3>

        {/* Description */}
        <p className="text-[14px] text-gray-400 leading-relaxed mb-3">{angle.description}</p>

        {/* Hook preview */}
        <div className="bg-gray-900/40 rounded-lg p-3 border border-gray-700/30 mb-3">
          <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">Hook preview</p>
          <p className="text-[14px] text-gray-200 leading-relaxed italic">
            &ldquo;{angle.hook_preview}&rdquo;
          </p>
        </div>

        {/* Story Arc toggle */}
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); setShowArc(!showArc); }}
          className="flex items-center gap-1.5 text-[12px] text-gray-500 hover:text-gray-400 transition"
        >
          <svg
            className={`w-3 h-3 transition-transform duration-200 ${showArc ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          <span className="uppercase tracking-wider font-medium">Story Arc</span>
        </button>

        {showArc && (
          <div className="mt-3 space-y-2">
            {ARC_LABELS.map(({ key, label, icon }) => (
              <div key={key} className="flex gap-2 items-start">
                <span className="text-[12px] flex-shrink-0 mt-0.5">{icon}</span>
                <div>
                  <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
                  <p className="text-[13px] text-gray-300 leading-relaxed">
                    {angle.story_arc[key as keyof StoryArc]}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Selection checkmark */}
      {isSelected && (
        <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
    </button>
  );
}
