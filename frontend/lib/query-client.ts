/**
 * TanStack Query client configuration.
 * Singleton client used across the App Router layout.
 */
import { QueryClient } from '@tanstack/react-query';

/**
 * Creates a configured QueryClient with sensible defaults for this app:
 * - staleTime: 60s — avoid refetching fresh data on window focus
 * - retry: 1 — retry failed requests once before surfacing error
 * - refetchOnWindowFocus: false — prevents noisy background refetches
 */
export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

// Browser-side singleton — avoids creating a new client on every render
let browserQueryClient: QueryClient | undefined = undefined;

export function getQueryClient() {
  if (typeof window === 'undefined') {
    // Server: always create a new client per request
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
