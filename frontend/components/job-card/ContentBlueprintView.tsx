/**
 * ContentBlueprintView component for displaying video structure analysis.
 * Shows hook analysis, narrative structure, open loops, style, and sources.
 * Phase 3: Full Research Assistant Pipeline (Jan 2026)
 */
import { useState } from 'react';

/**
 * Act/section breakdown structure
 */
export interface ActSection {
  name: string;
  timestamp_start: string;
  timestamp_end: string;
  description: string;
}

/**
 * Open loop (re-engagement point) structure
 */
export interface OpenLoop {
  timestamp: string;
  technique: string;
  description: string;
}

/**
 * ContentBlueprint structure matching backend dataclass
 * H-013: Added parse_error field to detect partial failures
 */
export interface ContentBlueprint {
  video_url: string;
  title: string;
  hook_timestamp: string;
  hook_technique: string;
  hook_description: string;
  structure_type: string;
  act_breakdown: ActSection[];
  open_loops: OpenLoop[];
  pacing: string;
  editing_style: string;
  likely_primary_sources: string[];
  referenced_materials: string[];
  parse_error?: boolean;  // H-013: True if LLM parsing failed
}

interface ContentBlueprintViewProps {
  blueprints: ContentBlueprint[];
  isLoading?: boolean;  // H-009: Loading state
}

const techniqueColors: Record<string, { bg: string; text: string; border: string }> = {
  'pattern interrupt': { bg: 'bg-purple-900/30', text: 'text-purple-400', border: 'border-purple-700' },
  'provocative question': { bg: 'bg-blue-900/30', text: 'text-blue-400', border: 'border-blue-700' },
  'shocking statement': { bg: 'bg-red-900/30', text: 'text-red-400', border: 'border-red-700' },
  'story tease': { bg: 'bg-amber-900/30', text: 'text-amber-400', border: 'border-amber-700' },
  'default': { bg: 'bg-gray-800/50', text: 'text-gray-400', border: 'border-gray-700' },
};

function getYouTubeTimestampUrl(videoUrl: string, timestamp: string): string {
  const parts = timestamp.split(':').map(Number);
  let seconds = 0;
  if (parts.length === 2) {
    seconds = parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
  }

  if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {
    const separator = videoUrl.includes('?') ? '&' : '?';
    return `${videoUrl}${separator}t=${seconds}`;
  }
  return videoUrl;
}

