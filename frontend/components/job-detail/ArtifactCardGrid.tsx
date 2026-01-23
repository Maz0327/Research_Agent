/**
 * ArtifactCardGrid - Grid layout for artifact cards
 * Orchestrates card states, handles click routing, and manages document viewing.
 */
import { useState, useCallback, useMemo } from 'react';
import { ArtifactCard, type ArtifactState, type ArtifactType } from './ArtifactCard';
import { IterationSelector } from './IterationSelector';
import { DocumentViewerModal } from '../job-card/DocumentViewerModal';
import type { Job, IterationBundle } from '../../store/jobs';
import { API_URL } from '../../lib/constants';
import { getAccessToken } from '../../lib/supabase';

/** Props for document modal */
interface DocModalState {
  isOpen: boolean;
  docNumber: 0 | 1 | 2 | 3 | 'B';
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
}

export interface ArtifactCardGridProps {
  /** Job data */
  job: Job;
  /** Handler to trigger booster */
  onTriggerBooster: () => void;
  /** Handler to trigger producer packet */
  onTriggerProducer: () => void;
  /** Handler to open iteration dialog */
  onOpenIterationDialog: () => void;
  /** Whether actions are disabled (loading state) */
  actionsDisabled?: boolean;
}

/** Determine artifact state from job data */
function getArtifactState(
  job: Job,
  type: ArtifactType,
  selectedVersion: string
): ArtifactState {
  const { status, artifacts, booster_status, producer_status, iteration_status } = job;
  const mainComplete = status === 'completed' || status === 'completed_with_warnings';

  // Viewing iteration version
  if (selectedVersion !== 'baseline' && type !== 'booster' && type !== 'iteration') {
    const iteration = artifacts?.iterations?.find(
      (it) => it.iteration_id === selectedVersion
    );
    if (!iteration) return 'not_available';
    if (iteration.status === 'completed') return 'completed';
    if (iteration.status === 'failed') return 'failed';
    if (iteration.status === 'running') return 'running';
    return 'queued';
  }

  switch (type) {
    case 'doc_0':
      if (artifacts?.doc_0_path || artifacts?.source_ledger) return 'completed';
      if (status === 'running' || status === 'queued') return 'running';
      return 'not_available';

    case 'doc_1':
      if (artifacts?.doc_1_path || artifacts?.jump_start) return 'completed';
      if (status === 'running') return 'running';
      if (status === 'queued') return 'queued';
      return 'not_available';

    case 'doc_2':
      if (artifacts?.doc_2_path || artifacts?.semantic_brief) return 'completed';
      if (status === 'running') return 'running';
      if (status === 'queued') return 'queued';
      return 'not_available';

    case 'doc_3':
      if (artifacts?.doc_3_path || artifacts?.producer_packet_md) return 'completed';
      if (producer_status === 'failed') return 'failed';
      if (producer_status === 'running') return 'running';
      if (producer_status === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';

    case 'booster':
      if (booster_status === 'completed') return 'completed';
      if (booster_status === 'failed') return 'failed';
      if (booster_status === 'running') return 'running';
      if (booster_status === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';

    case 'iteration':
      if (iteration_status === 'running') return 'running';
      if (iteration_status === 'queued') return 'queued';
      if (iteration_status === 'failed') return 'failed';
      const hasCompletedIterations = artifacts?.iterations?.some(
        (it) => it.status === 'completed'
      );
      if (hasCompletedIterations) return 'completed';
      if (!mainComplete) return 'not_available';
      return 'ready';

    default:
      return 'not_available';
  }
}

/** Fetch document content from API endpoint */
async function fetchDocumentFromAPI(
  jobId: string,
  docType: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3'
): Promise<{ data: Record<string, unknown>; markdown?: string }> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Call the correct backend endpoint
  const response = await fetch(`${API_URL}/jobs/${jobId}/documents/${docType}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch document: ${response.statusText}`);
  }

  const result = await response.json();

  // Backend returns either {url, expires_in} for storage jobs or inline data
  if (result.url) {
    // Fetch from signed URL
    const docResponse = await fetch(result.url);
    if (!docResponse.ok) {
      throw new Error(`Failed to fetch from storage: ${docResponse.statusText}`);
    }
    const data = await docResponse.json();
    return {
      data: data.data || data,
      markdown: data.markdown || data.content,
    };
  }

  // Inline data returned directly
  return {
    data: result.data || result,
    markdown: result.markdown || result.content,
  };
}

