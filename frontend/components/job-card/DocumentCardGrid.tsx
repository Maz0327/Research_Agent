/**
 * DocumentCardGrid - Clean grid of document cards that open directly to fullscreen modal.
 * Replaces cramped inline accordion approach with cards → modal flow.
 */
import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { authFetch, parseJsonResponse } from '@/lib/api-client';
import { getAccessToken } from '@/lib/supabase';
import { exportToPdf } from '@/lib/pdf-export';
import { DocumentViewerModal } from './DocumentViewerModal';

// Document configuration
interface DocConfig {
  key: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3' | 'booster';
  docNumber: 0 | 1 | 2 | 3 | 'B';
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  color: {
    bg: string;
    border: string;
    text: string;
    badge: string;
  };
}

// Core documents (always shown if available)
const coreDocConfigs: DocConfig[] = [
  {
    key: 'doc_0',
    docNumber: 0,
    title: 'Source Ledger',
    subtitle: 'What was analyzed',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    color: {
      bg: 'bg-gray-800/50 hover:bg-gray-800/70',
      border: 'border-gray-700 hover:border-gray-600',
      text: 'text-gray-300',
      badge: 'bg-gray-700 text-gray-300',
    },
  },
  {
    key: 'doc_1',
    docNumber: 1,
    title: 'Jump-Start',
    subtitle: 'Where to go next',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
      </svg>
    ),
    color: {
      bg: 'bg-blue-900/20 hover:bg-blue-900/30',
      border: 'border-blue-800/50 hover:border-blue-700/50',
      text: 'text-blue-300',
      badge: 'bg-blue-900/50 text-blue-300',
    },
  },
  {
    key: 'doc_2',
    docNumber: 2,
    title: 'Semantic Brief',
    subtitle: 'What sources reveal',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    color: {
      bg: 'bg-purple-900/20 hover:bg-purple-900/30',
      border: 'border-purple-800/50 hover:border-purple-700/50',
      text: 'text-purple-300',
      badge: 'bg-purple-900/50 text-purple-300',
    },
  },
];

// Optional documents (booster and producer packet)
const boosterConfig: DocConfig = {
  key: 'booster',
  docNumber: 'B',
  title: 'Deep Research',
  subtitle: 'Expanded directions',
  icon: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  color: {
    bg: 'bg-indigo-900/20 hover:bg-indigo-900/30',
    border: 'border-indigo-800/50 hover:border-indigo-700/50',
    text: 'text-indigo-300',
    badge: 'bg-indigo-900/50 text-indigo-300',
  },
};

const doc3Config: DocConfig = {
  key: 'doc_3',
  docNumber: 3,
  title: 'Producer Packet',
  subtitle: 'Creative layer output',
  icon: (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  ),
  color: {
    bg: 'bg-amber-900/20 hover:bg-amber-900/30',
    border: 'border-amber-800/50 hover:border-amber-700/50',
    text: 'text-amber-300',
    badge: 'bg-amber-900/50 text-amber-300',
  },
};

// API response for lazy loading
interface DocumentApiResponse {
  url?: string;
  data?: Record<string, unknown>;
  markdown?: string;
}

interface DocumentCardGridProps {
  jobId: string;
  jobTitle?: string;
  artifacts?: {
    source_ledger?: { data: Record<string, unknown>; markdown?: string };
    jump_start?: { data: Record<string, unknown>; markdown?: string };
    semantic_brief?: { data: Record<string, unknown>; markdown?: string };
    doc_0_path?: string;
    doc_1_path?: string;
    doc_2_path?: string;
    doc_3_path?: string;
    booster_expansion_md?: string;
    producer_packet?: Record<string, unknown>;
  };
  /** Booster markdown content (when booster is completed) */
  boosterMarkdown?: string;
}

// Check if markdown is a placeholder stub
function isPlaceholderContent(content: string | null | undefined): boolean {
  if (!content) return true;
  return (
    content.includes('Document Available via Cloud Storage') ||
    content.includes('inline JSON omitted')
  );
}

