/**
 * Zustand store for managing research jobs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

// Phase 3 types - import from job-card components
import type { ContentBlueprint } from '../components/job-card/ContentBlueprintView';
import type { GapAnalysis } from '../components/job-card/GapAnalysisView';
import type { ResearchStarter } from '../components/job-card/ResearchStarterView';

/**
 * Interpretation represents a possible meaning of an ambiguous topic.
 */
export interface Interpretation {
  /** Short label for the interpretation */
  label: string;
  /** Detailed description of what this interpretation means */
  description: string;
  /** Refined topic string for this interpretation */
  topic: string;
}

/**
 * JobPreview represents the interpreted plan before job creation.
 */
export interface JobPreview {
  /** Whether the topic is ambiguous and needs clarification */
  is_ambiguous: boolean;
  /** Possible interpretations if ambiguous */
  interpretations?: Interpretation[];
  /** How the AI interpreted the topic */
  interpreted_topic?: string;
  /** Research mode that will be used */
  mode?: string;
  /** Category/niche applied */
  niche?: string;
  /** Reddit communities to search */
  subreddits?: string[];
  /** Types of sources to collect */
  source_types?: string[];
}

/**
 * Clip from video analysis
 */
export interface Clip {
  clip_id: string;
  video_url: string;
  timestamp_start: string;
  timestamp_end: string;
  speaker: string;
  quote: string;
  quote_type: string;
  range_verified: boolean;
  quote_verified: boolean;
  verification_level: 'verified' | 'probable' | 'unverified';
}

/**
 * Quote from video analysis
 */
export interface Quote {
  quote_id: string;
  video_url: string;
  text: string;
  speaker: string;
  timestamp: string;
  quote_verified: boolean;
  match_score: number;
}

/**
 * Producer packet quality gate results
 */
export interface QualityGate {
  passes: boolean;
  failures: string[];
  clip_count: number;
  quote_count: number;
  verified_claim_count: number;
}

/**
 * Job artifacts including video analysis results
 */
export interface JobArtifacts {
  /** Google Drive folder URL containing research documents */
  drive_folder_url?: string;
  /** Array of individual document URLs */
  doc_urls?: string[];
  /** Video clips from Gemini extraction */
  clips?: Clip[];
  /** Quotes from Gemini extraction */
  quotes?: Quote[];
  /** Full producer packet data */
  producer_packet?: {
    title?: string;
    quality_gate?: QualityGate;
    extraction_cost?: number;
  };
  /** Whether producer packet passed quality gate */
  quality_gate_passed?: boolean;
  // Phase 3: Full Research Assistant Pipeline (Jan 2026)
  /** Content Blueprints - structure analysis per video */
  content_blueprints?: ContentBlueprint[];
  /** Gap Analysis - cross-video gaps, missing perspectives */
  gap_analysis?: GapAnalysis;
  /** Research Starter - actionable queries and content angles */
  research_starter?: ResearchStarter;
  // Semantic Pipeline Documents (Doc 0/1/2) - inline data (legacy)
  /** Doc 0: Source Ledger - what was analyzed */
  source_ledger?: {
    data: Record<string, unknown>;
    markdown?: string;
  };
  /** Doc 1: Jump-Start Directions - where to go next */
  jump_start?: {
    data: Record<string, unknown>;
    markdown?: string;
  };
  /** Doc 2: Semantic Brief - what sources reveal */
  semantic_brief?: {
    data: Record<string, unknown>;
    markdown?: string;
  };
  // Storage paths for new jobs (lazy loading)
  /** Storage path for Doc 0 (Source Ledger) */
  doc_0_path?: string;
  /** Storage path for Doc 1 (Jump-Start Directions) */
  doc_1_path?: string;
  /** Storage path for Doc 2 (Semantic Brief) */
  doc_2_path?: string;
  /** Storage path for Doc 3 (Producer Packet) */
  doc_3_path?: string;
  // Per-source extraction data
  /** Semantic extractions per source */
  semantic_extractions?: Record<string, unknown>[];
  // Booster Pipeline (Phase 7)
  /** Booster output for Doc 1 expansion */
  booster_output?: Record<string, unknown>;
  /** Booster markdown for Doc 1 */
  booster_expansion_md?: string;
  // Producer Packet markdown (Phase 8)
  /** Producer packet markdown output */
  producer_packet_md?: string;
  // Iteration Loop (Phase 9)
  /** Iteration bundles - each iteration produces its own doc set */
  iterations?: IterationBundle[];
}

