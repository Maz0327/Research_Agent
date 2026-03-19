/**
 * Job Detail Page - Full page view for a single research job
 * Shows artifact cards and iteration selector.
 * Loading states are shown directly on artifact cards (not in banners).
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../../components/Layout';
import { ProtectedRoute, useAuth } from '../../components/AuthProvider';
import { useJobsStore } from '../../store/jobs';
import { POLLING_INTERVALS } from '../../lib/constants';
import {
  JobDetailHeader,
  ArtifactCardGrid,
  JobProgressPanel,
} from '../../components/job-detail';
import { CreatorBriefView } from '../../components/creator-brief/CreatorBriefView';
import { RefinePanel } from '../../components/iterate/RefinePanel';
import { ReadingGuide } from '../../components/job-detail/ReadingGuide';
import { DocumentAccordion } from '../../components/job-detail/DocumentAccordion';
import type { Job } from '../../store/jobs';
import { formatTimestampWithRelative } from '../../lib/document-formatters';

/** Research Overview panel — fills blank space below artifact grid for completed jobs */
function ResearchOverview({ job }: { job: Job }) {
  const { artifacts } = job;
  if (!artifacts) return null;

  // Count completed docs
  const docsCompleted = [
    artifacts.doc_0_path || artifacts.source_ledger,
    artifacts.doc_1_path || artifacts.jump_start,
    artifacts.doc_2_path || artifacts.semantic_brief,
    artifacts.doc_3_path || artifacts.creator_brief_md,
  ].filter(Boolean).length;

  // Count iterations
  const iterationCount = artifacts.iterations?.filter((it) => it.status === 'completed').length ?? 0;

  const docItems = [
    { key: 0, label: 'Source Ledger', color: 'bg-gray-500', ready: !!(artifacts.doc_0_path || artifacts.source_ledger) },
    { key: 1, label: 'Jump-Start', color: 'bg-blue-500', ready: !!(artifacts.doc_1_path || artifacts.jump_start) },
    { key: 2, label: 'Semantic Brief', color: 'bg-purple-500', ready: !!(artifacts.doc_2_path || artifacts.semantic_brief) },
    { key: 3, label: 'Creator Brief', color: 'bg-amber-500', ready: !!(artifacts.doc_3_path || artifacts.creator_brief_md) },
  ];

  return (
    <div className="mt-8 rounded-xl border border-gray-700/50 bg-gray-800/30 p-5">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Research Overview</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Documents completed */}
        <div className="space-y-2">
          <p className="text-xs text-gray-500 font-medium">Documents</p>
          <div className="space-y-1.5">
            {docItems.map((doc) => (
              <div key={doc.key} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${doc.ready ? doc.color : 'bg-gray-700'}`} />
                <span className={`text-xs ${doc.ready ? 'text-gray-300' : 'text-gray-600'}`}>{doc.label}</span>
                {doc.ready && <span className="text-xs text-green-500 ml-auto">✓</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Pipeline info */}
        <div className="space-y-2">
          <p className="text-xs text-gray-500 font-medium">Pipeline</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 capitalize">{job.pipeline?.replace(/_/g, ' ') || 'Semantic'}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">{docsCompleted} of 4 docs complete</span>
            </div>
            {iterationCount > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-teal-400">{iterationCount} iteration{iterationCount > 1 ? 's' : ''} run</span>
              </div>
            )}
          </div>
        </div>

        {/* Status */}
        <div className="space-y-2">
          <p className="text-xs text-gray-500 font-medium">Status</p>
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              {job.status === 'completed' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-green-900/40 text-green-400 border border-green-700/40">
                  ● Completed
                </span>
              )}
              {job.status === 'completed_with_warnings' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-yellow-900/40 text-yellow-400 border border-yellow-700/40">
                  ● Completed
                </span>
              )}
            </div>
            {artifacts.booster_output && (
              <span className="text-xs text-indigo-400">Deep Research: done</span>
            )}
          </div>
        </div>

        {/* Timestamps */}
        <div className="space-y-2">
          <p className="text-xs text-gray-500 font-medium">Created</p>
          <p className="text-xs text-gray-400">{formatTimestampWithRelative(job.created_at)}</p>
        </div>
      </div>
    </div>
  );
}

/** Skeleton loader for job detail */
function JobDetailSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-6 w-24 bg-gray-800 rounded mb-4" />
      <div className="h-8 w-3/4 bg-gray-800 rounded mb-2" />
      <div className="h-5 w-48 bg-gray-800 rounded mb-8" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="h-32 bg-gray-800 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

function JobDetailContent() {
  const router = useRouter();
  const { id } = router.query;
  const jobId = typeof id === 'string' ? id : '';

  const {
    jobs,
    refreshJob,
    deleteJob,
    archiveJob,
    triggerBooster,
    triggerProducerPacket,
    actionInProgress,
  } = useJobsStore();
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [newIterateDialogOpen, setNewIterateDialogOpen] = useState(false);
  const [iterateDefaultMode, setIterateDefaultMode] = useState<string | undefined>(undefined);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [viewMode, setViewMode] = useState<'hero' | 'grid'>('hero');
  const heroRef = useRef<HTMLDivElement>(null);

  // Find job in store
  const job = jobs.find((j) => j.id === jobId);

  // Fetch job on mount and setup polling
  useEffect(() => {
    if (!jobId || !user) return;

    const fetchData = async () => {
      try {
        await refreshJob(jobId);
        setIsLoading(false);
      } catch {
        setNotFound(true);
        setIsLoading(false);
      }
    };

    fetchData();
  }, [jobId, user, refreshJob]);

  // Polling for active jobs/tasks
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollErrorCountRef = useRef(0);
  const MAX_POLL_ERRORS = 5;

  useEffect(() => {
    if (!job || !jobId) return;

    // Should poll if main job running OR any secondary task running
    const shouldPoll =
      job.status === 'running' ||
      job.status === 'queued' ||
      job.booster_status === 'running' ||
      job.booster_status === 'queued' ||
      job.producer_status === 'running' ||
      job.producer_status === 'queued' ||
      job.iteration_status === 'running' ||
      job.iteration_status === 'queued';

    if (shouldPoll) {
      pollIntervalRef.current = setInterval(async () => {
        try {
          await refreshJob(jobId);
          pollErrorCountRef.current = 0; // Reset on success
        } catch {
          pollErrorCountRef.current += 1;
          if (pollErrorCountRef.current >= MAX_POLL_ERRORS && pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            console.warn(`Polling stopped after ${MAX_POLL_ERRORS} consecutive errors`);
          }
        }
      }, POLLING_INTERVALS.JOB_STATUS);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [job, jobId, refreshJob]);

  // Escape key + body scroll lock for delete modal
  useEffect(() => {
    if (!confirmDelete) return;
    document.body.style.overflow = 'hidden';
    const handleEscape = (e: KeyboardEvent) => { if (e.key === 'Escape') setConfirmDelete(false); };
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [confirmDelete]);

  // Handlers
  const handleArchive = useCallback(async () => {
    if (!jobId) return;
    await archiveJob(jobId);
    router.push('/dashboard');
  }, [jobId, archiveJob, router]);

  const handleDelete = useCallback(async () => {
    if (!jobId) return;
    await deleteJob(jobId);
    router.push('/dashboard');
  }, [jobId, deleteJob, router]);

  const handleTriggerBooster = useCallback(async () => {
    // Booster endpoint is deprecated (HTTP 410). Open the iterate dialog instead,
    // pre-selecting deep_dive mode as the booster replacement.
    setIterateDefaultMode('deep_dive');
    setNewIterateDialogOpen(true);
  }, []);

  const handleTriggerProducer = useCallback(async (runId?: string) => {
    if (!jobId) return;
    try {
      await triggerProducerPacket(jobId, runId);
    } catch (err) {
      console.error('Failed to trigger producer packet:', err);
    }
  }, [jobId, triggerProducerPacket]);

  const actionsDisabled = !!actionInProgress;

  // Loading state
  if (isLoading) {
    return (
      <Layout>
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-0 py-6">
          <JobDetailSkeleton />
        </div>
      </Layout>
    );
  }

  // Not found state
  if (notFound || !job) {
    return (
      <Layout>
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-0 py-6">
          <div className="text-center py-16">
            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-gray-800 p-4">
              <svg className="h-8 w-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-200">Job not found</h2>
            <p className="mt-2 text-gray-400">The job you&apos;re looking for doesn&apos;t exist or has been deleted.</p>
            <button
              onClick={() => router.push('/dashboard')}
              className="mt-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <JobDetailHeader
          jobId={job.id}
          title={job.title || job.prompt}
          status={job.status}
          createdAt={job.created_at}
          onArchive={handleArchive}
          onDelete={() => setConfirmDelete(true)}
          actionsDisabled={actionsDisabled}
        />

        {/* Active task loading states are now shown on individual artifact cards */}

        {/* Main job running indicator */}
        {(job.status === 'running' || job.status === 'queued') && (
          <JobProgressPanel job={job} />
        )}

        {/* Error display */}
        {job.status === 'failed' && job.error && (
          <div className="rounded-xl border border-red-700 bg-red-900/30 p-4 mb-6">
            <p className="font-medium text-red-300">Job Failed</p>
            <p className="text-sm text-red-200 mt-1">{job.error}</p>
          </div>
        )}

        {/* Warnings display */}
        {job.status === 'completed_with_warnings' && job.warnings && job.warnings.length > 0 && (
          <div className="rounded-xl border border-yellow-700 bg-yellow-900/30 p-4 mb-6">
            <p className="font-medium text-yellow-300">Completed with Warnings</p>
            <ul className="list-disc list-inside text-sm text-yellow-200 mt-1">
              {job.warnings.slice(0, 3).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
              {job.warnings.length > 3 && (
                <li className="text-yellow-400">+{job.warnings.length - 3} more warnings</li>
              )}
            </ul>
          </div>
        )}

        {/* ─── Progressive Document Reveal (Phase 3D) ──────────────── */}
        {(job.status === 'completed' || job.status === 'completed_with_warnings') && (
          <>
            {/* View mode toggle */}
            <div className="flex items-center justify-end mb-4 gap-2">
              <button
                onClick={() => setViewMode(viewMode === 'hero' ? 'grid' : 'hero')}
                className="text-[12px] text-white/40 hover:text-white/60 transition-colors flex items-center gap-1.5"
              >
                {viewMode === 'hero' ? (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                    </svg>
                    View all documents
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                    </svg>
                    Focus on Creator Brief
                  </>
                )}
              </button>
            </div>

            {viewMode === 'hero' ? (
              <>
                {/* Creator Brief Hero Section — full-width at top */}
                {(job.artifacts?.doc_3_path || job.artifacts?.creator_brief_md) && (
                  <div ref={heroRef} className="mb-8">
                    <CreatorBriefView
                      jobId={job.id}
                      onNavigateToDoc={() => {
                        setViewMode('grid');
                        setTimeout(() => {
                          const grid = document.getElementById('artifact-grid');
                          grid?.scrollIntoView({ behavior: 'smooth' });
                        }, 100);
                      }}
                    />
                  </div>
                )}

                {/* Supporting documents in accordion */}
                <div className="mb-8">
                  <DocumentAccordion
                    job={job}
                    onOpenDoc={(docNumber, title) => {
                      // Switch to grid view and scroll to the card
                      setViewMode('grid');
                    }}
                  />
                </div>

                {/* Iteration/Booster actions still visible */}
                <div id="artifact-grid">
                  <ArtifactCardGrid
                    job={job}
                    onTriggerBooster={handleTriggerBooster}
                    onTriggerProducer={handleTriggerProducer}
                    onOpenIterationDialog={() => setNewIterateDialogOpen(true)}
                    actionsDisabled={actionsDisabled}
                  />
                </div>
              </>
            ) : (
              <>
                {/* Grid view — original layout */}
                <ReadingGuide
                  hasCreatorBrief={!!(job.artifacts?.doc_3_path || job.artifacts?.creator_brief_md)}
                  onStartReading={() => {
                    setViewMode('hero');
                    setTimeout(() => {
                      heroRef.current?.scrollIntoView({ behavior: 'smooth' });
                    }, 100);
                  }}
                />
                <div id="artifact-grid">
                  <ArtifactCardGrid
                    job={job}
                    onTriggerBooster={handleTriggerBooster}
                    onTriggerProducer={handleTriggerProducer}
                    onOpenIterationDialog={() => setNewIterateDialogOpen(true)}
                    actionsDisabled={actionsDisabled}
                  />
                </div>
                <ResearchOverview job={job} />
              </>
            )}
          </>
        )}

        {/* For non-completed jobs, show the standard grid */}
        {job.status !== 'completed' && job.status !== 'completed_with_warnings' && (
          <div id="artifact-grid">
            <ArtifactCardGrid
              job={job}
              onTriggerBooster={handleTriggerBooster}
              onTriggerProducer={handleTriggerProducer}
              onOpenIterationDialog={() => setNewIterateDialogOpen(true)}
              actionsDisabled={actionsDisabled}
            />
          </div>
        )}

        {/* Natural Language Refine Panel — replaces 5-mode IterateDialog */}
        <RefinePanel
          isOpen={newIterateDialogOpen}
          onClose={() => {
            setNewIterateDialogOpen(false);
            setIterateDefaultMode(undefined);
          }}
          jobId={jobId}
          job={{ title: job.title || job.prompt, artifacts: job.artifacts as Record<string, unknown> | undefined }}
          onIterateStarted={() => {
            setNewIterateDialogOpen(false);
            setIterateDefaultMode(undefined);
            // Refresh job to start polling
            refreshJob(jobId);
          }}
        />

        {/* Delete Confirmation Modal */}
        <AnimatePresence>
          {confirmDelete && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={() => setConfirmDelete(false)}>
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-sm shadow-2xl"
              >
                <h3 className="text-lg font-semibold text-gray-100 mb-2">Delete Job?</h3>
                <p className="text-sm text-gray-400 mb-6">
                  This will permanently delete this job and all its artifacts. This action cannot be undone.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="flex-1 px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDelete}
                    className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition"
                  >
                    Delete
                  </button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </Layout>
  );
}

export default function JobDetailPage() {
  return (
    <ProtectedRoute>
      <JobDetailContent />
    </ProtectedRoute>
  );
}
