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
  source_identity: { label: 'Finding your sources', description: 'Fetching videos and articles...' },
  semantic_extraction: { label: 'Reading everything', description: 'Pulling key points from each source...' },
  semantic_validation: { label: 'Checking the facts', description: 'Verifying quotes and claims...' },
  gap_analysis: { label: 'Finding untold angles', description: 'What did nobody else cover?' },
  semantic_synthesis: { label: 'Connecting the dots', description: 'Cross-referencing across all sources...' },
  document_assembly: { label: 'Building your research', description: 'Assembling findings into documents...' },
  completion: { label: 'Done!', description: 'Your research is ready' },

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
  creator_brief_assembly: { label: 'Crafting story angles', description: 'Finding the best narrative hooks...' },

  // Booster stages
  booster_running: { label: 'Deep Research', description: 'Exploring new research directions and filling knowledge gaps…' },

  // Producer stages (Doc 4 — optional)
  producer_running: { label: 'Creating Producer Packet', description: 'Generating production-ready content with B-roll notes and script cues…' },

  // Iteration stages (5 modes via unified iterate endpoint)
  iteration_running: { label: 'Running update', description: 'Processing your research update...' },
  iterate_deep_dive: { label: 'Find What\'s Missing', description: 'Uncovering gaps and new research directions...' },
  iterate_expand_sources: { label: 'Adding More Sources', description: 'Discovering and analyzing new sources...' },
  iterate_deeper: { label: 'Digging Deeper', description: 'Re-analyzing your sources with greater depth...' },
  iterate_different_angle: { label: 'Trying a New Angle', description: 'Same research, fresh perspective...' },
  iterate_custom: { label: 'Custom Request', description: 'Running your custom instructions across the pipeline...' },
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

/**
 * Rough ETA strings per pipeline mode — shown to users during pipeline execution.
 * These are intentionally approximate: users want a ballpark, not a promise.
 */
export const PIPELINE_ETA: Record<string, string> = {
  quick: '~1 min',
  full: '~3 min',
  investigation: '~8 min',
} as const;

/**
 * Get rough ETA label for a pipeline mode
 */
export function getPipelineEta(pipeline: string | null | undefined): string | null {
  if (!pipeline) return null;
  return PIPELINE_ETA[pipeline] ?? null;
}
