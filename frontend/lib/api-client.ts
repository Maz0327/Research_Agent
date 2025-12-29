/**
 * Centralized API client with timeout support.
 *
 * Provides consistent fetch behavior across the frontend:
 * - Request timeout handling
 * - Authorization header injection
 * - Consistent error handling
 */

import { API_CONFIG, API_URL } from './constants';

// Re-export for backwards compatibility
export { API_URL };

interface FetchOptions extends RequestInit {
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
}

/**
 * Fetch with timeout support.
 *
 * @param endpoint - API endpoint (relative or absolute URL)
 * @param options - Fetch options including timeout
 * @returns Response object
 * @throws Error if request times out or fails
 */
export async function apiFetch(
  endpoint: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { timeout = API_CONFIG.DEFAULT_TIMEOUT, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;
    const response = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
    });
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Authenticated fetch with authorization header.
 *
 * @param endpoint - API endpoint (relative or absolute URL)
 * @param token - Bearer token for authorization
 * @param options - Fetch options including timeout
 * @returns Response object
 */
export async function authFetch(
  endpoint: string,
  token: string | null,
  options: FetchOptions = {}
): Promise<Response> {
  return apiFetch(endpoint, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });
}

/**
 * Parse JSON response with error handling.
 *
 * @param response - Fetch Response object
 * @returns Parsed JSON data
 * @throws Error if response is not OK or JSON parsing fails
 */
export async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch {
      // Ignore JSON parsing errors for error responses
    }
    throw new Error(errorMessage);
  }

  try {
    return await response.json();
  } catch {
    throw new Error('Invalid JSON response');
  }
}
