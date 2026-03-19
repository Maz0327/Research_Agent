/**
 * Helper utilities for the SharedJobView component.
 */

export function formatExpiration(expiresAt: string): string {
  const expires = new Date(expiresAt);
  const diffMs = expires.getTime() - Date.now();
  if (diffMs < 0) return 'Expired';
  const diffHours = Math.floor(diffMs / 3_600_000);
  if (diffHours < 1) {
    const m = Math.floor(diffMs / 60_000);
    return `${m} minute${m !== 1 ? 's' : ''} remaining`;
  }
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} remaining`;
  const d = Math.floor(diffHours / 24);
  return `${d} day${d !== 1 ? 's' : ''} remaining`;
}

/** Extract hook text from markdown (first line under a ## Hook heading) */
export function extractHook(markdown: string | null): string | null {
  if (!markdown) return null;
  const match = markdown.match(/##\s*Hook\s*\n+([^\n]+)/i);
  return match ? match[1].trim() : null;
}

/** Extract up to 5 key findings from markdown list under ## Key Findings heading */
export function extractKeyFindings(markdown: string | null): string[] {
  if (!markdown) return [];
  const section = markdown.match(/##\s*Key\s*Findings?\s*\n+([\s\S]*?)(?=\n##|$)/i);
  if (!section) return [];
  return section[1]
    .split('\n')
    .map((l) => l.replace(/^[-*\d.]\s*/, '').trim())
    .filter((l) => l.length > 0)
    .slice(0, 5);
}