/**
 * Iteration bundle - append-only artifact set per iteration
 */
export interface IterationBundle {
  iteration_id: string;
  index: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  error?: {
    message: string;
    stack?: string;
  };
  request: {
    mode: string;
    user_prompt: string;
    max_new_sources: number;
    angle?: string;
  };
  inputs?: {
    baseline_doc_0_path?: string;
    baseline_doc_1_path?: string;
    baseline_doc_2_path?: string;
    source_urls_added: string[];
  };
  outputs?: {
    doc_0_path?: string;
    doc_1_path?: string;
    doc_2_path?: string;
    doc_0_inline?: Record<string, unknown>;
    doc_1_inline?: Record<string, unknown>;
    doc_2_inline?: Record<string, unknown>;
  };
  metrics?: {
    llm_calls: number;
    tokens_in: number;
    tokens_out: number;
    wall_time_ms: number;
  };
}

/**
 * Job represents a research job with its status and artifacts.
 */
export interface Job {
  /** Unique job identifier (UUID) */
  id: string;
  /** Original research prompt from user */
  prompt: string;
  /** AI-generated short title for display */
  title?: string;
  /** Pipeline type (quick, full, breaking_news, investigation, profile, controversy, video_analysis) */
  pipeline: string;
  /** Current job status (main pipeline) */
  status: 'queued' | 'running' | 'completed' | 'completed_with_warnings' | 'failed' | 'failed_insufficient' | 'cancelled' | 'disambiguating';
  /** Current pipeline stage name */
  stage?: string;
  /** When current stage started (ISO timestamp for ETA calculation) */
  stage_started_at?: string;
  /** Detailed progress info (e.g., "Analyzing video 2/5") */
  pass_detail?: string;
  /** Job completion percentage (0-100) */
  progress_percent: number;
  /** Output artifacts from completed job */
  artifacts?: JobArtifacts;
  /** Error message if job failed */
  error?: string;
  /** Warning messages for completed_with_warnings status */
  warnings?: string[];
  /** Number of warnings (for quick preview) */
  warning_count?: number;
  /** Job creation timestamp (ISO format) */
  created_at: string;
  /** Possible interpretations when status is 'disambiguating' */
  interpretations?: Interpretation[];
  /** Booster execution status (separate from main job status) */
  booster_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** When booster started (ISO timestamp) */
  booster_started_at?: string;
  /** When booster completed/failed (ISO timestamp) */
  booster_completed_at?: string;
  /** Booster error message if failed */
  booster_error?: string;
  /** Booster progress percentage (0-100) */
  booster_progress_percent?: number;
  /** Producer packet execution status (separate from main job status) */
  producer_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** When producer packet started (ISO timestamp) */
  producer_started_at?: string;
  /** When producer packet completed/failed (ISO timestamp) */
  producer_completed_at?: string;
  /** Producer packet error message if failed */
  producer_error?: string;
  /** Producer packet progress percentage (0-100) */
  producer_progress_percent?: number;
  /** Current iteration status (separate from main job status) */
  iteration_status?: 'queued' | 'running' | 'completed' | 'failed' | null;
  /** Current iteration ID being processed (it_0001, ...) */
  iteration_id?: string;
  /** When current iteration started (ISO timestamp) */
  iteration_started_at?: string;
  /** When current iteration completed/failed (ISO timestamp) */
  iteration_completed_at?: string;
  /** Current iteration error message if failed */
  iteration_error?: string;
  /** Current iteration progress percentage (0-100) */
  iteration_progress_percent?: number;
}

/** Error from a bulk operation */
export interface BulkError {
  jobId: string;
  error: string;
}

