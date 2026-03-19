'use client';

/**
 * TanStack Query hook for fetching a single job with auto-polling.
 * Polls every 3s while job is running or queued.
 */
import { useQuery } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/supabase';
import { API_URL } from '@/lib/constants';
import type { Job } from '@/store/jobs';

async function fetchJob(jobId: string): Promise<Job> {
  const token = await getAccessToken();
  const res = await fetch(`${API_URL}/jobs/${jobId}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.status}`);
  return res.json();
}

/**
 * Single job detail with conditional polling.
 * Refetches every 3s when job is active (running/queued).
 */
export function useJobDetail(jobId: string) {
  return useQuery<Job, Error>({
    queryKey: ['job', jobId],
    queryFn: () => fetchJob(jobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      return job?.status === 'running' || job?.status === 'queued' ? 3000 : false;
    },
    enabled: !!jobId,
  });
}
