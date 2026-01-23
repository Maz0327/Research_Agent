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
  /** Booster execution status */
  boosterStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Booster progress percentage (0-100) */
  boosterProgressPercent?: number;
  /** Whether actions can be triggered (job completed) */
  canTriggerActions?: boolean;
  /** Callback to trigger booster */
  onTriggerBooster?: () => void;
  /** Callback to trigger producer packet */
  onTriggerProducerPacket?: () => void;
  /** Whether booster is currently being triggered */
  isTriggeringBooster?: boolean;
  /** Whether producer packet is currently being triggered */
  isTriggeringProducer?: boolean;
  /** Iteration execution status */
  iterationStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Current iteration ID */
  iterationId?: string;
  /** Iteration progress percentage (0-100) */
  iterationProgressPercent?: number;
  /** Callback to trigger iteration */
  onTriggerIteration?: (mode: string, userPrompt: string, maxNewSources: number, angle?: string) => void;
  /** Whether iteration is currently being triggered */
  isTriggeringIteration?: boolean;
}

// Check if markdown is a placeholder stub
function isPlaceholderContent(content: string | null | undefined): boolean {
  if (!content) return true;
  return (
    content.includes('Document Available via Cloud Storage') ||
    content.includes('inline JSON omitted')
  );
}

