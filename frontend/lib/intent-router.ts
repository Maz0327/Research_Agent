/**
 * IntentRouter — Detects user intent from free-form input text.
 *
 * Routes to the appropriate job creation flow based on what the user typed:
 * - URLs detected → "sources" (own sources flow)
 * - Creator analysis language → "creator_analysis" (Phase 3)
 * - Claims/fact-check language → "claims"
 * - Plain topic text → "topic" (search discovery flow)
 */

export type DetectedIntent =
  | 'topic'            // Plain topic → search discovery
  | 'sources'          // Contains URLs → own sources flow
  | 'claims'           // Fact-check / claims language
  | 'creator_analysis' // Analyze a creator's style (Phase 3)
  ;

interface IntentResult {
  intent: DetectedIntent;
  /** Extracted URLs (if any) */
  urls: string[];
  /** Cleaned topic text (URLs stripped) */
  topic: string;
}

const URL_PATTERN = /https?:\/\/[^\s,]+/g;
const YOUTUBE_PATTERN = /(?:youtube\.com|youtu\.be)/i;

const CLAIMS_KEYWORDS = [
  'fact check', 'fact-check', 'factcheck',
  'extract claims', 'pull claims', 'find claims',
  'verify', 'debunk',
];

const CREATOR_KEYWORDS = [
  'analyze style', 'analyse style',
  'style guide', 'style breakdown',
  'how does .+ make', 'how does .+ edit',
  'creator analysis', 'content style',
  'break down .+ style', 'study .+ videos',
];

/**
 * Detect user intent from free-form input text.
 */
export function detectIntent(input: string): IntentResult {
  const trimmed = input.trim();
  if (!trimmed) {
    return { intent: 'topic', urls: [], topic: '' };
  }

  // Extract URLs
  const urls = trimmed.match(URL_PATTERN) || [];
  const topicWithoutUrls = trimmed.replace(URL_PATTERN, '').replace(/\s+/g, ' ').trim();

  // Check for claims intent
  const lowerInput = trimmed.toLowerCase();
  if (CLAIMS_KEYWORDS.some(kw => lowerInput.includes(kw))) {
    return { intent: 'claims', urls, topic: topicWithoutUrls };
  }

  // Check for creator analysis intent
  if (CREATOR_KEYWORDS.some(kw => new RegExp(kw, 'i').test(trimmed))) {
    return { intent: 'creator_analysis', urls, topic: topicWithoutUrls };
  }

  // If input is primarily URLs (>50% of content is URLs), route to sources
  if (urls.length > 0 && (topicWithoutUrls.length < 20 || urls.length >= 2)) {
    return { intent: 'sources', urls, topic: topicWithoutUrls };
  }

  // Default: topic search
  return { intent: 'topic', urls, topic: trimmed };
}

/**
 * Check if a URL is a YouTube URL.
 */
export function isYouTubeUrl(url: string): boolean {
  return YOUTUBE_PATTERN.test(url);
}

/**
 * Separate URLs into YouTube and article categories.
 */
export function categorizeUrls(urls: string[]): { videoUrls: string[]; articleUrls: string[] } {
  const videoUrls: string[] = [];
  const articleUrls: string[] = [];

  for (const url of urls) {
    if (isYouTubeUrl(url)) {
      videoUrls.push(url);
    } else {
      articleUrls.push(url);
    }
  }

  return { videoUrls, articleUrls };
}
