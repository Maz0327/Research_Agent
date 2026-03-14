/**
 * Shared MarkdownRenderer — single source of truth for rendering markdown.
 *
 * Uses react-markdown with remark/rehype plugins for proper AST-based parsing.
 * Replaces three separate regex-based renderers (DocumentViewerModal,
 * DocumentAccordion, shared/[token]) with one shared component.
 *
 * Features:
 * - GFM tables, strikethrough, task lists (remark-gfm)
 * - Raw HTML passthrough for <details>/<summary> (rehype-raw)
 * - GitHub-style alerts (custom preprocessing)
 * - Clickable links with external indicators
 * - ADHD-friendly visual hierarchy (borders on headings, alternating table rows)
 * - Dark-mode-first Tailwind styling
 * - Collapsible sections for source transcripts
 */

import { useState, useCallback, type ReactNode, type HTMLAttributes, type DetailedHTMLProps } from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MarkdownRendererProps {
  /** Markdown string to render */
  content: string;
  /** Compact mode uses smaller text and spacing (for accordion previews) */
  compact?: boolean;
}

// ---------------------------------------------------------------------------
// Preprocessing — transform patterns the remark pipeline doesn't handle natively
// ---------------------------------------------------------------------------

/**
 * Preprocess markdown before passing to react-markdown.
 *
 * Handles:
 * - GitHub-style alerts (> [!NOTE]) → styled HTML divs
 *   (remark-gfm doesn't handle these, and rehype-raw lets our HTML through)
 */
function preprocessMarkdown(md: string): string {
  let result = md;

  // GitHub-style alerts → styled divs (must be done before remark parses blockquotes)
  const alertConfig: Record<string, { border: string; bg: string; icon: string; titleColor: string }> = {
    NOTE:      { border: '#3b82f6', bg: 'rgba(59,130,246,0.08)',  icon: 'ℹ️', titleColor: '#93c5fd' },
    TIP:       { border: '#22c55e', bg: 'rgba(34,197,94,0.07)',   icon: '💡', titleColor: '#86efac' },
    IMPORTANT: { border: '#8b5cf6', bg: 'rgba(139,92,246,0.08)',  icon: '⚡', titleColor: '#c4b5fd' },
    WARNING:   { border: '#f59e0b', bg: 'rgba(245,158,11,0.07)',  icon: '⚠️', titleColor: '#fde68a' },
    CAUTION:   { border: '#f59e0b', bg: 'rgba(245,158,11,0.07)',  icon: '🚨', titleColor: '#fde68a' },
  };

  result = result.replace(
    /^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n((?:^> .*\n?)*)/gm,
    (_, type: string, body: string) => {
      const content = body.replace(/^> ?/gm, '').trim();
      const cfg = alertConfig[type] || alertConfig.NOTE;
      return `<div class="github-alert" style="border-left:4px solid ${cfg.border};background:${cfg.bg};padding:16px 20px;margin:20px 0;border-radius:8px;">\n<div style="color:${cfg.titleColor};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">${cfg.icon} ${type}</div>\n<div style="color:#d1d5db;font-size:14px;line-height:1.65;">${content}</div>\n</div>\n`;
    }
  );

  return result;
}

// ---------------------------------------------------------------------------
// Custom components for react-markdown
// ---------------------------------------------------------------------------

/** Collapsible section — replaces native <details> with a styled React version */
function CollapsibleDetails({ children, ...props }: DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement>) {
  const [isOpen, setIsOpen] = useState(false);

  // Separate summary from body children
  let summaryContent: ReactNode = 'Details';
  const bodyChildren: ReactNode[] = [];

  const childArray = Array.isArray(children) ? children : [children];
  childArray.forEach((child) => {
    if (child && typeof child === 'object' && 'type' in child && child.type === 'summary') {
      summaryContent = child.props?.children || 'Details';
    } else {
      bodyChildren.push(child);
    }
  });

  return (
    <div className="collapsible-section my-4 border border-gray-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left text-sm font-medium text-blue-300 bg-gray-800/80 hover:bg-gray-700/80 transition cursor-pointer"
      >
        <span
          className="text-gray-500 transition-transform duration-200"
          style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
        >
          &#9654;
        </span>
        <span>{summaryContent}</span>
      </button>
      {isOpen && (
        <div className="bg-gray-900/50 border-t border-gray-700">
          <div className="p-4 max-h-[600px] overflow-y-auto">
            {bodyChildren}
          </div>
        </div>
      )}
    </div>
  );
}

