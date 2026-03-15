/**
 * Document presentation layer formatters.
 *
 * Transforms internal IDs and data to user-friendly display formats
 * WITHOUT modifying the underlying stored JSON.
 *
 * Internal IDs remain stable for cross-references; this layer only
 * affects UI and PDF rendering.
 */

// =============================================================================
// ID Formatting
// =============================================================================

/**
 * ID prefix to human-readable label mapping.
 */
const ID_LABEL_MAP: Record<string, string> = {
  SRC: 'Source',
  KP: 'Key Point',
  CLM: 'Claim',
  QT: 'Quote',
  OBS: 'Observation',
  THEME: 'Theme',
  TEN: 'Tension',
  GAP: 'Open Question',
  REF: 'Reference',
  EV: 'Evidence',
  ANG: 'Angle',
};

/**
 * Convert internal ID to user-facing label.
 *
 * @example
 * formatInternalId('SRC_1')     // → "Source 1"
 * formatInternalId('KP_12')     // → "Key Point 12"
 * formatInternalId('GAP_3')     // → "Open Question 3"
 * formatInternalId('THEME_2')   // → "Theme 2"
 * formatInternalId('unknown')   // → "unknown" (passthrough)
 */
export function formatInternalId(id: string): string {
  if (!id) return id;

  // Match pattern: PREFIX_NUMBER (e.g., SRC_1, KP_12, THEME_2)
  const match = id.match(/^([A-Z]+)_(\d+)$/);
  if (!match) return id;

  const [, prefix, number] = match;
  const label = ID_LABEL_MAP[prefix];

  if (!label) return id;
  return `${label} ${number}`;
}

/**
 * Format ID with internal reference shown as secondary text.
 *
 * @example
 * formatIdWithRef('SRC_1')  // → "Source 1 (SRC_1)"
 */
export function formatIdWithRef(id: string): string {
  const formatted = formatInternalId(id);
  if (formatted === id) return id;
  return `${formatted} (${id})`;
}

// =============================================================================
// Timestamp Formatting
// =============================================================================

/**
 * Format a timestamp for user display.
 *
 * @param dateStr - ISO date string, Date object, or null/undefined
 * @param options - Intl.DateTimeFormatOptions override
 * @returns Formatted date string or empty string if invalid
 */
export function formatTimestamp(
  dateStr: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateStr) return '';

  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    if (isNaN(date.getTime())) return '';

    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...options,
    };

    return date.toLocaleDateString('en-US', defaultOptions);
  } catch {
    return '';
  }
}

/**
 * Format timestamp with relative indicator (e.g., "Jan 15, 2026 (3 days ago)").
 */
export function formatTimestampWithRelative(
  dateStr: string | Date | null | undefined
): string {
  const formatted = formatTimestamp(dateStr);
  if (!formatted) return '';

  try {
    const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr;
    if (!date || isNaN(date.getTime())) return formatted;

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return `${formatted} (today)`;
    if (diffDays === 1) return `${formatted} (yesterday)`;
    if (diffDays < 7) return `${formatted} (${diffDays} days ago)`;
    if (diffDays < 30) return `${formatted} (${Math.floor(diffDays / 7)} weeks ago)`;

    return formatted;
  } catch {
    return formatted;
  }
}

// =============================================================================
// Document Markdown Preprocessor
// =============================================================================

/**
 * Preprocess raw document markdown to fix known rendering issues before display.
 *
 * Fixes applied (in order):
 * 1. Strip "> > " nested blockquote artifacts from doc headers
 * 2. Transform tree branch chars (├──, └──, │) into clean bullet lists
 * 3. Remove duplicate "Single-source claim (...)" lines
 * 4. Remove ALL-CAPS template title headers (already shown in modal header)
 */
