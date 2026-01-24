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
import { useJobsStore, type IterationRequest } from '../../store/jobs';
import { POLLING_INTERVALS, getStageLabel, getStageDescription } from '../../lib/constants';
import {
  JobDetailHeader,
  ArtifactCardGrid,
} from '../../components/job-detail';

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

/** Iteration Dialog Modal */
interface IterationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: IterationRequest) => void;
  isSubmitting: boolean;
}

function IterationDialog({ isOpen, onClose, onSubmit, isSubmitting }: IterationDialogProps) {
  const [mode, setMode] = useState<IterationRequest['mode']>('more_sources');
  const [userPrompt, setUserPrompt] = useState('');
  const [maxNewSources, setMaxNewSources] = useState(4);
  const [angle, setAngle] = useState('');

  const handleSubmit = () => {
    onSubmit({
      mode,
      user_prompt: userPrompt || undefined,
      max_new_sources: mode === 'more_sources' ? maxNewSources : undefined,
      angle: mode === 'different_angle' ? angle : undefined,
    });
    // Reset form
    setMode('more_sources');
    setUserPrompt('');
    setMaxNewSources(4);
    setAngle('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl"
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
            value={mode}
            onChange={(e) => setMode(e.target.value as IterationRequest['mode'])}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          >
            <option value="more_sources">Find More Sources</option>
            <option value="deeper">Deeper Analysis</option>
            <option value="different_angle">Different Angle</option>
            <option value="custom">Custom (User Prompt)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {mode === 'more_sources' && 'Search for additional sources to expand coverage'}
            {mode === 'deeper' && 'Perform deeper analysis on existing sources'}
            {mode === 'different_angle' && 'Explore a different perspective or angle'}
            {mode === 'custom' && 'Define a custom iteration via prompt'}
          </p>
        </div>

        {/* Angle input (for different_angle mode) */}
        {mode === 'different_angle' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">Angle to Explore</label>
            <input
              type="text"
              value={angle}
              onChange={(e) => setAngle(e.target.value)}
              placeholder="e.g., economic impact, environmental concerns"
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-gray-100 text-sm placeholder-gray-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>
        )}

        {/* Max new sources (for more_sources mode) */}
        {mode === 'more_sources' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Max New Sources: {maxNewSources}
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={maxNewSources}
              onChange={(e) => setMaxNewSources(Number(e.target.value))}
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
            {mode === 'custom' ? 'Custom Prompt' : 'Guidance (optional)'}
          </label>
          <textarea
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            rows={3}
            placeholder={mode === 'custom'
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
            onClick={onClose}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-lg transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || (mode === 'custom' && !userPrompt.trim())}
            className="flex-1 px-4 py-2 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-600/50 disabled:cursor-not-allowed rounded-lg transition"
          >
            {isSubmitting ? 'Starting...' : 'Start Iteration'}
          </button>
        </div>
      </motion.div>
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
    triggerIteration,
    actionInProgress,
  } = useJobsStore();
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [iterationDialogOpen, setIterationDialogOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

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
    if (!jobId) return;
    await triggerBooster(jobId);
  }, [jobId, triggerBooster]);

  const handleTriggerProducer = useCallback(async () => {
    if (!jobId) return;
    await triggerProducerPacket(jobId);
  }, [jobId, triggerProducerPacket]);

  const handleTriggerIteration = useCallback(
    async (request: IterationRequest) => {
      if (!jobId) return;
      await triggerIteration(jobId, request);
      setIterationDialogOpen(false);
    },
    [jobId, triggerIteration]
  );

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
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-blue-700 bg-blue-900/30 p-4 mb-6"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                <div>
                  <p className="font-medium text-blue-300">
                    {job.status === 'queued' ? 'Waiting in queue...' : getStageLabel(job.stage)}
                  </p>
                  <p className="text-sm text-gray-400">
                    {job.pass_detail || getStageDescription(job.stage) || 'Processing your research...'}
                  </p>
                </div>
              </div>
              <span className="text-sm font-mono text-blue-300">{job.progress_percent}%</span>
            </div>
            <div className="mt-3 h-2 bg-gray-700 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${job.progress_percent}%` }}
                transition={{ duration: 0.3 }}
                className="h-full bg-blue-500 rounded-full"
              />
            </div>
          </motion.div>
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

        {/* Artifact Cards Grid */}
        <ArtifactCardGrid
          job={job}
          onTriggerBooster={handleTriggerBooster}
          onTriggerProducer={handleTriggerProducer}
          onOpenIterationDialog={() => setIterationDialogOpen(true)}
          actionsDisabled={actionsDisabled}
        />

        {/* Iteration Dialog */}
        <AnimatePresence>
          {iterationDialogOpen && (
            <IterationDialog
              isOpen={iterationDialogOpen}
              onClose={() => setIterationDialogOpen(false)}
              onSubmit={handleTriggerIteration}
              isSubmitting={actionInProgress === 'iteration'}
            />
          )}
        </AnimatePresence>

        {/* Delete Confirmation Modal */}
        <AnimatePresence>
          {confirmDelete && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
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
