/**
 * Jobs Page - Central hub for viewing all jobs with tabbed navigation.
 * Tabs: Active (running/queued), Completed, Failed
 * ADHD-friendly: Clear status indicators, progress tracking, and easy navigation.
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import { ProtectedRoute } from '../components/AuthProvider';
import { useJobsStore, type Job } from '../store/jobs';
import { POLLING_INTERVALS, getStageLabel } from '../lib/constants';
import { statusConfig, pipelineLabels } from '../components/job-card/job-card-config';

// Tab types
type TabType = 'active' | 'completed' | 'failed' | 'archived';

/** Status badge component */
function StatusDot({ status }: { status: string }) {
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.queued;
  return (
    <span className={`inline-block h-2.5 w-2.5 rounded-full ${config.dotColor} ${status === 'running' ? 'animate-pulse' : ''}`} />
  );
}

/** Format relative time */
function formatRelativeTime(dateString?: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/** Format elapsed time since job started */
function formatElapsedTime(startTime?: string): string {
  if (!startTime) return '-';
  const start = new Date(startTime);
  const now = new Date();
  const diffMs = now.getTime() - start.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  
  if (diffSec < 60) return `${diffSec}s`;
  const mins = Math.floor(diffSec / 60);
  const secs = diffSec % 60;
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

/** Estimate ETA based on progress and elapsed time */
function estimateETA(progress: number, startTime?: string): string {
  if (!startTime || progress <= 0 || progress >= 100) return '-';
  
  const start = new Date(startTime);
  const now = new Date();
  const elapsedMs = now.getTime() - start.getTime();
  
  // Estimate total time based on current progress
  const estimatedTotalMs = (elapsedMs / progress) * 100;
  const remainingMs = estimatedTotalMs - elapsedMs;
  
  if (remainingMs <= 0) return 'Soon';
  
  const remainingSec = Math.floor(remainingMs / 1000);
  if (remainingSec < 60) return `~${remainingSec}s`;
  const mins = Math.floor(remainingSec / 60);
  if (mins < 60) return `~${mins}m`;
  const hours = Math.floor(mins / 60);
  return `~${hours}h ${mins % 60}m`;
}

/** Active job card with progress details */
function ActiveJobCard({ job, position }: { job: Job; position: number }) {
  const router = useRouter();
  const stageDescription = job.pass_detail || getStageLabel(job.stage);
  const progress = job.progress_percent || 0;
  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.queued;

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`group relative flex flex-col p-4 bg-[#1a1a1a] rounded-xl border ${config.borderColor} hover:border-gray-600 cursor-pointer transition-all`}
    >
      <div className="flex items-start gap-4">
        {/* Position indicator */}
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400 font-mono text-sm">
          #{position}
        </div>

        {/* Job info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusDot status={job.status} />
            <h3 className="text-white font-medium truncate">{job.title || 'Untitled Job'}</h3>
          </div>
          <p className="text-sm text-gray-400 truncate">{stageDescription}</p>
          
          {/* Time info row */}
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>Elapsed: {formatElapsedTime(job.stage_started_at || job.created_at)}</span>
            {job.status === 'running' && progress > 0 && (
              <span>ETA: {estimateETA(progress, job.stage_started_at || job.created_at)}</span>
            )}
          </div>
        </div>

        {/* Progress percentage */}
        <div className="flex-shrink-0 text-right">
          <span className={`text-lg font-mono ${config.textColor}`}>{progress}%</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
          className={`h-full rounded-full ${job.status === 'running' ? 'bg-blue-500' : 'bg-yellow-500'}`}
        />
      </div>
    </div>
  );
}

