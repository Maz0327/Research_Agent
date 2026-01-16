/**
 * Dashboard page showing job list and creation form.
 * Features dark mode design with modern UI/UX.
 */
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import JobCard from '../components/JobCard';
import { ProtectedRoute, useAuth } from '../components/AuthProvider';
import { useJobsStore, JobPreview, VideoAnalysisResponse, TextInputRequest, TextInputResponse, ScreenshotInputResponse } from '../store/jobs';
import { POLLING_INTERVALS, VALIDATION_LIMITS, PLATFORM_HINTS, SCREENSHOT_PLATFORM_HINTS } from '../lib/constants';

// Job creation modes
type JobMode = 'video' | 'topic' | 'content';

// Content input sub-modes
type ContentInputMode = 'text' | 'screenshot';

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
  // Job creation mode: 'video' (primary) or 'topic' (legacy)
  const [jobMode, setJobMode] = useState<JobMode>('video');

  // Video Analysis state (PRIMARY)
  const [videoUrls, setVideoUrls] = useState('');
  const [videoTitle, setVideoTitle] = useState('');
  const [geminiModel, setGeminiModel] = useState<'gemini-2.5-flash' | 'gemini-2.5-pro'>('gemini-2.5-flash');
  const [videoPreview, setVideoPreview] = useState<{
    estimatedCost: number;
    totalDuration: number;
    videoCount: number;
    warnings: string[];
  } | null>(null);
  const [isVideoSubmitting, setIsVideoSubmitting] = useState(false);

  // Content Input state (TEXT and SCREENSHOT modes)
  const [contentInputMode, setContentInputMode] = useState<ContentInputMode>('text');
  // Text input fields
  const [textTopic, setTextTopic] = useState('');
  const [textContent, setTextContent] = useState('');
  const [textSourceLabel, setTextSourceLabel] = useState('');
  const [textSourceUrl, setTextSourceUrl] = useState('');
  const [textAuthor, setTextAuthor] = useState('');
  const [textPubDate, setTextPubDate] = useState('');
  const [textContextNote, setTextContextNote] = useState('');
  const [textPlatformHint, setTextPlatformHint] = useState<TextInputRequest['platform_hint']>('article');
  const [isTextSubmitting, setIsTextSubmitting] = useState(false);
  const [textResult, setTextResult] = useState<TextInputResponse | null>(null);
  // Screenshot input fields
  const [screenshotTopic, setScreenshotTopic] = useState('');
  const [screenshotFile, setScreenshotFile] = useState<File | null>(null);
  const [screenshotPlatformHint, setScreenshotPlatformHint] = useState<string>('other');
  const [screenshotContextNote, setScreenshotContextNote] = useState('');
  const [isScreenshotSubmitting, setIsScreenshotSubmitting] = useState(false);
  const [screenshotResult, setScreenshotResult] = useState<ScreenshotInputResponse | null>(null);
  const [screenshotError, setScreenshotError] = useState<string | null>(null);

  // Topic Research state (LEGACY)
  const [prompt, setPrompt] = useState('');
  const [researchDepth, setResearchDepth] = useState('investigation');
  const [category, setCategory] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showPreview, setShowPreview] = useState(false);
  // Bulk delete confirmation
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [isBulkArchiving, setIsBulkArchiving] = useState(false);
  // Editable preview state
  const [editableSources, setEditableSources] = useState<string[]>([]);
  const [editableSubreddits, setEditableSubreddits] = useState<string[]>([]);
  const [newSubreddit, setNewSubreddit] = useState('');
  const {
    jobs, isLoading, preview, isPreviewLoading, fetchJobs, previewJob, createJob, createVideoAnalysisJob, createTextInputJob, createScreenshotInputJob, refreshJob, clearPreview,
    // Bulk selection
    isEditMode, selectedJobIds, bulkErrors, toggleEditMode, selectJob, deselectJob, selectAll, deselectAll, bulkDelete, bulkArchive, clearBulkErrors,
  } = useJobsStore();
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

  // Parse video URLs from textarea (one per line or comma-separated)
  const parseVideoUrls = (text: string): string[] => {
    return text
      .split(/[\n,]/)
      .map((url) => url.trim())
      .filter((url) => url.length > 0 && (url.includes('youtube.com') || url.includes('youtu.be')));
  };

  // Video Analysis submission
  const handleVideoAnalysisSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = parseVideoUrls(videoUrls);

    if (urls.length === 0) {
      return;
    }

    if (urls.length > 10) {
      alert('Maximum 10 videos per job. Please reduce the number of URLs.');
      return;
    }

    setIsVideoSubmitting(true);
    try {
      const result = await createVideoAnalysisJob(urls, videoTitle || undefined, geminiModel);
      // Show preview with cost info
      setVideoPreview({
        estimatedCost: result.estimated_cost,
        totalDuration: result.total_duration_minutes,
        videoCount: result.video_count,
        warnings: result.warnings || [],
      });
      // Clear form
      setVideoUrls('');
      setVideoTitle('');
      setVideoPreview(null);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create video analysis job:', error);
      }
    } finally {
      setIsVideoSubmitting(false);
    }
  };

  // Count valid URLs for display
  const validUrlCount = parseVideoUrls(videoUrls).length;

  // Text Input submission
  const handleTextInputSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textContent.trim() || textContent.length < VALIDATION_LIMITS.MIN_TEXT_CONTENT_LENGTH) {
      return;
    }
    if (!textSourceLabel.trim()) {
      return;
    }

    setIsTextSubmitting(true);
    setTextResult(null);
    try {
      const request: TextInputRequest = {
        topic: textTopic.trim() || textSourceLabel.trim(),
        content: textContent,
        source_label: textSourceLabel,
        source_url: textSourceUrl || undefined,
        author: textAuthor || undefined,
        publication_date: textPubDate || undefined,
        context_note: textContextNote || undefined,
        platform_hint: textPlatformHint,
      };
      const result = await createTextInputJob(request);
      setTextResult(result);
      // Clear form on success
      setTextTopic('');
      setTextContent('');
      setTextSourceLabel('');
      setTextSourceUrl('');
      setTextAuthor('');
      setTextPubDate('');
      setTextContextNote('');
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create text input job:', error);
      }
    } finally {
      setIsTextSubmitting(false);
    }
  };

  // Screenshot file change handler
  const handleScreenshotChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setScreenshotError(null);
    if (file) {
      // Validate file size
      if (file.size > VALIDATION_LIMITS.MAX_SCREENSHOT_SIZE) {
        setScreenshotError('File size exceeds 10MB limit');
        return;
      }
      // Validate file type
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
        setScreenshotError('Only PNG, JPG, and WEBP images are supported');
        return;
      }
      setScreenshotFile(file);
    }
  };

  // Screenshot Input submission
  const handleScreenshotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!screenshotFile || !screenshotTopic.trim()) {
      return;
    }

    setIsScreenshotSubmitting(true);
    setScreenshotResult(null);
    setScreenshotError(null);
    try {
      const result = await createScreenshotInputJob(
        screenshotFile,
        screenshotTopic,
        screenshotPlatformHint,
        screenshotContextNote || undefined
      );
      setScreenshotResult(result);
      // Clear form on success
      setScreenshotTopic('');
      setScreenshotFile(null);
      setScreenshotContextNote('');
      // Reset file input
      const fileInput = document.getElementById('screenshotFile') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to create screenshot input job:', error);
      }
      setScreenshotError(error instanceof Error ? error.message : 'Failed to upload screenshot');
    } finally {
      setIsScreenshotSubmitting(false);
    }
  };

  // Memoize filtered jobs to prevent unnecessary recalculations
  // Group related statuses for filtering (completed includes completed_with_warnings, failed includes failed_insufficient)
  const filteredJobs = useMemo(() => {
    if (statusFilter === 'all') return jobs;
    return jobs.filter((job) => {
      if (statusFilter === 'completed') {
        return job.status === 'completed' || job.status === 'completed_with_warnings';
      }
      if (statusFilter === 'failed') {
        return job.status === 'failed' || job.status === 'failed_insufficient';
      }
      return job.status === statusFilter;
    });
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
          {/* Mode Toggle */}
          <div className="mb-6 flex items-center gap-4 flex-wrap">
            <h2 className="text-lg font-semibold text-gray-100">New Job</h2>
            <div className="flex rounded-lg bg-gray-800 p-1">
              <button
                type="button"
                onClick={() => setJobMode('video')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                  jobMode === 'video'
                    ? 'bg-purple-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                🎬 Video Analysis
              </button>
              <button
                type="button"
                onClick={() => setJobMode('content')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                  jobMode === 'content'
                    ? 'bg-green-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                📝 Content Input
              </button>
              <button
                type="button"
                onClick={() => setJobMode('topic')}
                className={`px-4 py-1.5 text-sm font-medium rounded-md transition-all ${
                  jobMode === 'topic'
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-300'
                }`}
              >
                📚 Topic Research
              </button>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {/* VIDEO ANALYSIS MODE (PRIMARY) */}
            {jobMode === 'video' ? (
              <motion.form
                key="video-form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onSubmit={handleVideoAnalysisSubmit}
              >
                <div className="mb-4">
                  <label htmlFor="videoUrls" className="mb-1.5 block text-sm font-medium text-gray-400">
                    YouTube Video URLs
                    {validUrlCount > 0 && (
                      <span className="ml-2 text-purple-400">({validUrlCount} video{validUrlCount !== 1 ? 's' : ''})</span>
                    )}
                  </label>
                  <textarea
                    id="videoUrls"
                    value={videoUrls}
                    onChange={(e) => setVideoUrls(e.target.value)}
                    placeholder={`Paste YouTube URLs (one per line)\n\nhttps://youtube.com/watch?v=...\nhttps://youtu.be/...`}
                    rows={5}
                    className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                    disabled={isVideoSubmitting}
                  />
                  <p className="mt-2 text-xs text-gray-500">
                    <strong>Max 10 videos.</strong> AI will extract key moments, quotes, and timestamps from each video.
                  </p>
                </div>

                {/* Optional title and model selector */}
                <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="videoTitle" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Project Title (optional)
                    </label>
                    <input
                      type="text"
                      id="videoTitle"
                      value={videoTitle}
                      onChange={(e) => setVideoTitle(e.target.value)}
                      placeholder="e.g., Joe Rogan UFO Episodes"
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      disabled={isVideoSubmitting}
                    />
                  </div>
                  <div>
                    <label htmlFor="geminiModel" className="mb-1.5 block text-sm font-medium text-gray-400">
                      Analysis Model
                    </label>
                    <select
                      id="geminiModel"
                      value={geminiModel}
                      onChange={(e) => setGeminiModel(e.target.value as 'gemini-2.5-flash' | 'gemini-2.5-pro')}
                      disabled={isVideoSubmitting}
                      className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 cursor-pointer"
                    >
                      <option value="gemini-2.5-flash">Flash - Faster & Cheaper (~$0.15/hr)</option>
                      <option value="gemini-2.5-pro">Pro - More Accurate (~$1.15/hr)</option>
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isVideoSubmitting || validUrlCount === 0}
                  className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-3 font-medium text-white shadow-lg shadow-purple-500/20 transition-all duration-200 hover:from-purple-500 hover:to-purple-400 hover:shadow-purple-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                >
                  {isVideoSubmitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Analyze {validUrlCount > 0 ? `${validUrlCount} Video${validUrlCount !== 1 ? 's' : ''}` : 'Videos'}
                    </>
                  )}
                </button>
              </motion.form>
            ) : jobMode === 'content' ? (
              /* CONTENT INPUT MODE - Text and Screenshot */
              <motion.div
                key="content-form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {/* Sub-mode toggle for text vs screenshot */}
                <div className="mb-4 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setContentInputMode('text')}
                    className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all ${
                      contentInputMode === 'text'
                        ? 'bg-green-600/30 border border-green-500/50 text-green-300'
                        : 'bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-300'
                    }`}
                  >
                    📄 Paste Text
                  </button>
                  <button
                    type="button"
                    onClick={() => setContentInputMode('screenshot')}
                    className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all ${
                      contentInputMode === 'screenshot'
                        ? 'bg-green-600/30 border border-green-500/50 text-green-300'
                        : 'bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-300'
                    }`}
                  >
                    📷 Upload Screenshot
                  </button>
                </div>

                <AnimatePresence mode="wait">
                  {contentInputMode === 'text' ? (
                    /* TEXT INPUT FORM */
                    <motion.form
                      key="text-input-form"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      onSubmit={handleTextInputSubmit}
                    >
                      {/* Success message */}
                      {textResult && (
                        <div className="mb-4 rounded-lg border border-green-700/50 bg-green-900/20 p-3">
                          <p className="text-sm text-green-300">
                            ✓ Text submitted ({textResult.word_count} words). Job created.
                          </p>
                          {textResult.warnings?.length > 0 && (
                            <p className="mt-1 text-xs text-yellow-400">
                              ⚠ {textResult.warnings.join(', ')}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Source Label (required) */}
                      <div className="mb-4">
                        <label htmlFor="textSourceLabel" className="mb-1.5 block text-sm font-medium text-gray-400">
                          Source Label <span className="text-red-400">*</span>
                        </label>
                        <input
                          type="text"
                          id="textSourceLabel"
                          value={textSourceLabel}
                          onChange={(e) => setTextSourceLabel(e.target.value)}
                          placeholder="e.g., WSJ Article, Internal Email, Research Paper"
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                          disabled={isTextSubmitting}
                          required
                        />
                      </div>

                      {/* Content textarea (required) */}
                      <div className="mb-4">
                        <label htmlFor="textContent" className="mb-1.5 block text-sm font-medium text-gray-400">
                          Content <span className="text-red-400">*</span>
                          <span className="ml-2 text-gray-500">
                            ({textContent.length.toLocaleString()} / {VALIDATION_LIMITS.MAX_TEXT_CONTENT_LENGTH.toLocaleString()} chars)
                          </span>
                        </label>
                        <textarea
                          id="textContent"
                          value={textContent}
                          onChange={(e) => setTextContent(e.target.value)}
                          placeholder="Paste the article content, email, forum post, or other text here..."
                          rows={8}
                          maxLength={VALIDATION_LIMITS.MAX_TEXT_CONTENT_LENGTH}
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 font-mono text-sm transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                          disabled={isTextSubmitting}
                          required
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Minimum 50 characters. Quotes will be extracted with accuracy warnings.
                        </p>
                      </div>

                      {/* Source Metadata (optional but improves quote confidence) */}
                      <div className="mb-4 rounded-lg border border-gray-700 bg-gray-800/50 p-4">
                        <h4 className="mb-3 text-sm font-medium text-gray-300">
                          Source Metadata <span className="text-gray-500">(optional - reduces quote warnings)</span>
                        </h4>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div>
                            <label htmlFor="textSourceUrl" className="mb-1 block text-xs text-gray-500">
                              Source URL
                            </label>
                            <input
                              type="url"
                              id="textSourceUrl"
                              value={textSourceUrl}
                              onChange={(e) => setTextSourceUrl(e.target.value)}
                              placeholder="https://..."
                              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none"
                              disabled={isTextSubmitting}
                            />
                          </div>
                          <div>
                            <label htmlFor="textAuthor" className="mb-1 block text-xs text-gray-500">
                              Author
                            </label>
                            <input
                              type="text"
                              id="textAuthor"
                              value={textAuthor}
                              onChange={(e) => setTextAuthor(e.target.value)}
                              placeholder="Author name"
                              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none"
                              disabled={isTextSubmitting}
                            />
                          </div>
                          <div>
                            <label htmlFor="textPubDate" className="mb-1 block text-xs text-gray-500">
                              Publication Date
                            </label>
                            <input
                              type="text"
                              id="textPubDate"
                              value={textPubDate}
                              onChange={(e) => setTextPubDate(e.target.value)}
                              placeholder="e.g., January 2026"
                              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none"
                              disabled={isTextSubmitting}
                            />
                          </div>
                          <div>
                            <label htmlFor="textPlatformHint" className="mb-1 block text-xs text-gray-500">
                              Platform
                            </label>
                            <select
                              id="textPlatformHint"
                              value={textPlatformHint}
                              onChange={(e) => setTextPlatformHint(e.target.value as TextInputRequest['platform_hint'])}
                              disabled={isTextSubmitting}
                              className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 transition focus:border-green-500 focus:outline-none cursor-pointer"
                            >
                              {PLATFORM_HINTS.map((p) => (
                                <option key={p.value} value={p.value}>
                                  {p.icon} {p.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                        <div className="mt-3">
                          <label htmlFor="textContextNote" className="mb-1 block text-xs text-gray-500">
                            Context Note
                          </label>
                          <input
                            type="text"
                            id="textContextNote"
                            value={textContextNote}
                            onChange={(e) => setTextContextNote(e.target.value)}
                            placeholder="e.g., From paywall, may be incomplete"
                            className="w-full rounded-lg border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none"
                            disabled={isTextSubmitting}
                          />
                        </div>
                      </div>

                      {/* Research Topic (optional) */}
                      <div className="mb-5">
                        <label htmlFor="textTopic" className="mb-1.5 block text-sm font-medium text-gray-400">
                          Research Topic <span className="text-gray-500">(optional - defaults to source label)</span>
                        </label>
                        <input
                          type="text"
                          id="textTopic"
                          value={textTopic}
                          onChange={(e) => setTextTopic(e.target.value)}
                          placeholder="What are you researching?"
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                          disabled={isTextSubmitting}
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={isTextSubmitting || textContent.length < VALIDATION_LIMITS.MIN_TEXT_CONTENT_LENGTH || !textSourceLabel.trim()}
                        className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-green-500 px-6 py-3 font-medium text-white shadow-lg shadow-green-500/20 transition-all duration-200 hover:from-green-500 hover:to-green-400 hover:shadow-green-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                      >
                        {isTextSubmitting ? (
                          <>
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Processing...
                          </>
                        ) : (
                          <>
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Analyze Text
                          </>
                        )}
                      </button>
                    </motion.form>
                  ) : (
                    /* SCREENSHOT INPUT FORM */
                    <motion.form
                      key="screenshot-input-form"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      onSubmit={handleScreenshotSubmit}
                    >
                      {/* Success message */}
                      {screenshotResult && (
                        <div className="mb-4 rounded-lg border border-green-700/50 bg-green-900/20 p-3">
                          <p className="text-sm text-green-300">
                            ✓ Screenshot processed ({screenshotResult.ocr_word_count} words extracted).
                            {screenshotResult.platform_detected && ` Detected: ${screenshotResult.platform_detected}`}
                          </p>
                          {screenshotResult.warnings?.length > 0 && (
                            <p className="mt-1 text-xs text-yellow-400">
                              ⚠ {screenshotResult.warnings.join(', ')}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Error message */}
                      {screenshotError && (
                        <div className="mb-4 rounded-lg border border-red-700/50 bg-red-900/20 p-3">
                          <p className="text-sm text-red-300">✗ {screenshotError}</p>
                        </div>
                      )}

                      {/* File upload */}
                      <div className="mb-4">
                        <label htmlFor="screenshotFile" className="mb-1.5 block text-sm font-medium text-gray-400">
                          Screenshot <span className="text-red-400">*</span>
                        </label>
                        <div className="relative">
                          <input
                            type="file"
                            id="screenshotFile"
                            accept="image/png,image/jpeg,image/webp"
                            onChange={handleScreenshotChange}
                            className="hidden"
                            disabled={isScreenshotSubmitting}
                          />
                          <label
                            htmlFor="screenshotFile"
                            className={`flex items-center justify-center gap-2 w-full rounded-lg border-2 border-dashed py-8 px-4 text-center cursor-pointer transition ${
                              screenshotFile
                                ? 'border-green-500/50 bg-green-900/10 text-green-300'
                                : 'border-gray-600 bg-gray-800 text-gray-400 hover:border-gray-500 hover:text-gray-300'
                            }`}
                          >
                            {screenshotFile ? (
                              <>
                                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>{screenshotFile.name} ({(screenshotFile.size / 1024).toFixed(1)} KB)</span>
                              </>
                            ) : (
                              <>
                                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                <span>Click to upload (PNG, JPG, WEBP - max 10MB)</span>
                              </>
                            )}
                          </label>
                        </div>
                      </div>

                      {/* Research Topic (required for screenshots) */}
                      <div className="mb-4">
                        <label htmlFor="screenshotTopic" className="mb-1.5 block text-sm font-medium text-gray-400">
                          Research Topic <span className="text-red-400">*</span>
                        </label>
                        <input
                          type="text"
                          id="screenshotTopic"
                          value={screenshotTopic}
                          onChange={(e) => setScreenshotTopic(e.target.value)}
                          placeholder="What topic does this screenshot relate to?"
                          className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                          disabled={isScreenshotSubmitting}
                          required
                        />
                      </div>

                      {/* Platform hint and context */}
                      <div className="mb-5 grid gap-4 sm:grid-cols-2">
                        <div>
                          <label htmlFor="screenshotPlatformHint" className="mb-1.5 block text-sm font-medium text-gray-400">
                            Platform
                          </label>
                          <select
                            id="screenshotPlatformHint"
                            value={screenshotPlatformHint}
                            onChange={(e) => setScreenshotPlatformHint(e.target.value)}
                            disabled={isScreenshotSubmitting}
                            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500 cursor-pointer"
                          >
                            {SCREENSHOT_PLATFORM_HINTS.map((p) => (
                              <option key={p.value} value={p.value}>
                                {p.icon} {p.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label htmlFor="screenshotContextNote" className="mb-1.5 block text-sm font-medium text-gray-400">
                            Context Note <span className="text-gray-500">(optional)</span>
                          </label>
                          <input
                            type="text"
                            id="screenshotContextNote"
                            value={screenshotContextNote}
                            onChange={(e) => setScreenshotContextNote(e.target.value)}
                            placeholder="e.g., Thread about layoffs"
                            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-gray-100 placeholder-gray-500 transition focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                            disabled={isScreenshotSubmitting}
                          />
                        </div>
                      </div>

                      <div className="mb-4 rounded-lg border border-yellow-700/30 bg-yellow-900/10 p-3">
                        <p className="text-xs text-yellow-300/80">
                          ⚠ Screenshots are processed via OCR. Quotes extracted may contain errors and cannot be verified.
                          User should confirm quote accuracy.
                        </p>
                      </div>

                      <button
                        type="submit"
                        disabled={isScreenshotSubmitting || !screenshotFile || !screenshotTopic.trim()}
                        className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-green-600 to-green-500 px-6 py-3 font-medium text-white shadow-lg shadow-green-500/20 transition-all duration-200 hover:from-green-500 hover:to-green-400 hover:shadow-green-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
                      >
                        {isScreenshotSubmitting ? (
                          <>
                            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Processing OCR...
                          </>
                        ) : (
                          <>
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            Analyze Screenshot
                          </>
                        )}
                      </button>
                    </motion.form>
                  )}
                </AnimatePresence>
              </motion.div>
            ) : !showPreview ? (
              /* TOPIC RESEARCH MODE (LEGACY) - Input Form */
              <motion.form
                key="topic-form"
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
          {/* Bulk errors display */}
          {bulkErrors.length > 0 && (
            <div className="mb-4 rounded-lg border border-red-800 bg-red-900/30 p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-red-400">Some jobs failed:</p>
                <button
                  onClick={clearBulkErrors}
                  className="text-red-400 hover:text-red-300 text-sm"
                >
                  Dismiss
                </button>
              </div>
              {bulkErrors.map(({ jobId, error }) => (
                <p key={jobId} className="text-xs text-red-300">{jobId.slice(0, 8)}...: {error}</p>
              ))}
            </div>
          )}

          <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-100">Your Jobs</h2>
              {/* Edit Mode Toggle */}
              <button
                onClick={toggleEditMode}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ${
                  isEditMode
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-300'
                }`}
              >
                {isEditMode ? 'Done' : 'Select'}
              </button>
            </div>

            {/* Edit Mode Controls */}
            {isEditMode ? (
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={selectedJobIds.size > 0 ? deselectAll : selectAll}
                  className="rounded-lg bg-gray-800 px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-700"
                >
                  {selectedJobIds.size > 0 ? 'Deselect All' : 'Select All'}
                </button>
                <span className="text-sm text-gray-500">{selectedJobIds.size} selected</span>
                <button
                  onClick={async () => {
                    if (selectedJobIds.size === 0) return;
                    setIsBulkArchiving(true);
                    await bulkArchive();
                    setIsBulkArchiving(false);
                  }}
                  disabled={selectedJobIds.size === 0 || isBulkArchiving}
                  className="rounded-lg border border-gray-600 px-3 py-1.5 text-sm text-gray-400 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isBulkArchiving ? 'Archiving...' : 'Archive'}
                </button>
                <button
                  onClick={() => setShowBulkDeleteConfirm(true)}
                  disabled={selectedJobIds.size === 0}
                  className="rounded-lg border border-red-700 px-3 py-1.5 text-sm text-red-400 hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Delete
                </button>
              </div>
            ) : (
              /* Status Filter - only show when not in edit mode */
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
            )}
          </div>

          {/* Bulk Delete Confirmation Modal */}
          {showBulkDeleteConfirm && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="rounded-lg border border-gray-700 bg-gray-900 p-6 max-w-sm shadow-xl">
                <h3 className="text-lg font-medium text-gray-100 mb-2">Delete {selectedJobIds.size} jobs?</h3>
                <p className="text-sm text-gray-400 mb-4">This action cannot be undone.</p>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setShowBulkDeleteConfirm(false)}
                    className="rounded-lg px-4 py-2 text-gray-400 hover:text-gray-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      setIsBulkDeleting(true);
                      await bulkDelete();
                      setIsBulkDeleting(false);
                      setShowBulkDeleteConfirm(false);
                    }}
                    disabled={isBulkDeleting}
                    className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-500 disabled:opacity-50"
                  >
                    {isBulkDeleting ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            </div>
          )}

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
                  <JobCard
                    job={job}
                    onRefresh={handleRefresh}
                    isEditMode={isEditMode}
                    isSelected={selectedJobIds.has(job.id)}
                    onToggleSelect={() => {
                      if (selectedJobIds.has(job.id)) {
                        deselectJob(job.id);
                      } else {
                        selectJob(job.id);
                      }
                    }}
                  />
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