/**
 * Video analysis job response
 */
export interface VideoAnalysisResponse {
  job_id: string;
  estimated_cost: number;
  total_duration_minutes: number;
  video_count: number;
  warnings?: string[];
}

/**
 * Text input job request - for user-pasted content
 */
export interface TextInputRequest {
  topic: string;
  content: string;
  source_label: string;
  source_url?: string;
  author?: string;
  publication_date?: string;
  context_note?: string;
  platform_hint?: 'reddit' | 'twitter' | 'forum' | 'email' | 'article' | 'other';
}

/**
 * Text input job response
 */
export interface TextInputResponse {
  job_id: string;
  word_count: number;
  confidence_ceiling: string;
  warnings: string[];
}

/**
 * Screenshot input job response
 */
export interface ScreenshotInputResponse {
  job_id: string;
  ocr_word_count: number;
  confidence_ceiling: string;
  platform_detected?: string;
  warnings: string[];
}

/**
 * Mixed text input for unified input
 */
export interface MixedTextInput {
  title: string;
  content: string;
  platform_hint?: string;
}

/**
 * Mixed screenshot input for unified input
 */
export interface MixedScreenshotInput {
  filename: string;
  base64: string;
  platform_hint?: string;
}

/**
 * Mixed-input job request (unified input panel)
 */
export interface MixedInputRequest {
  topic: string;
  video_urls?: string[];
  article_urls?: string[];
  text_inputs?: MixedTextInput[];
  screenshots?: MixedScreenshotInput[];
}

/**
 * Source accepted in mixed-input response
 */
export interface SourceAccepted {
  source_id: string;
  source_type: string;
  url?: string;
  title?: string;
}

/**
 * Mixed-input job response
 */
export interface MixedInputResponse {
  job_id: string;
  status: string;
  source_count: number;
  sources_accepted: SourceAccepted[];
  duplicates_removed: number;
  warnings?: string[];
}

/**
 * Booster trigger response
 */
export interface BoosterResponse {
  job_id: string;
  status: string;
  message: string;
}

/**
 * Producer packet trigger response
 */
export interface ProducerPacketResponse {
  job_id: string;
  status: string;
  message: string;
}

/**
 * Iteration request parameters
 */
export interface IterationRequest {
  /** Iteration mode: more_sources, deeper, different_angle, custom */
  mode: 'more_sources' | 'deeper' | 'different_angle' | 'custom';
  /** User prompt for iteration guidance */
  user_prompt?: string;
  /** Max new sources to find (0-10) */
  max_new_sources?: number;
  /** Specific angle to explore (for different_angle mode) */
  angle?: string;
}

/**
 * Iteration trigger response
 */
export interface IterationResponse {
  job_id: string;
  iteration_id: string;
  iteration_index: number;
  status: string;
  message: string;
}

interface JobsState {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  preview: JobPreview | null;
  isPreviewLoading: boolean;
  // Action loading states
  isRefreshing: boolean;
  actionInProgress: 'booster' | 'producer' | 'iteration' | 'cancel' | 'delete' | 'archive' | null;
  // Bulk selection state
  selectedJobIds: Set<string>;
  isEditMode: boolean;
  bulkErrors: BulkError[];
  // Methods
  fetchJobs: () => Promise<void>;
  previewJob: (prompt: string, pipeline: string, niche?: string) => Promise<JobPreview>;
  createJob: (prompt: string, pipeline: string, niche?: string, options?: { custom_subreddits?: string[] }) => Promise<string>;
  createVideoAnalysisJob: (videoUrls: string[], title?: string, model?: 'gemini-2.5-flash' | 'gemini-2.5-pro') => Promise<VideoAnalysisResponse>;
  createTextInputJob: (request: TextInputRequest) => Promise<TextInputResponse>;
  createScreenshotInputJob: (file: File, topic: string, platformHint?: string, contextNote?: string) => Promise<ScreenshotInputResponse>;
  createMixedInputJob: (request: MixedInputRequest) => Promise<MixedInputResponse>;
  triggerBooster: (jobId: string) => Promise<BoosterResponse>;
  triggerProducerPacket: (jobId: string) => Promise<ProducerPacketResponse>;
  triggerIteration: (jobId: string, request: IterationRequest) => Promise<IterationResponse>;
  refreshJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  archiveJob: (jobId: string) => Promise<void>;
  selectInterpretation: (jobId: string, indices: number[] | 'all') => Promise<void>;
  clearPreview: () => void;
  clearJobs: () => void;
  // Bulk selection methods
  toggleEditMode: () => void;
  selectJob: (jobId: string) => void;
  deselectJob: (jobId: string) => void;
  selectAll: () => void;
  deselectAll: () => void;
  bulkDelete: () => Promise<void>;
  bulkArchive: () => Promise<void>;
  clearBulkErrors: () => void;
}

