/**
 * DocumentAccordion - Collapsible document section with lazy loading.
 * Replaces DocumentCard grid with expandable accordion UI.
 *
 * Uses presentation layer formatting to display user-friendly labels
 * (e.g., "Source 1" instead of "SRC_1") without modifying stored JSON.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import DOMPurify from 'dompurify';
import { authFetch, parseJsonResponse } from '@/lib/api-client';
import { getAccessToken } from '@/lib/supabase';
import { exportToPdf } from '@/lib/pdf-export';
import { transformMarkdownForDisplay } from '@/lib/document-formatters';

export type DocKey = 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3' | 'booster';
export type ColorScheme = 'gray' | 'blue' | 'purple' | 'amber' | 'indigo';

export interface DocumentAccordionProps {
  jobId: string;
  docKey: DocKey;
  title: string;
  subtitle: string;
  colorScheme: ColorScheme;
  /** Pre-loaded inline data (legacy jobs only - not used when hasStoragePath=true) */
  inlineMarkdown?: string;
  /** Whether a storage path exists for this document (forces API fetch over inline) */
  hasStoragePath?: boolean;
}

// API response for lazy loading
interface DocumentApiResponse {
  url?: string;
  expires_in?: number;
  data?: Record<string, unknown>;
  markdown?: string;
}

// Color scheme configuration
const colorConfig: Record<ColorScheme, {
  headerBg: string;
  headerBorder: string;
  badge: string;
  chevron: string;
  contentBg: string;
  button: string;
}> = {
  gray: {
    headerBg: 'bg-gray-800/50 hover:bg-gray-800/70',
    headerBorder: 'border-gray-700',
    badge: 'bg-gray-700 text-gray-300',
    chevron: 'text-gray-400',
    contentBg: 'bg-gray-900/50',
    button: 'bg-gray-700 hover:bg-gray-600 text-gray-300',
  },
  blue: {
    headerBg: 'bg-blue-900/20 hover:bg-blue-900/30',
    headerBorder: 'border-blue-800/50',
    badge: 'bg-blue-900/50 text-blue-300',
    chevron: 'text-blue-400',
    contentBg: 'bg-blue-950/20',
    button: 'bg-blue-600/30 hover:bg-blue-600/40 text-blue-300',
  },
  purple: {
    headerBg: 'bg-purple-900/20 hover:bg-purple-900/30',
    headerBorder: 'border-purple-800/50',
    badge: 'bg-purple-900/50 text-purple-300',
    chevron: 'text-purple-400',
    contentBg: 'bg-purple-950/20',
    button: 'bg-purple-600/30 hover:bg-purple-600/40 text-purple-300',
  },
  amber: {
    headerBg: 'bg-amber-900/20 hover:bg-amber-900/30',
    headerBorder: 'border-amber-800/50',
    badge: 'bg-amber-900/50 text-amber-300',
    chevron: 'text-amber-400',
    contentBg: 'bg-amber-950/20',
    button: 'bg-amber-600/30 hover:bg-amber-600/40 text-amber-300',
  },
  indigo: {
    headerBg: 'bg-indigo-900/20 hover:bg-indigo-900/30',
    headerBorder: 'border-indigo-800/50',
    badge: 'bg-indigo-900/50 text-indigo-300',
    chevron: 'text-indigo-400',
    contentBg: 'bg-indigo-950/20',
    button: 'bg-indigo-600/30 hover:bg-indigo-600/40 text-indigo-300',
  },
};

// Doc number mapping (null for non-numbered docs like booster)
const docNumbers: Record<DocKey, number | null> = {
  doc_0: 0,
  doc_1: 1,
  doc_2: 2,
  doc_3: 3,
  booster: null,
};

/**
 * Detect if markdown content is a placeholder stub (not real content).
 * Backend writes these when storage upload succeeds to reduce payload.
 */
function isPlaceholderContent(content: string | null | undefined): boolean {
  if (!content) return true;
  return (
    content.includes('Document Available via Cloud Storage') ||
    content.includes('inline JSON omitted')
  );
}

