'use client';

/**
 * Admin state management for users, jobs, and error logs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

/**
 * Admin view of a user with account and activity metadata.
 */
export interface AdminUser {
  /** Unique user identifier (UUID) */
  id: string;
  /** User's email address */
  email: string;
  /** Account creation timestamp (ISO format) */
  created_at: string;
  /** Last sign-in timestamp (ISO format, null if never signed in) */
  last_sign_in_at: string | null;
  /** Total number of jobs created by this user */
  job_count: number;
  /** Whether user has admin privileges */
  is_admin: boolean;
  /** Whether user is banned from creating jobs */
  is_banned: boolean;
}

/**
 * Admin view of a job with user attribution.
 */
export interface AdminJob {
  /** Unique job identifier (UUID) */
  id: string;
  /** User ID who created this job */
  user_id: string;
  /** Email of user who created this job */
  user_email: string;
  /** Research prompt */
  prompt: string;
  /** Pipeline type used */
  pipeline: string;
  /** Current job status */
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  /** Job completion percentage (0-100) */
  progress_percent: number;
  /** Job creation timestamp (ISO format) */
  created_at: string;
  /** Error message if job failed */
  error?: string;
}

/**
 * Error log entry for admin monitoring.
 */
export interface ErrorLog {
  /** Unique error log identifier (UUID) */
  id: string;
  /** Associated job ID (null for system errors) */
  job_id: string | null;
  /** Associated user ID (null for anonymous errors) */
  user_id: string | null;
  /** Email of user who triggered error (null for anonymous) */
  user_email: string | null;
  /** User-friendly error message */
  user_message: string;
  /** Error category for classification */
  error_category: string;
  /** Technical error message with details */
  technical_message: string;
  /** Full stack trace (null if not available) */
  stack_trace: string | null;
  /** Pipeline stage where error occurred (null for non-pipeline errors) */
  stage: string | null;
  /** Error timestamp (ISO format) */
  created_at: string;
  /** Whether error has been resolved by admin */
  resolved: boolean;
}

/**
 * Admin dashboard statistics.
 */
export interface AdminStats {
  /** Total number of registered users */
  total_users: number;
  /** Total number of jobs created */
  total_jobs: number;
  /** Jobs created today (UTC) */
  jobs_today: number;
  /** Currently running jobs */
  jobs_running: number;
  /** Jobs that failed today (UTC) */
  jobs_failed_today: number;
  /** Error logs not yet resolved */
  unresolved_errors: number;
}

interface AdminFilters {
  status?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  resolved?: boolean;
}

interface AdminState {
  // Data
  stats: AdminStats | null;
  users: AdminUser[];
  jobs: AdminJob[];
  errorLogs: ErrorLog[];

  // Error state
  error: string | null;

  // Loading states
  isLoadingStats: boolean;
  isLoadingUsers: boolean;
  isLoadingJobs: boolean;
  isLoadingErrors: boolean;

  // Pagination
  usersPage: number;
  jobsPage: number;
  errorsPage: number;
  pageSize: number;
  totalUsers: number;
  totalJobs: number;
  totalErrors: number;

  // Actions
  fetchStats: () => Promise<void>;
  fetchUsers: (page?: number) => Promise<void>;
  fetchJobs: (page?: number, filters?: AdminFilters) => Promise<void>;
  fetchErrorLogs: (page?: number, filters?: AdminFilters) => Promise<void>;
  cancelJob: (jobId: string) => Promise<void>;
  deleteJob: (jobId: string) => Promise<void>;
  banUser: (userId: string) => Promise<void>;
  unbanUser: (userId: string) => Promise<void>;
  resolveError: (errorId: string) => Promise<void>;
  clearError: () => void;
}

