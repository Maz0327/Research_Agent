/**
 * DocumentAccordion - Collapsible document section with lazy loading.
 * Replaces DocumentCard grid with expandable accordion UI.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import DOMPurify from 'dompurify';
import { authFetch, parseJsonResponse } from '@/lib/api-client';
import { getAccessToken } from '@/lib/supabase';
import { exportToPdf } from '@/lib/pdf-export';

export type DocKey = 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3';
export type ColorScheme = 'gray' | 'blue' | 'purple' | 'amber';

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
};

// Doc number mapping
const docNumbers: Record<DocKey, number> = {
  doc_0: 0,
  doc_1: 1,
  doc_2: 2,
  doc_3: 3,
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
    const filename = `doc-${docNum}-${title.toLowerCase().replace(/\s+/g, '-')}`;
    try {
      await exportToPdf(markdown!, filename);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate PDF');
    }
  };

  return (
    <div className={`rounded-lg border ${config.headerBorder} overflow-hidden`}>
      {/* Header - Always visible */}
      <button
        onClick={handleToggle}
        className={`w-full flex items-center justify-between px-4 py-3 ${config.headerBg} transition-colors`}
      >
        <div className="flex items-center gap-3">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.badge}`}>
            DOC {docNum}
          </span>
          <div className="text-left">
            <h4 className="font-medium text-gray-100">{title}</h4>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* PDF Download - only when real content loaded (not placeholder) */}
          {hasExportableContent && (
            <button
              onClick={handleDownloadPdf}
              className={`p-1.5 rounded ${config.button} transition-colors`}
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
            <div className={`px-4 py-4 ${config.contentBg} border-t ${config.headerBorder}`}>
              {/* Loading state */}
              {isLoading && (
                <div className="flex items-center justify-center py-8">
                  <svg className="h-6 w-6 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <span className="ml-2 text-gray-400">Loading document...</span>
                </div>
              )}

              {/* Error state */}
              {error && !isLoading && (
                <div className="rounded-lg border border-red-800 bg-red-900/30 p-3">
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}

              {/* Content */}
              {markdown && !isLoading && (
                <div className="prose prose-invert prose-sm max-w-none max-h-96 overflow-y-auto">
                  <MarkdownRenderer content={markdown} />
                </div>
              )}

              {/* No content */}
              {!markdown && !isLoading && !error && (
                <p className="text-sm text-gray-500 italic">No content available</p>
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
    return text
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-800 rounded p-3 my-2 overflow-x-auto"><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code class="bg-gray-800 px-1 rounded text-blue-300">$1</code>')
      .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-200 mt-4 mb-2">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-gray-100 mt-6 mb-3">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mt-6 mb-4">$1</h1>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-100">$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>')
      .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
      .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="my-2">$&</ul>')
      .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')
      .replace(/^---$/gm, '<hr class="border-gray-700 my-4" />')
      .replace(/^(?!<[hl]|<ul|<li|<pre|<hr)(.+)$/gm, '<p class="my-2">$1</p>')
      .replace(/\n/g, '');
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
