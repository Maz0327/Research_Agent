/**
 * ResearchStarterView component for displaying actionable research next steps.
 * Shows search queries, source suggestions, rabbit holes, and content angles.
 * Phase 3: Full Research Assistant Pipeline (Jan 2026)
 */
import { useState } from 'react';

/**
 * Search query structure
 */
export interface SearchQuery {
  query: string;
  platform: string;
  why: string;
}

/**
 * Source suggestion structure
 */
export interface SourceSuggestion {
  source_type: string;
  description: string;
  why_helpful: string;
}

/**
 * Rabbit hole (bounded tangent) structure
 */
export interface RabbitHole {
  topic: string;
  mentioned_in: string;
  potential_angle: string;
}

/**
 * Content angle structure
 */
export interface ContentAngle {
  angle: string;
  differentiator: string;
  why_unique: string;
}

/**
 * ResearchStarter structure matching backend dataclass
 * H-013: Added parse_error field to detect partial failures
 */
export interface ResearchStarter {
  search_queries: SearchQuery[];
  source_suggestions: SourceSuggestion[];
  rabbit_holes: RabbitHole[];
  content_angles: ContentAngle[];
  parse_error?: boolean;  // H-013: True if LLM parsing failed
}

interface ResearchStarterViewProps {
  researchStarter: ResearchStarter;
  isLoading?: boolean;  // H-009: Loading state
}

const platformIcons: Record<string, { icon: string; color: string; bg: string }> = {
  google: { icon: 'G', color: 'text-blue-400', bg: 'bg-blue-900/50' },
  youtube: { icon: '>', color: 'text-red-400', bg: 'bg-red-900/50' },
  reddit: { icon: 'R', color: 'text-orange-400', bg: 'bg-orange-900/50' },
  academic: { icon: 'A', color: 'text-green-400', bg: 'bg-green-900/50' },
  default: { icon: '?', color: 'text-gray-400', bg: 'bg-gray-800/50' },
};

const sourceTypeIcons: Record<string, { icon: string; color: string }> = {
  documentary: { icon: 'Doc', color: 'text-purple-400' },
  podcast: { icon: 'Pod', color: 'text-pink-400' },
  academic_paper: { icon: 'Paper', color: 'text-blue-400' },
  news_article: { icon: 'News', color: 'text-amber-400' },
  reddit_discussion: { icon: 'Reddit', color: 'text-orange-400' },
  book: { icon: 'Book', color: 'text-green-400' },
  default: { icon: 'Src', color: 'text-gray-400' },
};

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
        copied
          ? 'bg-green-600 text-white'
          : 'bg-gray-700 text-gray-400 hover:bg-gray-600 hover:text-gray-300'
      }`}
      title={copied ? 'Copied!' : label || 'Copy'}
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}

function SearchQueryCard({ query }: { query: SearchQuery }) {
  const platform = query.platform.toLowerCase();
  const config = platformIcons[platform] || platformIcons.default;

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-3">
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center`}>
          <span className={`text-xs font-bold ${config.color}`}>{config.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className={`text-xs font-medium ${config.color} uppercase`}>
              {query.platform}
            </span>
            <CopyButton text={query.query} label="Copy query" />
          </div>
          <code className="block text-sm text-gray-200 bg-gray-900/50 rounded px-2 py-1.5 mb-2 break-all">
            {query.query}
          </code>
          <p className="text-xs text-gray-500">{query.why}</p>
        </div>
      </div>
    </div>
  );
}

function SourceSuggestionCard({ suggestion }: { suggestion: SourceSuggestion }) {
  const sourceType = suggestion.source_type.toLowerCase();
  const config = sourceTypeIcons[sourceType] || sourceTypeIcons.default;

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-3">
      <div className="flex items-start gap-3">
        <span className={`text-xs font-bold ${config.color} bg-gray-900/50 rounded px-2 py-1`}>
          {config.icon}
        </span>
        <div className="flex-1">
          <p className="text-sm text-gray-300 mb-1">{suggestion.description}</p>
          <p className="text-xs text-gray-500">{suggestion.why_helpful}</p>
        </div>
      </div>
    </div>
  );
}