async function authFetch(endpoint: string, options: RequestInit = {}) {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const useAdminStore = create<AdminState>((set, get) => ({
  stats: null,
  users: [],
  jobs: [],
  errorLogs: [],
  error: null,

  isLoadingStats: false,
  isLoadingUsers: false,
  isLoadingJobs: false,
  isLoadingErrors: false,

  usersPage: 1,
  jobsPage: 1,
  errorsPage: 1,
  pageSize: 20,
  totalUsers: 0,
  totalJobs: 0,
  totalErrors: 0,

  fetchStats: async () => {
    set({ isLoadingStats: true, error: null });
    try {
      const stats = await authFetch('/admin/stats');
      set({ stats, isLoadingStats: false });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch stats';
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to fetch admin stats:', error);
      }
      set({ isLoadingStats: false, error: errorMessage });
    }
  },

  fetchUsers: async (page = 1) => {
    set({ isLoadingUsers: true, usersPage: page, error: null });
    try {
      const { pageSize } = get();
      const data = await authFetch(`/admin/users?page=${page}&page_size=${pageSize}`);
      set({
        users: data.users,
        totalUsers: data.total,
        isLoadingUsers: false,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch users';
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to fetch users:', error);
      }
      set({ isLoadingUsers: false, error: errorMessage });
    }
  },

  fetchJobs: async (page = 1, filters = {}) => {
    set({ isLoadingJobs: true, jobsPage: page, error: null });
    try {
      const { pageSize } = get();
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });

      if (filters.status) params.append('status', filters.status);
      if (filters.user_id) params.append('user_id', filters.user_id);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);

      const data = await authFetch(`/admin/jobs?${params.toString()}`);
      set({
        jobs: data.jobs,
        totalJobs: data.total,
        isLoadingJobs: false,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch jobs';
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to fetch jobs:', error);
      }
      set({ isLoadingJobs: false, error: errorMessage });
    }
  },

  fetchErrorLogs: async (page = 1, filters = {}) => {
    set({ isLoadingErrors: true, errorsPage: page, error: null });
    try {
      const { pageSize } = get();
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });

      if (filters.category) params.append('category', filters.category);
      if (filters.resolved !== undefined) params.append('resolved', String(filters.resolved));
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);

      const data = await authFetch(`/admin/errors?${params.toString()}`);
      set({
        errorLogs: data.errors,
        totalErrors: data.total,
        isLoadingErrors: false,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch error logs';
      if (process.env.NODE_ENV === 'development') {
        console.error('Failed to fetch error logs:', error);
      }
      set({ isLoadingErrors: false, error: errorMessage });
    }
  },

  cancelJob: async (jobId: string) => {
    await authFetch(`/admin/jobs/${jobId}/cancel`, { method: 'POST' });
    set((state) => ({
      jobs: state.jobs.map((job) =>
        job.id === jobId ? { ...job, status: 'cancelled' as const } : job
      ),
    }));
  },

  deleteJob: async (jobId: string) => {
    await authFetch(`/admin/jobs/${jobId}`, { method: 'DELETE' });
    set((state) => ({
      jobs: state.jobs.filter((job) => job.id !== jobId),
      totalJobs: state.totalJobs - 1,
    }));
  },

  banUser: async (userId: string) => {
    await authFetch(`/admin/users/${userId}/ban`, { method: 'POST' });
    set((state) => ({
      users: state.users.map((user) =>
        user.id === userId ? { ...user, is_banned: true } : user
      ),
    }));
  },

  unbanUser: async (userId: string) => {
    await authFetch(`/admin/users/${userId}/unban`, { method: 'POST' });
    set((state) => ({
      users: state.users.map((user) =>
        user.id === userId ? { ...user, is_banned: false } : user
      ),
    }));
  },

  resolveError: async (errorId: string) => {
    await authFetch(`/admin/errors/${errorId}/resolve`, { method: 'POST' });
    set((state) => ({
      errorLogs: state.errorLogs.map((error) =>
        error.id === errorId ? { ...error, resolved: true } : error
      ),
    }));
  },

  clearError: () => {
    set({ error: null });
  },
}));
