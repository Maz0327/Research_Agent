/**
 * Admin state management for users, jobs, and error logs.
 */
import { create } from 'zustand';
import { getAccessToken } from '../lib/supabase';

export interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at: string | null;
  job_count: number;
  is_admin: boolean;
  is_banned: boolean;
}

export interface AdminJob {
  id: string;
  user_id: string;
  user_email: string;
  prompt: string;
  pipeline: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  created_at: string;
  error?: string;
}

export interface ErrorLog {
  id: string;
  job_id: string | null;
  user_id: string | null;
  user_email: string | null;
  user_message: string;
  error_category: string;
  technical_message: string;
  stack_trace: string | null;
  stage: string | null;
  created_at: string;
  resolved: boolean;
}

export interface AdminStats {
  total_users: number;
  total_jobs: number;
  jobs_today: number;
  jobs_running: number;
  jobs_failed_today: number;
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
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    set({ isLoadingStats: true });
    try {
      const stats = await authFetch('/admin/stats');
      set({ stats, isLoadingStats: false });
    } catch (error) {
      console.error('Failed to fetch admin stats:', error);
      set({ isLoadingStats: false });
    }
  },

  fetchUsers: async (page = 1) => {
    set({ isLoadingUsers: true, usersPage: page });
    try {
      const { pageSize } = get();
      const data = await authFetch(`/admin/users?page=${page}&page_size=${pageSize}`);
      set({
        users: data.users,
        totalUsers: data.total,
        isLoadingUsers: false,
      });
    } catch (error) {
      console.error('Failed to fetch users:', error);
      set({ isLoadingUsers: false });
    }
  },

  fetchJobs: async (page = 1, filters = {}) => {
    set({ isLoadingJobs: true, jobsPage: page });
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
      console.error('Failed to fetch jobs:', error);
      set({ isLoadingJobs: false });
    }
  },

  fetchErrorLogs: async (page = 1, filters = {}) => {
    set({ isLoadingErrors: true, errorsPage: page });
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
      console.error('Failed to fetch error logs:', error);
      set({ isLoadingErrors: false });
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
}));
