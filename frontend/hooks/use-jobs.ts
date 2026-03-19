'use client';

/**
 * TanStack Query hook for fetching and auto-polling research jobs.
 * Polls every 5s when any job is running or queued.
 */
import { useQuery } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/supabase';
import { API_URL } from '@/lib/constants';
import type { Job } from '@/store/jobs';

const ACTIVE_STATUSES = new Set(['running', 'queued']);

async function fetchJobs(): Promise<Job[]> {
  const token = await getAccessToken();
  const res = await fetch(`${API_URL}/jobs`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
  });
  if (!res.ok) throw new Error(`Failed to fetch jobs: ${res.status}`);
  return res.json();
}

/**
 * List all jobs with conditional auto-polling.
 * Refetches every 5s when any job is active (running/queued).
 */
export function useJobs() {
  return useQuery<Job[], Error>({
    queryKey: ['jobs'],
    queryFn: fetchJobs,
    refetchInterval: (query) => {
      const jobs = query.state.data;
      const hasActive = jobs?.some((j) => ACTIVE_STATUSES.has(j.status));
      return hasActive ? 5000 : false;
    },
  });
}