/** Completed job card with document access */
function CompletedJobCard({ job }: { job: Job }) {
  const router = useRouter();
  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.completed;
  const hasWarnings = job.status === 'completed_with_warnings';
  const hasDocuments = job.artifacts && (
    job.artifacts.doc_0_path || 
    job.artifacts.doc_1_path || 
    job.artifacts.doc_2_path ||
    job.artifacts.source_ledger ||
    job.artifacts.jump_start ||
    job.artifacts.semantic_brief
  );

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`group relative flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border ${config.borderColor} hover:border-gray-600 cursor-pointer transition-all`}
    >
      {/* Status icon */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-lg ${config.bgColor} flex items-center justify-center`}>
        {hasWarnings ? (
          <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>

      {/* Job info */}
      <div className="flex-1 min-w-0">
        <h3 className="text-white font-medium truncate">{job.title || 'Untitled Job'}</h3>
        <div className="flex items-center gap-3 mt-1 text-sm text-gray-400">
          <span>{pipelineLabels[job.pipeline] || job.pipeline}</span>
          <span className="text-gray-600">•</span>
          <span>{formatRelativeTime(job.created_at)}</span>
          {hasWarnings && job.warning_count && (
            <>
              <span className="text-gray-600">•</span>
              <span className="text-yellow-400">{job.warning_count} warning{job.warning_count > 1 ? 's' : ''}</span>
            </>
          )}
        </div>
      </div>

      {/* Document indicator */}
      {hasDocuments && (
        <div className="flex items-center gap-2 text-gray-400">
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-xs">View Docs</span>
        </div>
      )}

      {/* Hover arrow */}
      <svg
        className="flex-shrink-0 h-5 w-5 text-gray-600 group-hover:text-gray-400 transition-colors"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

/** Failed job card with error info */
function FailedJobCard({ job }: { job: Job }) {
  const router = useRouter();
  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.failed;
  const isCancelled = job.status === 'cancelled';
  const isInsufficient = job.status === 'failed_insufficient';

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`group relative flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border ${config.borderColor} hover:border-gray-600 cursor-pointer transition-all`}
    >
      {/* Status icon */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-lg ${config.bgColor} flex items-center justify-center`}>
        {isCancelled ? (
          <svg className="h-5 w-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        ) : isInsufficient ? (
          <svg className="h-5 w-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
      </div>

      {/* Job info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-white font-medium truncate">{job.title || 'Untitled Job'}</h3>
          <span className={`px-2 py-0.5 text-xs rounded-full ${config.bgColor} ${config.textColor}`}>
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1 text-sm text-gray-400">
          <span>{formatRelativeTime(job.created_at)}</span>
        </div>
        {job.error && (
          <p className="mt-2 text-sm text-red-300 truncate">{job.error}</p>
        )}
      </div>

      {/* Hover arrow */}
      <svg
        className="flex-shrink-0 h-5 w-5 text-gray-600 group-hover:text-gray-400 transition-colors"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    </div>
  );
}

