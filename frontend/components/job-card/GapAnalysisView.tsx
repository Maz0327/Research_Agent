/**
 * GapAnalysisView component for displaying cross-video gap analysis.
 * Shows missing perspectives, unanswered questions, unexplored topics, and contradictions.
 * Phase 3: Full Research Assistant Pipeline (Jan 2026)
 */
import { useState } from 'react';

/**
 * Missing perspective structure
 */
export interface MissingPerspective {
  perspective: string;
  why_important: string;
  suggested_search: string;
}

/**
 * Coverage blind spot structure
 */
export interface CoverageBlindSpot {
  topic: string;
  where_mentioned: string;
  why_explore: string;
}

/**
 * Contradiction (opportunity) structure
 */
export interface Contradiction {
  claim_a: string;
  source_a: string;
  claim_b: string;
  source_b: string;
  opportunity: string;
}

/**
 * GapAnalysis structure matching backend dataclass
 * H-013: Added parse_error field to detect partial failures
 */
export interface GapAnalysis {
  missing_perspectives: MissingPerspective[];
  unanswered_questions: string[];
  mentioned_but_unexplored: CoverageBlindSpot[];
  contradictions: Contradiction[];
  parse_error?: boolean;  // H-013: True if LLM parsing failed
}

interface GapAnalysisViewProps {
  gapAnalysis: GapAnalysis;
  isLoading?: boolean;  // H-009: Loading state
}

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
      className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs transition ${
        copied
          ? 'bg-green-600 text-white'
          : 'bg-muted text-muted-foreground hover:bg-secondary hover:text-muted-foreground'
      }`}
      title={copied ? 'Copied!' : label || 'Copy'}
    >
      {copied ? (
        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
          />
        </svg>
      )}
    </button>
  );
}

function MissingPerspectiveCard({ perspective }: { perspective: MissingPerspective }) {
  return (
    <div className="rounded-lg border border-red-800/50 bg-red-900/20 p-3">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h6 className="font-medium text-red-300">{perspective.perspective}</h6>
      </div>
      <p className="text-sm text-muted-foreground mb-2">{perspective.why_important}</p>
      <div className="flex items-center gap-2 bg-card/50 rounded px-2 py-1.5">
        <span className="text-xs text-muted-foreground/70">Search:</span>
        <code className="text-xs text-blue-400 flex-1">{perspective.suggested_search}</code>
        <CopyButton text={perspective.suggested_search} label="Copy search query" />
      </div>
    </div>
  );
}

function ContradictionCard({ contradiction }: { contradiction: Contradiction }) {
  return (
    <div className="rounded-lg border border-yellow-800/50 bg-yellow-900/20 p-3">
      <div className="space-y-2">
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-900/50 flex items-center justify-center">
            <span className="text-xs text-blue-400">A</span>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">&ldquo;{contradiction.claim_a}&rdquo;</p>
            <p className="text-xs text-muted-foreground/70">- {contradiction.source_a}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 pl-9">
          <span className="text-muted-foreground/60">vs</span>
        </div>
        <div className="flex gap-3">
          <div className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-900/50 flex items-center justify-center">
            <span className="text-xs text-purple-400">B</span>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">&ldquo;{contradiction.claim_b}&rdquo;</p>
            <p className="text-xs text-muted-foreground/70">- {contradiction.source_b}</p>
          </div>
        </div>
      </div>
      <div className="mt-3 pt-2 border-t border-yellow-800/30">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <p className="text-sm text-yellow-400">{contradiction.opportunity}</p>
        </div>
      </div>
    </div>
  );
}

export function GapAnalysisView({ gapAnalysis, isLoading }: GapAnalysisViewProps) {
  const [copied, setCopied] = useState(false);

  // H-009: Show loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-muted-foreground">Gap Analysis</h4>
          <p className="text-xs text-muted-foreground/70">Identifying gaps...</p>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
        </div>
      </div>
    );
  }

  const hasContent =
    gapAnalysis.missing_perspectives.length > 0 ||
    gapAnalysis.unanswered_questions.length > 0 ||
    gapAnalysis.mentioned_but_unexplored.length > 0 ||
    gapAnalysis.contradictions.length > 0;

  // M-007: Improved empty state with actionable information
  if (!hasContent) {
    return (
      <div 
        className="text-center py-8 px-4 rounded-lg border border-dashed border-border"
        role="status"
        aria-label="No gaps identified"
      >
        <svg className="mx-auto h-12 w-12 text-muted-foreground/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
        <h5 className="mt-3 text-sm font-medium text-muted-foreground">Comprehensive Coverage</h5>
        <p className="mt-1 text-xs text-muted-foreground/70">
          The analyzed videos appear to cover the topic well. No significant gaps detected.
        </p>
      </div>
    );
  }

  const handleCopyAll = async () => {
    const markdown = generateGapAnalysisMarkdown(gapAnalysis);
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
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

  return (
    <div className="space-y-6">
      {/* H-013: Parse error warning */}
      {gapAnalysis.parse_error && (
        <div className="flex items-center gap-2 text-xs text-yellow-500 bg-yellow-900/20 rounded px-3 py-2">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>Gap analysis incomplete - some data may be missing</span>
        </div>
      )}
      
      {/* Header - M-006: ARIA labels */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-muted-foreground">Gap Analysis</h4>
        <button
          onClick={handleCopyAll}
          className={`inline-flex items-center gap-1 rounded px-2 py-1 text-xs transition ${
            copied
              ? 'bg-green-600 text-white'
              : 'bg-muted text-muted-foreground hover:bg-secondary'
          }`}
          aria-label={copied ? 'Gap analysis copied to clipboard' : 'Copy all gap analysis as Markdown'}
        >
          {copied ? 'Copied!' : 'Copy All as Markdown'}
        </button>
      </div>

      {/* Missing Perspectives */}
      {gapAnalysis.missing_perspectives.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground uppercase mb-3 flex items-center gap-2">
            <svg className="h-4 w-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
            </svg>
            Missing Perspectives ({gapAnalysis.missing_perspectives.length})
          </h5>
          <div className="space-y-3">
            {gapAnalysis.missing_perspectives.map((mp, idx) => (
              <MissingPerspectiveCard key={idx} perspective={mp} />
            ))}
          </div>
        </div>
      )}

      {/* Unanswered Questions */}
      {gapAnalysis.unanswered_questions.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground uppercase mb-3 flex items-center gap-2">
            <svg className="h-4 w-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Unanswered Questions ({gapAnalysis.unanswered_questions.length})
          </h5>
          <ul className="space-y-2">
            {gapAnalysis.unanswered_questions.map((question, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm">
                <span className="text-blue-500 flex-shrink-0">?</span>
                <span className="text-muted-foreground">{question}</span>
                <CopyButton text={question} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Mentioned But Unexplored */}
      {gapAnalysis.mentioned_but_unexplored.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground uppercase mb-3 flex items-center gap-2">
            <svg className="h-4 w-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Coverage Blind Spots ({gapAnalysis.mentioned_but_unexplored.length})
          </h5>
          <div className="space-y-2">
            {gapAnalysis.mentioned_but_unexplored.map((topic, idx) => (
              <div key={idx} className="rounded-lg border border-amber-800/50 bg-amber-900/20 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h6 className="font-medium text-amber-300">{topic.topic}</h6>
                    <p className="text-xs text-muted-foreground/70 mt-0.5">Mentioned in: {topic.where_mentioned}</p>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-2">{topic.why_explore}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictions */}
      {gapAnalysis.contradictions.length > 0 && (
        <div>
          <h5 className="text-xs font-medium text-muted-foreground uppercase mb-3 flex items-center gap-2">
            <svg className="h-4 w-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Contradictions - Opportunities ({gapAnalysis.contradictions.length})
          </h5>
          <div className="space-y-3">
            {gapAnalysis.contradictions.map((c, idx) => (
              <ContradictionCard key={idx} contradiction={c} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function generateGapAnalysisMarkdown(gapAnalysis: GapAnalysis): string {
  let md = `# Gap Analysis\n\n`;

  if (gapAnalysis.missing_perspectives.length > 0) {
    md += `## Missing Perspectives\n\n`;
    gapAnalysis.missing_perspectives.forEach((mp, idx) => {
      md += `### ${idx + 1}. ${mp.perspective}\n`;
      md += `**Why Important:** ${mp.why_important}\n`;
      md += `**Suggested Search:** \`${mp.suggested_search}\`\n\n`;
    });
  }

  if (gapAnalysis.unanswered_questions.length > 0) {
    md += `## Unanswered Questions\n\n`;
    gapAnalysis.unanswered_questions.forEach((q) => {
      md += `- ${q}\n`;
    });
    md += '\n';
  }

  if (gapAnalysis.mentioned_but_unexplored.length > 0) {
    md += `## Coverage Blind Spots\n\n`;
    gapAnalysis.mentioned_but_unexplored.forEach((topic) => {
      md += `### ${topic.topic}\n`;
      md += `**Mentioned in:** ${topic.where_mentioned}\n`;
      md += `**Why Explore:** ${topic.why_explore}\n\n`;
    });
  }

  if (gapAnalysis.contradictions.length > 0) {
    md += `## Contradictions (Opportunities)\n\n`;
    gapAnalysis.contradictions.forEach((c, idx) => {
      md += `### ${idx + 1}. Conflict\n`;
      md += `**Claim A (${c.source_a}):** "${c.claim_a}"\n`;
      md += `**Claim B (${c.source_b}):** "${c.claim_b}"\n`;
      md += `**Opportunity:** ${c.opportunity}\n\n`;
    });
  }

  return md;
}

export default GapAnalysisView;
