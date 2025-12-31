/**
 * Dashboard page showing job list and creation form.
 * Features dark mode design with modern UI/UX.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import JobCard from '../components/JobCard';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import { useJobsStore, JobPreview } from '../store/jobs';
import { POLLING_INTERVALS } from '../lib/constants';

// Research depth options (mode)
const researchDepths = [
  { value: 'quick', label: 'Quick Brief', description: 'Fast, surface-level coverage', example: 'What is quantum computing?' },
  { value: 'breaking_news', label: 'Breaking News', description: 'Recent events, fast turnaround', example: 'OpenAI leadership changes December 2024' },
  { value: 'full', label: 'Standard Research', description: 'Balanced depth and coverage', example: 'Electric vehicle market trends 2024' },
  { value: 'investigation', label: 'Deep Investigation', description: 'Thorough verification, multiple sources', example: 'FTX collapse timeline and key players' },
  { value: 'profile', label: 'Entity Profile', description: 'Single person/company focus', example: 'Elon Musk business ventures and controversies' },
];

// Category options (niche) - affects sources, subreddits, search queries
const categories = [
  { value: '', label: 'Auto-detect', description: 'AI determines best category' },
  { value: 'pop_culture', label: 'Entertainment & Pop Culture', description: 'TV, movies, celebrities, fan theories' },
  { value: 'political', label: 'Politics & Policy', description: 'Government, elections, legislation' },
  { value: 'true_crime', label: 'True Crime & Legal', description: 'Cases, investigations, court proceedings' },
  { value: 'mysteries', label: 'Mysteries & Conspiracies', description: 'Evidence analysis, theories, debunking' },
  { value: 'downfalls', label: 'Scandals & Downfalls', description: 'Drama, public reactions, timelines' },
  { value: 'controversy', label: 'Controversy', description: 'Multiple perspectives, balanced views' },
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

// Available source types
const availableSourceTypes = ['web', 'news', 'youtube', 'reddit'];

function DashboardContent() {
  const [prompt, setPrompt] = useState('');
  const [researchDepth, setResearchDepth] = useState('investigation');
  const [category, setCategory] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showPreview, setShowPreview] = useState(false);
  // Editable preview state
  const [editableSources, setEditableSources] = useState<string[]>([]);
  const [editableSubreddits, setEditableSubreddits] = useState<string[]>([]);
  const [newSubreddit, setNewSubreddit] = useState('');
  const { jobs, isLoading, preview, isPreviewLoading, fetchJobs, previewJob, createJob, refreshJob, clearPreview } = useJobsStore();
  const { user } = useAuth();

  // Get current depth config for placeholder example
  const currentDepth = researchDepths.find(d => d.value === researchDepth) || researchDepths[3];

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

  // Step 1: Preview the job before creating
  const handlePreviewJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    try {
      const result = await previewJob(prompt, researchDepth, category || undefined);
      // Initialize editable state from preview
      setEditableSources(result.source_types || ['web', 'news', 'youtube', 'reddit']);
      setEditableSubreddits(result.subreddits || []);
      setNewSubreddit('');
      setShowPreview(true);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to preview job:', error);
      }
    }
  };

  // Toggle a source type
  const toggleSource = (source: string) => {
    setEditableSources(prev =>
      prev.includes(source)
        ? prev.filter(s => s !== source)
        : [...prev, source]
    );
  };

  // Add a subreddit
  const addSubreddit = () => {
    const cleaned = newSubreddit.trim().toLowerCase().replace(/^r\//, '');
    if (cleaned && !editableSubreddits.includes(cleaned)) {
      setEditableSubreddits(prev => [...prev, cleaned]);
      setNewSubreddit('');
    }
  };

  // Remove a subreddit
  const removeSubreddit = (sub: string) => {
    setEditableSubreddits(prev => prev.filter(s => s !== sub));
  };

  // Step 2: Confirm and create the job
  const handleConfirmJob = async () => {
    setIsCreating(true);
    try {
      // Pass custom subreddits if user modified them
      const options = editableSubreddits.length > 0 ? { custom_subreddits: editableSubreddits } : undefined;
      await createJob(prompt, researchDepth, category || undefined, options);
      setPrompt('');
      setShowPreview(false);
      clearPreview();
      setEditableSources([]);
      setEditableSubreddits([]);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create job:', error);
      }
    } finally {
      setIsCreating(false);
    }
  };

  // Cancel preview and go back to editing
  const handleCancelPreview = () => {
    setShowPreview(false);
    clearPreview();
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

          <AnimatePresence mode="wait">
            {!showPreview ? (
              /* Input Form */
              <motion.form
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handlePreviewJob}
              >
                <div className="mb-4">
                  <label htmlFor="prompt" className="mb-1.5 block text-sm font-medium text-gray-400">
                    Research Topic
                  </label>
                  <textarea
                    id="prompt"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder={`e.g., "${currentDepth.example}"`}
                    rows={3}
                    className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    disabled={isPreviewLoading}
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    <strong>Tips:</strong> Be specific with names, dates, and context. Include key entities (people, companies, events) for better results.
                  </p>
                </div>

                {/* Two dropdown selectors for Research Depth and Category */}
                <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {/* Research Depth dropdown */}
                  <div>
                    <label htmlFor="researchDepth" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Research Depth
                    </label>
                    <select
                      id="researchDepth"
                      value={researchDepth}
                      onChange={(e) => setResearchDepth(e.target.value)}
                      disabled={isPreviewLoading}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                    >
                      {researchDepths.map((depth) => (
                        <option key={depth.value} value={depth.value}>
                          {depth.label} - {depth.description}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Category dropdown */}
                  <div>
                    <label htmlFor="category" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Category
                    </label>
                    <select
                      id="category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      disabled={isPreviewLoading}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
                    >
                      {categories.map((cat) => (
                        <option key={cat.value} value={cat.value}>
                          {cat.label}{cat.description ? ` - ${cat.description}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isPreviewLoading || !prompt.trim()}
                  className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-3 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                >
                  {isPreviewLoading ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Preview Research Plan
                    </>
                  )}
                </button>
              </motion.form>
            ) : (
              /* Preview Confirmation Card */
              <motion.div
                key="preview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-4"
              >
                <div className="rounded-lg border border-blue-800/50 bg-blue-900/20 p-4">
                  <h3 className="mb-3 text-sm font-semibold text-blue-400 uppercase tracking-wide">
                    Research Plan Preview
                  </h3>

                  {preview?.is_ambiguous ? (
                    /* Ambiguous topic - show interpretations */
                    <div className="space-y-3">
                      <p className="text-sm text-gray-300">
                        This topic could mean different things. Please select which one you meant:
                      </p>
                      <div className="space-y-2">
                        {preview.interpretations?.map((interp, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setPrompt(interp.topic);
                              setShowPreview(false);
                              clearPreview();
                            }}
                            className="w-full text-left rounded-lg border border-gray-700 bg-gray-800 p-3 hover:border-blue-500 hover:bg-gray-750 transition"
                          >
                            <div className="font-medium text-gray-100">{interp.label}</div>
                            <div className="text-sm text-gray-400">{interp.description}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    /* Clear topic - show editable research plan */
                    <div className="space-y-4">
                      {/* Topic and Mode info */}
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <span className="text-xs text-gray-500 uppercase">Topic</span>
                          <p className="text-gray-100">{preview?.interpreted_topic || prompt}</p>
                        </div>
                        <div>
                          <span className="text-xs text-gray-500 uppercase">Mode</span>
                          <p className="text-gray-100 capitalize">{preview?.mode?.replace('_', ' ') || researchDepth}</p>
                        </div>
                        {preview?.niche && (
                          <div>
                            <span className="text-xs text-gray-500 uppercase">Category</span>
                            <p className="text-gray-100 capitalize">{preview.niche.replace('_', ' ')}</p>
                          </div>
                        )}
                      </div>

                      {/* Editable source types */}
                      <div>
                        <span className="text-xs text-gray-500 uppercase mb-2 block">Sources (click to toggle)</span>
                        <div className="flex flex-wrap gap-2">
                          {availableSourceTypes.map((type) => {
                            const isEnabled = editableSources.includes(type);
                            return (
                              <button
                                key={type}
                                onClick={() => toggleSource(type)}
                                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                                  isEnabled
                                    ? 'bg-blue-600/30 border border-blue-500/50 text-blue-300'
                                    : 'bg-gray-800 border border-gray-700 text-gray-500 hover:text-gray-400'
                                }`}
                              >
                                {isEnabled ? (
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                  </svg>
                                ) : (
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                  </svg>
                                )}
                                {type}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Editable subreddits */}
                      <div>
                        <span className="text-xs text-gray-500 uppercase mb-2 block">Reddit Communities</span>
                        <div className="flex flex-wrap gap-2 mb-2">
                          {editableSubreddits.map((sub) => (
                            <span
                              key={sub}
                              className="inline-flex items-center gap-1 rounded-full bg-orange-900/30 border border-orange-700/50 pl-2.5 pr-1 py-1 text-xs text-orange-300"
                            >
                              r/{sub}
                              <button
                                onClick={() => removeSubreddit(sub)}
                                className="p-0.5 hover:bg-orange-800/50 rounded-full transition"
                                aria-label={`Remove r/${sub}`}
                              >
                                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </span>
                          ))}
                          {editableSubreddits.length === 0 && (
                            <span className="text-xs text-gray-500 italic">No subreddits selected</span>
                          )}
                        </div>
                        {/* Add subreddit input */}
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={newSubreddit}
                            onChange={(e) => setNewSubreddit(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSubreddit())}
                            placeholder="Add subreddit (e.g., FanTheories)"
                            className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:border-orange-500 focus:outline-none focus:ring-1 focus:ring-orange-500"
                          />
                          <button
                            onClick={addSubreddit}
                            disabled={!newSubreddit.trim()}
                            className="rounded-lg bg-orange-600/30 border border-orange-600/50 px-3 py-1.5 text-sm font-medium text-orange-300 hover:bg-orange-600/40 disabled:opacity-50 disabled:cursor-not-allowed transition"
                          >
                            Add
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action buttons */}
                {!preview?.is_ambiguous && (
                  <div className="flex gap-3">
                    <button
                      onClick={handleCancelPreview}
                      disabled={isCreating}
                      className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 font-medium text-gray-300 transition hover:bg-gray-700 disabled:opacity-50"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                      </svg>
                      Edit
                    </button>
                    <button
                      onClick={handleConfirmJob}
                      disabled={isCreating}
                      className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-green-500 px-6 py-2.5 font-medium text-white shadow-lg shadow-green-500/20 transition-all duration-200 hover:from-green-500 hover:to-green-400 disabled:opacity-50"
                    >
                      {isCreating ? (
                        <>
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Starting...
                        </>
                      ) : (
                        <>
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Start Research
                        </>
                      )}
                    </button>
                  </div>
                )}

                {preview?.is_ambiguous && (
                  <button
                    onClick={handleCancelPreview}
                    className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 px-4 py-2.5 font-medium text-gray-300 transition hover:bg-gray-700"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                    </svg>
                    Back to Edit
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
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
