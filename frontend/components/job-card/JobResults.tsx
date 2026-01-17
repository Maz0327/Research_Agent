/**
 * Job results display component for completed/failed/cancelled jobs.
 * Displays semantic pipeline outputs (Doc 0/1/2) for all job types.
 *
 * Document Outputs:
 * - Doc 0: Source Ledger (what was analyzed)
 * - Doc 1: Jump-Start Directions (where to go next)
 * - Doc 2: Semantic Brief (what sources reveal)
 *
 * Supports both inline data (legacy) and storage paths (new jobs with lazy loading).
 */
import { useState, useCallback, useEffect } from 'react';
import { JobStatus } from './job-card-config';
import { ExportButton } from './ExportButton';
import { DocumentCard } from './DocumentCard';
import { DocumentViewerModal } from './DocumentViewerModal';
import { authFetch, parseJsonResponse } from '@/lib/api-client';
import { getAccessToken } from '@/lib/supabase';

// Document output structure from backend
interface DocumentOutput {
  data: Record<string, unknown>;
  markdown?: string;
}

interface JobArtifacts {
  // Document outputs (Doc 0/1/2) - inline data (legacy jobs)
  source_ledger?: DocumentOutput;
  jump_start?: DocumentOutput;
  semantic_brief?: DocumentOutput;

  // Storage paths (new jobs with lazy loading)
  doc_0_path?: string;
  doc_1_path?: string;
  doc_2_path?: string;
  doc_3_path?: string;

  // Quality gate (from semantic pipeline)
  quality_gate_passed?: boolean;
  producer_packet?: {
    title?: string;
    quality_gate?: {
      passes: boolean;
      failures: string[];
      clip_count: number;
      quote_count: number;
      verified_claim_count: number;
    };
    extraction_cost?: number;
  };
}

interface JobResultsProps {
  jobId: string;
  status: JobStatus;
  driveFolderUrl?: string;
  error?: string;
  pipeline?: string;
  artifacts?: JobArtifacts;
}

/**
 * Extract stats from document data for display on DocumentCard.
 */
function getDocStats(data: Record<string, unknown>, docNumber: 0 | 1 | 2): { label: string; value: number | string }[] {
  const stats: { label: string; value: number | string }[] = [];

  if (docNumber === 0) {
    // Source Ledger stats
    const sources = Array.isArray(data.sources) ? data.sources.length : 0;
    const rawDuration = data.total_duration ?? data.totalDuration;
    const duration = typeof rawDuration === 'number' ? `${Math.round(rawDuration / 60)}m` : '-';
    stats.push({ label: 'Sources', value: sources });
    stats.push({ label: 'Duration', value: duration });
  } else if (docNumber === 1) {
    // Jump-Start stats
    const directions = Array.isArray(data.directions) ? data.directions.length : 0;
    const queriesData = data.search_queries ?? data.searchQueries;
    const queries = Array.isArray(queriesData) ? queriesData.length : 0;
    stats.push({ label: 'Directions', value: directions });
    stats.push({ label: 'Queries', value: queries });
  } else if (docNumber === 2) {
    // Semantic Brief stats
    const keyPointsData = data.key_points ?? data.keyPoints;
    const keyPoints = Array.isArray(keyPointsData) ? keyPointsData.length : 0;
    const themes = Array.isArray(data.themes) ? data.themes.length : 0;
    const claims = Array.isArray(data.claims) ? data.claims.length : 0;
    stats.push({ label: 'Key Points', value: keyPoints });
    stats.push({ label: 'Themes', value: themes });
    if (claims > 0) stats.push({ label: 'Claims', value: claims });
  }

  return stats;
}

// Document viewer state
interface ViewerState {
  isOpen: boolean;
  docNumber: 0 | 1 | 2;
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
}

// API response for lazy loading
interface DocumentApiResponse {
  url?: string;
  expires_in?: number;
  data?: Record<string, unknown>;
  markdown?: string;
}

