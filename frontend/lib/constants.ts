/**
 * Application constants for consistent configuration across the frontend.
 */

/** Polling intervals in milliseconds */
export const POLLING_INTERVALS = {
  /** Job status polling interval (2 seconds) */
  JOB_STATUS: 2000,
  /** Transcript job polling interval (2 seconds) */
  TRANSCRIPTS: 2000,
  /** ETA update interval (1 second) */
  ETA_UPDATE: 1000,
  /** Dashboard refresh interval (30 seconds) */
  DASHBOARD_REFRESH: 30000,
} as const;

/** Maximum error retry counts before giving up */
export const MAX_RETRY_COUNTS = {
  /** Maximum polling errors before stopping */
  POLLING: 5,
  /** Maximum API request retries */
  API_REQUEST: 3,
} as const;

/** API configuration */
export const API_CONFIG = {
  /** Default request timeout in milliseconds */
  DEFAULT_TIMEOUT: 30000,
  /** Jobs per page default */
  JOBS_PER_PAGE: 10,
} as const;

/** UI timing constants */
export const UI_TIMING = {
  /** Toast/notification display duration */
  TOAST_DURATION: 3000,
  /** Debounce delay for search inputs */
  SEARCH_DEBOUNCE: 300,
  /** Animation duration for transitions */
  ANIMATION_DURATION: 200,
} as const;

/** Centralized API URL - use this instead of defining locally in stores */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Validation limits for form inputs and business logic */
export const VALIDATION_LIMITS = {
  /** Maximum consecutive poll errors before stopping */
  MAX_POLL_ERRORS: 5,
  /** Maximum Drive folders to display */
  MAX_DRIVE_FOLDERS: 3,
  /** Maximum username length */
  MAX_USERNAME_LENGTH: 30,
  /** Minimum username length */
  MIN_USERNAME_LENGTH: 3,
  /** Maximum prompt/topic length */
  MAX_PROMPT_LENGTH: 500,
  /** Maximum transcript jobs */
  MAX_TRANSCRIPT_JOBS: 50,
} as const;
