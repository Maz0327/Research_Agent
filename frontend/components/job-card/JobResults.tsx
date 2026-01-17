/**
 * Job results display component for completed/failed/cancelled jobs.
 * Displays semantic pipeline outputs (Doc 0/1/2) for all job types.
 *
 * Document Outputs:
 * - Doc 0: Source Ledger (what was analyzed)
 * - Doc 1: Jump-Start Directions (where to go next)
 * - Doc 2: Semantic Brief (what sources reveal)
 */
import { useState } from 'react';
import { JobStatus } from './job-card-config';
import { ExportButton } from './ExportButton';
import { DocumentCard } from './DocumentCard';
import { DocumentViewerModal } from './DocumentViewerModal';

// Document output structure from backend
interface DocumentOutput {
  data: Record<string, unknown>;
  markdown?: string;
}

interface JobArtifacts {
  // Document outputs (Doc 0/1/2) - primary outputs
  source_ledger?: DocumentOutput;
  jump_start?: DocumentOutput;
  semantic_brief?: DocumentOutput;
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

export function JobResults({ jobId, status, driveFolderUrl, error, pipeline, artifacts }: JobResultsProps) {
  const [viewer, setViewer] = useState<ViewerState>({
    isOpen: false,
    docNumber: 0,
    title: '',
    data: {},
  });

  // Open document viewer
  const openDocument = (docNumber: 0 | 1 | 2, title: string, doc: DocumentOutput) => {
    setViewer({
      isOpen: true,
      docNumber,
      title,
      markdown: doc.markdown,
      data: doc.data,
    });
  };

  // Close document viewer
  const closeViewer = () => {
    setViewer(prev => ({ ...prev, isOpen: false }));
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
  const hasDocuments = artifacts?.source_ledger || artifacts?.jump_start || artifacts?.semantic_brief;

  if (isCompleted && hasDocuments) {
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

        {/* Document Cards - Doc 0/1/2 */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400">Research Documents</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {artifacts.source_ledger && (
              <DocumentCard
                docNumber={0}
                title="Source Ledger"
                subtitle="What was analyzed"
                stats={getDocStats(artifacts.source_ledger.data, 0)}
                data={artifacts.source_ledger.data}
                markdown={artifacts.source_ledger.markdown}
                onView={() => openDocument(0, 'Source Ledger', artifacts.source_ledger!)}
              />
            )}
            {artifacts.jump_start && (
              <DocumentCard
                docNumber={1}
                title="Jump-Start"
                subtitle="Where to go next"
                stats={getDocStats(artifacts.jump_start.data, 1)}
                data={artifacts.jump_start.data}
                markdown={artifacts.jump_start.markdown}
                onView={() => openDocument(1, 'Jump-Start Directions', artifacts.jump_start!)}
              />
            )}
            {artifacts.semantic_brief && (
              <DocumentCard
                docNumber={2}
                title="Semantic Brief"
                subtitle="What sources reveal"
                stats={getDocStats(artifacts.semantic_brief.data, 2)}
                data={artifacts.semantic_brief.data}
                markdown={artifacts.semantic_brief.markdown}
                onView={() => openDocument(2, 'Semantic Brief', artifacts.semantic_brief!)}
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