export function preprocessDocumentMarkdown(markdown: string): string {
  if (!markdown) return markdown;

  let result = markdown;

  // Fix 1: Strip "> > " artifacts (nested blockquotes that render as literal "> >")
  // Pattern: lines starting with "> > " — flatten to just the content
  result = result.replace(/^> > /gm, '');

  // Fix 2: Transform tree branch lines into clean indented markdown lists
  // Detect blocks of lines starting with tree chars and convert them
  result = result.replace(
    /((?:^[ \t]*[├└│][─ ][^\n]*\n?)+)/gm,
    (block) => {
      const lines = block.split('\n').filter(line => line.trim());
      const converted = lines.map(line => {
        const trimmed = line.trim();
        // Skip pure connector lines (│ alone or │   )
        if (/^│\s*$/.test(trimmed)) return null;
        // Strip tree prefix chars
        const content = trimmed.replace(/^[├└│][─ ]+/, '').trim();
        if (!content) return null;
        // Convert pipe-separated source citations: "text | (Source X)" → "text *(Source X)*"
        const withCitation = content.replace(/\s*\|\s*(\(Source[^)]+\))/g, ' *$1*');
        // Determine indent level from original indentation
        const indent = line.match(/^([ \t]*)/)?.[1] ?? '';
        const depth = Math.floor(indent.length / 2);
        const prefix = '  '.repeat(depth) + '- ';
        return prefix + withCitation;
      }).filter(Boolean);
      return converted.join('\n') + '\n';
    }
  );

  // Fix 3: Remove duplicate "Single-source claim (X only — verify independently)" lines
  // These always repeat the parenthetical already on the previous bullet line
  result = result.replace(/^Single-source claim \([^)]+only[^)]*\)\s*$/gm, '');

  // Fix 4: Remove ALL-CAPS document template title headers
  // The modal header already shows the doc name — these add visual noise
  result = result.replace(
    /^(SEMANTIC RESEARCH BRIEF|RESEARCH BRIEF|SOURCE LEDGER|CREATOR BRIEF|JUMP-START DIRECTIONS|PRODUCER PACKET)\s*$/gm,
    ''
  );

  // Clean up any triple+ blank lines left by removals
  result = result.replace(/\n{3,}/g, '\n\n');

  return result;
}

// =============================================================================
// Markdown Transformation
// =============================================================================

/**
 * Protected content placeholder for code blocks and URLs during transformation.
 * Uses a unique token that won't appear in real content.
 */
const PLACEHOLDER_PREFIX = '\u0000PROTECTED_';
const PLACEHOLDER_SUFFIX = '_END\u0000';

/**
 * Extract protected sections (code blocks, URLs) and replace with placeholders.
 * Returns the modified text and a map of placeholders to original content.
 */