/** Suppressed — we handle summary content inside CollapsibleDetails */
function CollapsibleSummary({ children }: { children?: ReactNode }) {
  return <>{children}</>;
}

// Table row index tracker for alternating backgrounds
let tableRowIndex = 0;

/**
 * Build the components map for react-markdown.
 * @param compact — smaller text + tighter spacing for accordion views
 */
function buildComponents(compact: boolean) {
  // Heading sizes by level
  const headingStyles = compact
    ? {
        h1: 'text-xl font-bold text-white mt-5 mb-3 pb-2 border-b-2 border-gray-600',
        h2: 'text-lg font-bold text-gray-50 mt-5 mb-2 pb-1 border-b border-gray-700',
        h3: 'text-base font-semibold text-gray-100 mt-4 mb-2 pb-1 border-b border-gray-800',
        h4: 'text-sm font-semibold text-gray-200 mt-3 mb-1',
      }
    : {
        h1: 'text-2xl font-bold text-white mt-8 mb-5 pb-3 border-b-2 border-gray-600',
        h2: 'text-xl font-bold text-gray-50 mt-10 mb-4 pb-2 border-b border-gray-700',
        h3: 'text-base font-semibold text-gray-100 mt-7 mb-3',
        h4: 'text-base font-semibold text-gray-200 mt-5 mb-2',
      };

  const components: Record<string, any> = {
    // ----- Headings with visual hierarchy -----
    h1: ({ children }: { children?: ReactNode }) => (
      <h1 className={headingStyles.h1}>{children}</h1>
    ),
    h2: ({ children }: { children?: ReactNode }) => (
      <h2 className={headingStyles.h2}>{children}</h2>
    ),
    h3: ({ children }: { children?: ReactNode }) => (
      <h3 className={headingStyles.h3}>{children}</h3>
    ),
    h4: ({ children }: { children?: ReactNode }) => (
      <h4 className={headingStyles.h4}>{children}</h4>
    ),

    // ----- Paragraph — improved line-height and spacing -----
    p: ({ children }: { children?: ReactNode }) => (
      <p className={compact ? 'my-1.5 leading-relaxed text-sm' : 'my-3 leading-[1.75] text-[15px]'}>{children}</p>
    ),

    // ----- Links with external indicator -----
    a: ({ href, children }: { href?: string; children?: ReactNode }) => {
      const isExternal = href?.startsWith('http');
      return (
        <a
          href={href}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
          className="text-blue-400 hover:text-blue-300 underline decoration-blue-400/30 hover:decoration-blue-300 transition inline-flex items-center gap-1 break-all"
        >
          {children}
          {isExternal && (
            <svg className="h-3 w-3 inline-block flex-shrink-0 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          )}
        </a>
      );
    },

    // ----- Code blocks — prose detection for source text -----
    pre: ({ children }: { children?: ReactNode }) => (
      <pre className={`bg-gray-800/80 rounded-lg ${compact ? 'p-3 my-2' : 'p-4 my-4'} border border-gray-700/50 text-sm leading-relaxed whitespace-pre-wrap break-words overflow-x-hidden`}>
        {children}
      </pre>
    ),
    code: ({ className, children, ...props }: { className?: string; children?: ReactNode; inline?: boolean }) => {
      // If there's a language class it's a fenced code block (rendered inside <pre>)
      const isBlock = className?.startsWith('language-');
      if (isBlock) {
        return (
          <code className="text-gray-300 whitespace-pre-wrap break-words" {...props}>
            {children}
          </code>
        );
      }
      // Inline code
      return (
        <code className="bg-gray-800 px-1.5 py-0.5 rounded text-blue-300 text-sm" {...props}>
          {children}
        </code>
      );
    },

    // ----- Tables with alternating rows — more padding -----
    table: ({ children }: { children?: ReactNode }) => {
      tableRowIndex = 0; // reset on each table
      return (
        <div className={`overflow-x-auto ${compact ? 'my-3' : 'my-5'} rounded-lg border border-gray-700/50`}>
          <table className="w-full text-sm border-collapse">{children}</table>
        </div>
      );
    },
    thead: ({ children }: { children?: ReactNode }) => (
      <thead className="bg-gray-800/60">{children}</thead>
    ),
    th: ({ children }: { children?: ReactNode }) => (
      <th className={`${compact ? 'px-2 py-1.5 text-xs' : 'px-4 py-3 text-xs'} text-left font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-600`}>
        {children}
      </th>
    ),
    td: ({ children }: { children?: ReactNode }) => (
      <td className={`${compact ? 'px-2 py-1.5 text-xs' : 'px-4 py-3 text-sm'} text-gray-200 border-b border-gray-800/50`}>
        {children}
      </td>
    ),
    tr: ({ children }: { children?: ReactNode }) => {
      const idx = tableRowIndex++;
      const bg = idx % 2 === 0 ? 'bg-gray-800/30' : 'bg-gray-800/10';
      return (
        <tr className={`${bg} hover:bg-gray-700/30 transition-colors`}>{children}</tr>
      );
    },

    // ----- Lists — more breathing room -----
    ul: ({ children }: { children?: ReactNode }) => (
      <ul className={`${compact ? 'my-2 space-y-0.5' : 'my-4 space-y-2'}`}>{children}</ul>
    ),
    ol: ({ children }: { children?: ReactNode }) => (
      <ol className={`${compact ? 'my-2 space-y-0.5' : 'my-4 space-y-2'} list-decimal`}>{children}</ol>
    ),
    li: ({ children }: { children?: ReactNode }) => (
      <li className="ml-4 pl-1 list-disc text-gray-300 leading-[1.7]">{children}</li>
    ),

    // ----- Blockquotes — remove italic, improve readability -----
    blockquote: ({ children }: { children?: ReactNode }) => (
      <blockquote className="border-l-4 border-gray-600 pl-5 py-2 my-4 text-gray-300 leading-relaxed">
        {children}
      </blockquote>
    ),

    // ----- Horizontal rule -----
    hr: () => <hr className={`border-gray-700/50 ${compact ? 'my-4' : 'my-8'}`} />,

    // ----- Strong / emphasis -----
    strong: ({ children }: { children?: ReactNode }) => (
      <strong className="font-semibold text-gray-100">{children}</strong>
    ),
    em: ({ children }: { children?: ReactNode }) => (
      <em className="italic text-gray-300">{children}</em>
    ),

    // ----- Images -----
    img: ({ src, alt }: { src?: string; alt?: string }) => (
      <img src={src} alt={alt || ''} className="rounded-lg max-w-full h-auto my-3 border border-gray-700" loading="lazy" />
    ),

    // ----- Collapsible sections (from backend's <details>/<summary>) -----
    details: CollapsibleDetails,
    summary: CollapsibleSummary,

    // ----- GitHub alert divs (from our preprocessing) -----
    div: ({ className, style, children, ...props }: DetailedHTMLProps<HTMLAttributes<HTMLDivElement>, HTMLDivElement>) => {
      // Pass through our preprocessed alert divs with their inline styles
      return <div className={className} style={style} {...props}>{children}</div>;
    },
  };

  return components;
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function MarkdownRenderer({ content, compact = false }: MarkdownRendererProps) {
  const processed = preprocessMarkdown(content);
  const components = useCallback(() => buildComponents(compact), [compact])();

  return (
    <div className={`text-gray-300 leading-relaxed ${compact ? 'text-sm' : ''}`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={components}
      >
        {processed}
      </Markdown>
    </div>
  );
}

export default MarkdownRenderer;