export function DocumentAccordion({
  jobId,
  docKey,
  title,
  subtitle,
  colorScheme,
  inlineMarkdown,
  hasStoragePath = false,
}: DocumentAccordionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Determine if we have real content or just a placeholder
  const inlineIsPlaceholder = isPlaceholderContent(inlineMarkdown);

  // Only use inline markdown if: (1) no storage path AND (2) not a placeholder
  const initialMarkdown = (!hasStoragePath && !inlineIsPlaceholder) ? (inlineMarkdown ?? null) : null;
  const [markdown, setMarkdown] = useState<string | null>(initialMarkdown);

  // Track whether we need to fetch from storage
  const needsStorageFetch = hasStoragePath || inlineIsPlaceholder;

  const config = colorConfig[colorScheme];
  const docNum = docNumbers[docKey];

  // Fetch document content (lazy loading)
  const fetchDocument = useCallback(async (): Promise<string | null> => {
    try {
      const token = await getAccessToken();
      const response = await authFetch(`/jobs/${jobId}/documents/${docKey}`, token);
      const result = await parseJsonResponse<DocumentApiResponse>(response);

      // If we got a signed URL, fetch the actual content
      if (result.url) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        try {
          const contentResponse = await fetch(result.url, { signal: controller.signal });
          clearTimeout(timeoutId);
          if (!contentResponse.ok) {
            throw new Error(`Failed to fetch document from storage: ${contentResponse.status}`);
          }
          const content = await contentResponse.json();
          return content.markdown || null;
        } catch (err) {
          clearTimeout(timeoutId);
          if (err instanceof Error && err.name === 'AbortError') {
            throw new Error('Document fetch timed out. Please try again.');
          }
          throw err;
        }
      }

      // Direct inline data response (fallback)
      return result.markdown || null;
    } catch (err) {
      console.error(`Failed to fetch ${docKey}:`, err);
      throw err;
    }
  }, [jobId, docKey]);

  // Handle accordion toggle
  const handleToggle = async () => {
    if (isExpanded) {
      setIsExpanded(false);
      return;
    }

    setIsExpanded(true);

    // If markdown already loaded from storage or real inline, don't fetch again
    // Exception: if we need storage fetch and haven't fetched yet, always fetch
    if (markdown && !needsStorageFetch) return;
    if (markdown && needsStorageFetch && !isPlaceholderContent(markdown)) return;

    // Lazy load content from storage API
    setIsLoading(true);
    setError(null);
    try {
      const content = await fetchDocument();
      setMarkdown(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setIsLoading(false);
    }
  };

  // Check if current markdown is exportable (real content, not placeholder)
  const hasExportableContent = markdown && !isPlaceholderContent(markdown);

  // Handle PDF download
  const handleDownloadPdf = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!hasExportableContent) {
      alert('Please expand the document to load it before downloading.');
      return;
    }
    const filename = docNum !== null
      ? `doc-${docNum}-${title.toLowerCase().replace(/\s+/g, '-')}`
      : `${docKey}-${title.toLowerCase().replace(/\s+/g, '-')}`;
    try {
      await exportToPdf(markdown!, filename);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate PDF');
    }
  };

  return (
    <div className={`rounded-xl ${config.headerBg} overflow-hidden transition-all`}>
      {/* Header - Always visible, touch-optimized */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4 transition-colors cursor-pointer touch-manipulation min-h-[56px] sm:min-h-0"
      >
        <div className="flex items-center gap-3 sm:gap-4 min-w-0">
          <span className={`px-2 sm:px-2.5 py-1 rounded-md text-xs font-semibold flex-shrink-0 ${config.badge}`}>
            {docNum !== null ? `DOC ${docNum}` : 'BOOST'}
          </span>
          <div className="text-left min-w-0">
            <h4 className="font-medium text-gray-100 text-sm sm:text-base truncate">{title}</h4>
            <p className="text-xs text-gray-500 mt-0.5 truncate">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0 ml-2">
          {/* PDF Download - 44px touch target on mobile */}
          {hasExportableContent && (
            <button
              onClick={handleDownloadPdf}
              className={`p-2.5 sm:p-2 rounded-lg ${config.button} transition-colors min-w-[44px] min-h-[44px] sm:min-w-0 sm:min-h-0 flex items-center justify-center touch-manipulation`}
              title="Download PDF"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </button>
          )}

          {/* Chevron indicator */}
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className={config.chevron}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </motion.div>
        </div>
      </button>

      {/* Content - Expandable */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            {/* Content area - responsive padding and height */}
            <div className={`px-4 sm:px-5 py-4 sm:py-5 ${config.contentBg}`}>
              {/* Loading state */}
              {isLoading && (
                <div className="flex items-center justify-center py-8 sm:py-12">
                  <svg className="h-6 w-6 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="ml-3 text-gray-400 text-sm sm:text-base">Loading document...</span>
                </div>
              )}

              {/* Error state */}
              {error && !isLoading && (
                <div className="rounded-lg bg-red-900/20 p-3 sm:p-4">
                  <p className="text-sm text-red-300 leading-relaxed">{error}</p>
                </div>
              )}

              {/* Content - Apply presentation layer transformation, responsive max-height */}
              {markdown && !isLoading && (
                <div className="prose prose-invert prose-sm max-w-none max-h-[20rem] sm:max-h-[28rem] overflow-y-auto leading-relaxed overscroll-contain">
                  <MarkdownRenderer content={transformMarkdownForDisplay(markdown)} />
                </div>
              )}

              {/* No content */}
              {!markdown && !isLoading && !error && (
                <p className="text-sm text-gray-500 italic py-4">No content available</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Simple markdown renderer - converts basic markdown to HTML.
 * Uses DOMPurify to sanitize output and prevent XSS attacks.
 */
function MarkdownRenderer({ content }: { content: string }) {
  const parseMarkdown = (text: string): string => {
    let result = text;

    // Code blocks (protect from other transformations)
    result = result.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-800 rounded p-3 my-2 overflow-x-auto"><code>$2</code></pre>');

    // Inline code
    result = result.replace(/`([^`]+)`/g, '<code class="bg-gray-800 px-1 rounded text-blue-300">$1</code>');

    // GitHub-style alerts - convert to styled callout boxes
    // Must be processed BEFORE blockquotes since alerts use > prefix
    result = result.replace(/^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n((?:^> .*\n?)*)/gm, (_, type, content) => {
      const alertContent = content.replace(/^> ?/gm, '').trim();
      const colors: Record<string, string> = {
        NOTE: 'border-blue-500 bg-blue-900/20',
        TIP: 'border-green-500 bg-green-900/20',
        IMPORTANT: 'border-purple-500 bg-purple-900/20',
        WARNING: 'border-yellow-500 bg-yellow-900/20',
        CAUTION: 'border-red-500 bg-red-900/20',
      };
      const colorClass = colors[type] || colors.NOTE;
      return `<div class="border-l-4 ${colorClass} pl-4 py-2 my-3 rounded-r">${alertContent}</div>`;
    });

    // Simple blockquotes (lines starting with >)
    result = result.replace(/^> (.+)$/gm, '<blockquote class="border-l-4 border-gray-600 pl-4 py-1 my-2 text-gray-400 italic">$1</blockquote>');

    // Merge consecutive blockquotes
    result = result.replace(/(<\/blockquote>\n?<blockquote[^>]*>)/g, '<br/>');

    // Tables - detect table blocks and convert
    result = result.replace(/(\|[^\n]+\|\n)+/g, (tableBlock) => {
      const rows = tableBlock.trim().split('\n');
      if (rows.length < 2) return tableBlock;

      let html = '<table class="w-full my-3 text-sm border-collapse">';

      rows.forEach((row, idx) => {
        // Skip separator row (|---|---|)
        if (/^\|[\s-:|]+\|$/.test(row)) return;

        const cells = row.split('|').filter((c, i, arr) => i > 0 && i < arr.length - 1);
        const isHeader = idx === 0;
        const tag = isHeader ? 'th' : 'td';
        const cellClass = isHeader
          ? 'px-3 py-2 text-left font-semibold text-gray-200 border-b border-gray-700'
          : 'px-3 py-2 text-gray-300 border-b border-gray-800';

        html += '<tr>';
        cells.forEach(cell => {
          html += `<${tag} class="${cellClass}">${cell.trim()}</${tag}>`;
        });
        html += '</tr>';
      });

      html += '</table>';
      return html;
    });

    // Headers (#### before ### before ## before #)
    result = result.replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-gray-200 mt-3 mb-2">$1</h4>');
    result = result.replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-200 mt-4 mb-2">$1</h3>');
    result = result.replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-gray-100 mt-6 mb-3">$1</h2>');
    result = result.replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mt-6 mb-4">$1</h1>');

    // Bold
    result = result.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-100">$1</strong>');

    // Italic
    result = result.replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>');

    // Unordered lists
    result = result.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
    result = result.replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="my-2">$&</ul>');

    // Ordered lists
    result = result.replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>');

    // Horizontal rule
    result = result.replace(/^---$/gm, '<hr class="border-gray-700 my-4" />');

    // Paragraphs (lines not already converted to HTML elements)
    result = result.replace(/^(?!<[a-z]|$)(.+)$/gm, '<p class="my-2">$1</p>');

    // Clean up extra newlines
    result = result.replace(/\n+/g, '\n').replace(/\n/g, '');

    return result;
  };

  const sanitizedHtml = DOMPurify.sanitize(parseMarkdown(content));

  return (
    <div
      className="text-gray-300"
      dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
    />
  );
}

export default DocumentAccordion;
