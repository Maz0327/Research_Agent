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
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Enforce HTTPS in production to prevent mixed-content issues on mobile
export const API_URL =
  process.env.NODE_ENV === 'production' && rawApiUrl.startsWith('http://')
    ? rawApiUrl.replace('http://', 'https://')
    : rawApiUrl;

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
  /** Maximum prompt/topic length (backend enforces 2000) */
  MAX_PROMPT_LENGTH: 2000,
  /** Maximum transcript jobs */
  MAX_TRANSCRIPT_JOBS: 50,
  /** Maximum text content length for text input (50k chars) */
  MAX_TEXT_CONTENT_LENGTH: 50000,
  /** Minimum text content length for text input */
  MIN_TEXT_CONTENT_LENGTH: 50,
  /** Maximum screenshot file size (10MB) */
  MAX_SCREENSHOT_SIZE: 10 * 1024 * 1024,
} as const;

/** Platform hints for content input modes */
export const PLATFORM_HINTS = [
  { value: 'reddit', label: 'Reddit', icon: '📱' },
  { value: 'twitter', label: 'Twitter/X', icon: '🐦' },
  { value: 'forum', label: 'Forum', icon: '💬' },
  { value: 'email', label: 'Email', icon: '📧' },
  { value: 'article', label: 'Article', icon: '📰' },
  { value: 'other', label: 'Other', icon: '📄' },
] as const;

/** Screenshot platform hints (subset for OCR) */
export const SCREENSHOT_PLATFORM_HINTS = [
  { value: 'reddit', label: 'Reddit', icon: '📱' },
  { value: 'twitter', label: 'Twitter/X', icon: '🐦' },
  { value: 'forum', label: 'Forum', icon: '💬' },
  { value: 'other', label: 'Other', icon: '📄' },
] as const;

/**
 * Stage label mapping - converts backend stage names to user-friendly descriptions.
 * Backend stage names are technical (snake_case), this provides human-readable labels.
 */
export const STAGE_LABELS: Record<string, { label: string; description: string }> = {
  // Main pipeline stages
  source_identity: { label: 'Identifying Sources', description: 'Cataloging and analyzing your source content…' },
  semantic_extraction: { label: 'Extracting Claims', description: 'Pulling key points, claims, and quotes from each source…' },
  semantic_validation: { label: 'Validating Claims', description: 'Cross-checking extracted claims for accuracy…' },
  gap_analysis: { label: 'Finding Gaps', description: 'Identifying missing research angles and blind spots…' },
  semantic_synthesis: { label: 'Connecting Themes', description: 'Finding patterns and tensions across all sources…' },
  document_assembly: { label: 'Assembling Documents', description: 'Building your research documents from validated insights…' },
  completion: { label: 'Finalizing', description: 'Wrapping up and saving your research…' },

  // Transcript stages
  extracting_transcripts: { label: 'Extracting Transcripts', description: 'Getting video transcripts' },
  storing_transcripts: { label: 'Saving Transcripts', description: 'Storing extracted transcripts' },

  // Video analysis stages
  pass_1_extraction: { label: 'Video Analysis', description: 'Analyzing video content' },

  // Evolving job stages (add sources flow)
  evolving_source_identity: { label: 'Processing New Sources', description: 'Analyzing added sources' },
  evolving_extraction: { label: 'Extracting New Content', description: 'Processing added source content' },
  evolving_validation: { label: 'Validating Additions', description: 'Verifying new source content' },
  evolving_gap_analysis: { label: 'Updating Gaps', description: 'Reassessing research gaps' },
  cross_reference: { label: 'Cross-Referencing', description: 'Comparing new and existing sources' },
  addendum_assembly: { label: 'Creating Addendum', description: 'Assembling updated documents' },
  evolving_complete: { label: 'Update Complete', description: 'Source addition completed' },

  // Status stages
  completed: { label: 'Completed', description: 'Research complete' },
  error: { label: 'Error', description: 'An error occurred' },
  timeout: { label: 'Timed Out', description: 'Process took too long' },
  no_pending_sources: { label: 'No Pending Sources', description: 'Nothing to process' },

  // Creator Brief stage
  creator_brief_assembly: { label: 'Assembling Creator Brief', description: 'Distilling hooks, core facts, and narrative structure from your research…' },

  // Booster stages
  booster_running: { label: 'Deep Research', description: 'Exploring new research directions and filling knowledge gaps…' },

  // Producer stages (Doc 4 — optional)
  producer_running: { label: 'Creating Producer Packet', description: 'Generating production-ready content with B-roll notes and script cues…' },

  // Iteration stages (5 modes via unified iterate endpoint)
  iteration_running: { label: 'Running Iteration', description: 'Processing your research iteration…' },
  iterate_deep_dive: { label: 'Deep Dive', description: 'Searching for gaps and unexplored research directions…' },
  iterate_expand_sources: { label: 'Expanding Sources', description: 'Discovering and analyzing new sources for your research…' },
  iterate_deeper: { label: 'Going Deeper', description: 'Re-extracting your sources with greater depth and detail…' },
  iterate_different_angle: { label: 'Different Angle', description: 'Re-analyzing your research from a fresh perspective…' },
  iterate_custom: { label: 'Custom Iteration', description: 'Running your custom instructions across the pipeline…' },
} as const;

/**
 * Get user-friendly stage label with fallback
 */
export function getStageLabel(stage: string | null | undefined): string {
  if (!stage) return 'Running';
  const info = STAGE_LABELS[stage];
  return info?.label || stage.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Get stage description for additional context
 */
export function getStageDescription(stage: string | null | undefined): string | null {
  if (!stage) return null;
  return STAGE_LABELS[stage]?.description || null;
}