export function DocumentCardGrid({ jobId, jobTitle, artifacts, boosterMarkdown }: DocumentCardGridProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeDoc, setActiveDoc] = useState<DocConfig | null>(null);
  const [loadingDoc, setLoadingDoc] = useState<string | null>(null);
  const [docContent, setDocContent] = useState<{ markdown: string; data: Record<string, unknown> } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check document availability for core docs (0, 1, 2)
  const hasCoreDoc = (docNum: 0 | 1 | 2): boolean => {
    const inlineMap: Record<number, unknown> = {
      0: artifacts?.source_ledger,
      1: artifacts?.jump_start,
      2: artifacts?.semantic_brief,
    };
    const pathMap: Record<number, string | undefined> = {
      0: artifacts?.doc_0_path,
      1: artifacts?.doc_1_path,
      2: artifacts?.doc_2_path,
    };
    return !!(inlineMap[docNum] || pathMap[docNum]);
  };

  // Check if doc 3 exists
  const hasDoc3 = !!(artifacts?.doc_3_path || artifacts?.producer_packet);

  // Check if booster exists
  const hasBooster = !!(boosterMarkdown || artifacts?.booster_expansion_md);

  // Get inline markdown if available
  const getInlineMarkdown = useCallback((docNum: 0 | 1 | 2): string | undefined => {
    const inlineMap: Record<number, { markdown?: string } | undefined> = {
      0: artifacts?.source_ledger,
      1: artifacts?.jump_start,
      2: artifacts?.semantic_brief,
    };
    return inlineMap[docNum]?.markdown;
  }, [artifacts?.source_ledger, artifacts?.jump_start, artifacts?.semantic_brief]);

  // Check if needs storage fetch
  const needsStorageFetch = useCallback((docNum: 0 | 1 | 2): boolean => {
    const pathMap: Record<number, string | undefined> = {
      0: artifacts?.doc_0_path,
      1: artifacts?.doc_1_path,
      2: artifacts?.doc_2_path,
    };
    const inlineMarkdown = getInlineMarkdown(docNum);
    return !!pathMap[docNum] || isPlaceholderContent(inlineMarkdown);
  }, [artifacts?.doc_0_path, artifacts?.doc_1_path, artifacts?.doc_2_path, getInlineMarkdown]);

  // Fetch document content
  const fetchDocument = useCallback(async (docKey: string): Promise<string | null> => {
    const token = await getAccessToken();
    const response = await authFetch(`/jobs/${jobId}/documents/${docKey}`, token);
    const result = await parseJsonResponse<DocumentApiResponse>(response);

    if (result.url) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);
      try {
        const contentResponse = await fetch(result.url, { signal: controller.signal });
        clearTimeout(timeoutId);
        if (!contentResponse.ok) {
          throw new Error(`Failed to fetch document: ${contentResponse.status}`);
        }
        const content = await contentResponse.json();
        return content.markdown || null;
      } catch (err) {
        clearTimeout(timeoutId);
        if (err instanceof Error && err.name === 'AbortError') {
          throw new Error('Document fetch timed out');
        }
        throw err;
      }
    }

    return result.markdown || null;
  }, [jobId]);

  // Handle card click - open modal
  const handleCardClick = useCallback(async (config: DocConfig) => {
    setActiveDoc(config);
    setError(null);

    // Handle booster (always inline)
    if (config.key === 'booster') {
      const content = boosterMarkdown || artifacts?.booster_expansion_md;
      if (content) {
        setDocContent({ markdown: content, data: {} });
        setModalOpen(true);
      } else {
        setError('No booster content available');
      }
      return;
    }

    // Handle doc_3 (storage path)
    if (config.key === 'doc_3') {
      setLoadingDoc(config.key);
      try {
        const markdown = await fetchDocument('doc_3');
        if (markdown) {
          setDocContent({ markdown, data: {} });
          setModalOpen(true);
        } else {
          setError('No content available');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load document');
      } finally {
        setLoadingDoc(null);
      }
      return;
    }

    // Handle core docs (0, 1, 2)
    const docNum = config.docNumber as 0 | 1 | 2;
    const inlineMarkdown = getInlineMarkdown(docNum);
    const needsFetch = needsStorageFetch(docNum);

    if (!needsFetch && inlineMarkdown && !isPlaceholderContent(inlineMarkdown)) {
      // Use inline content directly
      setDocContent({ markdown: inlineMarkdown, data: {} });
      setModalOpen(true);
      return;
    }

    // Fetch from storage
    setLoadingDoc(config.key);
    try {
      const markdown = await fetchDocument(config.key);
      if (markdown) {
        setDocContent({ markdown, data: {} });
        setModalOpen(true);
      } else {
        setError('No content available');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoadingDoc(null);
    }
  }, [fetchDocument, artifacts, boosterMarkdown, getInlineMarkdown, needsStorageFetch]);

  // Handle PDF download
  const handleDownloadPdf = useCallback(async (e: React.MouseEvent, config: DocConfig) => {
    e.stopPropagation();
    setLoadingDoc(config.key);
    setError(null);

    try {
      let markdown: string | null = null;

      // Handle booster (always inline)
      if (config.key === 'booster') {
        markdown = boosterMarkdown || artifacts?.booster_expansion_md || null;
      }
      // Handle doc_3 (storage path)
      else if (config.key === 'doc_3') {
        markdown = await fetchDocument('doc_3');
      }
      // Handle core docs (0, 1, 2)
      else {
        const docNum = config.docNumber as 0 | 1 | 2;
        const inlineMarkdown = getInlineMarkdown(docNum);
        const needsFetch = needsStorageFetch(docNum);

        if (!needsFetch && inlineMarkdown && !isPlaceholderContent(inlineMarkdown)) {
          markdown = inlineMarkdown;
        } else {
          markdown = await fetchDocument(config.key);
        }
      }

      if (!markdown) {
        throw new Error('No content available');
      }

      const filename = `doc-${config.docNumber}-${config.title.toLowerCase().replace(/\s+/g, '-')}`;
      await exportToPdf(markdown, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download PDF');
    } finally {
      setLoadingDoc(null);
    }
  }, [fetchDocument, artifacts, boosterMarkdown, getInlineMarkdown, needsStorageFetch]);

  // Close modal
  const handleCloseModal = () => {
    setModalOpen(false);
    setActiveDoc(null);
    setDocContent(null);
  };

  // Build list of available documents
  const availableDocs: DocConfig[] = [
    // Core docs (0, 1, 2)
    ...coreDocConfigs.filter((config) => hasCoreDoc(config.docNumber as 0 | 1 | 2)),
    // Booster (if available)
    ...(hasBooster ? [boosterConfig] : []),
    // Doc 3 (if available)
    ...(hasDoc3 ? [doc3Config] : []),
  ];

  if (availableDocs.length === 0) {
    return null;
  }

  return (
    <>
      {/* Document Cards Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Research Documents
        </h3>

        {/* Error message */}
        {error && (
          <div className="rounded-lg bg-red-900/20 border border-red-800/50 p-3 text-sm text-red-300">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-2 text-red-400 hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Cards grid - responsive: 1 col mobile, 3 col desktop */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {availableDocs.map((config) => {
            const isLoading = loadingDoc === config.key;

            return (
              <motion.div
                key={config.key}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`
                  relative rounded-xl border ${config.color.border} ${config.color.bg}
                  p-4 cursor-pointer transition-all duration-200
                  flex flex-col min-h-[100px]
                `}
                onClick={() => !isLoading && handleCardClick(config)}
              >
                {/* Loading overlay */}
                {isLoading && (
                  <div className="absolute inset-0 bg-gray-900/50 rounded-xl flex items-center justify-center z-10">
                    <svg className="h-6 w-6 animate-spin text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                )}

                {/* Header with badge and download */}
                <div className="flex items-center justify-between mb-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${config.color.badge}`}>
                    DOC {config.docNumber}
                  </span>
                  <button
                    onClick={(e) => handleDownloadPdf(e, config)}
                    className="p-1.5 rounded-lg hover:bg-gray-700/50 text-gray-400 hover:text-gray-300 transition"
                    title="Download PDF"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                  </button>
                </div>

                {/* Title and subtitle */}
                <div className="flex items-center gap-2 mb-1">
                  <span className={config.color.text}>{config.icon}</span>
                  <h4 className="font-medium text-gray-100 text-sm">{config.title}</h4>
                </div>
                <p className="text-xs text-gray-500">{config.subtitle}</p>

                {/* Open indicator */}
                <div className="mt-auto pt-3 flex items-center justify-end">
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    Click to open
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Fullscreen Document Modal */}
      {activeDoc && docContent && (
        <DocumentViewerModal
          isOpen={modalOpen}
          onClose={handleCloseModal}
          docNumber={activeDoc.docNumber}
          title={activeDoc.title}
          markdown={docContent.markdown}
          data={docContent.data}
          jobTitle={jobTitle}
        />
      )}
    </>
  );
}

export default DocumentCardGrid;
