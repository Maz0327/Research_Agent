/**
 * iterate-intent — Maps natural language to iteration modes.
 *
 * Users describe what they want in plain English; this maps it to
 * one of the 5 backend iteration modes via keyword matching.
 * No LLM call needed.
 */

import type { IterateMode } from '../types/run';

interface InferredIteration {
  mode: IterateMode;
  /** Pre-filled params extracted from the text */
  angle?: string;
  userPrompt?: string;
  /** Confidence in the match (for UI feedback) */
  confidence: 'high' | 'medium' | 'low';
}

const EXPAND_PATTERNS = [
  /more sources/i,
  /find more/i,
  /add sources/i,
  /additional sources/i,
  /not enough sources/i,
  /need more/i,
  /broaden/i,
  /wider search/i,
  /more perspectives/i,
];

const ANGLE_PATTERNS = [
  /different angle/i,
  /new perspective/i,
  /rewrite/i,
  /different lens/i,
  /from the perspective/i,
  /angle of/i,
  /focus on the .+ side/i,
  /economic angle/i,
  /political angle/i,
  /social angle/i,
  /more casual/i,
  /more dramatic/i,
  /more investigative/i,
  /tone/i,
];

const DEEPER_PATTERNS = [
  /go deeper/i,
  /more detail/i,
  /more depth/i,
  /deeper analysis/i,
  /elaborate/i,
  /expand on/i,
  /dig deeper/i,
  /more thorough/i,
  /flesh out/i,
];

const GAP_PATTERNS = [
  /what.+missing/i,
  /gaps/i,
  /what.+not covered/i,
  /blind spots/i,
  /overlooked/i,
  /unanswered/i,
  /what else/i,
  /open questions/i,
];

/**
 * Infer the iteration mode from a natural language description.
 */
export function inferIterateMode(text: string): InferredIteration {
  const trimmed = text.trim();

  // Check each pattern set in priority order
  if (EXPAND_PATTERNS.some(p => p.test(trimmed))) {
    return { mode: 'expand_sources', userPrompt: trimmed, confidence: 'high' };
  }

  if (ANGLE_PATTERNS.some(p => p.test(trimmed))) {
    return { mode: 'different_angle', angle: trimmed, confidence: 'high' };
  }

  if (DEEPER_PATTERNS.some(p => p.test(trimmed))) {
    return { mode: 'deeper', userPrompt: trimmed, confidence: 'high' };
  }

  if (GAP_PATTERNS.some(p => p.test(trimmed))) {
    return { mode: 'deep_dive', confidence: 'high' };
  }

  // Default: custom mode with the full text as prompt
  return { mode: 'custom', userPrompt: trimmed, confidence: 'low' };
}

/**
 * Generate contextual suggestions based on job data.
 * These appear as clickable chips in the RefinePanel.
 */
export function generateSuggestions(job: {
  title?: string;
  artifacts?: Record<string, unknown>;
}): string[] {
  const suggestions: string[] = [];

  // Always suggest these universal options
  suggestions.push('Find more sources on this topic');
  suggestions.push('Go deeper on the key findings');
  suggestions.push('What am I missing?');
  suggestions.push('Try a more casual tone');

  return suggestions.slice(0, 4);
}