export const useJobsStore = create<JobsState>((set, get) => ({
  jobs: [],
  isLoading: false,
  error: null,
  preview: null,
  isPreviewLoading: false,
  // Action loading states
  isRefreshing: false,
  actionInProgress: null,
  // Bulk selection initial state
  selectedJobIds: new Set<string>(),
  isEditMode: false,
  bulkErrors: [],

  fetchJobs: async () => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();

      // If no token, user is not authenticated - don't fetch
      if (!token) {
        set({ jobs: [], isLoading: false });
        return;
      }

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      const response = await fetch(`${API_URL}/jobs`, { headers });

      if (!response.ok) {
        // If 401, clear jobs and notify user to re-login
        if (response.status === 401) {
          set({ jobs: [], isLoading: false, error: 'Session expired. Please log in again.' });
          return;
        }
        throw new Error('Failed to fetch jobs');
      }

      let data;
      try {
        data = await response.json();
      } catch {
        throw new Error('Invalid response from server');
      }
      set({ jobs: data.jobs || [], isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch jobs',
        isLoading: false,
      });
    }
  },

  previewJob: async (prompt: string, pipeline: string, niche?: string) => {
    set({ isPreviewLoading: true, error: null, preview: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: Record<string, string> = { prompt, pipeline };
      if (niche) {
        body.niche = niche;
      }

      const response = await fetch(`${API_URL}/jobs/preview`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to preview job');
      }

      const preview: JobPreview = await response.json();
      set({ preview, isPreviewLoading: false });
      return preview;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to preview job',
        isPreviewLoading: false,
      });
      throw error;
    }
  },

  clearPreview: () => {
    set({ preview: null, error: null });
  },

  createJob: async (prompt: string, pipeline: string, niche?: string, options?: { custom_subreddits?: string[] }) => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Build request body
      const body: Record<string, unknown> = { prompt, pipeline };
      if (niche) {
        body.niche = niche;
      }
      if (options?.custom_subreddits && options.custom_subreddits.length > 0) {
        body.options = { custom_subreddits: options.custom_subreddits };
      }

      const response = await fetch(`${API_URL}/jobs`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('Failed to create job');
      }

      const data = await response.json();
      const jobId = data.job_id;

      // Add job to local state
      const newJob: Job = {
        id: jobId,
        prompt,
        pipeline,
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        isLoading: false,
      }));

      return jobId;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create job',
        isLoading: false,
      });
      throw error;
    }
  },

  createVideoAnalysisJob: async (
    videoUrls: string[],
    title?: string,
    model: 'gemini-2.5-flash' | 'gemini-2.5-pro' = 'gemini-2.5-flash'
  ): Promise<VideoAnalysisResponse> => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: Record<string, unknown> = {
        video_urls: videoUrls,
        model,
      };
      if (title) {
        body.title = title;
      }

      const response = await fetch(`${API_URL}/jobs/video-analysis`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create video analysis job');
      }

      const data: VideoAnalysisResponse = await response.json();

      // Add job to local state
      const newJob: Job = {
        id: data.job_id,
        prompt: title || `Video Analysis (${data.video_count} videos)`,
        pipeline: 'video_analysis',
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        isLoading: false,
      }));

      return data;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create video analysis job',
        isLoading: false,
      });
      throw error;
    }
  },

  createTextInputJob: async (request: TextInputRequest): Promise<TextInputResponse> => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/text-input`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create text input job');
      }

      const data: TextInputResponse = await response.json();

      // Add job to local state
      const newJob: Job = {
        id: data.job_id,
        prompt: request.source_label || 'Text Analysis',
        pipeline: 'text_provided',
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        isLoading: false,
      }));

      return data;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create text input job',
        isLoading: false,
      });
      throw error;
    }
  },

  createScreenshotInputJob: async (
    file: File,
    topic: string,
    platformHint?: string,
    contextNote?: string
  ): Promise<ScreenshotInputResponse> => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();

      // Use FormData for file upload - do NOT set Content-Type header
      const formData = new FormData();
      formData.append('screenshot', file);
      formData.append('topic', topic);
      if (platformHint) {
        formData.append('platform_hint', platformHint);
      }
      if (contextNote) {
        formData.append('context_note', contextNote);
      }

      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      // IMPORTANT: Do NOT set Content-Type for FormData - browser handles it

      const response = await fetch(`${API_URL}/jobs/screenshot-input`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create screenshot input job');
      }

      const data: ScreenshotInputResponse = await response.json();

      // Add job to local state
      const newJob: Job = {
        id: data.job_id,
        prompt: `Screenshot Analysis (${data.platform_detected || platformHint || 'other'})`,
        pipeline: 'ocr_extracted',
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        isLoading: false,
      }));

      return data;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create screenshot input job',
        isLoading: false,
      });
      throw error;
    }
  },

  createMixedInputJob: async (request: MixedInputRequest): Promise<MixedInputResponse> => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/mixed-input`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create mixed input job');
      }

      const data: MixedInputResponse = await response.json();

      // Add job to local state
      const sourceTypes: string[] = [];
      if (request.video_urls?.length) sourceTypes.push(`${request.video_urls.length} video`);
      if (request.text_inputs?.length) sourceTypes.push(`${request.text_inputs.length} text`);
      if (request.article_urls?.length) sourceTypes.push(`${request.article_urls.length} article`);

      const newJob: Job = {
        id: data.job_id,
        prompt: request.topic,
        title: request.topic,
        pipeline: 'mixed_input',
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        isLoading: false,
      }));

      return data;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to create mixed input job',
        isLoading: false,
      });
      throw error;
    }
  },

  triggerBooster: async (jobId: string): Promise<BoosterResponse> => {
    set({ actionInProgress: 'booster' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/booster`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to trigger booster');
      }

      const data: BoosterResponse = await response.json();

      // Update booster_status in local state (DO NOT change job.status)
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId ? { ...job, booster_status: 'queued' as const } : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to trigger booster';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  triggerProducerPacket: async (jobId: string): Promise<ProducerPacketResponse> => {
    set({ actionInProgress: 'producer' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/producer-packet`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to trigger producer packet');
      }

      const data: ProducerPacketResponse = await response.json();

      // Update producer_status in local state (DO NOT change job.status)
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId ? { ...job, producer_status: 'queued' as const } : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to trigger producer packet';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  triggerIteration: async (jobId: string, request: IterationRequest): Promise<IterationResponse> => {
    set({ actionInProgress: 'iteration' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/iterate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to start iteration');
      }

      const data: IterationResponse = await response.json();

      // Update job iteration status in local state (DO NOT change job.status)
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                iteration_status: 'queued' as const,
                iteration_id: data.iteration_id,
              }
            : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start iteration';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  refreshJob: async (jobId: string) => {
    set({ isRefreshing: true });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}`, { headers });

      if (!response.ok) {
        throw new Error('Failed to fetch job');
      }

      const data = await response.json();

      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                status: data.status,
                stage: data.stage,
                stage_started_at: data.stage_started_at,
                progress_percent: data.progress_percent,
                pass_detail: data.pass_detail,
                title: data.title,
                artifacts: data.artifacts,
                error: data.error,
                warnings: data.warnings,
                warning_count: data.warning_count,
                interpretations: data.interpretations,
                // Booster tracking fields
                booster_status: data.booster_status,
                booster_started_at: data.booster_started_at,
                booster_completed_at: data.booster_completed_at,
                booster_error: data.booster_error,
                booster_progress_percent: data.booster_progress_percent,
                // Iteration tracking fields
                iteration_status: data.iteration_status,
                iteration_id: data.iteration_id,
                iteration_started_at: data.iteration_started_at,
                iteration_completed_at: data.iteration_completed_at,
                iteration_error: data.iteration_error,
                iteration_progress_percent: data.iteration_progress_percent,
              }
            : job
        ),
        isRefreshing: false,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to refresh job';
      set({ error: message, isRefreshing: false });
      throw error;
    }
  },

  selectInterpretation: async (jobId: string, indices: number[] | 'all') => {
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/select-interpretation`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ indices }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to select interpretation');
      }

      // Update local state to show job is resuming
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? { ...job, status: 'queued' as const, interpretations: undefined }
            : job
        ),
      }));

      // Refresh the job to get latest status
      await get().refreshJob(jobId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to select interpretation';
      set({ error: message });
      throw error;
    }
  },

  cancelJob: async (jobId: string) => {
    set({ actionInProgress: 'cancel' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to cancel job');
      }

      // Update local state to reflect cancellation
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? { ...job, status: 'cancelled' as const }
            : job
        ),
        actionInProgress: null,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to cancel job';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  deleteJob: async (jobId: string) => {
    set({ actionInProgress: 'delete' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}`, {
        method: 'DELETE',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to delete job');
      }

      // Remove from local state
      set((state) => ({
        jobs: state.jobs.filter((job) => job.id !== jobId),
        actionInProgress: null,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to delete job';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  archiveJob: async (jobId: string) => {
    set({ actionInProgress: 'archive' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/archive`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to archive job');
      }

      // Remove from local state (archived jobs are hidden)
      set((state) => ({
        jobs: state.jobs.filter((job) => job.id !== jobId),
        actionInProgress: null,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to archive job';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  clearJobs: () => {
    set({ jobs: [], error: null });
  },

  // Bulk selection methods
  toggleEditMode: () => {
    set((state) => ({
      isEditMode: !state.isEditMode,
      selectedJobIds: new Set<string>(),
      bulkErrors: [],
    }));
  },

  selectJob: (jobId: string) => {
    set((state) => {
      const newSet = new Set(state.selectedJobIds);
      newSet.add(jobId);
      return { selectedJobIds: newSet };
    });
  },

  deselectJob: (jobId: string) => {
    set((state) => {
      const newSet = new Set(state.selectedJobIds);
      newSet.delete(jobId);
      return { selectedJobIds: newSet };
    });
  },

  selectAll: () => {
    set((state) => ({
      selectedJobIds: new Set(
        state.jobs
          .filter((j) => !['running', 'queued'].includes(j.status))
          .map((j) => j.id)
      ),
    }));
  },

  deselectAll: () => {
    set({ selectedJobIds: new Set<string>() });
  },

  bulkDelete: async () => {
    const { selectedJobIds, deleteJob } = get();
    const errors: BulkError[] = [];
    const jobIds = Array.from(selectedJobIds);

    for (const id of jobIds) {
      try {
        await deleteJob(id);
      } catch (e) {
        errors.push({ jobId: id, error: e instanceof Error ? e.message : 'Failed to delete' });
      }
    }

    set({ selectedJobIds: new Set<string>(), bulkErrors: errors });
  },

  bulkArchive: async () => {
    const { selectedJobIds, archiveJob } = get();
    const errors: BulkError[] = [];
    const jobIds = Array.from(selectedJobIds);

    for (const id of jobIds) {
      try {
        await archiveJob(id);
      } catch (e) {
        errors.push({ jobId: id, error: e instanceof Error ? e.message : 'Failed to archive' });
      }
    }

    set({ selectedJobIds: new Set<string>(), bulkErrors: errors });
  },

  clearBulkErrors: () => {
    set({ bulkErrors: [] });
  },
}));
