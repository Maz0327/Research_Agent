/**
 * Zustand store for managing research jobs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';

export interface Job {
  id: string;
  prompt: string;
  title?: string;  // AI-generated short title
  pipeline: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  stage?: string;  // Current pipeline stage
  stage_started_at?: string;  // When current stage started (for ETA)
  progress_percent: number;
  artifacts?: {
    drive_folder_url?: string;
    doc_urls?: string[];
  };
  error?: string;
  created_at: string;
}

interface JobsState {
  jobs: Job[];
  isLoading: boolean;
  error: string | null;
  fetchJobs: () => Promise<void>;
  createJob: (prompt: string, pipeline: string) => Promise<string>;
  refreshJob: (jobId: string) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useJobsStore = create<JobsState>((set, get) => ({
  jobs: [],
  isLoading: false,
  error: null,

  fetchJobs: async () => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs`, { headers });

      if (!response.ok) {
        throw new Error('Failed to fetch jobs');
      }

      const data = await response.json();
      set({ jobs: data.jobs, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch jobs',
        isLoading: false,
      });
    }
  },

  createJob: async (prompt: string, pipeline: string) => {
    set({ isLoading: true, error: null });
    try {
      const token = await getAccessToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/jobs`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt, pipeline }),
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
              }
            : job
        ),
      }));
    } catch (error) {
      console.error('Failed to refresh job:', error);
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
      console.error('Failed to cancel job:', error);
      throw error;
    }
  },
}));
