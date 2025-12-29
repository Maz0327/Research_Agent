/**
 * Tests for the admin Zustand store.
 */
import { act, renderHook } from '@testing-library/react';
import { useAdminStore, AdminUser, AdminJob } from '../../store/admin';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock getAccessToken
jest.mock('../../lib/supabase', () => ({
  getAccessToken: jest.fn().mockResolvedValue('mock-admin-token'),
}));

describe('useAdminStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAdminStore.setState({
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
    });
    mockFetch.mockClear();
  });

  describe('initial state', () => {
    it('should have null stats initially', () => {
      const { result } = renderHook(() => useAdminStore());
      expect(result.current.stats).toBeNull();
    });

    it('should have empty arrays for lists', () => {
      const { result } = renderHook(() => useAdminStore());
      expect(result.current.users).toEqual([]);
      expect(result.current.jobs).toEqual([]);
      expect(result.current.errorLogs).toEqual([]);
    });

    it('should have null error initially', () => {
      const { result } = renderHook(() => useAdminStore());
      expect(result.current.error).toBeNull();
    });
  });

  describe('fetchStats', () => {
    it('should fetch stats successfully', async () => {
      const mockStats = {
        total_users: 100,
        total_jobs: 500,
        jobs_today: 10,
        jobs_running: 2,
        jobs_failed_today: 1,
        unresolved_errors: 5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.stats).toEqual(mockStats);
      expect(result.current.isLoadingStats).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should set error on fetch failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.error).toBe('Network error');
      expect(result.current.isLoadingStats).toBe(false);
    });

    it('should handle API error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Unauthorized' }),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchStats();
      });

      expect(result.current.error).toBe('Unauthorized');
    });
  });

  describe('fetchUsers', () => {
    it('should fetch users with pagination', async () => {
      const mockUsers: AdminUser[] = [
        {
          id: 'user-1',
          email: 'user1@example.com',
          created_at: '2025-01-01T00:00:00Z',
          last_sign_in_at: null,
          job_count: 5,
          is_admin: false,
          is_banned: false,
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ users: mockUsers, total: 1 }),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchUsers(1);
      });

      expect(result.current.users).toEqual(mockUsers);
      expect(result.current.totalUsers).toBe(1);
      expect(result.current.usersPage).toBe(1);
    });

    it('should set error on failure', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Failed to fetch'));

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchUsers();
      });

      expect(result.current.error).toBe('Failed to fetch');
    });
  });

  describe('fetchJobs', () => {
    it('should fetch jobs with filters', async () => {
      const mockJobs: AdminJob[] = [
        {
          id: 'job-1',
          user_id: 'user-1',
          user_email: 'user@example.com',
          prompt: 'Test research',
          pipeline: 'investigation',
          status: 'completed',
          progress_percent: 100,
          created_at: '2025-01-01T00:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ jobs: mockJobs, total: 1 }),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.fetchJobs(1, { status: 'completed' });
      });

      expect(result.current.jobs).toEqual(mockJobs);
      expect(result.current.totalJobs).toBe(1);
    });
  });

  describe('cancelJob', () => {
    it('should update job status optimistically', async () => {
      const initialJobs: AdminJob[] = [
        {
          id: 'job-1',
          user_id: 'user-1',
          user_email: 'user@example.com',
          prompt: 'Test',
          pipeline: 'quick',
          status: 'running',
          progress_percent: 50,
          created_at: '2025-01-01T00:00:00Z',
        },
      ];

      useAdminStore.setState({ jobs: initialJobs });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.cancelJob('job-1');
      });

      const job = result.current.jobs.find((j) => j.id === 'job-1');
      expect(job?.status).toBe('cancelled');
    });
  });

  describe('deleteJob', () => {
    it('should remove job from state', async () => {
      const initialJobs: AdminJob[] = [
        {
          id: 'job-1',
          user_id: 'user-1',
          user_email: 'user@example.com',
          prompt: 'Test',
          pipeline: 'quick',
          status: 'completed',
          progress_percent: 100,
          created_at: '2025-01-01T00:00:00Z',
        },
      ];

      useAdminStore.setState({ jobs: initialJobs, totalJobs: 1 });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.deleteJob('job-1');
      });

      expect(result.current.jobs).toEqual([]);
      expect(result.current.totalJobs).toBe(0);
    });
  });

  describe('banUser', () => {
    it('should update user banned status', async () => {
      const initialUsers: AdminUser[] = [
        {
          id: 'user-1',
          email: 'user@example.com',
          created_at: '2025-01-01T00:00:00Z',
          last_sign_in_at: null,
          job_count: 0,
          is_admin: false,
          is_banned: false,
        },
      ];

      useAdminStore.setState({ users: initialUsers });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.banUser('user-1');
      });

      const user = result.current.users.find((u) => u.id === 'user-1');
      expect(user?.is_banned).toBe(true);
    });
  });

  describe('unbanUser', () => {
    it('should update user unbanned status', async () => {
      const initialUsers: AdminUser[] = [
        {
          id: 'user-1',
          email: 'user@example.com',
          created_at: '2025-01-01T00:00:00Z',
          last_sign_in_at: null,
          job_count: 0,
          is_admin: false,
          is_banned: true,
        },
      ];

      useAdminStore.setState({ users: initialUsers });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const { result } = renderHook(() => useAdminStore());

      await act(async () => {
        await result.current.unbanUser('user-1');
      });

      const user = result.current.users.find((u) => u.id === 'user-1');
      expect(user?.is_banned).toBe(false);
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useAdminStore.setState({ error: 'Some error' });

      const { result } = renderHook(() => useAdminStore());

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
