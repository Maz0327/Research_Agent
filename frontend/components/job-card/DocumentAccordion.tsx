/**
 * DocumentAccordion - Collapsible document section with lazy loading.
 * Replaces DocumentCard grid with expandable accordion UI.
 *
 * Uses presentation layer formatting to display user-friendly labels
 * (e.g., "Source 1" instead of "SRC_1") without modifying stored JSON.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { authFetch, parseJsonResponse } from '@/lib/api-client';
import { getAccessToken } from '@/lib/supabase';
import { exportToPdf } from '@/lib/pdf-export';
import { transformMarkdownForDisplay } from '@/lib/document-formatters';
import { MarkdownRenderer } from '@/components/common/MarkdownRenderer';
import { Spinner } from '@/components/ui/Spinner';

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
    headerBg: 'bg-card/50 hover:bg-card/70',
    headerBorder: 'border-border',
    badge: 'bg-muted text-muted-foreground',
    chevron: 'text-muted-foreground',
    contentBg: 'bg-background/50',
    button: 'bg-muted hover:bg-secondary text-muted-foreground',
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
            <h4 className="font-medium text-foreground text-sm sm:text-base truncate">{title}</h4>
            <p className="text-xs text-muted-foreground/70 mt-0.5 truncate">{subtitle}</p>
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
                  <Spinner size="lg" />
                  <span className="ml-3 text-muted-foreground text-sm sm:text-base">Loading document...</span>
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
                <div className="max-w-none max-h-[40rem] sm:max-h-[60rem] overflow-y-auto leading-relaxed overscroll-contain">
                  <MarkdownRenderer content={transformMarkdownForDisplay(markdown)} compact />
                </div>
              )}

              {/* No content */}
              {!markdown && !isLoading && !error && (
                <p className="text-sm text-muted-foreground/70 italic py-4">No content available</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default DocumentAccordion;
