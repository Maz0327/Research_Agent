/**
 * ArtifactCardGrid - Grid layout for artifact cards
 * Orchestrates card states, handles click routing, and manages document viewing.
 * Stage-aware: maps pipeline stage to per-card progress, descriptions, and animations.
 */
import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArtifactCard, type ArtifactState, type ArtifactType } from './ArtifactCard';
import { RunSelector } from './RunSelector';
import { DocumentViewerModal } from '../job-card/DocumentViewerModal';
import type { Job, IterationBundle } from '../../store/jobs';
import type { Run } from '../../types/run';
import { isV2Run } from '../../types/run';
import { API_URL } from '../../lib/constants';
import { getAccessToken } from '../../lib/supabase';

// ─── Reading Order Badges ───────────────────────────────────────────────────────

/** Reading order labels shown on completed doc cards */
const READING_ORDER: Partial<Record<ArtifactType, string>> = {
  doc_3: '1 · Start Here',
  doc_2: '2 · Deep Research',
  doc_1: '3 · Next Steps',
  doc_0: '4 · All Sources',
  doc_4: '5 · Production',
};

// ─── Stage-to-Card Mapping Constants ───────────────────────────────────────────

/** Pipeline stage order — matches exact backend/worker.py update_job() calls */
const STAGE_ORDER = [
  'source_identity',       // 5%
  'semantic_extraction',   // 20%
  'semantic_validation',   // 35%
  'gap_analysis',          // 50%
  'semantic_synthesis',    // 65%
  'document_assembly',     // 80%  (all docs assembled here, including creator brief)
  'completion',            // 95%
] as const;

/** Progress % emitted at each stage boundary */
const STAGE_PROGRESS: Record<string, number> = {
  source_identity: 5,
  semantic_extraction: 20,
  semantic_validation: 35,
  gap_analysis: 50,
  semantic_synthesis: 65,
  document_assembly: 80,
  completion: 95,
};

/** Per-card: which stage starts feeding it, and which stage produces the doc */
const CARD_STAGE_RANGES: Record<string, { start: string; end: string }> = {
  doc_0: { start: 'source_identity', end: 'document_assembly' },
  doc_1: { start: 'gap_analysis', end: 'document_assembly' },
  doc_2: { start: 'semantic_synthesis', end: 'document_assembly' },
  doc_3: { start: 'document_assembly', end: 'completion' },
};

/** Stage-aware descriptions for each card at each pipeline stage */
const CARD_STAGE_DESCRIPTIONS: Record<string, Record<string, string>> = {
  doc_0: {
    source_identity: 'Identifying sources',
    semantic_extraction: 'Extracting content from sources',
    semantic_validation: 'Validating extracted data',
    gap_analysis: 'Cataloging source details',
    semantic_synthesis: 'Finalizing source catalog',
    document_assembly: 'Assembling source ledger',
  },
  doc_1: {
    gap_analysis: 'Analyzing research gaps',
    semantic_synthesis: 'Connecting themes across sources',
    document_assembly: 'Assembling jump-start directions',
  },
  doc_2: {
    semantic_synthesis: 'Synthesizing semantic brief',
    document_assembly: 'Assembling semantic brief',
  },
  doc_3: {
    document_assembly: 'Generating creator brief',
    completion: 'Finalizing creator brief',
  },
};

/** Stagger delay (ms) per card index for sequential animations */
const CARD_STAGGER_DELAY = 0.12; // 120ms between cards

// ─── Stage Info Function ───────────────────────────────────────────────────────

interface CardStageInfo {
  state: ArtifactState;
  progress: number;
  description: string;
}