function BlueprintCard({ blueprint }: { blueprint: ContentBlueprint }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const technique = blueprint.hook_technique.toLowerCase();
  const colors = techniqueColors[technique] || techniqueColors.default;

  const handleCopyMarkdown = async () => {
    const markdown = generateBlueprintMarkdown(blueprint);
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // H-013: Show warning border if parse error
  const borderClass = blueprint.parse_error
    ? 'border-yellow-600'
    : colors.border;

  return (
    <div className={`rounded-lg border ${borderClass} ${colors.bg} p-4 transition-all`}>
      {/* H-013: Parse error warning */}
      {blueprint.parse_error && (
        <div className="mb-3 flex items-center gap-2 text-xs text-yellow-500 bg-yellow-900/20 rounded px-2 py-1">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>Analysis incomplete - some data may be missing</span>
        </div>
      )}
      
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h5 className="font-medium text-gray-200 truncate" title={blueprint.title}>
            {blueprint.title}
          </h5>
          <a
            href={blueprint.video_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-gray-400 truncate block"
          >
            {blueprint.video_url.replace(/https?:\/\/(www\.)?/, '').substring(0, 50)}...
          </a>
        </div>
        {/* M-006: ARIA labels for accessibility */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="ml-2 text-gray-400 hover:text-gray-300"
          aria-expanded={expanded}
          aria-label={expanded ? 'Collapse blueprint details' : 'Expand blueprint details'}
        >
          <svg
            className={`h-5 w-5 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* Hook Summary (always visible) */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
            Hook: {blueprint.hook_technique}
          </span>
          <a
            href={getYouTubeTimestampUrl(blueprint.video_url, blueprint.hook_timestamp)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-xs text-blue-400 hover:underline"
          >
            0:00 - {blueprint.hook_timestamp}
          </a>
        </div>
        <p className="text-sm text-gray-300">{blueprint.hook_description}</p>
      </div>

      {/* Structure & Style Tags */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span className="inline-flex items-center rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
          {blueprint.structure_type}
        </span>
        <span className="inline-flex items-center rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
          {blueprint.pacing} pacing
        </span>
        <span className="inline-flex items-center rounded bg-gray-700 px-2 py-0.5 text-xs text-gray-300">
          {blueprint.editing_style}
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-700 space-y-4">
          {/* Act Breakdown */}
          {blueprint.act_breakdown.length > 0 && (
            <div>
              <h6 className="text-xs font-medium text-gray-400 uppercase mb-2">Narrative Structure</h6>
              <div className="space-y-2">
                {blueprint.act_breakdown.map((act, idx) => (
                  <div key={idx} className="flex items-start gap-3 text-sm">
                    <a
                      href={getYouTubeTimestampUrl(blueprint.video_url, act.timestamp_start)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs text-blue-400 hover:underline whitespace-nowrap"
                    >
                      {act.timestamp_start}
                    </a>
                    <div>
                      <span className="font-medium text-gray-300">{act.name}</span>
                      <p className="text-gray-400 text-xs">{act.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Open Loops */}
          {blueprint.open_loops.length > 0 && (
            <div>
              <h6 className="text-xs font-medium text-gray-400 uppercase mb-2">Re-engagement Points</h6>
              <div className="space-y-2">
                {blueprint.open_loops.map((loop, idx) => (
                  <div key={idx} className="flex items-start gap-3 text-sm">
                    <a
                      href={getYouTubeTimestampUrl(blueprint.video_url, loop.timestamp)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs text-blue-400 hover:underline whitespace-nowrap"
                    >
                      {loop.timestamp}
                    </a>
                    <div>
                      <span className="text-xs bg-yellow-900/50 text-yellow-400 rounded px-1.5 py-0.5">
                        {loop.technique}
                      </span>
                      <p className="text-gray-400 text-xs mt-1">{loop.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {(blueprint.likely_primary_sources.length > 0 || blueprint.referenced_materials.length > 0) && (
            <div>
              <h6 className="text-xs font-medium text-gray-400 uppercase mb-2">Source Tracing</h6>
              {blueprint.likely_primary_sources.length > 0 && (
                <div className="mb-2">
                  <span className="text-xs text-gray-500">Likely Sources: </span>
                  <span className="text-sm text-gray-300">
                    {blueprint.likely_primary_sources.join(', ')}
                  </span>
                </div>
              )}
              {blueprint.referenced_materials.length > 0 && (
                <div>
                  <span className="text-xs text-gray-500">Referenced: </span>
                  <span className="text-sm text-gray-300">
                    {blueprint.referenced_materials.join(', ')}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Copy button - M-006: ARIA label */}
          <div className="pt-2 flex justify-end">
            <button
              onClick={handleCopyMarkdown}
              className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
                copied
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
              aria-label={copied ? 'Blueprint copied to clipboard' : 'Copy blueprint as Markdown'}
            >
              {copied ? 'Copied!' : 'Copy as Markdown'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function generateBlueprintMarkdown(blueprint: ContentBlueprint): string {
  let md = `## ${blueprint.title}\n\n`;
  md += `**Video:** ${blueprint.video_url}\n\n`;
  md += `### Hook Analysis\n`;
  md += `- **Technique:** ${blueprint.hook_technique}\n`;
  md += `- **Timestamp:** 0:00 - ${blueprint.hook_timestamp}\n`;
  md += `- **Description:** ${blueprint.hook_description}\n\n`;
  md += `### Structure\n`;
  md += `- **Type:** ${blueprint.structure_type}\n`;
  md += `- **Pacing:** ${blueprint.pacing}\n`;
  md += `- **Style:** ${blueprint.editing_style}\n\n`;

  if (blueprint.act_breakdown.length > 0) {
    md += `### Act Breakdown\n`;
    blueprint.act_breakdown.forEach((act, idx) => {
      md += `${idx + 1}. **${act.name}** (${act.timestamp_start} - ${act.timestamp_end})\n`;
      md += `   ${act.description}\n\n`;
    });
  }

  if (blueprint.open_loops.length > 0) {
    md += `### Open Loops\n`;
    blueprint.open_loops.forEach((loop) => {
      md += `- [${loop.timestamp}] **${loop.technique}:** ${loop.description}\n`;
    });
    md += '\n';
  }

  if (blueprint.likely_primary_sources.length > 0) {
    md += `### Sources\n`;
    md += `- **Primary:** ${blueprint.likely_primary_sources.join(', ')}\n`;
  }
  if (blueprint.referenced_materials.length > 0) {
    md += `- **Referenced:** ${blueprint.referenced_materials.join(', ')}\n`;
  }

  return md;
}

export function ContentBlueprintView({ blueprints, isLoading }: ContentBlueprintViewProps) {
  // H-009: Show loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-300">
            Content Blueprints
          </h4>
          <p className="text-xs text-gray-500">
            Analyzing video structures...
          </p>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }
  
  // M-007: Improved empty state with actionable information
  if (blueprints.length === 0) {
    return (
      <div 
        className="text-center py-8 px-4 rounded-lg border border-dashed border-gray-700"
        role="status"
        aria-label="No content blueprints available"
      >
        <svg className="mx-auto h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h5 className="mt-3 text-sm font-medium text-gray-400">No Content Blueprints</h5>
        <p className="mt-1 text-xs text-gray-500">
          Structure analysis will appear here once videos are processed.
        </p>
      </div>
    );
  }

  // H-013: Count blueprints with parse errors
  const errorCount = blueprints.filter(bp => bp.parse_error).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">
          Content Blueprints ({blueprints.length})
          {errorCount > 0 && (
            <span className="ml-2 text-xs text-yellow-500">
              ({errorCount} with parse errors)
            </span>
          )}
        </h4>
        <p className="text-xs text-gray-500">
          Reverse-engineered video structures
        </p>
      </div>

      <div className="space-y-3">
        {blueprints.map((blueprint, idx) => (
          <BlueprintCard key={idx} blueprint={blueprint} />
        ))}
      </div>
    </div>
  );
}

export default ContentBlueprintView;
