/**
 * Tests for the jobs Zustand store.
 */
import { act, renderHook } from '@testing-library/react';
import { useJobsStore, Job } from '../../store/jobs';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock getAccessToken
jest.mock('../../lib/supabase', () => ({
  getAccessToken: jest.fn().mockResolvedValue('mock-token'),
}));

describe('useJobsStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useJobsStore());
    act(() => {
      result.current.clearJobs();
    });
    mockFetch.mockClear();
  });

  describe('initial state', () => {
    it('should have empty jobs array initially', () => {
      const { result } = renderHook(() => useJobsStore());
      expect(result.current.jobs).toEqual([]);
    });

    it('should have isLoading false initially', () => {
      const { result } = renderHook(() => useJobsStore());
      expect(result.current.isLoading).toBe(false);
    });

    it('should have null error initially', () => {
      const { result } = renderHook(() => useJobsStore());
      expect(result.current.error).toBeNull();
    });
  });

  describe('fetchJobs', () => {
    it('should fetch jobs successfully', async () => {
      const mockJobs: Job[] = [
        {
          id: 'job-1',
          prompt: 'Test prompt',
          pipeline: 'investigation',
          status: 'completed',
          progress_percent: 100,
          created_at: '2025-01-01T00:00:00Z',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ jobs: mockJobs }),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.jobs).toEqual(mockJobs);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.error).toBe('Failed to fetch jobs');
      expect(result.current.isLoading).toBe(false);
    });

    it('should set session expired error on 401', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.jobs).toEqual([]);
      expect(result.current.error).toContain('Session expired');
    });

    it('should handle invalid JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => { throw new Error('Invalid JSON'); },
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.error).toContain('Invalid response');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      expect(result.current.error).toBe('Network error');
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('createJob', () => {
    it('should create job and add to state', async () => {
      const mockJobId = 'new-job-123';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: mockJobId }),
      });

      const { result } = renderHook(() => useJobsStore());

      let returnedId: string;
      await act(async () => {
        returnedId = await result.current.createJob('Test topic', 'investigation');
      });

      expect(returnedId!).toBe(mockJobId);
      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.jobs[0].id).toBe(mockJobId);
      expect(result.current.jobs[0].status).toBe('queued');
    });

    it('should throw on create error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useJobsStore());

      await expect(
        act(async () => {
          await result.current.createJob('Test topic', 'investigation');
        })
      ).rejects.toThrow('Failed to create job');
    });
  });

  describe('refreshJob', () => {
    it('should update job with new data', async () => {
      // Setup initial state with a job
      const initialJob: Job = {
        id: 'job-1',
        prompt: 'Test prompt',
        pipeline: 'investigation',
        status: 'running',
        progress_percent: 50,
        created_at: '2025-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ jobs: [initialJob] }),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      // Now refresh with updated data
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'completed',
          progress_percent: 100,
          title: 'Generated Title',
        }),
      });

      await act(async () => {
        await result.current.refreshJob('job-1');
      });

      expect(result.current.jobs[0].status).toBe('completed');
      expect(result.current.jobs[0].progress_percent).toBe(100);
      expect(result.current.jobs[0].title).toBe('Generated Title');
    });
  });

  describe('cancelJob', () => {
    it('should update job status to cancelled', async () => {
      // Setup initial state with a job
      const initialJob: Job = {
        id: 'job-1',
        prompt: 'Test prompt',
        pipeline: 'investigation',
        status: 'running',
        progress_percent: 50,
        created_at: '2025-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ jobs: [initialJob] }),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.fetchJobs();
      });

      // Cancel the job
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await act(async () => {
        await result.current.cancelJob('job-1');
      });

      expect(result.current.jobs[0].status).toBe('cancelled');
    });
  });

  describe('clearJobs', () => {
    it('should clear all jobs and errors', async () => {
      // Add a job first
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: 'job-1' }),
      });

      const { result } = renderHook(() => useJobsStore());

      await act(async () => {
        await result.current.createJob('Test', 'quick');
      });

      expect(result.current.jobs).toHaveLength(1);

      act(() => {
        result.current.clearJobs();
      });

      expect(result.current.jobs).toEqual([]);
      expect(result.current.error).toBeNull();
    });
  });
});
