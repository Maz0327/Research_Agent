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
import { IterateDialog } from '../../components/iterate/IterateDialog';

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
  const [confirmDelete, setConfirmDelete] = useState(false);
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
      pollIntervalRef.current = setInterval(() => {
        refreshJob(jobId);
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

  const handleTriggerBooster = useCallback(async (runId?: string) => {
    if (!jobId) return;
    await triggerBooster(jobId, runId);
  }, [jobId, triggerBooster]);

  const handleTriggerProducer = useCallback(async (runId?: string) => {
    if (!jobId) return;
    await triggerProducerPacket(jobId, runId);
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
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-0 py-6">
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

        {/* Creator Brief Hero Section — shown when job completed and doc_3 exists */}
        {(job.status === 'completed' || job.status === 'completed_with_warnings') &&
          (job.artifacts?.doc_3_path || job.artifacts?.creator_brief_md) && (
          <div ref={heroRef} className="mb-8">
            <CreatorBriefView
              jobId={job.id}
              onNavigateToDoc={(docType) => {
                // Scroll to artifact card grid — user can click the relevant card
                const grid = document.getElementById('artifact-grid');
                grid?.scrollIntoView({ behavior: 'smooth' });
              }}
            />
          </div>
        )}

        {/* Improve Research button — uses new 5-mode IterateDialog */}
        {(job.status === 'completed' || job.status === 'completed_with_warnings') && (
          <div className="mb-6 flex justify-end">
            <button
              onClick={() => setNewIterateDialogOpen(true)}
              disabled={actionsDisabled}
              className="px-5 py-2.5 rounded-lg text-sm font-medium bg-amber-600 hover:bg-amber-500 text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Improve Research
            </button>
          </div>
        )}

        {/* Artifact Cards Grid */}
        <div id="artifact-grid">
          <ArtifactCardGrid
            job={job}
            onTriggerBooster={handleTriggerBooster}
            onTriggerProducer={handleTriggerProducer}
            onOpenIterationDialog={() => setNewIterateDialogOpen(true)}
            actionsDisabled={actionsDisabled}
            hasHeroSection={!!(job.artifacts?.doc_3_path || job.artifacts?.creator_brief_md)}
            onScrollToHero={() => heroRef.current?.scrollIntoView({ behavior: 'smooth' })}
          />
        </div>

        {/* 5-Mode Iterate Dialog */}
        <IterateDialog
          isOpen={newIterateDialogOpen}
          onClose={() => setNewIterateDialogOpen(false)}
          jobId={jobId}
          onIterateStarted={() => {
            setNewIterateDialogOpen(false);
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