function protectSections(text: string): { text: string; protected: Map<string, string> } {
  const protectedMap = new Map<string, string>();
  let counter = 0;
  let result = text;

  // Protect fenced code blocks (``` ... ```)
  result = result.replace(/```[\s\S]*?```/g, (match) => {
    const placeholder = `${PLACEHOLDER_PREFIX}CODE_${counter++}${PLACEHOLDER_SUFFIX}`;
    protectedMap.set(placeholder, match);
    return placeholder;
  });

  // Protect inline code (`...`)
  result = result.replace(/`[^`\n]+`/g, (match) => {
    const placeholder = `${PLACEHOLDER_PREFIX}INLINE_${counter++}${PLACEHOLDER_SUFFIX}`;
    protectedMap.set(placeholder, match);
    return placeholder;
  });

  // Protect markdown links [text](url)
  result = result.replace(/\[[^\]]*\]\([^)]+\)/g, (match) => {
    const placeholder = `${PLACEHOLDER_PREFIX}LINK_${counter++}${PLACEHOLDER_SUFFIX}`;
    protectedMap.set(placeholder, match);
    return placeholder;
  });

  // Protect bare URLs (http:// or https://)
  result = result.replace(/https?:\/\/[^\s<>"]+/g, (match) => {
    const placeholder = `${PLACEHOLDER_PREFIX}URL_${counter++}${PLACEHOLDER_SUFFIX}`;
    protectedMap.set(placeholder, match);
    return placeholder;
  });

  return { text: result, protected: protectedMap };
}

/**
 * Restore protected sections from placeholders.
 */
function restoreProtectedSections(text: string, protectedMap: Map<string, string>): string {
  let result = text;
  protectedMap.forEach((original, placeholder) => {
    result = result.replace(placeholder, original);
  });
  return result;
}

/**
 * Transform markdown content for user-friendly display.
 *
 * This replaces internal IDs with readable labels throughout the
 * markdown content without modifying the stored JSON.
 *
 * SAFETY: Does NOT transform IDs inside:
 * - Code blocks (fenced or inline)
 * - URLs (bare or markdown links)
 *
 * @param markdown - Raw markdown content
 * @returns Transformed markdown with user-friendly labels
 */
export function transformMarkdownForDisplay(markdown: string): string {
  if (!markdown) return markdown;

  // Step 0: Fix known rendering artifacts before any transformation
  const preprocessed = preprocessDocumentMarkdown(markdown);

  // Step 1: Protect code blocks and URLs from transformation
  const { text: safeText, protected: protectedMap } = protectSections(preprocessed);

  let result = safeText;

  // Step 2: Replace standalone IDs (e.g., "SRC_1" → "Source 1")
  // Pattern matches IDs at word boundaries, not part of other strings
  Object.keys(ID_LABEL_MAP).forEach((prefix) => {
    const label = ID_LABEL_MAP[prefix];
    // Match PREFIX_NUMBER with word boundaries
    const pattern = new RegExp(`(?<![/\\w])${prefix}_(\\d+)(?![\\w])`, 'g');
    result = result.replace(pattern, `${label} $1`);
  });

  // Step 3: Normalize section headings for readability
  result = normalizeHeadings(result);

  // Step 4: Restore protected sections
  result = restoreProtectedSections(result, protectedMap);

  return result;
}

/**
 * Transform markdown with optional Details toggle to reveal internal IDs.
 *
 * When showDetails=true, IDs are shown as "Source 1 (SRC_1)"
 * When showDetails=false, IDs are shown as "Source 1"
 *
 * @param markdown - Raw markdown content
 * @param showDetails - Whether to show internal IDs in parentheses
 * @returns Transformed markdown
 */
export function transformMarkdownWithDetails(markdown: string, showDetails: boolean): string {
  if (!markdown) return markdown;

  // Step 0: Fix known rendering artifacts
  const preprocessed = preprocessDocumentMarkdown(markdown);

  // Step 1: Protect code blocks and URLs
  const { text: safeText, protected: protectedMap } = protectSections(preprocessed);

  let result = safeText;

  // Step 2: Replace IDs with optional internal reference
  Object.keys(ID_LABEL_MAP).forEach((prefix) => {
    const label = ID_LABEL_MAP[prefix];
    const pattern = new RegExp(`(?<![/\\w])(${prefix}_(\\d+))(?![\\w])`, 'g');

    if (showDetails) {
      // Show both: "Source 1 (SRC_1)"
      result = result.replace(pattern, `${label} $2 ($1)`);
    } else {
      // Show friendly only: "Source 1"
      result = result.replace(pattern, `${label} $2`);
    }
  });

  // Step 3: Normalize headings
  result = normalizeHeadings(result);

  // Step 4: Restore protected sections
  result = restoreProtectedSections(result, protectedMap);

  return result;
}

/**
 * Normalize section headings to user-friendly names.
 */
function normalizeHeadings(markdown: string): string {
  const headingMap: Record<string, string> = {
    // Doc 0 - Source Ledger
    'Source Manifest': 'Sources Analyzed',
    'source_manifest': 'Sources Analyzed',
    'Transcript Provenance': 'Transcript Quality',
    'transcript_provenance': 'Transcript Quality',
    'Skim Summary': 'Quick Summary',
    'skim_summary': 'Quick Summary',
    'Confidence Ceiling': 'Confidence Level',
    'confidence_ceiling': 'Confidence Level',

    // Doc 1 - Jump-Start
    'Key Points': 'Key Takeaways',
    'key_points': 'Key Takeaways',
    'Research Gaps': 'Open Questions',
    'research_gaps': 'Open Questions',
    'Suggested Directions': 'What to Do Next',
    'suggested_directions': 'What to Do Next',
    'Missing Angles': 'Unexplored Angles',
    'missing_angles': 'Unexplored Angles',

    // Doc 2 - Semantic Brief
    'Cross-Source Themes': 'Patterns & Insights',
    'cross_source_themes': 'Patterns & Insights',
    'Source Tensions': 'Where Sources Disagree',
    'source_tensions': 'Where Sources Disagree',
    'Evidence Summary': 'Evidence Overview',
    'evidence_summary': 'Evidence Overview',
    'Verified Claims': 'Confirmed Facts',
    'verified_claims': 'Confirmed Facts',
    'Unverified Claims': 'Unconfirmed Claims',
    'unverified_claims': 'Unconfirmed Claims',

    // Doc 1 - Jump-Start (typed renderer renames)
    'Research Threads': 'What We Found',
    'Cross-Cutting Analysis': 'What Multiple Sources Agree On',
    'cross_cutting_analysis': 'What Multiple Sources Agree On',

    // Doc 2 - Semantic Brief (typed renderer renames)
    'Themes': 'Patterns & Insights',
    'Tensions': 'Conflicting Views',
    'Speculative Observations': 'Worth Exploring',
    'SCQA Framework': 'The Big Picture',
    'scqa_framework': 'The Big Picture',

    // Booster / Iteration documents
    'Booster Directions': 'Go Deeper',
    'booster_directions': 'Go Deeper',
    'Deep Dive Results': 'Deep Dive Findings',
    'Iteration Results': 'Updated Findings',

    // Generic improvements
    'Executive Summary': 'Overview',
    'executive_summary': 'Overview',
  };

  let result = markdown;
  Object.entries(headingMap).forEach(([original, replacement]) => {
    // Match as heading (# ## ###) or bold (**text**)
    const headingPattern = new RegExp(`(^#{1,3}\\s*)${original}(\\s*$)`, 'gm');
    const boldPattern = new RegExp(`\\*\\*${original}\\*\\*`, 'g');

    result = result.replace(headingPattern, `$1${replacement}$2`);
    result = result.replace(boldPattern, `**${replacement}**`);
  });

  return result;
}

