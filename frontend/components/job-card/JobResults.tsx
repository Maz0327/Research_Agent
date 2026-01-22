/**
 * Job results display component for completed/failed/cancelled jobs.
 * Displays semantic pipeline outputs (Doc 0/1/2/3) as collapsible accordions.
 *
 * Document Outputs:
 * - Doc 0: Source Ledger (what was analyzed)
 * - Doc 1: Jump-Start Directions (where to go next)
 * - Doc 2: Semantic Brief (what sources reveal)
 * - Doc 3: Producer Packet (optional, creative layer)
 *
 * Supports both inline data (legacy) and storage paths (new jobs with lazy loading).
 */
import { useState, useCallback } from 'react';
import { JobStatus } from './job-card-config';
import { ExportButton } from './ExportButton';
import { DocumentAccordion } from './DocumentAccordion';
import { useJobsStore } from '../../store/jobs';

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

  // Booster output (Deep Research expansion)
  booster_output?: Record<string, unknown>;
  booster_expansion_md?: string;

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
  onRefresh?: () => void;
  /** Booster execution status (separate from main job status) */
  boosterStatus?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Booster error message if failed */
  boosterError?: string;
  /** Booster progress percentage (0-100) */
  boosterProgressPercent?: number;
}

export function JobResults({
  jobId,
  status,
  driveFolderUrl,
  error,
  pipeline,
  artifacts,
  onRefresh,
  boosterStatus,
  boosterError,
  boosterProgressPercent,
}: JobResultsProps) {
  const [isTriggeringBooster, setIsTriggeringBooster] = useState(false);
  const [isTriggeringProducer, setIsTriggeringProducer] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const triggerBooster = useJobsStore((state) => state.triggerBooster);
  const triggerProducerPacket = useJobsStore((state) => state.triggerProducerPacket);

  // Booster state helpers
  const isBoosterRunning = boosterStatus === 'running' || boosterStatus === 'queued';
  const isBoosterCompleted = boosterStatus === 'completed';
  const isBoosterFailed = boosterStatus === 'failed';

  // Handle Booster trigger
  const handleBooster = useCallback(async () => {
    if (isTriggeringBooster) return;
    setIsTriggeringBooster(true);
    setActionError(null);
    try {
      await triggerBooster(jobId);
      onRefresh?.();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to trigger deep research');
    } finally {
      setIsTriggeringBooster(false);
    }
  }, [jobId, isTriggeringBooster, triggerBooster, onRefresh]);

  // Handle Producer Packet trigger
  const handleProducerPacket = useCallback(async () => {
    if (isTriggeringProducer) return;
    setIsTriggeringProducer(true);
    setActionError(null);
    try {
      await triggerProducerPacket(jobId);
      onRefresh?.();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to generate producer packet');
    } finally {
      setIsTriggeringProducer(false);
    }
  }, [jobId, isTriggeringProducer, triggerProducerPacket, onRefresh]);

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

  // Check if Doc 3 exists
  const hasDoc3 = !!(artifacts?.doc_3_path || artifacts?.producer_packet);

  // Check if actions can be triggered (only when job is fully completed)
  const canTriggerActions = status === 'completed' || status === 'completed_with_warnings';

  if (isCompleted && hasDocuments) {
    // Get inline markdown if available (legacy jobs)
    const getInlineMarkdown = (docNum: 0 | 1 | 2): string | undefined => {
      const inlineMap: Record<number, DocumentOutput | undefined> = {
        0: artifacts?.source_ledger,
        1: artifacts?.jump_start,
        2: artifacts?.semantic_brief,
      };
      return inlineMap[docNum]?.markdown;
    };

    // Check if document is available (inline or storage path)
    const hasDoc = (docNum: 0 | 1 | 2 | 3): boolean => {
      const availabilityMap: Record<number, boolean> = {
        0: !!(artifacts?.source_ledger || artifacts?.doc_0_path),
        1: !!(artifacts?.jump_start || artifacts?.doc_1_path),
        2: !!(artifacts?.semantic_brief || artifacts?.doc_2_path),
        3: hasDoc3,
      };
      return availabilityMap[docNum];
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

        {/* Document Accordions */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-400">Research Documents</h3>

          {/* Doc 0 - Source Ledger */}
          {hasDoc(0) && (
            <DocumentAccordion
              jobId={jobId}
              docKey="doc_0"
              title="Source Ledger"
              subtitle="What was analyzed"
              colorScheme="gray"
              inlineMarkdown={getInlineMarkdown(0)}
              hasStoragePath={!!artifacts?.doc_0_path}
            />
          )}

          {/* Doc 1 - Jump-Start */}
          {hasDoc(1) && (
            <DocumentAccordion
              jobId={jobId}
              docKey="doc_1"
              title="Jump-Start"
              subtitle="Where to go next"
              colorScheme="blue"
              inlineMarkdown={getInlineMarkdown(1)}
              hasStoragePath={!!artifacts?.doc_1_path}
            />
          )}

          {/* Doc 2 - Semantic Brief */}
          {hasDoc(2) && (
            <DocumentAccordion
              jobId={jobId}
              docKey="doc_2"
              title="Semantic Brief"
              subtitle="What sources reveal"
              colorScheme="purple"
              inlineMarkdown={getInlineMarkdown(2)}
              hasStoragePath={!!artifacts?.doc_2_path}
            />
          )}

          {/* Booster - Deep Research Expansion (conditional) */}
          {isBoosterCompleted && artifacts?.booster_expansion_md && (
            <DocumentAccordion
              jobId={jobId}
              docKey="booster"
              title="Deep Research"
              subtitle="Expanded directions & perspectives"
              colorScheme="indigo"
              inlineMarkdown={artifacts.booster_expansion_md}
              hasStoragePath={false}
            />
          )}

          {/* Doc 3 - Producer Packet (conditional) */}
          {hasDoc3 && (
            <DocumentAccordion
              jobId={jobId}
              docKey="doc_3"
              title="Producer Packet"
              subtitle="Creative layer output"
              colorScheme="amber"
              hasStoragePath={!!artifacts?.doc_3_path}
            />
          )}
        </div>

        {/* Action Bar */}
        <div className="flex flex-wrap gap-2 pt-4 border-t border-gray-700">
          {/* Generate Producer Packet - only if Doc 3 doesn't exist */}
          {!hasDoc3 && (
            <button
              onClick={(e) => { e.stopPropagation(); handleProducerPacket(); }}
              disabled={!canTriggerActions || isTriggeringProducer}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600/20 border border-amber-600/30 px-3 py-1.5 text-sm font-medium text-amber-400 transition hover:bg-amber-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTriggeringProducer ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generating...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
                  Generate Producer Packet
                </>
              )}
            </button>
          )}

          {/* Deep Research (Booster) */}
          <button
            onClick={(e) => { e.stopPropagation(); handleBooster(); }}
            disabled={!canTriggerActions || isTriggeringBooster || isBoosterRunning}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600/20 border border-indigo-600/30 px-3 py-1.5 text-sm font-medium text-indigo-400 transition hover:bg-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {(isTriggeringBooster || isBoosterRunning) ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {boosterStatus === 'running' ? `Running${boosterProgressPercent ? ` (${boosterProgressPercent}%)` : ''}...` : 'Starting...'}
              </>
            ) : isBoosterCompleted ? (
              <>
                <svg className="h-4 w-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Booster Complete
              </>
            ) : isBoosterFailed ? (
              <>
                <svg className="h-4 w-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-red-400">Booster Failed</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Deep Research
              </>
            )}
          </button>
        </div>

        {/* Booster Error */}
        {isBoosterFailed && boosterError && (
          <div className="rounded-lg border border-red-800 bg-red-900/30 p-3">
            <p className="text-sm text-red-300">
              <strong>Booster Error:</strong> {boosterError}
            </p>
          </div>
        )}

        {/* Action Error */}
        {actionError && (
          <div className="rounded-lg border border-red-800 bg-red-900/30 p-3">
            <p className="text-sm text-red-300">{actionError}</p>
          </div>
        )}
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
