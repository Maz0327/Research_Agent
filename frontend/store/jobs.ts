/**
 * Zustand store for managing research jobs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

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
  /** Current job status */
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'disambiguating';
  /** Current pipeline stage name */
  stage?: string;
  /** When current stage started (ISO timestamp for ETA calculation) */
  stage_started_at?: string;
  /** Job completion percentage (0-100) */
  progress_percent: number;
  /** Output artifacts from completed job */
  artifacts?: JobArtifacts;
  /** Error message if job failed */
  error?: string;
  /** Job creation timestamp (ISO format) */
  created_at: string;
  /** Possible interpretations when status is 'disambiguating' */
  interpretations?: Interpretation[];
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

interface JobsState {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  preview: JobPreview | null;
  isPreviewLoading: boolean;
  // Bulk selection state
  selectedJobIds: Set<string>;
  isEditMode: boolean;
  bulkErrors: BulkError[];
  // Methods
  fetchJobs: () => Promise<void>;
  previewJob: (prompt: string, pipeline: string, niche?: string) => Promise<JobPreview>;
  createJob: (prompt: string, pipeline: string, niche?: string, options?: { custom_subreddits?: string[] }) => Promise<string>;
  createVideoAnalysisJob: (videoUrls: string[], title?: string, model?: 'gemini-2.5-flash' | 'gemini-2.5-pro') => Promise<VideoAnalysisResponse>;
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

  refreshJob: async (jobId: string) => {
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
                title: data.title,
                artifacts: data.artifacts,
                error: data.error,
                interpretations: data.interpretations,
              }
            : job
        ),
      }));
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to refresh job:', error);
      }
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
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to select interpretation:', error);
      }
      throw error;
    }
  },

  cancelJob: async (jobId: string) => {
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
      }));
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to cancel job:', error);
      }
      throw error;
    }
  },

  deleteJob: async (jobId: string) => {
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
      }));
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to delete job:', error);
      }
      throw error;
    }
  },

  archiveJob: async (jobId: string) => {
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
      }));
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to archive job:', error);
      }
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