export function ArtifactCardGrid({
  job,
  onTriggerBooster,
  onTriggerProducer,
  onOpenIterationDialog,
  actionsDisabled = false,
}: ArtifactCardGridProps) {
  // Selected iteration version ('baseline' or iteration_id)
  const [selectedVersion, setSelectedVersion] = useState<string>('baseline');

  // Document viewer modal state
  const [docModal, setDocModal] = useState<DocModalState>({
    isOpen: false,
    docNumber: 0,
    title: '',
    data: {},
  });

  // Loading state for document fetch
  const [isLoadingDoc, setIsLoadingDoc] = useState(false);

  // Get iterations for selector (memoized to prevent useCallback deps change)
  const iterations = useMemo(() => job.artifacts?.iterations || [], [job.artifacts?.iterations]);

  /** Open document viewer for a specific doc */
  const openDocViewer = useCallback(
    async (docNumber: 0 | 1 | 2 | 3 | 'B', title: string) => {
      setIsLoadingDoc(true);

      try {
        let data: Record<string, unknown> = {};
        let markdown: string | undefined;

        // Check if viewing iteration version
        if (selectedVersion !== 'baseline') {
          const iteration = iterations.find((it) => it.iteration_id === selectedVersion);
          if (iteration?.outputs) {
            // Get inline data from iteration using correct positional keys
            // IterationBundle.outputs uses doc_X_inline keys, not named keys like source_ledger
            const inlineKey = docNumber === 0 ? 'doc_0_inline' :
                             docNumber === 1 ? 'doc_1_inline' :
                             docNumber === 2 ? 'doc_2_inline' : null;

            // Note: Doc 3 (producer_packet) is not generated for iterations
            if (inlineKey && iteration.outputs[inlineKey as keyof typeof iteration.outputs]) {
              const inlineData = iteration.outputs[inlineKey as keyof typeof iteration.outputs] as Record<string, unknown>;
              const nestedData = inlineData.data as Record<string, unknown> | undefined;
              data = nestedData || inlineData;
              markdown = (inlineData as { markdown?: string }).markdown;
            }
          }
        } else {
          // Baseline documents - use API endpoint
          const { artifacts } = job;
          if (!artifacts) {
            throw new Error('No artifacts available');
          }

          switch (docNumber) {
            case 0:
              // Try API first, fall back to inline data
              if (artifacts.doc_0_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_0');
                data = result.data;
                markdown = result.markdown;
              } else if (artifacts.source_ledger) {
                data = artifacts.source_ledger.data || artifacts.source_ledger;
                markdown = artifacts.source_ledger.markdown;
              }
              break;

            case 1:
              if (artifacts.doc_1_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_1');
                data = result.data;
                markdown = result.markdown;
              } else if (artifacts.jump_start) {
                data = artifacts.jump_start.data || artifacts.jump_start;
                markdown = artifacts.jump_start.markdown;
              }
              break;

            case 2:
              if (artifacts.doc_2_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_2');
                data = result.data;
                markdown = result.markdown;
              } else if (artifacts.semantic_brief) {
                data = artifacts.semantic_brief.data || artifacts.semantic_brief;
                markdown = artifacts.semantic_brief.markdown;
              }
              break;

            case 3:
              if (artifacts.doc_3_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_3');
                data = result.data;
                markdown = result.markdown;
              } else if (artifacts.producer_packet_md) {
                data = { markdown: artifacts.producer_packet_md };
                markdown = artifacts.producer_packet_md;
              }
              break;

            case 'B':
              // Booster uses inline data only
              if (artifacts.booster_output) {
                data = artifacts.booster_output;
                markdown = artifacts.booster_expansion_md;
              }
              break;
          }
        }

        setDocModal({
          isOpen: true,
          docNumber,
          title,
          data,
          markdown,
        });
      } catch (error) {
        console.error('Failed to load document:', error);
        // Show error in modal
        setDocModal({
          isOpen: true,
          docNumber,
          title,
          data: { error: error instanceof Error ? error.message : 'Failed to load document' },
        });
      } finally {
        setIsLoadingDoc(false);
      }
    },
    [job, selectedVersion, iterations]
  );

  /** Handle card click based on type */
  const handleCardClick = useCallback(
    (type: ArtifactType) => {
      const state = getArtifactState(job, type, selectedVersion);

      switch (type) {
        case 'doc_0':
          if (state === 'completed') {
            openDocViewer(0, 'Source Ledger');
          }
          break;
        case 'doc_1':
          if (state === 'completed') {
            openDocViewer(1, 'Jump-Start Directions');
          }
          break;
        case 'doc_2':
          if (state === 'completed') {
            openDocViewer(2, 'Semantic Brief');
          }
          break;
        case 'doc_3':
          if (state === 'completed') {
            openDocViewer(3, 'Producer Packet');
          } else if (state === 'ready' && !actionsDisabled) {
            onTriggerProducer();
          }
          break;
        case 'booster':
          if (state === 'completed') {
            openDocViewer('B', 'Deep Research');
          } else if (state === 'ready' && !actionsDisabled) {
            onTriggerBooster();
          }
          break;
        case 'iteration':
          if (state === 'ready' || state === 'completed') {
            if (!actionsDisabled) {
              onOpenIterationDialog();
            }
          }
          break;
      }
    },
    [job, selectedVersion, openDocViewer, onTriggerBooster, onTriggerProducer, onOpenIterationDialog, actionsDisabled]
  );

  // Count completed iterations
  const completedIterationCount = iterations.filter((it) => it.status === 'completed').length;

  return (
    <div className="space-y-6">
      {/* Iteration selector - show if iterations exist */}
      {iterations.length > 0 && (
        <IterationSelector
          iterations={iterations}
          selectedVersion={selectedVersion}
          onSelectVersion={setSelectedVersion}
        />
      )}

      {/* Artifact card grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Doc 0: Source Ledger */}
        <ArtifactCard
          type="doc_0"
          state={getArtifactState(job, 'doc_0', selectedVersion)}
          progressPercent={job.progress_percent}
          onClick={() => handleCardClick('doc_0')}
        />

        {/* Doc 1: Jump-Start */}
        <ArtifactCard
          type="doc_1"
          state={getArtifactState(job, 'doc_1', selectedVersion)}
          progressPercent={job.progress_percent}
          onClick={() => handleCardClick('doc_1')}
        />

        {/* Doc 2: Semantic Brief */}
        <ArtifactCard
          type="doc_2"
          state={getArtifactState(job, 'doc_2', selectedVersion)}
          progressPercent={job.progress_percent}
          onClick={() => handleCardClick('doc_2')}
        />

        {/* Doc 3: Producer Packet */}
        <ArtifactCard
          type="doc_3"
          state={getArtifactState(job, 'doc_3', selectedVersion)}
          onClick={() => handleCardClick('doc_3')}
        />

        {/* Booster: Deep Research */}
        <ArtifactCard
          type="booster"
          state={getArtifactState(job, 'booster', selectedVersion)}
          progressPercent={job.booster_progress_percent}
          error={job.booster_error}
          onClick={() => handleCardClick('booster')}
          onRetry={onTriggerBooster}
        />

        {/* Iterations */}
        <ArtifactCard
          type="iteration"
          state={getArtifactState(job, 'iteration', selectedVersion)}
          progressPercent={job.iteration_progress_percent}
          iterationCount={completedIterationCount}
          iterationId={job.iteration_id}
          error={job.iteration_error}
          onClick={() => handleCardClick('iteration')}
          onRetry={onOpenIterationDialog}
        />
      </div>

      {/* Loading overlay */}
      {isLoadingDoc && (
        <div className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center">
          <div className="bg-gray-800 rounded-lg p-6 flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-white">Loading document...</span>
          </div>
        </div>
      )}

      {/* Document viewer modal */}
      <DocumentViewerModal
        isOpen={docModal.isOpen}
        onClose={() => setDocModal((s) => ({ ...s, isOpen: false }))}
        docNumber={docModal.docNumber}
        title={docModal.title}
        markdown={docModal.markdown}
        data={docModal.data}
        jobTitle={job.title || job.prompt}
      />
    </div>
  );
}

export default ArtifactCardGrid;
