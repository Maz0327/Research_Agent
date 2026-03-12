/**
 * V2 Run Types - TypeScript definitions for Run Abstraction
 *
 * These types mirror the backend Run models for type-safe frontend usage.
 *
 * Run types:
 * - baseline: Initial research run
 * - expand: Add new sources + append findings to Doc 0/1/2
 * - refine: Re-analyze existing sources from new angle, append to Doc 1/2
 * - regenerate: Full rewrite of Doc 1/2 from all sources
 */

/** Run execution status */
export type RunStatus = 'queued' | 'running' | 'awaiting_review' | 'completed' | 'failed';

/** Canonical run types */
export type RunType =
  | 'baseline'
  | 'expand'
  | 'refine'
  | 'regenerate'
  // Legacy aliases (for backward compatibility with stored data)
  | 'add_sources'
  | 'fix_weak'
  | 'counter'
  | 'angle';

/** Display labels for run types */
export const RUN_TYPE_LABELS: Record<RunType, string> = {
  baseline: 'Baseline',
  expand: 'Expand Sources',
  refine: 'Refine Analysis',
  regenerate: 'Regenerate',
  // Legacy labels
  add_sources: 'Expand Sources',
  fix_weak: 'Refine Analysis',
  counter: 'Expand Sources',
  angle: 'Refine Analysis',
};

/** Run type icons/badges */
export const RUN_TYPE_ICONS: Record<RunType, string> = {
  baseline: '●',
  expand: '+',
  refine: '🔍',
  regenerate: '🔄',
  // Legacy icons
  add_sources: '+',
  fix_weak: '🔍',
  counter: '+',
  angle: '🔍',
};

/** Badge colors for run types */
export const RUN_TYPE_COLORS: Record<string, string> = {
  baseline: 'gray',
  expand: 'blue',
  refine: 'orange',
  regenerate: 'red',
  // Legacy mappings
  add_sources: 'blue',
  fix_weak: 'orange',
  counter: 'blue',
  angle: 'orange',
};

/** Normalize legacy run type to canonical type */
export function normalizeRunType(runType: string): 'expand' | 'refine' | 'regenerate' | 'baseline' {
  const legacyMap: Record<string, 'expand' | 'refine' | 'regenerate' | 'baseline'> = {
    add_sources: 'expand',
    fix_weak: 'refine',
    counter: 'expand',
    angle: 'refine',
    baseline: 'baseline',
    expand: 'expand',
    refine: 'refine',
    regenerate: 'regenerate',
  };
  return legacyMap[runType] || 'regenerate';
}

// =============================================================================
// Iterate System (unified 5-mode iteration via POST /jobs/{job_id}/iterate)
// =============================================================================

/** The 5 iterate modes supported by the unified iterate endpoint */
export type IterateMode = 'deep_dive' | 'expand_sources' | 'deeper' | 'different_angle' | 'custom';

/** Request body for POST /jobs/{job_id}/iterate */
export interface IterateRequest {
  mode: IterateMode;
  /** URLs to add (expand_sources mode) */
  new_source_urls?: string[];
  /** Max sources to auto-discover (expand_sources mode, 1-10, default 4) */
  max_new_sources?: number;
  /** New perspective to explore (different_angle mode — required) */
  angle?: string;
  /** Custom instructions (custom mode — required; deeper mode — optional) */
  user_prompt?: string;
}

/** Display configuration for iterate modes */
export const ITERATE_MODE_CONFIG: Record<IterateMode, {
  label: string;
  description: string;
  icon: string;
  color: string;
  docsAffected: string;
}> = {
  deep_dive: {
    label: 'Deep Dive',
    description: 'Find gaps and search directions',
    icon: '🔬',
    color: 'blue',
    docsAffected: 'Doc 1',
  },
  expand_sources: {
    label: 'Expand Sources',
    description: 'Add more sources and re-run pipeline',
    icon: '➕',
    color: 'green',
    docsAffected: 'Doc 0/1/2/3',
  },
  deeper: {
    label: 'Go Deeper',
    description: 'Re-extract with more detail',
    icon: '🔍',
    color: 'purple',
    docsAffected: 'Doc 0/1/2/3',
  },
  different_angle: {
    label: 'Different Angle',
    description: 'Same data, new perspective',
    icon: '🔄',
    color: 'orange',
    docsAffected: 'Doc 2/3',
  },
  custom: {
    label: 'Custom',
    description: 'Your own instructions',
    icon: '✏️',
    color: 'gray',
    docsAffected: 'Varies',
  },
};

// =============================================================================
// Search Candidates
// =============================================================================

/** Search candidate from grounded search */
export interface SearchCandidate {
  url: string;
  title: string;
  snippet: string;
  relevance_score: number;
  provider: string;
}

/** Run request parameters */
export interface RunRequest {
  user_prompt?: string;
  new_source_urls?: string[];
  max_new_sources?: number;
  search_mode?: 'auto' | 'manual';
  trust_mode?: boolean;
  search_candidates?: SearchCandidate[];
  // Legacy fields
  gap_ids?: string[];
  claim_ids?: string[];
  perspective?: string;
  requested_by: string;
  requested_at: string;
}

/** Run outputs (document paths) */
export interface RunOutputs {
  doc_0_path?: string;
  doc_1_path?: string;
  doc_2_path?: string;
  doc_0_inline?: Record<string, unknown>;
  doc_1_inline?: Record<string, unknown>;
  doc_2_inline?: Record<string, unknown>;
  doc_0_is_delta: boolean;
  doc_0_parent_path?: string;
  new_source_ids?: string[];
  // Append metadata
  doc_1_is_append?: boolean;
  doc_2_is_append?: boolean;
  doc_1_parent_path?: string;
  doc_2_parent_path?: string;
}

/** Run metrics */
export interface RunMetrics {
  wall_time_ms: number;
  sources_processed: number;
  sources_new: number;
  key_points_found: number;
  claims_extracted: number;
  themes_identified: number;
  llm_cost_usd: number;
  llm_tokens_input: number;
  llm_tokens_output: number;
}

/** Run error details */
export interface RunError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** Run-scoped producer packet */
export interface RunProducerPacket {
  status: RunStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  path?: string;
  inline?: Record<string, unknown>;
  markdown?: string;
  error?: string;
}

/** Run-scoped booster expansion */
export interface RunBoosterExpansion {
  status: RunStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  output?: Record<string, unknown>;
  markdown?: string;
  error?: string;
}

/** V2 Run object */
export interface Run {
  run_id: string;
  run_index: number;
  run_type: RunType;
  parent_run_id?: string;
  status: RunStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  request: RunRequest;
  outputs?: RunOutputs;
  metrics?: RunMetrics;
  error?: RunError;
  producer_packet?: RunProducerPacket;
  booster_expansion?: RunBoosterExpansion;
}

/** Helper to check if a version ID is a V2 run */
export function isV2Run(versionId: string): boolean {
  return versionId.startsWith('run_');
}

/** Helper to get run display label */
export function getRunLabel(run: Run): string {
  const canonical = normalizeRunType(run.run_type);
  const typeLabel = RUN_TYPE_LABELS[canonical] || run.run_type;
  if (canonical === 'baseline') {
    return 'Baseline (original)';
  }
  return `${run.run_id} - ${typeLabel}`;
}

/** Helper to get run icon */
export function getRunIcon(runType: RunType): string {
  return RUN_TYPE_ICONS[runType] || '○';
}

/** Helper to get run badge color */
export function getRunColor(runType: RunType): string {
  return RUN_TYPE_COLORS[runType] || 'gray';
}
