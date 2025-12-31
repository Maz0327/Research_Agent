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
 * Job represents a research job with its status and artifacts.
 */
export interface Job {
  /** Unique job identifier (UUID) */
  id: string;
  /** Original research prompt from user */
  prompt: string;
  /** AI-generated short title for display */
  title?: string;
  /** Pipeline type (quick, full, breaking_news, investigation, profile, controversy) */
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
  artifacts?: {
    /** Google Drive folder URL containing research documents */
    drive_folder_url?: string;
    /** Array of individual document URLs */
    doc_urls?: string[];
  };
  /** Error message if job failed */
  error?: string;
  /** Job creation timestamp (ISO format) */
  created_at: string;
  /** Possible interpretations when status is 'disambiguating' */
  interpretations?: Interpretation[];
}

interface JobsState {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  preview: JobPreview | null;
  isPreviewLoading: boolean;
  fetchJobs: () => Promise<void>;
  previewJob: (prompt: string, pipeline: string, niche?: string) => Promise<JobPreview>;
  createJob: (prompt: string, pipeline: string, niche?: string, options?: { custom_subreddits?: string[] }) => Promise<string>;
  refreshJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  archiveJob: (jobId: string) => Promise<void>;
  selectInterpretation: (jobId: string, indices: number[] | 'all') => Promise<void>;
  clearPreview: () => void;
  clearJobs: () => void;
}

export const useJobsStore = create<JobsState>((set, get) => ({
  jobs: [],
  isLoading: false,
  error: null,
  preview: null,
  isPreviewLoading: false,

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
}));