/** Tab button component */
function TabButton({ 
  active, 
  onClick, 
  children, 
  count 
}: { 
  active: boolean; 
  onClick: () => void; 
  children: React.ReactNode; 
  count: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative px-4 py-2.5 text-sm font-medium transition-all rounded-lg ${
        active
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
          : 'text-gray-400 hover:text-gray-300 hover:bg-gray-800'
      }`}
    >
      {children}
      {count > 0 && (
        <span className={`ml-2 px-1.5 py-0.5 text-xs rounded-full ${
          active ? 'bg-blue-500 text-white' : 'bg-gray-700 text-gray-300'
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

/** Archived job card with recovery option */
function ArchivedJobCard({ job, onRecover }: { job: Job; onRecover: (jobId: string) => void }) {
  const router = useRouter();
  const [isRecovering, setIsRecovering] = useState(false);
  const config = statusConfig[job.status as keyof typeof statusConfig] || statusConfig.completed;

  const handleRecover = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsRecovering(true);
    try {
      await onRecover(job.id);
    } finally {
      setIsRecovering(false);
    }
  };

  return (
    <div
      onClick={() => router.push(`/jobs/${job.id}`)}
      className={`group relative flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border border-gray-700 hover:border-gray-600 cursor-pointer transition-all opacity-70 hover:opacity-100`}
    >
      {/* Archive icon */}
      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-800 flex items-center justify-center">
        <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
        </svg>
      </div>

      {/* Job info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-white font-medium truncate">{job.title || 'Untitled Job'}</h3>
          <span className={`px-2 py-0.5 text-xs rounded-full ${config.bgColor} ${config.textColor}`}>
            {config.label}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1 text-sm text-gray-400">
          <span>{pipelineLabels[job.pipeline] || job.pipeline}</span>
          <span className="text-gray-600">•</span>
          <span>{formatRelativeTime(job.created_at)}</span>
        </div>
      </div>

      {/* Recover button */}
      <button
        onClick={handleRecover}
        disabled={isRecovering}
        className="flex-shrink-0 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
      >
        {isRecovering ? (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          'Recover'
        )}
      </button>
    </div>
  );
}

function JobsContent() {
  const router = useRouter();
  const { jobs, archivedJobs, fetchJobs, fetchArchivedJobs, refreshJob, unarchiveJob, isLoadingArchived } = useJobsStore();
  const [isLoading, setIsLoading] = useState(true);
  
  // Get initial tab from query parameter
  const queryTab = router.query.tab as TabType | undefined;
  const [activeTab, setActiveTab] = useState<TabType>('active');
  
  // Sync tab with URL query parameter
  useEffect(() => {
    if (queryTab && ['active', 'completed', 'failed', 'archived'].includes(queryTab)) {
      setActiveTab(queryTab);
    }
  }, [queryTab]);

  // Fetch archived jobs when switching to archived tab
  useEffect(() => {
    if (activeTab === 'archived') {
      fetchArchivedJobs();
    }
  }, [activeTab, fetchArchivedJobs]);

  // Update URL when tab changes
  const handleTabChange = useCallback((tab: TabType) => {
    setActiveTab(tab);
    router.push(`/queue?tab=${tab}`, undefined, { shallow: true });
  }, [router]);

  // Filter jobs by tab
  const activeJobs = useMemo(() => {
    return jobs
      .filter((job) => job.status === 'running' || job.status === 'queued')
      .sort((a, b) => {
        // Running jobs first, then by created_at
        if (a.status === 'running' && b.status !== 'running') return -1;
        if (b.status === 'running' && a.status !== 'running') return 1;
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      });
  }, [jobs]);

  const completedJobs = useMemo(() => {
    return jobs
      .filter((job) => job.status === 'completed' || job.status === 'completed_with_warnings')
      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  }, [jobs]);

  const failedJobs = useMemo(() => {
    return jobs
      .filter((job) => job.status === 'failed' || job.status === 'failed_insufficient' || job.status === 'cancelled')
      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  }, [jobs]);

  // Tab counts
  const counts = {
    active: activeJobs.length,
    completed: completedJobs.length,
    failed: failedJobs.length,
    archived: archivedJobs.length,
  };

  // Initial fetch
  useEffect(() => {
    fetchJobs().finally(() => setIsLoading(false));
  }, [fetchJobs]);

  // Poll active jobs
  useEffect(() => {
    if (activeJobs.length === 0) return;

    const interval = setInterval(() => {
      activeJobs.forEach((job) => {
        refreshJob(job.id);
      });
    }, POLLING_INTERVALS.JOB_STATUS);

    return () => clearInterval(interval);
  }, [activeJobs, refreshJob]);

  // Auto-switch to completed tab when all active jobs finish
  useEffect(() => {
    if (activeTab === 'active' && activeJobs.length === 0 && completedJobs.length > 0 && !isLoading) {
      // Small delay to let user see the "all done" state
      const timer = setTimeout(() => {
        if (activeJobs.length === 0) {
          handleTabChange('completed');
        }
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [activeTab, activeJobs.length, completedJobs.length, isLoading, handleTabChange]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const currentJobs = activeTab === 'active' ? activeJobs : activeTab === 'completed' ? completedJobs : activeTab === 'failed' ? failedJobs : archivedJobs;

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">My Jobs</h1>
        <p className="text-gray-400">
          {jobs.length === 0
            ? 'No jobs yet. Start a new research from the dashboard.'
            : `${jobs.length} total job${jobs.length === 1 ? '' : 's'}`}
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6 p-1 bg-gray-900 rounded-xl border border-gray-800">
        <TabButton 
          active={activeTab === 'active'} 
          onClick={() => handleTabChange('active')}
          count={counts.active}
        >
          <span className="flex items-center gap-2">
            {counts.active > 0 && (
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            )}
            Active
          </span>
        </TabButton>
        <TabButton 
          active={activeTab === 'completed'} 
          onClick={() => handleTabChange('completed')}
          count={counts.completed}
        >
          Completed
        </TabButton>
        <TabButton
          active={activeTab === 'failed'}
          onClick={() => handleTabChange('failed')}
          count={counts.failed}
        >
          Failed
        </TabButton>
        <TabButton
          active={activeTab === 'archived'}
          onClick={() => handleTabChange('archived')}
          count={counts.archived}
        >
          Archived
        </TabButton>
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {/* Loading state for archived tab */}
          {activeTab === 'archived' && isLoadingArchived && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full" />
            </div>
          )}

          {/* Empty state */}
          {currentJobs.length === 0 && !(activeTab === 'archived' && isLoadingArchived) && (
            <div className="text-center py-16 bg-[#1a1a1a] rounded-xl border border-gray-800">
              <svg
                className="mx-auto h-12 w-12 text-gray-600 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                {activeTab === 'active' ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                  />
                ) : activeTab === 'completed' ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                ) : activeTab === 'archived' ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                )}
              </svg>
              <p className="text-gray-400 mb-4">
                {activeTab === 'active' && 'No active jobs in the queue'}
                {activeTab === 'completed' && 'No completed jobs yet'}
                {activeTab === 'failed' && 'No failed jobs'}
                {activeTab === 'archived' && 'No archived jobs'}
              </p>
              {activeTab === 'active' && (
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Start New Research
                </Link>
              )}
            </div>
          )}

          {/* Job lists */}
          {currentJobs.length > 0 && !(activeTab === 'archived' && isLoadingArchived) && (
            <div className="space-y-3">
              {activeTab === 'active' && activeJobs.map((job, idx) => (
                <ActiveJobCard key={job.id} job={job} position={idx + 1} />
              ))}

              {activeTab === 'completed' && completedJobs.map((job) => (
                <CompletedJobCard key={job.id} job={job} />
              ))}

              {activeTab === 'failed' && failedJobs.map((job) => (
                <FailedJobCard key={job.id} job={job} />
              ))}

              {activeTab === 'archived' && archivedJobs.map((job) => (
                <ArchivedJobCard key={job.id} job={job} onRecover={unarchiveJob} />
              ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* Link back to dashboard */}
      <div className="mt-8 text-center">
        <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-400 transition-colors">
          ← Back to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function QueuePage() {
  return (
    <ProtectedRoute>
      <Layout>
        <Head>
          <title>My Jobs | Research Agent</title>
        </Head>
        <JobsContent />
      </Layout>
    </ProtectedRoute>
  );
}
