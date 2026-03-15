/**
 * Zustand store for managing research jobs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';
import { formatApiError } from '../lib/error-utils';
import type { SearchCandidate, IterateRequest, SearchDiscoveryResponse, QuickBriefResponse, SearchApproveResponse } from '../types/run';

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
  /** Storage path for Doc 3 (Creator Brief) */
  doc_3_path?: string;
  /** Storage path for Doc 4 (Producer Packet) */
  doc_4_path?: string;
  // Per-source extraction data
  /** Semantic extractions per source */
  semantic_extractions?: Record<string, unknown>[];
  // Booster Pipeline (Phase 7)
  /** Booster output for Doc 1 expansion */
  booster_output?: Record<string, unknown>;
  /** Booster markdown for Doc 1 */
  booster_expansion_md?: string;
  // Creator Brief markdown (Doc 3 — auto-generated hero document)
  /** Creator Brief markdown output */
  creator_brief_md?: string;
  // Producer Packet markdown (Doc 4 — optional, user-triggered)
  /** Producer packet markdown output */
  producer_packet_md?: string;
  // Iteration Loop (Phase 9)
  /** Iteration bundles - each iteration produces its own doc set */
  iterations?: IterationBundle[];
  // V2 Run Abstraction (Phase 10)
  /** V2 runs - unified model for baseline/iterations/regenerations */
  runs?: unknown[];
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
 * Claim extraction text input
 */
export interface ClaimExtractionTextInput {
  title: string;
  content: string;
  platform_hint?: string;
}

/**
 * Claim extraction screenshot input
 */
export interface ClaimExtractionScreenshot {
  filename: string;
  base64: string;
  platform_hint?: string;
}

/**
 * Claim extraction job request
 */
export interface ClaimExtractionRequest {
  title: string;
  video_urls?: string[];
  article_urls?: string[];
  text_inputs?: ClaimExtractionTextInput[];
  screenshots?: ClaimExtractionScreenshot[];
  model?: 'gemini-2.5-flash' | 'gemini-2.5-pro';
}

/**
 * Claim extraction job response
 */