// =============================================================================
// Document-Specific Formatters
// =============================================================================

/**
 * Get document metadata for display.
 */
export interface DocumentMeta {
  title: string;
  subtitle: string;
  description: string;
}

export const DOCUMENT_META: Record<string, DocumentMeta> = {
  doc_0: {
    title: 'Source Ledger',
    subtitle: 'What was analyzed',
    description: 'Complete record of all sources examined, with confidence levels and transcript quality indicators.',
  },
  doc_1: {
    title: 'Jump-Start',
    subtitle: 'Where to go next',
    description: 'Key takeaways and suggested research directions based on the analysis.',
  },
  doc_2: {
    title: 'Semantic Brief',
    subtitle: 'What sources reveal',
    description: 'Cross-source analysis showing common themes, tensions, and verified claims.',
  },
  doc_3: {
    title: 'Creator Brief',
    subtitle: 'Your hero document',
    description: 'Hook options, core facts, and narrative structure distilled from your research.',
  },
  doc_4: {
    title: 'Producer Packet',
    subtitle: 'Production-ready package',
    description: 'Detailed production notes, B-roll suggestions, and script-ready content.',
  },
};

/**
 * Get confidence level display properties.
 */
export function getConfidenceDisplay(level: string): {
  label: string;
  color: string;
  bgColor: string;
} {
  const normalized = level?.toLowerCase() || 'unknown';

  switch (normalized) {
    case 'high':
      return {
        label: 'High Confidence',
        color: 'text-green-400',
        bgColor: 'bg-green-900/30',
      };
    case 'medium':
      return {
        label: 'Medium Confidence',
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-900/30',
      };
    case 'low':
      return {
        label: 'Low Confidence',
        color: 'text-orange-400',
        bgColor: 'bg-orange-900/30',
      };
    default:
      return {
        label: 'Unknown',
        color: 'text-gray-400',
        bgColor: 'bg-gray-900/30',
      };
  }
}

/**
 * Get source type display properties.
 */
export function getSourceTypeDisplay(type: string): {
  label: string;
  icon: string;
} {
  const normalized = type?.toLowerCase() || 'unknown';

  switch (normalized) {
    case 'youtube':
      return { label: 'Video', icon: 'video' };
    case 'article':
      return { label: 'Article', icon: 'document' };
    case 'reddit':
      return { label: 'Reddit', icon: 'chat' };
    case 'screenshot':
      return { label: 'Screenshot', icon: 'image' };
    case 'text':
      return { label: 'Text', icon: 'text' };
    default:
      return { label: type || 'Source', icon: 'document' };
  }
}
