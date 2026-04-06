/**
 * ExportToolbar — Persistent export/share toolbar for document viewer.
 *
 * Phase 3E: Export & Sharing Redesign
 * Sits at the top of the document viewer with clear, always-visible actions:
 * - Copy full document
 * - Download (MD, JSON, PDF, DOCX)
 * - Share link
 */

import { useState, useCallback } from 'react';

interface ExportToolbarProps {
  /** Full markdown content of the document */
  markdown?: string;
  /** Raw JSON data */
  data: Record<string, unknown>;
  /** Document title for filenames */
  title: string;
  /** Document number */
  docNumber: number | string;
  /** Job ID for share functionality */
  jobId?: string;
  /** Handler for PDF export */
  onExportPdf?: () => void;
  /** Handler for DOCX export */
  onExportDocx?: () => void;
}

export function ExportToolbar({
  markdown,
  data,
  title,
  docNumber,
  jobId,
  onExportPdf,
  onExportDocx,
}: ExportToolbarProps) {
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  const handleCopyAll = useCallback(async () => {
    const text = markdown || JSON.stringify(data, null, 2);
    try {
      await navigator.clipboard.writeText(text);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    }
  }, [markdown, data]);

  const handleDownloadMd = useCallback(() => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '-')}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDropdown(false);
  }, [markdown, title]);

  const handleDownloadJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDropdown(false);
  }, [data, title]);

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.06] bg-white/[0.02] sticky top-0 z-10">
      {/* Copy full document */}
      <button
        onClick={handleCopyAll}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-body-sm font-medium rounded-lg border border-white/[0.08] text-white/60 hover:text-white/80 hover:bg-white/[0.04] transition-colors"
      >
        {copyFeedback ? (
          <>
            <svg className="w-3.5 h-3.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Copied
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy All
          </>
        )}
      </button>

      {/* Download dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-body-sm font-medium rounded-lg border border-white/[0.08] text-white/60 hover:text-white/80 hover:bg-white/[0.04] transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showDropdown && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setShowDropdown(false)} />
            <div className="absolute left-0 top-full mt-1 z-20 bg-card border border-border rounded-lg shadow-xl py-1 min-w-[140px]">
              {markdown && (
                <button
                  onClick={handleDownloadMd}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-muted-foreground hover:bg-muted transition-colors"
                >
                  Markdown (.md)
                </button>
              )}
              <button
                onClick={handleDownloadJson}
                className="w-full text-left px-3 py-1.5 text-body-sm text-muted-foreground hover:bg-muted transition-colors"
              >
                JSON (.json)
              </button>
              {onExportPdf && (
                <button
                  onClick={() => { onExportPdf(); setShowDropdown(false); }}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-muted-foreground hover:bg-muted transition-colors"
                >
                  PDF (.pdf)
                </button>
              )}
              {onExportDocx && (
                <button
                  onClick={() => { onExportDocx(); setShowDropdown(false); }}
                  className="w-full text-left px-3 py-1.5 text-body-sm text-muted-foreground hover:bg-muted transition-colors"
                >
                  Word (.docx)
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Document label */}
      <span className="text-caption text-white/20 font-mono">Doc {docNumber}</span>
    </div>
  );
}
