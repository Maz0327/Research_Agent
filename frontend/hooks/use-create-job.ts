'use client';

/**
 * TanStack Query mutation hook for creating a new research job.
 * Invalidates the ['jobs'] query on success to trigger a refetch.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/supabase';
import { API_URL } from '@/lib/constants';
import type { Job } from '@/store/jobs';

interface CreateJobPayload {
  topic: string;
  pipeline?: string;
  source_urls?: string[];
  niche?: string;
}

async function createJob(payload: CreateJobPayload): Promise<Job> {
  const token = await getAccessToken();
  const res = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Failed to create job: ${res.status}`);
  }
  return res.json();
}

/**
 * Mutation hook for creating a research job.
 * Invalidates ['jobs'] cache on success so the list refreshes immediately.
 */
export function useCreateJob() {
  const queryClient = useQueryClient();

  return useMutation<Job, Error, CreateJobPayload>({
    mutationFn: createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}