/** Map pipeline stage + progress to per-card state, progress, and description */
function getCardStageInfo(
  jobStage: string | undefined,
  jobProgress: number,
  cardType: string
): CardStageInfo {
  const range = CARD_STAGE_RANGES[cardType];
  if (!range || !jobStage) {
    return { state: 'running', progress: jobProgress, description: '' };
  }

  const currentIdx = STAGE_ORDER.indexOf(jobStage as typeof STAGE_ORDER[number]);
  const startIdx = STAGE_ORDER.indexOf(range.start as typeof STAGE_ORDER[number]);
  const endIdx = STAGE_ORDER.indexOf(range.end as typeof STAGE_ORDER[number]);

  // Stage not found in our order — fall back to generic running
  if (currentIdx === -1) {
    return { state: 'running', progress: jobProgress, description: '' };
  }

  // Pipeline hasn't reached this card's relevant stage yet
  if (currentIdx < startIdx) {
    return { state: 'waiting', progress: 0, description: '' };
  }

  // Pipeline is at the assembly/end stage for this card — nearly ready
  if (currentIdx === endIdx) {
    const descriptions = CARD_STAGE_DESCRIPTIONS[cardType];
    const desc = descriptions?.[jobStage] || 'Assembling document\u2026';
    return { state: 'nearly_ready', progress: 90, description: desc };
  }

  // Pipeline is past the end stage — card should show as completed
  // (actual completed detection still uses artifact presence in getArtifactState)
  if (currentIdx > endIdx) {
    return { state: 'running', progress: 100, description: '' };
  }

  // Pipeline is in the card's active building range
  // Map job progress to the card's own 0-100% range
  const startProgress = STAGE_PROGRESS[range.start] || 0;
  const endProgress = STAGE_PROGRESS[range.end] || 100;
  const progressRange = endProgress - startProgress;
  const cardProgress = progressRange > 0
    ? Math.round(((jobProgress - startProgress) / progressRange) * 100)
    : 0;
  const clampedProgress = Math.max(5, Math.min(95, cardProgress)); // min 5% so bar is visible

  const descriptions = CARD_STAGE_DESCRIPTIONS[cardType];
  const desc = descriptions?.[jobStage] || 'Processing\u2026';

  return { state: 'running', progress: clampedProgress, description: desc };
}

// ─── Types ─────────────────────────────────────────────────────────────────────

/** Props for document modal */
interface DocModalState {
  isOpen: boolean;
  docNumber: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B';
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
}

export interface ArtifactCardGridProps {
  /** Job data */
  job: Job;
  /** Handler to trigger booster (optional runId for V2 runs) */
  onTriggerBooster: (runId?: string) => void;
  /** Handler to trigger producer packet (optional runId for V2 runs) */
  onTriggerProducer: (runId?: string) => void;
  /** Handler to open iteration dialog */
  onOpenIterationDialog: () => void;
  /** Handler to trigger blog post generation */
  onTriggerBlogPost?: () => void;
  /** Handler to trigger script generation */
  onTriggerScript?: () => void;
  /** Handler to trigger social kit generation */
  onTriggerSocialKit?: () => void;
  /** Whether actions are disabled (loading state) */
  actionsDisabled?: boolean;
}

// ─── getArtifactState ──────────────────────────────────────────────────────────

