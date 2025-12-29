/**
 * Error handling utilities for consistent error formatting.
 */

/**
 * Format an error into a user-friendly message.
 *
 * @param error - The error to format (can be Error, string, or unknown)
 * @param fallback - Fallback message if error cannot be formatted
 * @returns A formatted error message string
 */
export function formatError(error: unknown, fallback: string = 'An unexpected error occurred'): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
}

/**
 * Extract error message from API response.
 *
 * @param response - The response object or error
 * @param fallback - Fallback message
 * @returns Extracted error message
 */
export function formatApiError(
  response: unknown,
  fallback: string = 'API request failed'
): string {
  if (response && typeof response === 'object') {
    const resp = response as Record<string, unknown>;
    if (typeof resp.detail === 'string') {
      return resp.detail;
    }
    if (typeof resp.error === 'string') {
      return resp.error;
    }
    if (typeof resp.message === 'string') {
      return resp.message;
    }
  }
  return formatError(response, fallback);
}

/**
 * Log errors in development mode only.
 *
 * @param message - Log message prefix
 * @param error - The error to log
 */
export function logError(message: string, error: unknown): void {
  if (process.env.NODE_ENV === 'development') {
    console.error(message, error);
  }
}

/**
 * Log warnings in development mode only.
 *
 * @param message - Log message prefix
 * @param data - Additional data to log
 */
export function logWarning(message: string, data?: unknown): void {
  if (process.env.NODE_ENV === 'development') {
    if (data !== undefined) {
      console.warn(message, data);
    } else {
      console.warn(message);
    }
  }
}

/**
 * Log debug information in development mode only.
 *
 * @param message - Log message prefix
 * @param data - Additional data to log
 */
export function logDebug(message: string, data?: unknown): void {
  if (process.env.NODE_ENV === 'development') {
    if (data !== undefined) {
      console.log(message, data);
    } else {
      console.log(message);
    }
  }
}