export interface ClaimExtractionResponse {
  job_id: string;
  source_count: number;
  video_count: number;
  article_count: number;
  text_count: number;
  screenshot_count: number;
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
 * V2 Run request parameters (replaces IterationRequest)
 */
export interface CreateRunRequest {
  /** Run type: expand, refine, regenerate */
  run_type: 'expand' | 'refine' | 'regenerate';
  /** Parent run ID to build on (default: run_0) */
  parent_run_id?: string;
  /** User guidance for the run (required for refine, optional for expand) */
  user_prompt?: string;
  /** URLs to add (for expand type with manual search) */
  new_source_urls?: string[];
  /** Max sources for auto-search (for expand type) */
  max_new_sources?: number;
  /** 'manual' for user-provided URLs, 'auto' for grounded search */
  search_mode?: 'auto' | 'manual';
  /** Skip user review of search candidates (default: false) */
  trust_mode?: boolean;
}

/**
 * V2 Run creation response
 */
export interface CreateRunResponse {
  job_id: string;
  run_id: string;
  run_index: number;
  run_type: string;
  parent_run_id: string;
  status: string;
  message: string;
}

/**
 * Document version metadata from the versioning system.
 */
export interface DocumentVersion {
  /** Version number (1-based) */
  version: number;
  /** When this version was created */
  created_at: string;
  /** What triggered this version (initial_run, deep_dive, expand_sources, etc.) */
  trigger: string;
  /** Number of sources in the job at this version */
  source_count: number;
  /** Number of claims extracted at this version */
  claim_count: number;
  /** Human-readable summary of changes from previous version */
  diff_summary: string;
}

/**
 * Iterate response from POST /jobs/{job_id}/iterate
 */
export interface IterateResponse {
  job_id: string;
  iterate_id: string;
  mode: string;
  status: string;
  message: string;
}

interface JobsState {
  jobs: Job[];
  archivedJobs: Job[];
  isLoading: boolean;
  isLoadingArchived: boolean;
  error: string | null;
  preview: JobPreview | null;
  isPreviewLoading: boolean;
  // Action loading states
  isRefreshing: boolean;
  actionInProgress: 'booster' | 'producer' | 'iteration' | 'cancel' | 'delete' | 'archive' | 'unarchive' | null;
  // Bulk selection state
  selectedJobIds: Set<string>;
  isEditMode: boolean;
  bulkErrors: BulkError[];
  // Methods
  fetchJobs: () => Promise<void>;
  fetchArchivedJobs: () => Promise<void>;
  previewJob: (prompt: string, pipeline: string, niche?: string) => Promise<JobPreview>;
  createJob: (prompt: string, pipeline: string, niche?: string, options?: { custom_subreddits?: string[] }) => Promise<string>;
  createTextInputJob: (request: TextInputRequest) => Promise<TextInputResponse>;
  createScreenshotInputJob: (file: File, topic: string, platformHint?: string, contextNote?: string) => Promise<ScreenshotInputResponse>;
  createMixedInputJob: (request: MixedInputRequest) => Promise<MixedInputResponse>;
  createClaimExtractionJob: (request: ClaimExtractionRequest) => Promise<ClaimExtractionResponse>;
  triggerBooster: (jobId: string, runId?: string) => Promise<BoosterResponse>;
  triggerProducerPacket: (jobId: string, runId?: string) => Promise<ProducerPacketResponse>;
  createRun: (jobId: string, request: CreateRunRequest) => Promise<CreateRunResponse>;
  approveSearchSources: (jobId: string, runId: string, approvedUrls: string[]) => Promise<void>;
  getSearchCandidates: (jobId: string, runId: string) => Promise<SearchCandidate[]>;
  refreshJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  archiveJob: (jobId: string) => Promise<void>;
  unarchiveJob: (jobId: string) => Promise<void>;
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
  // Document versioning
  documentVersions: Record<string, DocumentVersion[]>;
  fetchDocumentVersions: (jobId: string, docType: string) => Promise<DocumentVersion[]>;
  fetchDocumentByVersion: (jobId: string, docType: string, version?: number) => Promise<{ data?: Record<string, unknown>; markdown?: string; version_metadata?: DocumentVersion }>;
  // Unified iterate endpoint
  iterateJob: (jobId: string, request: IterateRequest) => Promise<IterateResponse>;
  // Search discovery (Phase 5)
  searchResults: SearchDiscoveryResponse | null;
  isSearching: boolean;
  quickBrief: QuickBriefResponse | null;
  isLoadingQuickBrief: boolean;
  searchTopic: (topic: string, depth?: string, category?: string) => Promise<SearchDiscoveryResponse>;
  fetchQuickBrief: (searchId: string) => Promise<QuickBriefResponse>;
  approveSearchSources_v2: (searchId: string, selectedUrls: string[], depth?: string) => Promise<SearchApproveResponse>;
  clearSearchResults: () => void;
  // Brainstorm pre-stage (Phase 2A)
  brainstormResult: any | null;
  isBrainstorming: boolean;
  brainstormTopic: (topic: string, audienceHint?: string, styleGuideId?: string) => Promise<any>;
  clearBrainstorm: () => void;
  // Creator analysis (Phase 3A)
  creatorAnalysisResult: any | null;
  isAnalyzingCreator: boolean;
  analyzeCreator: (creatorName: string, videoUrls: string[]) => Promise<any>;
  clearCreatorAnalysis: () => void;
}

export const useJobsStore = create<JobsState>((set, get) => ({
  jobs: [],
  archivedJobs: [],
  isLoading: false,
  isLoadingArchived: false,
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
  // Document versioning state
  documentVersions: {},
  // Search discovery state (Phase 5)
  searchResults: null,
  isSearching: false,
  quickBrief: null,
  isLoadingQuickBrief: false,
  // Brainstorm pre-stage (Phase 2A)
  brainstormResult: null,
  isBrainstorming: false,
  creatorAnalysisResult: null,
  isAnalyzingCreator: false,

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

  previewJob: async (_prompt: string, _pipeline: string, _niche?: string) => {
    // DEPRECATED: POST /jobs/preview returns 410 Gone since 2026-01-26.
    // Kept for interface compatibility. Will be replaced by Quick Brief (Phase 5).
    // Original implementation archived to backend/archive/deprecated_route_handlers.py
    set({ isPreviewLoading: false, error: 'Preview endpoint is deprecated. Use mixed-input or search instead.', preview: null });
    throw new Error('Preview endpoint is deprecated (410 Gone). Use mixed-input or search entry points instead.');
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
        throw new Error(formatApiError(errorData, 'Failed to create text input job'));
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
        throw new Error(formatApiError(errorData, 'Failed to create screenshot input job'));
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
        throw new Error(formatApiError(errorData, 'Failed to create mixed input job'));
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

  createClaimExtractionJob: async (request: ClaimExtractionRequest): Promise<ClaimExtractionResponse> => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/claim-extraction`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to create claim extraction job'));
      }

      const data: ClaimExtractionResponse = await response.json();

      // Add job to local state
      const newJob: Job = {
        id: data.job_id,
        prompt: request.title,
        title: request.title,
        pipeline: 'claim_extraction',
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
        error: error instanceof Error ? error.message : 'Failed to create claim extraction job',
        isLoading: false,
      });
      throw error;
    }
  },

  triggerBooster: async (jobId: string, runId?: string): Promise<BoosterResponse> => {
    set({ actionInProgress: 'booster' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Use run-scoped endpoint if runId provided
      const endpoint = runId
        ? `${API_URL}/jobs/${jobId}/runs/${runId}/booster`
        : `${API_URL}/jobs/${jobId}/booster`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to trigger booster'));
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

  triggerProducerPacket: async (jobId: string, runId?: string): Promise<ProducerPacketResponse> => {
    set({ actionInProgress: 'producer' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Use run-scoped endpoint if runId provided
      const endpoint = runId
        ? `${API_URL}/jobs/${jobId}/runs/${runId}/producer`
        : `${API_URL}/jobs/${jobId}/producer-packet`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to trigger producer packet'));
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

  triggerScript: async (jobId: string, options?: { tone?: string; target_length?: string; story_arc?: string; voice_profile_id?: string }): Promise<{ job_id: string; status: string; message: string }> => {
    set({ actionInProgress: 'script' as any });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/script`, {
        method: 'POST',
        headers,
        body: JSON.stringify(options || {}),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to trigger script'));
      }

      const data = await response.json();

      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId ? { ...job, script_status: 'queued' as any } : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to trigger script';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  triggerBlogPost: async (jobId: string): Promise<{ job_id: string; status: string; message: string }> => {
    set({ actionInProgress: 'blog_post' as any });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/blog-post`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to trigger blog post'));
      }

      const data = await response.json();

      // Update blog_post_status in local state (DO NOT change job.status)
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId ? { ...job, blog_post_status: 'queued' as any } : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to trigger blog post';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  createRun: async (jobId: string, request: CreateRunRequest): Promise<CreateRunResponse> => {
    set({ actionInProgress: 'iteration' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // V2 endpoint: POST /jobs/{id}/runs
      const response = await fetch(`${API_URL}/jobs/${jobId}/runs`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          run_type: request.run_type,
          parent_run_id: request.parent_run_id || 'run_0',
          user_prompt: request.user_prompt || '',
          new_source_urls: request.new_source_urls || [],
          max_new_sources: request.max_new_sources || 4,
          search_mode: request.search_mode || 'manual',
          trust_mode: request.trust_mode || false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to create run'));
      }

      const data: CreateRunResponse = await response.json();

      // Update job iteration status in local state (DO NOT change job.status)
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                iteration_status: 'queued' as const,
                iteration_id: data.run_id,
              }
            : job
        ),
        actionInProgress: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create run';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  approveSearchSources: async (jobId: string, runId: string, approvedUrls: string[]) => {
    set({ actionInProgress: 'iteration' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/runs/${runId}/approve-sources`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          approved_urls: approvedUrls,
          rejected_urls: [],
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to approve sources'));
      }

      // Update local state: run is back to running
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? { ...job, iteration_status: 'running' as const }
            : job
        ),
        actionInProgress: null,
      }));
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to approve sources';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  getSearchCandidates: async (jobId: string, runId: string): Promise<SearchCandidate[]> => {
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/runs/${runId}/search-candidates`, {
        headers,
      });

      if (!response.ok) {
        return [];
      }

      const data = await response.json();
      return data.candidates || [];
    } catch {
      return [];
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
                // Producer packet tracking fields
                producer_status: data.producer_status,
                producer_started_at: data.producer_started_at,
                producer_completed_at: data.producer_completed_at,
                producer_error: data.producer_error,
                producer_progress_percent: data.producer_progress_percent,
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
        throw new Error(formatApiError(errorData, 'Failed to select interpretation'));
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
        throw new Error(formatApiError(errorData, 'Failed to cancel job'));
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
        throw new Error(formatApiError(errorData, 'Failed to delete job'));
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
        throw new Error(formatApiError(errorData, 'Failed to archive job'));
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

  unarchiveJob: async (jobId: string) => {
    set({ actionInProgress: 'unarchive' });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/unarchive`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to recover job'));
      }

      // Remove from archived list and refresh main jobs
      set((state) => ({
        archivedJobs: state.archivedJobs.filter((job) => job.id !== jobId),
        actionInProgress: null,
      }));

      // Refresh main jobs list to include recovered job
      get().fetchJobs();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to recover job';
      set({ error: message, actionInProgress: null });
      throw error;
    }
  },

  fetchArchivedJobs: async () => {
    set({ isLoadingArchived: true });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/archived`, { headers });

      if (!response.ok) {
        throw new Error('Failed to fetch archived jobs');
      }

      const data = await response.json();
      const jobs: Job[] = (data.jobs || []).map((job: Record<string, unknown>) => ({
        id: job.id,
        prompt: job.prompt || '',
        title: job.title || '',
        pipeline: job.pipeline || 'full',
        status: job.status,
        created_at: job.created_at,
        progress_percent: 0,
      }));

      set({ archivedJobs: jobs, isLoadingArchived: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch archived jobs';
      set({ error: message, isLoadingArchived: false });
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

  // =========================================================================
  // Document Versioning
  // =========================================================================

  fetchDocumentVersions: async (jobId: string, docType: string): Promise<DocumentVersion[]> => {
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/${jobId}/documents/${docType}/versions`, {
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to fetch document versions'));
      }

      const data = await response.json();
      const versions: DocumentVersion[] = data.versions || [];

      // Cache in store
      set((state) => ({
        documentVersions: {
          ...state.documentVersions,
          [`${jobId}_${docType}`]: versions,
        },
      }));

      return versions;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch versions';
      console.error(`[Store] fetchDocumentVersions error: ${message}`);
      throw error;
    }
  },

  fetchDocumentByVersion: async (
    jobId: string,
    docType: string,
    version?: number
  ): Promise<{ data?: Record<string, unknown>; markdown?: string; version_metadata?: DocumentVersion }> => {
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const url = version
        ? `${API_URL}/jobs/${jobId}/documents/${docType}?version=${version}`
        : `${API_URL}/jobs/${jobId}/documents/${docType}`;

      const response = await fetch(url, { headers });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to fetch document'));
      }

      return await response.json();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch document';
      console.error(`[Store] fetchDocumentByVersion error: ${message}`);
      throw error;
    }
  },

  // =========================================================================
  // Unified Iterate Endpoint
  // =========================================================================

  iterateJob: async (jobId: string, request: IterateRequest): Promise<IterateResponse> => {
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
        throw new Error(formatApiError(errorData, 'Failed to start iteration'));
      }

      const data: IterateResponse = await response.json();

      // Update job iteration status in local state
      set((state) => ({
        jobs: state.jobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                iteration_status: 'queued' as const,
                iteration_id: data.iterate_id,
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

  // =========================================================================
  // Search Discovery (Phase 5)
  // =========================================================================

  searchTopic: async (topic: string, depth?: string, category?: string): Promise<SearchDiscoveryResponse> => {
    set({ isSearching: true, searchResults: null, quickBrief: null, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: Record<string, unknown> = { topic };
      if (depth) body.depth = depth;
      if (category) body.category = category;

      const response = await fetch(`${API_URL}/jobs/search`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Search discovery failed'));
      }

      const data: SearchDiscoveryResponse = await response.json();
      set({ searchResults: data, isSearching: false });
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Search discovery failed';
      set({ error: message, isSearching: false });
      throw error;
    }
  },

  fetchQuickBrief: async (searchId: string): Promise<QuickBriefResponse> => {
    set({ isLoadingQuickBrief: true });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs/search/${searchId}/quick-brief`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Quick brief generation failed'));
      }

      const data: QuickBriefResponse = await response.json();
      set({ quickBrief: data, isLoadingQuickBrief: false });
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Quick brief generation failed';
      set({ error: message, isLoadingQuickBrief: false });
      throw error;
    }
  },

  approveSearchSources_v2: async (searchId: string, selectedUrls: string[], depth?: string): Promise<SearchApproveResponse> => {
    set({ error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body: Record<string, unknown> = { selected_urls: selectedUrls };
      if (depth) body.depth = depth;

      const response = await fetch(`${API_URL}/jobs/search/${searchId}/approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(formatApiError(errorData, 'Failed to approve search sources'));
      }

      const data: SearchApproveResponse = await response.json();

      // Add job to local state
      const newJob: Job = {
        id: data.job_id,
        prompt: get().searchResults?.topic || 'Research Job',
        pipeline: 'full',
        status: 'queued',
        progress_percent: 0,
        created_at: new Date().toISOString(),
      };

      set((state) => ({
        jobs: [newJob, ...state.jobs],
        searchResults: null,
        quickBrief: null,
      }));

      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to approve sources';
      set({ error: message });
      throw error;
    }
  },

  clearSearchResults: () => {
    set({ searchResults: null, quickBrief: null, isSearching: false, isLoadingQuickBrief: false });
  },

  // ─── Brainstorm Pre-Stage (Phase 2A) ─────────────────────────────────────
  brainstormTopic: async (topic: string, audienceHint?: string, styleGuideId?: string) => {
    set({ isBrainstorming: true, brainstormResult: null, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const body: Record<string, unknown> = { topic };
      if (audienceHint) body.audience_hint = audienceHint;
      if (styleGuideId) body.style_guide_id = styleGuideId;

      const res = await fetch(`${API_URL}/jobs/brainstorm`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Brainstorm failed: ${res.status}`);
      }
      const result = await res.json();
      set({ brainstormResult: result, isBrainstorming: false });
      return result;
    } catch (e: any) {
      set({ error: formatApiError(e), isBrainstorming: false });
      return null;
    }
  },

  clearBrainstorm: () => {
    set({ brainstormResult: null, isBrainstorming: false });
  },

  // ─── Creator Analysis (Phase 3A) ──────────────────────────────────────────
  analyzeCreator: async (creatorName: string, videoUrls: string[]) => {
    set({ isAnalyzingCreator: true, creatorAnalysisResult: null, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const res = await fetch(`${API_URL}/creator-analysis`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          creator_name: creatorName,
          video_urls: videoUrls,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Creator analysis failed: ${res.status}`);
      }
      const result = await res.json();
      set({ creatorAnalysisResult: result, isAnalyzingCreator: false });
      return result;
    } catch (e: any) {
      set({ error: formatApiError(e), isAnalyzingCreator: false });
      throw e;
    }
  },

  clearCreatorAnalysis: () => {
    set({ creatorAnalysisResult: null, isAnalyzingCreator: false });
  },
}));