/** Determine artifact state from job data */
function getArtifactState(
  job: Job,
  type: ArtifactType,
  selectedVersion: string
): ArtifactState {
  const { status, artifacts, booster_status, producer_status, iteration_status } = job;
  const mainComplete = status === 'completed' || status === 'completed_with_warnings';
  const isBaseline = selectedVersion === 'baseline' || selectedVersion === 'run_0';

  // Viewing V2 run version
  if (!isBaseline && isV2Run(selectedVersion) && type !== 'iteration') {
    const runs = (artifacts?.runs || []) as Run[];
    const run = runs.find((r) => r.run_id === selectedVersion);
    if (!run) return 'not_available';

    // Doc 3 (Creator Brief) - check run.producer_packet status (legacy field name)
    if (type === 'doc_3') {
      if (run.producer_packet?.status === 'completed') return 'completed';
      if (run.producer_packet?.status === 'failed') return 'failed';
      if (run.producer_packet?.status === 'running') return 'running';
      if (run.producer_packet?.status === 'queued') return 'queued';
      if (run.status === 'completed') return 'ready';
      return 'not_available';
    }

    // Booster - check run.booster_expansion status
    if (type === 'booster') {
      if (run.booster_expansion?.status === 'completed') return 'completed';
      if (run.booster_expansion?.status === 'failed') return 'failed';
      if (run.booster_expansion?.status === 'running') return 'running';
      if (run.booster_expansion?.status === 'queued') return 'queued';
      if (run.status === 'completed') return 'ready';
      return 'not_available';
    }

    // Doc 0/1/2 - use run status directly
    if (run.status === 'completed') return 'completed';
    if (run.status === 'failed') return 'failed';
    if (run.status === 'running') return 'running';
    return 'queued';
  }

  // Viewing V1 iteration version
  if (!isBaseline && type !== 'booster' && type !== 'iteration') {
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
    case 'claims_doc':
      if (artifacts?.doc_0_path || artifacts?.source_ledger) return 'completed';
      if (status === 'running' || status === 'queued') return 'running';
      return 'not_available';

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
      if (artifacts?.doc_3_path || artifacts?.creator_brief_md) return 'completed';
      if (producer_status === 'failed') return 'failed';
      if (producer_status === 'running') return 'running';
      if (producer_status === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';

    case 'doc_4':
      if (artifacts?.doc_4_path) return 'completed';
      // Doc 4 requires Doc 3 to be done first
      if (!(artifacts?.doc_3_path || artifacts?.creator_brief_md)) return 'not_available';
      if (!mainComplete) return 'not_available';
      return 'ready';

    case 'doc_5': {
      const a5 = artifacts as any;
      if (a5?.doc_5_path || a5?.script) return 'completed';
      const scriptStatus = (job as any).script_status;
      if (scriptStatus === 'failed') return 'failed';
      if (scriptStatus === 'running') return 'running';
      if (scriptStatus === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';
    }

    case 'doc_6': {
      const a6 = artifacts as any;
      if (a6?.doc_6_path || a6?.social_kit) return 'completed';
      const socialKitStatus = (job as any).social_kit_status;
      if (socialKitStatus === 'failed') return 'failed';
      if (socialKitStatus === 'running') return 'running';
      if (socialKitStatus === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';
    }

    case 'doc_7': {
      const a7 = artifacts as any;
      if (a7?.doc_7_path || a7?.blog_post) return 'completed';
      const blogPostStatus = (job as any).blog_post_status;
      if (blogPostStatus === 'failed') return 'failed';
      if (blogPostStatus === 'running') return 'running';
      if (blogPostStatus === 'queued') return 'queued';
      if (!mainComplete) return 'not_available';
      return 'ready';
    }

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
      const hasCompletedRuns = ((artifacts?.runs || []) as Run[]).some(
        (r) => r.status === 'completed' && r.run_type !== 'baseline'
      );
      if (hasCompletedIterations || hasCompletedRuns) return 'completed';
      if (!mainComplete) return 'not_available';
      return 'ready';

    default:
      return 'not_available';
  }
}

// ─── Document Fetch ────────────────────────────────────────────────────────────

/** Fetch document content from API endpoint */
async function fetchDocumentFromAPI(
  jobId: string,
  docType: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3' | 'doc_4' | 'doc_5' | 'doc_6' | 'doc_7'
): Promise<{ data: Record<string, unknown>; markdown?: string }> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}/jobs/${jobId}/documents/${docType}`, {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch document: ${response.statusText}`);
  }

  const result = await response.json();

  if (result.url) {
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

  return {
    data: result.data || result,
    markdown: result.markdown || result.content,
  };
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function ArtifactCardGrid({
  job,
  onTriggerBooster,
  onTriggerProducer,
  onOpenIterationDialog,
  onTriggerBlogPost,
  onTriggerScript,
  onTriggerSocialKit,
  actionsDisabled = false,
}: ArtifactCardGridProps) {
  // Check if this is a claim extraction job
  const isClaimExtractionJob = job.pipeline === 'claim_extraction';

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

  // Get iterations and runs for selector (memoized to prevent useCallback deps change)
  const iterations = useMemo(() => job.artifacts?.iterations || [], [job.artifacts?.iterations]);
  const runs = useMemo(() => (job.artifacts?.runs || []) as Run[], [job.artifacts?.runs]);

  const isBaseline = selectedVersion === 'baseline' || selectedVersion === 'run_0';

  // ─── Stage-aware card info for doc cards during baseline running ────────────

  const docCardInfos = useMemo(() => {
    if (!isBaseline || job.status !== 'running') return null;

    return {
      doc_0: getCardStageInfo(job.stage, job.progress_percent, 'doc_0'),
      doc_1: getCardStageInfo(job.stage, job.progress_percent, 'doc_1'),
      doc_2: getCardStageInfo(job.stage, job.progress_percent, 'doc_2'),
      doc_3: getCardStageInfo(job.stage, job.progress_percent, 'doc_3'),
    };
  }, [job.stage, job.progress_percent, job.status, isBaseline]);

  // Track previous card states to detect transitions for animations
  const prevStatesRef = useRef<Record<string, ArtifactState>>({});

  useEffect(() => {
    if (docCardInfos) {
      // Store current states for next render comparison
      prevStatesRef.current = {
        doc_0: docCardInfos.doc_0.state,
        doc_1: docCardInfos.doc_1.state,
        doc_2: docCardInfos.doc_2.state,
        doc_3: docCardInfos.doc_3.state,
      };
    }
  }, [docCardInfos]);

  // ─── Compute effective card props ──────────────────────────────────────────

  /** Get effective state, progress, and description for a doc card */
  const getEffectiveCardProps = useCallback(
    (cardType: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3') => {
      const baseState = getArtifactState(job, cardType, selectedVersion);
      const info = docCardInfos?.[cardType];

      // Only override if base state is 'running' and we have stage info
      if (baseState === 'running' && info) {
        return {
          state: info.state,
          progressPercent: info.progress,
          runningDescription: info.description || undefined,
        };
      }

      return {
        state: baseState,
        progressPercent: cardType === 'doc_3' ? undefined : job.progress_percent,
        runningDescription: undefined,
      };
    },
    [job, selectedVersion, docCardInfos]
  );

  // ─── Document viewer ──────────────────────────────────────────────────────

  /** Open document viewer for a specific doc */
  const openDocViewer = useCallback(
    async (docNumber: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B', title: string) => {
      setIsLoadingDoc(true);

      try {
        let data: Record<string, unknown> = {};
        let markdown: string | undefined;

        const viewingBaseline = selectedVersion === 'baseline' || selectedVersion === 'run_0';

        if (!viewingBaseline && isV2Run(selectedVersion)) {
          const run = runs.find((r) => r.run_id === selectedVersion);

          if (docNumber === 3 && run?.producer_packet) {
            if (run.producer_packet.status === 'completed') {
              data = run.producer_packet.inline || {};
              markdown = run.producer_packet.markdown;
            }
          } else if (docNumber === 'B' && run?.booster_expansion) {
            if (run.booster_expansion.status === 'completed') {
              data = run.booster_expansion.output || {};
              markdown = run.booster_expansion.markdown;
            }
          } else if (run?.outputs) {
            const inlineKey = docNumber === 0 ? 'doc_0_inline' :
                             docNumber === 1 ? 'doc_1_inline' :
                             docNumber === 2 ? 'doc_2_inline' : null;

            if (inlineKey && run.outputs[inlineKey as keyof typeof run.outputs]) {
              const inlineData = run.outputs[inlineKey as keyof typeof run.outputs] as Record<string, unknown>;
              const nestedData = inlineData.data as Record<string, unknown> | undefined;
              data = nestedData || inlineData;
              markdown = (inlineData as { markdown?: string }).markdown;
            }
          }
        } else if (!viewingBaseline) {
          const iteration = iterations.find((it) => it.iteration_id === selectedVersion);
          if (iteration?.outputs) {
            const inlineKey = docNumber === 0 ? 'doc_0_inline' :
                             docNumber === 1 ? 'doc_1_inline' :
                             docNumber === 2 ? 'doc_2_inline' : null;

            if (inlineKey && iteration.outputs[inlineKey as keyof typeof iteration.outputs]) {
              const inlineData = iteration.outputs[inlineKey as keyof typeof iteration.outputs] as Record<string, unknown>;
              const nestedData = inlineData.data as Record<string, unknown> | undefined;
              data = nestedData || inlineData;
              markdown = (inlineData as { markdown?: string }).markdown;
            }
          }
        } else {
          const { artifacts } = job;
          if (!artifacts) {
            throw new Error('No artifacts available');
          }

          switch (docNumber) {
            case 0:
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
              } else if (artifacts.creator_brief_md) {
                data = { markdown: artifacts.creator_brief_md };
                markdown = artifacts.creator_brief_md;
              }
              break;
            case 4:
              if (artifacts.doc_4_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_4');
                data = result.data;
                markdown = result.markdown;
              }
              break;
            case 5: {
              const a5 = artifacts as any;
              if (a5.doc_5_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_5');
                data = result.data;
                markdown = result.markdown;
              } else if (a5.script) {
                data = a5.script;
                markdown = a5.script_md;
              }
              break;
            }
            case 6: {
              const a6 = artifacts as any;
              if (a6.doc_6_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_6');
                data = result.data;
                markdown = result.markdown;
              } else if (a6.social_kit) {
                data = a6.social_kit;
                markdown = a6.social_kit_md;
              }
              break;
            }
            case 7: {
              const a7 = artifacts as any;
              if (a7.doc_7_path) {
                const result = await fetchDocumentFromAPI(job.id, 'doc_7');
                data = result.data;
                markdown = result.markdown;
              } else if (a7.blog_post) {
                data = a7.blog_post;
                markdown = a7.blog_post_md;
              }
              break;
            }
            case 'B':
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
    [job, selectedVersion, iterations, runs]
  );

  /** Handle card click based on type */
  const handleCardClick = useCallback(
    (type: ArtifactType) => {
      const state = getArtifactState(job, type, selectedVersion);

      switch (type) {
        case 'claims_doc':
          if (state === 'completed') {
            openDocViewer(0, 'Claims Document');
          }
          break;
        case 'doc_0':
          if (state === 'completed') {
            openDocViewer(0, 'Your Sources');
          }
          break;
        case 'doc_1':
          if (state === 'completed') {
            openDocViewer(1, 'Research Gaps');
          }
          break;
        case 'doc_2':
          if (state === 'completed') {
            openDocViewer(2, 'Key Findings');
          }
          break;
        case 'doc_3':
          if (state === 'completed') {
            openDocViewer(3, 'Creator Brief');
          } else if (state === 'ready' && !actionsDisabled) {
            const producerRunId = isV2Run(selectedVersion) && selectedVersion !== 'run_0'
              ? selectedVersion
              : undefined;
            onTriggerProducer(producerRunId);
          }
          break;
        case 'doc_4':
          if (state === 'completed') {
            openDocViewer(4, 'Producer Packet');
          } else if (state === 'ready' && !actionsDisabled) {
            onTriggerProducer(); // Producer packet generation
          }
          break;
        case 'doc_5':
          if (state === 'completed') {
            openDocViewer(5, 'Script');
          } else if (state === 'ready' && !actionsDisabled) {
            onTriggerScript?.();
          }
          break;
        case 'doc_6':
          if (state === 'completed') {
            openDocViewer(6, 'Social Media Kit');
          } else if (state === 'ready' && !actionsDisabled) {
            onTriggerSocialKit?.();
          }
          break;
        case 'doc_7':
          if (state === 'completed') {
            openDocViewer(7, 'Blog Post');
          } else if (state === 'ready' && !actionsDisabled) {
            // Trigger blog post generation
            onTriggerBlogPost?.();
          }
          break;
        case 'booster':
          if (state === 'completed') {
            openDocViewer('B', 'Deep Research');
          } else if (state === 'ready' && !actionsDisabled) {
            const boosterRunId = isV2Run(selectedVersion) && selectedVersion !== 'run_0'
              ? selectedVersion
              : undefined;
            onTriggerBooster(boosterRunId);
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
    [job, selectedVersion, openDocViewer, onTriggerBooster, onTriggerProducer, onOpenIterationDialog, onTriggerBlogPost, onTriggerScript, onTriggerSocialKit, actionsDisabled]
  );

  // Count completed iterations and runs
  const completedIterationCount = iterations.filter((it) => it.status === 'completed').length;
  const completedRunCount = runs.filter((r) => r.status === 'completed' && r.run_type !== 'baseline').length;
  const totalCompletedCount = completedIterationCount + completedRunCount;

  // ─── Render: Claim Extraction (single card) ──────────────────────────────

  if (isClaimExtractionJob) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <ArtifactCard
            type="claims_doc"
            state={getArtifactState(job, 'claims_doc', selectedVersion)}
            progressPercent={job.progress_percent}
            onClick={() => handleCardClick('claims_doc')}
          />
        </div>

        {isLoadingDoc && (
          <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center">
            <div className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-6 py-4 flex items-center gap-3">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="animate-spin text-white/50">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.12" />
                <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
              </svg>
              <span className="text-sm text-white/70 font-medium">Loading document</span>
            </div>
          </div>
        )}

        <DocumentViewerModal
          isOpen={docModal.isOpen}
          onClose={() => setDocModal((s) => ({ ...s, isOpen: false }))}
          docNumber={docModal.docNumber}
          title={docModal.title}
          markdown={docModal.markdown}
          data={docModal.data}
          jobTitle={job.title || job.prompt}
          jobId={job.id}
        />
      </div>
    );
  }

  // ─── Render: Semantic Pipeline (full grid with stage-aware cards) ─────────

  // Compute effective props for each doc card
  const doc0Props = getEffectiveCardProps('doc_0');
  const doc1Props = getEffectiveCardProps('doc_1');
  const doc2Props = getEffectiveCardProps('doc_2');
  const doc3Props = getEffectiveCardProps('doc_3');

  // Determine if we should animate transitions (only during running baseline)
  const shouldAnimate = isBaseline && job.status === 'running' && !!docCardInfos;

  return (
    <div className="space-y-6">
      {/* Run/Iteration selector */}
      {(runs.length > 0 || iterations.length > 0) && (
        <RunSelector
          runs={runs}
          iterations={iterations}
          selectedVersion={selectedVersion}
          onSelectVersion={setSelectedVersion}
        />
      )}

      {/* Artifact card grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {/* Doc cards with stage-aware animations */}
        {([
          { key: 'doc_0' as const, props: doc0Props, idx: 0 },
          { key: 'doc_1' as const, props: doc1Props, idx: 1 },
          { key: 'doc_2' as const, props: doc2Props, idx: 2 },
          { key: 'doc_3' as const, props: doc3Props, idx: 3 },
        ]).map(({ key, props, idx }) => (
          <motion.div
            key={key}
            initial={false}
            animate={{
              opacity: props.state === 'waiting' ? 0.5 : 1,
              scale: props.state === 'waiting' ? 0.98 : 1,
            }}
            transition={{
              type: 'spring',
              stiffness: 300,
              damping: 30,
              delay: shouldAnimate ? idx * CARD_STAGGER_DELAY : 0,
            }}
          >
            <ArtifactCard
              type={key}
              state={props.state}
              progressPercent={props.progressPercent}
              runningDescription={props.runningDescription}
              onClick={() => handleCardClick(key)}
              readingOrder={READING_ORDER[key]}
            />
          </motion.div>
        ))}

        {/* Doc 4: Producer Packet — available after Doc 3 completes */}
        <ArtifactCard
          type="doc_4"
          state={getArtifactState(job, 'doc_4', selectedVersion)}
          onClick={() => handleCardClick('doc_4')}
          readingOrder={READING_ORDER.doc_4}
        />

        {/* Doc 5: Script — user-triggered */}
        <ArtifactCard
          type="doc_5"
          state={getArtifactState(job, 'doc_5', selectedVersion)}
          onClick={() => handleCardClick('doc_5')}
        />

        {/* Doc 6: Social Media Kit — user-triggered */}
        <ArtifactCard
          type="doc_6"
          state={getArtifactState(job, 'doc_6', selectedVersion)}
          onClick={() => handleCardClick('doc_6')}
        />

        {/* Doc 7: Blog Post — user-triggered */}
        <ArtifactCard
          type="doc_7"
          state={getArtifactState(job, 'doc_7', selectedVersion)}
          onClick={() => handleCardClick('doc_7')}
        />

        {/* Booster: Deep Research — independent progress tracking */}
        <ArtifactCard
          type="booster"
          state={getArtifactState(job, 'booster', selectedVersion)}
          progressPercent={job.booster_progress_percent}
          error={job.booster_error}
          onClick={() => handleCardClick('booster')}
          onRetry={onTriggerBooster}
        />

        {/* Iterations / Runs — independent progress tracking */}
        <ArtifactCard
          type="iteration"
          state={getArtifactState(job, 'iteration', selectedVersion)}
          progressPercent={job.iteration_progress_percent}
          iterationCount={totalCompletedCount}
          iterationId={job.iteration_id}
          error={job.iteration_error}
          onClick={() => handleCardClick('iteration')}
          onRetry={onOpenIterationDialog}
        />
      </div>

      {/* Loading overlay */}
      {isLoadingDoc && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center">
          <div className="bg-white/[0.05] border border-white/[0.08] rounded-lg px-6 py-4 flex items-center gap-3">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="animate-spin text-white/50">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" opacity="0.12" />
              <path d="M12 2 a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <span className="text-sm text-white/70 font-medium">Loading document</span>
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
        jobId={job.id}
      />
    </div>
  );
}

export default ArtifactCardGrid;
