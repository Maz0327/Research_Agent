/**
 * V2 Run Types - TypeScript definitions for Run Abstraction
 *
 * These types mirror the backend Run models for type-safe frontend usage.
 */

/** Run execution status */
export type RunStatus = 'queued' | 'running' | 'completed' | 'failed';

/** Run types supported by the system */
export type RunType =
  | 'baseline'
  | 'add_sources'
  | 'fix_weak'
  | 'counter'
  | 'angle'
  | 'regenerate';

/** Display labels for run types */
export const RUN_TYPE_LABELS: Record<RunType, string> = {
  baseline: 'Baseline',
  add_sources: 'Add Sources',
  fix_weak: 'Fix Weak Spots',
  counter: 'Counterargument',
  angle: 'Different Angle',
  regenerate: 'Regenerate',
};

/** Run type icons/badges */
export const RUN_TYPE_ICONS: Record<RunType, string> = {
  baseline: '●',
  add_sources: '+',
  fix_weak: '🔧',
  counter: '⚖️',
  angle: '↗️',
  regenerate: '🔄',
};

/** Run request parameters */
export interface RunRequest {
  user_prompt?: string;
  new_source_urls?: string[];
  max_new_sources?: number;
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
  const typeLabel = RUN_TYPE_LABELS[run.run_type] || run.run_type;
  if (run.run_type === 'baseline') {
    return 'Baseline (original)';
  }
  return `${run.run_id} - ${typeLabel}`;
}

/** Helper to get run icon */
export function getRunIcon(runType: RunType): string {
  return RUN_TYPE_ICONS[runType] || '○';
}