function RabbitHoleCard({ rabbitHole }: { rabbitHole: RabbitHole }) {
  return (
    <div className="rounded-lg border border-purple-800/50 bg-purple-900/20 p-3">
      <h6 className="font-medium text-purple-300 mb-1">{rabbitHole.topic}</h6>
      <p className="text-xs text-gray-500 mb-2">Mentioned in: {rabbitHole.mentioned_in}</p>
      <p className="text-sm text-gray-400">{rabbitHole.potential_angle}</p>
    </div>
  );
}

function ContentAngleCard({ angle }: { angle: ContentAngle }) {
  return (
    <div className="rounded-lg border border-green-800/50 bg-green-900/20 p-4">
      <h6 className="font-medium text-green-300 mb-2">{angle.angle}</h6>
      <div className="space-y-2">
        <div>
          <span className="text-xs text-gray-500">Differentiator: </span>
          <span className="text-sm text-gray-300">{angle.differentiator}</span>
        </div>
        <div>
          <span className="text-xs text-gray-500">Why it works: </span>
          <span className="text-sm text-gray-400">{angle.why_unique}</span>
        </div>
      </div>
    </div>
  );
}

export function ResearchStarterView({ researchStarter, isLoading }: ResearchStarterViewProps) {
  const [activeSection, setActiveSection] = useState<'queries' | 'sources' | 'angles'>('queries');
  const [copiedAll, setCopiedAll] = useState(false);

  // H-009: Show loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-300">Research Starter</h4>
          <p className="text-xs text-gray-500">Generating research directions...</p>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
        </div>
      </div>
    );
  }

  const hasContent =
    researchStarter.search_queries.length > 0 ||
    researchStarter.source_suggestions.length > 0 ||
    researchStarter.rabbit_holes.length > 0 ||
    researchStarter.content_angles.length > 0;

  // M-007: Improved empty state with actionable information
  if (!hasContent) {
    return (
      <div 
        className="text-center py-8 px-4 rounded-lg border border-dashed border-gray-700"
        role="status"
        aria-label="No research starters generated"
      >
        <svg className="mx-auto h-12 w-12 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <h5 className="mt-3 text-sm font-medium text-gray-400">No Research Directions</h5>
        <p className="mt-1 text-xs text-gray-500">
          Research suggestions will appear after gap analysis identifies areas to explore.
        </p>
      </div>
    );
  }

  const handleCopyAll = async () => {
    const markdown = generateResearchStarterMarkdown(researchStarter);
    try {
      await navigator.clipboard.writeText(markdown);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      {/* H-013: Parse error warning */}
      {researchStarter.parse_error && (
        <div className="flex items-center gap-2 text-xs text-yellow-500 bg-yellow-900/20 rounded px-3 py-2">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>Research starter generation incomplete - some suggestions may be missing</span>
        </div>
      )}
      
      {/* Header - M-006: ARIA labels */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-300">Research Starter</h4>
        <button
          onClick={handleCopyAll}
          className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
            copiedAll
              ? 'bg-green-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
          aria-label={copiedAll ? 'Research starter copied to clipboard' : 'Copy all research starters as Markdown'}
        >
          {copiedAll ? 'Copied!' : 'Copy All as Markdown'}
        </button>
      </div>

      {/* Section tabs */}
      <div className="flex border-b border-gray-700">
        <button
          onClick={() => setActiveSection('queries')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeSection === 'queries'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          Queries ({researchStarter.search_queries.length})
        </button>
        <button
          onClick={() => setActiveSection('sources')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeSection === 'sources'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          Sources ({researchStarter.source_suggestions.length})
        </button>
        <button
          onClick={() => setActiveSection('angles')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeSection === 'angles'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-400 hover:text-gray-300'
          }`}
        >
          Angles ({researchStarter.content_angles.length})
        </button>
      </div>

      {/* Content */}
      <div className="space-y-4">
        {/* Search Queries */}
        {activeSection === 'queries' && (
          <div className="space-y-3">
            {researchStarter.search_queries.length > 0 ? (
              researchStarter.search_queries.map((query, idx) => (
                <SearchQueryCard key={idx} query={query} />
              ))
            ) : (
              <p className="text-center text-gray-500 py-4">No search queries generated.</p>
            )}
          </div>
        )}

        {/* Source Suggestions */}
        {activeSection === 'sources' && (
          <div className="space-y-3">
            {researchStarter.source_suggestions.length > 0 ? (
              researchStarter.source_suggestions.map((suggestion, idx) => (
                <SourceSuggestionCard key={idx} suggestion={suggestion} />
              ))
            ) : (
              <p className="text-center text-gray-500 py-4">No source suggestions generated.</p>
            )}
          </div>
        )}

        {/* Content Angles + Rabbit Holes */}
        {activeSection === 'angles' && (
          <div className="space-y-6">
            {/* Content Angles */}
            {researchStarter.content_angles.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-gray-400 uppercase mb-3 flex items-center gap-2">
                  <svg className="h-4 w-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Content Angles
                </h5>
                <div className="space-y-3">
                  {researchStarter.content_angles.map((angle, idx) => (
                    <ContentAngleCard key={idx} angle={angle} />
                  ))}
                </div>
              </div>
            )}

            {/* Rabbit Holes */}
            {researchStarter.rabbit_holes.length > 0 && (
              <div>
                <h5 className="text-xs font-medium text-gray-400 uppercase mb-3 flex items-center gap-2">
                  <svg className="h-4 w-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  Bounded Rabbit Holes ({researchStarter.rabbit_holes.length})
                </h5>
                <div className="space-y-3">
                  {researchStarter.rabbit_holes.map((rh, idx) => (
                    <RabbitHoleCard key={idx} rabbitHole={rh} />
                  ))}
                </div>
              </div>
            )}

            {researchStarter.content_angles.length === 0 && researchStarter.rabbit_holes.length === 0 && (
              <p className="text-center text-gray-500 py-4">No content angles generated.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function generateResearchStarterMarkdown(researchStarter: ResearchStarter): string {
  let md = `# Research Starter\n\n`;

  if (researchStarter.search_queries.length > 0) {
    md += `## Search Queries\n\n`;
    const groupedByPlatform: Record<string, SearchQuery[]> = {};
    researchStarter.search_queries.forEach((q) => {
      const platform = q.platform || 'other';
      if (!groupedByPlatform[platform]) groupedByPlatform[platform] = [];
      groupedByPlatform[platform].push(q);
    });

    Object.entries(groupedByPlatform).forEach(([platform, queries]) => {
      md += `### ${platform.charAt(0).toUpperCase() + platform.slice(1)}\n\n`;
      queries.forEach((q) => {
        md += `- \`${q.query}\`\n  - ${q.why}\n\n`;
      });
    });
  }

  if (researchStarter.source_suggestions.length > 0) {
    md += `## Source Suggestions\n\n`;
    researchStarter.source_suggestions.forEach((s) => {
      md += `### ${s.source_type}\n`;
      md += `- **What to find:** ${s.description}\n`;
      md += `- **Why helpful:** ${s.why_helpful}\n\n`;
    });
  }

  if (researchStarter.content_angles.length > 0) {
    md += `## Content Angles\n\n`;
    researchStarter.content_angles.forEach((a, idx) => {
      md += `### ${idx + 1}. ${a.angle}\n`;
      md += `- **Differentiator:** ${a.differentiator}\n`;
      md += `- **Why unique:** ${a.why_unique}\n\n`;
    });
  }

  if (researchStarter.rabbit_holes.length > 0) {
    md += `## Rabbit Holes (Bounded)\n\n`;
    researchStarter.rabbit_holes.forEach((rh) => {
      md += `### ${rh.topic}\n`;
      md += `- **Mentioned in:** ${rh.mentioned_in}\n`;
      md += `- **Potential angle:** ${rh.potential_angle}\n\n`;
    });
  }

  return md;
}

export default ResearchStarterView;