export function DocumentCardGrid({
  jobId,
  jobTitle,
  artifacts,
  boosterMarkdown,
  boosterStatus,
  boosterProgressPercent,
  canTriggerActions = false,
  onTriggerBooster,
  onTriggerProducerPacket,
  isTriggeringBooster = false,
  isTriggeringProducer = false,
  iterationStatus,
  iterationId,
  iterationProgressPercent,
  onTriggerIteration,
  isTriggeringIteration = false,
}: DocumentCardGridProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [activeDoc, setActiveDoc] = useState<DocConfig | null>(null);
  const [loadingDoc, setLoadingDoc] = useState<string | null>(null);
  const [docContent, setDocContent] = useState<{ markdown: string; data: Record<string, unknown> } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Iteration modal state
  const [iterationModalOpen, setIterationModalOpen] = useState(false);
  const [iterationMode, setIterationMode] = useState<'more_sources' | 'deeper' | 'different_angle' | 'custom'>('more_sources');
  const [iterationPrompt, setIterationPrompt] = useState('');
  const [iterationMaxSources, setIterationMaxSources] = useState(4);
  const [iterationAngle, setIterationAngle] = useState('');

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

  // Booster state helpers
  const isBoosterRunning = boosterStatus === 'running' || boosterStatus === 'queued';
  const isBoosterCompleted = boosterStatus === 'completed';
  const isBoosterFailed = boosterStatus === 'failed';

  // Iteration state helpers
  const isIterationRunning = iterationStatus === 'running' || iterationStatus === 'queued';
  const isIterationCompleted = iterationStatus === 'completed';
  const isIterationFailed = iterationStatus === 'failed';

  // Handle iteration submission
  const handleIterationSubmit = useCallback(() => {
    if (!onTriggerIteration) return;
    onTriggerIteration(
      iterationMode,
      iterationPrompt,
      iterationMaxSources,
      iterationMode === 'different_angle' ? iterationAngle : undefined
    );
    setIterationModalOpen(false);
    // Reset form
    setIterationMode('more_sources');
    setIterationPrompt('');
    setIterationMaxSources(4);
    setIterationAngle('');
  }, [onTriggerIteration, iterationMode, iterationPrompt, iterationMaxSources, iterationAngle]);

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

  // Check if we should show action card for Doc 1 (Deep Research)
  const showDoc1ActionCard = !hasBooster && canTriggerActions && onTriggerBooster;

  // Check if we should show action card for Doc 3 (Producer Packet)
  const showDoc3ActionCard = !hasDoc3 && canTriggerActions && onTriggerProducerPacket;

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
            // Show Deep Research action button below Doc 1 card
            const showBoosterAction = config.docNumber === 1 && showDoc1ActionCard;

            return (
              <div key={config.key} className="flex flex-col gap-2">
                <motion.div
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

                {/* Deep Research action button - inside Doc 1 section */}
                {showBoosterAction && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onTriggerBooster?.(); }}
                    disabled={isTriggeringBooster || isBoosterRunning}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600/20 border border-indigo-600/30 px-3 py-2 text-xs font-medium text-indigo-400 transition hover:bg-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed min-h-[36px] touch-manipulation"
                  >
                    {(isTriggeringBooster || isBoosterRunning) ? (
                      <>
                        <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        {boosterStatus === 'running' ? `${boosterProgressPercent || 0}%` : 'Starting...'}
                      </>
                    ) : isBoosterFailed ? (
                      <>
                        <svg className="h-3.5 w-3.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="text-red-400">Retry Deep Research</span>
                      </>
                    ) : (
                      <>
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Expand with Deep Research
                      </>
                    )}
                  </button>
                )}
              </div>
            );
          })}

          {/* Producer Packet action card - placeholder when Doc 3 doesn't exist */}
          {showDoc3ActionCard && (
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={(e) => { e.stopPropagation(); onTriggerProducerPacket?.(); }}
              className={`
                relative rounded-xl border border-amber-800/50 border-dashed bg-amber-900/10 hover:bg-amber-900/20
                p-4 cursor-pointer transition-all duration-200
                flex flex-col min-h-[100px]
                ${isTriggeringProducer ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              {/* Loading overlay */}
              {isTriggeringProducer && (
                <div className="absolute inset-0 bg-gray-900/50 rounded-xl flex items-center justify-center z-10">
                  <svg className="h-6 w-6 animate-spin text-amber-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </div>
              )}

              {/* Header with badge */}
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-900/50 text-amber-400">
                  DOC 3
                </span>
                <span className="text-xs text-amber-500/70 bg-amber-900/30 px-2 py-0.5 rounded">
                  Generate
                </span>
              </div>

              {/* Title and subtitle */}
              <div className="flex items-center gap-2 mb-1">
                <span className="text-amber-400">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                </span>
                <h4 className="font-medium text-amber-300/80 text-sm">Producer Packet</h4>
              </div>
              <p className="text-xs text-gray-500">Creative layer output</p>

              {/* Action indicator */}
              <div className="mt-auto pt-3 flex items-center justify-end">
                <span className="text-xs text-amber-500 flex items-center gap-1">
                  {isTriggeringProducer ? 'Generating...' : 'Click to generate'}
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Iteration Loop Trigger */}
        {canTriggerActions && onTriggerIteration && (
          <div className="mt-4 pt-4 border-t border-gray-700/50">
            <button
              onClick={() => setIterationModalOpen(true)}
              disabled={isTriggeringIteration || isIterationRunning}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600/20 border border-emerald-600/30 px-4 py-3 text-sm font-medium text-emerald-400 transition hover:bg-emerald-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {(isTriggeringIteration || isIterationRunning) ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  {iterationStatus === 'running' ? `Iteration ${iterationId}: ${iterationProgressPercent || 0}%` : 'Starting iteration...'}
                </>
              ) : isIterationFailed ? (
                <>
                  <svg className="h-4 w-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-red-400">Retry Iteration</span>
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Run Another Pass (Iteration)
                </>
              )}
            </button>
            {isIterationCompleted && (
              <p className="text-xs text-emerald-400/70 text-center mt-2">
                ✓ Iteration completed — results appended to artifacts
              </p>
            )}
          </div>
        )}
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

      {/* Iteration Configuration Modal */}
      {iterationModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md mx-4 shadow-2xl"
          >
            <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
              <svg className="h-5 w-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Run Iteration
            </h3>

            {/* Mode Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">Mode</label>
              <select
                value={iterationMode}
                onChange={(e) => setIterationMode(e.target.value as typeof iterationMode)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              >
                <option value="more_sources">Find More Sources</option>
                <option value="deeper">Deeper Analysis</option>
                <option value="different_angle">Different Angle</option>
                <option value="custom">Custom (User Prompt)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {iterationMode === 'more_sources' && 'Search for additional sources to expand coverage'}
                {iterationMode === 'deeper' && 'Perform deeper analysis on existing sources'}
                {iterationMode === 'different_angle' && 'Explore a different perspective or angle'}
                {iterationMode === 'custom' && 'Define a custom iteration via prompt'}
              </p>
            </div>

            {/* Angle input (for different_angle mode) */}
            {iterationMode === 'different_angle' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">Angle to Explore</label>
                <input
                  type="text"
                  value={iterationAngle}
                  onChange={(e) => setIterationAngle(e.target.value)}
                  placeholder="e.g., economic impact, environmental concerns"
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm placeholder-gray-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                />
              </div>
            )}

            {/* Max new sources (for more_sources mode) */}
            {iterationMode === 'more_sources' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Max New Sources: {iterationMaxSources}
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={iterationMaxSources}
                  onChange={(e) => setIterationMaxSources(Number(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1</span>
                  <span>10</span>
                </div>
              </div>
            )}

            {/* User prompt */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {iterationMode === 'custom' ? 'Custom Prompt' : 'Guidance (optional)'}
              </label>
              <textarea
                value={iterationPrompt}
                onChange={(e) => setIterationPrompt(e.target.value)}
                rows={3}
                placeholder={iterationMode === 'custom'
                  ? 'Describe what you want the iteration to do...'
                  : 'Any specific guidance for this iteration...'}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm placeholder-gray-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
              />
            </div>

            {/* Note about append-only */}
            <div className="mb-6 p-3 bg-gray-700/50 rounded-lg border border-gray-600/50">
              <p className="text-xs text-gray-400">
                <span className="text-emerald-400 font-medium">Append-only:</span> Iterations create new document bundles without modifying your original research.
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => setIterationModalOpen(false)}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={handleIterationSubmit}
                disabled={iterationMode === 'custom' && !iterationPrompt.trim()}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-not-allowed rounded-lg transition"
              >
                Start Iteration
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </>
  );
}

export default DocumentCardGrid;
