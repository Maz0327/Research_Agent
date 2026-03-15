/**
 * SectionActions — Copy and share buttons for individual document sections.
 *
 * Phase 3E: Section-level copy and "Share snippet" for social media.
 * - Copy section text to clipboard
 * - Share snippet: formats text for social media (280 chars max)
 */

import { useState, useCallback } from 'react';

interface SectionActionsProps {
  /** Section text content to copy/share */
  content: string;
  /** Section title for context in share snippet */
  sectionTitle?: string;
}

function truncateForSocial(text: string, maxLen: number = 280): string {
  if (text.length <= maxLen) return text;
  // Find a good breakpoint (end of sentence or word)
  const truncated = text.slice(0, maxLen - 3);
  const lastSpace = truncated.lastIndexOf(' ');
  const lastPeriod = truncated.lastIndexOf('.');
  const breakpoint = lastPeriod > maxLen * 0.6 ? lastPeriod + 1 : lastSpace > 0 ? lastSpace : maxLen - 3;
  return truncated.slice(0, breakpoint).trim() + '...';
}

export function SectionActions({ content, sectionTitle }: SectionActionsProps) {
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [snippetFeedback, setSnippetFeedback] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 1500);
    } catch {
      // silent fail
    }
  }, [content]);

  const handleShareSnippet = useCallback(async () => {
    const snippet = truncateForSocial(content);
    try {
      await navigator.clipboard.writeText(snippet);
      setSnippetFeedback(true);
      setTimeout(() => setSnippetFeedback(false), 1500);
    } catch {
      // silent fail
    }
  }, [content]);

  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {/* Copy section */}
      <button
        onClick={handleCopy}
        title="Copy section"
        className="p-1 rounded text-white/20 hover:text-white/50 hover:bg-white/[0.04] transition-colors"
      >
        {copyFeedback ? (
          <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        )}
      </button>

      {/* Share snippet (280 chars) */}
      <button
        onClick={handleShareSnippet}
        title="Copy as social snippet (280 chars)"
        className="p-1 rounded text-white/20 hover:text-white/50 hover:bg-white/[0.04] transition-colors"
      >
        {snippetFeedback ? (
          <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        )}
      </button>
    </div>
  );
}