export function JobResults({ jobId, status, driveFolderUrl, error, pipeline, artifacts }: JobResultsProps) {
  const [viewer, setViewer] = useState<ViewerState>({
    isOpen: false,
    docNumber: 0,
    title: '',
    data: {},
  });

  // Cache for lazy-loaded documents
  const [loadedDocs, setLoadedDocs] = useState<Record<string, DocumentOutput>>({});
  const [loadingDoc, setLoadingDoc] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Check if job uses storage (new jobs) vs inline data (legacy)
  const usesStorage = !!(artifacts?.doc_0_path || artifacts?.doc_1_path || artifacts?.doc_2_path);

  // Fetch document from API (for storage-based jobs)
  const fetchDocument = useCallback(async (docType: string): Promise<DocumentOutput | null> => {
    try {
      const token = await getAccessToken();
      const response = await authFetch(`/jobs/${jobId}/documents/${docType}`, token);
      const result = await parseJsonResponse<DocumentApiResponse>(response);

      // If we got a signed URL, fetch the actual content
      if (result.url) {
        const contentResponse = await fetch(result.url);
        if (!contentResponse.ok) {
          throw new Error(`Failed to fetch document from storage: ${contentResponse.status}`);
        }
        const content = await contentResponse.json();
        return {
          data: content.data || content,
          markdown: content.markdown,
        };
      }

      // Direct inline data response (fallback)
      if (result.data) {
        return {
          data: result.data,
          markdown: result.markdown,
        };
      }

      return null;
    } catch (err) {
      console.error(`Failed to fetch ${docType}:`, err);
      throw err;
    }
  }, [jobId]);

  // Open document viewer - lazy loads if needed
  const openDocument = useCallback(async (
    docNumber: 0 | 1 | 2,
    title: string,
    inlineDoc?: DocumentOutput
  ) => {
    const docType = `doc_${docNumber}`;

    // If inline data provided (legacy), use it directly
    if (inlineDoc) {
      setViewer({
        isOpen: true,
        docNumber,
        title,
        markdown: inlineDoc.markdown,
        data: inlineDoc.data,
      });
      return;
    }

    // Check cache first
    const cached = loadedDocs[docType];
    if (cached) {
      setViewer({
        isOpen: true,
        docNumber,
        title,
        markdown: cached.markdown,
        data: cached.data,
      });
      return;
    }

    // Lazy load from API
    setLoadingDoc(docType);
    setLoadError(null);

    try {
      const doc = await fetchDocument(docType);
      if (doc) {
        // Cache the loaded document
        setLoadedDocs(prev => ({ ...prev, [docType]: doc }));
        setViewer({
          isOpen: true,
          docNumber,
          title,
          markdown: doc.markdown,
          data: doc.data,
        });
      } else {
        setLoadError(`Document ${docType} not found`);
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoadingDoc(null);
    }
  }, [fetchDocument, loadedDocs]);

  // Close document viewer
  const closeViewer = () => {
    setViewer(prev => ({ ...prev, isOpen: false }));
    setLoadError(null);
  };

  // Error state
  if (status === 'failed' && error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-900/30 p-4">
        <h4 className="text-sm font-medium text-red-400 mb-1">Error</h4>
        <p className="text-sm text-red-300 break-words" style={{ overflowWrap: 'anywhere' }}>{error}</p>
      </div>
    );
  }

  // Cancelled state
  if (status === 'cancelled') {
    return (
      <div className="rounded-lg border border-orange-800 bg-orange-900/30 p-4">
        <p className="text-sm text-orange-300">
          This job was cancelled. Any partial results may have been saved.
        </p>
      </div>
    );
  }

  // Completed job with semantic pipeline artifacts (Doc 0/1/2)
  const isCompleted = ['completed', 'completed_with_warnings', 'failed_insufficient'].includes(status);
  const hasInlineDocuments = artifacts?.source_ledger || artifacts?.jump_start || artifacts?.semantic_brief;
  const hasStorageDocuments = artifacts?.doc_0_path || artifacts?.doc_1_path || artifacts?.doc_2_path;
  const hasDocuments = hasInlineDocuments || hasStorageDocuments;

  if (isCompleted && hasDocuments) {
    // Helper to get document data - from cache, inline, or placeholder
    const getDocData = (docNumber: 0 | 1 | 2) => {
      const docType = `doc_${docNumber}`;
      const cached = loadedDocs[docType];
      if (cached) return cached;

      // Inline data mapping
      const inlineMap: Record<number, DocumentOutput | undefined> = {
        0: artifacts?.source_ledger,
        1: artifacts?.jump_start,
        2: artifacts?.semantic_brief,
      };
      return inlineMap[docNumber];
    };

    // Check if document is available (inline or cached)
    const hasDoc = (docNumber: 0 | 1 | 2) => {
      const inlineMap: Record<number, boolean> = {
        0: !!(artifacts?.source_ledger || artifacts?.doc_0_path),
        1: !!(artifacts?.jump_start || artifacts?.doc_1_path),
        2: !!(artifacts?.semantic_brief || artifacts?.doc_2_path),
      };
      return inlineMap[docNumber];
    };

    // Get inline document if available
    const getInlineDoc = (docNumber: 0 | 1 | 2): DocumentOutput | undefined => {
      const inlineMap: Record<number, DocumentOutput | undefined> = {
        0: artifacts?.source_ledger,
        1: artifacts?.jump_start,
        2: artifacts?.semantic_brief,
      };
      return inlineMap[docNumber];
    };

    return (
      <div className="space-y-4">
        {/* Completion Status */}
        <div className="rounded-lg border border-green-800 bg-green-900/30 p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-800/50">
                <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-green-300">Research Complete</p>
                <p className="text-sm text-green-400/70">
                  Semantic analysis finished
                </p>
              </div>
            </div>
            <ExportButton jobId={jobId} />
          </div>
        </div>

        {/* Loading Error */}
        {loadError && (
          <div className="rounded-lg border border-red-800 bg-red-900/30 p-3">
            <p className="text-sm text-red-300">{loadError}</p>
          </div>
        )}

        {/* Document Cards - Doc 0/1/2 */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400">Research Documents</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {hasDoc(0) && (
              <DocumentCard
                docNumber={0}
                title="Source Ledger"
                subtitle="What was analyzed"
                stats={getDocData(0) ? getDocStats(getDocData(0)!.data, 0) : []}
                data={getDocData(0)?.data || {}}
                markdown={getDocData(0)?.markdown}
                onView={() => openDocument(0, 'Source Ledger', getInlineDoc(0))}
                isLoading={loadingDoc === 'doc_0'}
                usesLazyLoading={!getInlineDoc(0) && !!artifacts?.doc_0_path}
              />
            )}
            {hasDoc(1) && (
              <DocumentCard
                docNumber={1}
                title="Jump-Start"
                subtitle="Where to go next"
                stats={getDocData(1) ? getDocStats(getDocData(1)!.data, 1) : []}
                data={getDocData(1)?.data || {}}
                markdown={getDocData(1)?.markdown}
                onView={() => openDocument(1, 'Jump-Start Directions', getInlineDoc(1))}
                isLoading={loadingDoc === 'doc_1'}
                usesLazyLoading={!getInlineDoc(1) && !!artifacts?.doc_1_path}
              />
            )}
            {hasDoc(2) && (
              <DocumentCard
                docNumber={2}
                title="Semantic Brief"
                subtitle="What sources reveal"
                stats={getDocData(2) ? getDocStats(getDocData(2)!.data, 2) : []}
                data={getDocData(2)?.data || {}}
                markdown={getDocData(2)?.markdown}
                onView={() => openDocument(2, 'Semantic Brief', getInlineDoc(2))}
                isLoading={loadingDoc === 'doc_2'}
                usesLazyLoading={!getInlineDoc(2) && !!artifacts?.doc_2_path}
              />
            )}
          </div>
        </div>

        {/* Document Viewer Modal */}
        <DocumentViewerModal
          isOpen={viewer.isOpen}
          onClose={closeViewer}
          docNumber={viewer.docNumber}
          title={viewer.title}
          markdown={viewer.markdown}
          data={viewer.data}
        />
      </div>
    );
  }

  // Legacy: Topic Research results (Drive folder) - fallback for old jobs
  const isTopicCompleted = ['completed', 'completed_with_warnings'].includes(status);
  if (isTopicCompleted && driveFolderUrl) {
    return (
      <div className="rounded-lg border border-green-800 bg-green-900/30 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-800/50 rounded-lg">
              <svg className="h-6 w-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <div>
              <p className="font-medium text-green-300">Research Complete</p>
              <p className="text-sm text-green-400/70">Your documents are ready</p>
            </div>
          </div>
          <a
            href={driveFolderUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-500"
            onClick={(e) => e.stopPropagation()}
          >
            Open in Drive
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
      </div>
    );
  }

  return null;
}

export default JobResults;
