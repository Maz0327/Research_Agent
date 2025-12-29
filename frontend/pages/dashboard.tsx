/**
 * Dashboard page showing job list and creation form.
 * Features dark mode design with modern UI/UX.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import JobCard from '../components/JobCard';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import { useJobsStore } from '../store/jobs';
import { POLLING_INTERVALS } from '../lib/constants';

const pipelines = [
  { value: 'quick', label: 'Quick', description: 'Fast research with basic coverage' },
  { value: 'full', label: 'Full', description: 'Comprehensive research with full coverage' },
  { value: 'breaking_news', label: 'Breaking News', description: 'Fast-turnaround current events' },
  { value: 'investigation', label: 'Investigation', description: 'Deep-dive investigative research' },
  { value: 'profile', label: 'Profile', description: 'Character-driven biographical research' },
  { value: 'controversy', label: 'Controversy', description: 'Balanced multi-perspective analysis' },
];

// Skeleton loader for jobs
function JobSkeleton() {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="h-5 w-3/4 rounded bg-gray-800" />
          <div className="mt-2 flex gap-2">
            <div className="h-4 w-20 rounded bg-gray-800" />
            <div className="h-4 w-24 rounded bg-gray-800" />
          </div>
        </div>
        <div className="h-6 w-20 rounded-full bg-gray-800" />
      </div>
    </div>
  );
}

function DashboardContent() {
  const [prompt, setPrompt] = useState('');
  const [pipeline, setPipeline] = useState('investigation');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const { jobs, isLoading, fetchJobs, createJob, refreshJob } = useJobsStore();
  const { user } = useAuth();

  // Fetch jobs on mount and when user changes
  useEffect(() => {
    if (user) {
      fetchJobs();
    }
  }, [fetchJobs, user]);

  // Debounced batch refresh for running jobs
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const batchRefreshJobs = useCallback((jobIds: string[]) => {
    // Clear any pending refresh
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
    // Debounce the batch refresh
    refreshTimeoutRef.current = setTimeout(() => {
      jobIds.forEach((id) => refreshJob(id));
    }, 100); // 100ms debounce to batch rapid updates
  }, [refreshJob]);

  // Polling for running jobs
  useEffect(() => {
    const runningJobs = jobs.filter((job) => job.status === 'running' || job.status === 'queued');
    if (runningJobs.length === 0) return;

    const interval = setInterval(() => {
      batchRefreshJobs(runningJobs.map((job) => job.id));
    }, POLLING_INTERVALS.JOB_STATUS);

    return () => {
      clearInterval(interval);
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [jobs, batchRefreshJobs]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsCreating(true);
    try {
      await createJob(prompt, pipeline);
      setPrompt('');
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create job:', error);
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleRefresh = () => {
    fetchJobs();
  };

  // Memoize filtered jobs to prevent unnecessary recalculations
  const filteredJobs = useMemo(() => {
    if (statusFilter === 'all') return jobs;
    return jobs.filter((job) => job.status === statusFilter);
  }, [jobs, statusFilter]);

  return (
    <Layout>
      <div className="mx-auto max-w-5xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p className="mt-2 text-gray-400">Create and manage your research jobs</p>
        </motion.div>

        {/* Create Job Form */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 rounded-xl border border-gray-800 bg-gray-900 p-6 shadow-lg"
        >
          <h2 className="mb-4 text-lg font-semibold text-gray-100">New Research Job</h2>
          <form onSubmit={handleCreateJob}>
            <div className="mb-4">
              <label htmlFor="prompt" className="mb-1.5 block text-sm font-medium text-gray-400">
                Research Topic
              </label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter your research topic or question..."
                rows={3}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                disabled={isCreating}
              />
            </div>

            <div className="mb-5">
              <label className="mb-2 block text-sm font-medium text-gray-400">
                Pipeline Mode
              </label>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Select pipeline mode">
                {pipelines.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    role="radio"
                    aria-checked={pipeline === p.value}
                    aria-label={`Select ${p.label} pipeline mode: ${p.description}`}
                    onClick={() => setPipeline(p.value)}
                    className={`rounded-lg border p-3 text-left transition-all duration-200 ${
                      pipeline === p.value
                        ? 'border-blue-500 bg-blue-900/30 ring-1 ring-blue-500'
                        : 'border-gray-700 bg-gray-800 hover:border-gray-600 hover:bg-gray-750'
                    }`}
                  >
                    <span className="block text-sm font-medium text-gray-200">
                      {p.label}
                    </span>
                    <span className="mt-0.5 block text-xs text-gray-500">
                      {p.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isCreating || !prompt.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
            >
              {isCreating ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Start Research
                </>
              )}
            </button>
          </form>
        </motion.div>

        {/* Jobs List */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-100">Your Jobs</h2>

            {/* Status Filter */}
            <div className="flex flex-wrap gap-2">
              {['all', 'running', 'completed', 'failed', 'cancelled'].map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
                    statusFilter === status
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <div className="space-y-4">
              <JobSkeleton />
              <JobSkeleton />
              <JobSkeleton />
            </div>
          ) : filteredJobs.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-xl border border-dashed border-gray-700 py-16 text-center"
            >
              <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-gray-800 p-4">
                <svg
                  className="h-8 w-8 text-gray-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-300">No jobs yet</h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your first research job above to get started.
              </p>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4"
            >
              {filteredJobs.map((job, index) => (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <JobCard job={job} onRefresh={handleRefresh} />
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
