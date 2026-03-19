'use client';

/**
 * TanStack Query mutation hook for previewing/disambiguating a job topic
 * before creation. Returns a JobPreview with possible interpretations.
 */
import { useMutation } from '@tanstack/react-query';
import { getAccessToken } from '@/lib/supabase';
import { API_URL } from '@/lib/constants';
import type { JobPreview } from '@/store/jobs';

interface PreviewJobPayload {
  topic: string;
  pipeline?: string;
  source_urls?: string[];
  niche?: string;
}

async function previewJob(payload: PreviewJobPayload): Promise<JobPreview> {
  const token = await getAccessToken();
  const res = await fetch(`${API_URL}/jobs/preview`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Preview failed: ${res.status}`);
  }
  return res.json();
}

/**
 * Mutation hook for previewing a job before creation.
 * Use mutateAsync to await and inspect the JobPreview result.
 */
export function usePreviewJob() {
  return useMutation<JobPreview, Error, PreviewJobPayload>({
    mutationFn: previewJob,
  });
}
