/**
 * DocumentViewerModal - Full-screen modal to view document content.
 *
 * Supports:
 * - Markdown rendering for formatted documents
 * - JSON viewer for raw data
 * - Copy to clipboard functionality
 * - Mobile-first fullscreen slide-over design
 * - Swipe-to-close gesture on mobile
 *
 * Uses presentation layer formatting to display user-friendly labels
 * (e.g., "Source 1" instead of "SRC_1") without modifying stored JSON.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence, PanInfo } from 'framer-motion';
import { exportToPdf } from '@/lib/pdf-export';
import { exportToDocx } from '@/lib/docx-export';
import { ResearchDocumentRenderer } from '@/components/document/ResearchDocumentRenderer';
import { ShareButton } from './ShareButton';
import { ExportToolbar } from '@/components/document/ExportToolbar';
import { API_URL } from '@/lib/constants';
import { getAccessToken } from '@/lib/supabase';
import { Spinner } from '@/components/ui/Spinner';

interface VersionMeta {
  version: number;
  created_at: string;
  trigger: string;
  source_count?: number;
  claim_count?: number;
  diff_summary?: string;
}

export interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  docNumber: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B';
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
  // Optional: job title for breadcrumb
  jobTitle?: string;
  // Optional: job ID for sharing (enables share button)
  jobId?: string;
}

// Document type styling
const docStyles: Record<0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B', { headerBg: string; headerBorder: string; badge: string; accent: string; accentBar: string }> = {
  0: {
    headerBg: 'bg-card',
    headerBorder: 'border-border',
    badge: 'bg-muted text-muted-foreground',
    accent: 'text-muted-foreground',
    accentBar: 'bg-muted-foreground/50',
  },
  1: {
    headerBg: 'bg-blue-900/30',
    headerBorder: 'border-blue-800/50',
    badge: 'bg-blue-900/50 text-blue-300',
    accent: 'text-blue-400',
    accentBar: 'bg-blue-500',
  },
  2: {
    headerBg: 'bg-purple-900/30',
    headerBorder: 'border-purple-800/50',
    badge: 'bg-purple-900/50 text-purple-300',
    accent: 'text-purple-400',
    accentBar: 'bg-purple-500',
  },
  3: {
    headerBg: 'bg-amber-900/30',
    headerBorder: 'border-amber-800/50',
    badge: 'bg-amber-900/50 text-amber-300',
    accent: 'text-amber-400',
    accentBar: 'bg-amber-500',
  },
  4: {
    headerBg: 'bg-green-900/30',
    headerBorder: 'border-green-800/50',
    badge: 'bg-green-900/50 text-green-300',
    accent: 'text-green-400',
    accentBar: 'bg-green-500',
  },
  5: {
    headerBg: 'bg-cyan-900/30',
    headerBorder: 'border-cyan-800/50',
    badge: 'bg-cyan-900/50 text-cyan-300',
    accent: 'text-cyan-400',
    accentBar: 'bg-cyan-500',
  },
  6: {
    headerBg: 'bg-pink-900/30',
    headerBorder: 'border-pink-800/50',
    badge: 'bg-pink-900/50 text-pink-300',
    accent: 'text-pink-400',
    accentBar: 'bg-pink-500',
  },
  7: {
    headerBg: 'bg-emerald-900/30',
    headerBorder: 'border-emerald-800/50',
    badge: 'bg-emerald-900/50 text-emerald-300',
    accent: 'text-emerald-400',
    accentBar: 'bg-emerald-500',
  },
  'B': {
    headerBg: 'bg-indigo-900/30',
    headerBorder: 'border-indigo-800/50',
    badge: 'bg-indigo-900/50 text-indigo-300',
    accent: 'text-indigo-400',
    accentBar: 'bg-indigo-500',
  },
};

// Document titles for breadcrumbs
const docTitles: Record<0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 'B', string> = {
  0: 'Source Ledger',
  1: 'Jump-Start Directions',
  2: 'Semantic Brief',
  3: 'Creator Brief',
  4: 'Producer Packet',
  5: 'Script',
  6: 'Social Media Kit',
  7: 'Blog Post',
  'B': 'Deep Research',
};

export function DocumentViewerModal({
  isOpen,
  onClose,
  docNumber,
  title,
  markdown,
  data,
  jobTitle,
  jobId,
}: DocumentViewerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const style = docStyles[docNumber];
  const [copied, setCopied] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);

  // Version selector state
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [activeVersion, setActiveVersion] = useState<number | null>(null);
  const [versionMarkdown, setVersionMarkdown] = useState<string | undefined>(undefined);
  const [versionData, setVersionData] = useState<Record<string, unknown> | null>(null);
  const [isLoadingVersion, setIsLoadingVersion] = useState(false);

  // Fetch available versions when modal opens
  useEffect(() => {
    if (!isOpen || !jobId || docNumber === 'B') {
      setVersions([]);
      setActiveVersion(null);
      setVersionMarkdown(undefined);
      setVersionData(null);
      return;
    }

    const docType = `doc_${docNumber}`;
    let cancelled = false;

    (async () => {
      try {
        const token = await getAccessToken();
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_URL}/jobs/${jobId}/documents/${docType}/versions`, { headers });
        if (!res.ok || cancelled) return;

        const json = await res.json();
        if (!cancelled && json.versions && json.versions.length > 1) {
          setVersions(json.versions);
        }
      } catch {
        // Version listing is optional — silently fail
      }
    })();

    return () => { cancelled = true; };
  }, [isOpen, jobId, docNumber]);

  // Load a specific version
  const loadVersion = useCallback(async (version: number) => {
    if (!jobId || docNumber === 'B') return;
    setIsLoadingVersion(true);
    setActiveVersion(version);

    try {
      const docType = `doc_${docNumber}`;
      const token = await getAccessToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_URL}/jobs/${jobId}/documents/${docType}?version=${version}`, { headers });
      if (!res.ok) throw new Error('Failed to fetch version');

      const json = await res.json();

      if (json.url) {
        const docRes = await fetch(json.url);
        const docJson = await docRes.json();
        setVersionData(docJson.data || docJson);
        setVersionMarkdown(docJson.markdown || docJson.content);
      } else {
        setVersionData(json.data || json);
        setVersionMarkdown(json.markdown || json.content);
      }
    } catch {
      setVersionData(null);
      setVersionMarkdown(undefined);
    } finally {
      setIsLoadingVersion(false);
    }
  }, [jobId, docNumber]);

  // Reset to latest (original props)
  const resetToLatest = useCallback(() => {
    setActiveVersion(null);
    setVersionData(null);
    setVersionMarkdown(undefined);
  }, []);

  // Effective content — use version override if active
  const effectiveMarkdown = activeVersion !== null ? versionMarkdown : markdown;
  const effectiveData = activeVersion !== null && versionData ? versionData : data;

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  // Close when clicking backdrop
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  // Handle swipe to close on mobile
  const handleDragEnd = useCallback(
    (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      // Close if swiped right more than 100px with velocity
      if (info.offset.x > 100 || (info.offset.x > 50 && info.velocity.x > 500)) {
        onClose();
      }
    },
    [onClose]
  );

  // Copy with feedback
  const handleCopy = useCallback(async () => {
    const content = effectiveMarkdown || JSON.stringify(effectiveData, null, 2);
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [effectiveMarkdown, effectiveData]);

  // Download as Markdown
  const handleDownloadMarkdown = useCallback(() => {
    if (!effectiveMarkdown) return;
    const blob = new Blob([effectiveMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadMenu(false);
  }, [effectiveMarkdown, docNumber, title]);

  // Download as JSON
  const handleDownloadJSON = useCallback(() => {
    const blob = new Blob([JSON.stringify(effectiveData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadMenu(false);
  }, [effectiveData, docNumber, title]);

  // Download as PDF
  const handleDownloadPDF = useCallback(async () => {
    if (!effectiveMarkdown) return;
    setShowDownloadMenu(false);
    try {
      const filename = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}`;
      await exportToPdf(effectiveMarkdown, filename);
    } catch (err) {
      console.error('PDF download failed:', err);
    }
  }, [effectiveMarkdown, docNumber, title]);

  // Download as DOCX
  const handleDownloadDocx = useCallback(async () => {
    if (!effectiveMarkdown) return;
    setShowDownloadMenu(false);
    try {
      const filename = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}`;
      await exportToDocx(effectiveMarkdown, filename);
    } catch (err) {
      console.error('DOCX download failed:', err);
    }
  }, [effectiveMarkdown, docNumber, title]);

  const hasContent = !!effectiveMarkdown || Object.keys(effectiveData).length > 0;
  const hasData = Object.keys(effectiveData).length > 0;

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50"
          onClick={handleBackdropClick}
          role="dialog"
          aria-modal="true"
          aria-label="Document viewer"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
          />

          {/* Modal - fullscreen on mobile, centered on desktop */}
          <motion.div
            ref={modalRef}
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={{ left: 0, right: 0.5 }}
            onDragEnd={handleDragEnd}
            className="absolute inset-0 bg-background flex flex-col overflow-hidden shadow-2xl"
          >
            {/* Header with breadcrumb */}
            <div className={`flex-shrink-0 ${style.headerBg} border-b ${style.headerBorder}`}>
              {/* Breadcrumb strip - shown if jobTitle is provided */}
              {jobTitle && (
                <div className="px-4 sm:px-6 pt-2.5 pb-0 flex items-center gap-2 text-xs text-muted-foreground/70">
                  <span className="truncate max-w-[200px] sm:max-w-none">{jobTitle}</span>
                  <svg className="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span className={`${style.accent} font-medium`}>{docTitles[docNumber]}</span>
                </div>
              )}

              {/* Main header row: left accent bar + content */}
              <div className="flex">
                {/* 4px left accent bar */}
                <div className={`w-1 flex-shrink-0 ${style.accentBar}`} />
                {/* Header content */}
                <div className="flex-1 flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4">
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                    <span className={`px-2 py-1 rounded text-xs font-medium flex-shrink-0 ${style.badge}`}>
                      DOC {docNumber}
                    </span>
                    <h2 className="text-base sm:text-xl font-semibold text-foreground truncate">{title}</h2>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={onClose}
                      className="p-2 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
                      title="Close (Esc)"
                      aria-label="Close document viewer"
                    >
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Swipe hint on mobile */}
            <div className="lg:hidden flex justify-center py-1.5 bg-card/50">
              <div className="w-10 h-1 rounded-full bg-secondary" />
            </div>

            {/* Version selector — show when multiple versions exist */}
            {versions.length > 1 && (
              <div className="flex-shrink-0 flex items-center gap-2 px-4 sm:px-6 py-2 border-b border-border/50 bg-card/30">
                <span className="text-caption font-medium text-muted-foreground/70 uppercase tracking-wider">Version</span>
                <select
                  value={activeVersion ?? ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === '') {
                      resetToLatest();
                    } else {
                      loadVersion(Number(val));
                    }
                  }}
                  className="bg-muted/50 border border-border/50 rounded px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">Latest (v{versions[0]?.version})</option>
                  {versions.slice(1).map((v) => (
                    <option key={v.version} value={v.version}>
                      v{v.version} — {v.trigger}{v.diff_summary ? ` (${v.diff_summary})` : ''}
                    </option>
                  ))}
                </select>
                {isLoadingVersion && <Spinner size="sm" />}
                {activeVersion !== null && !isLoadingVersion && (
                  <span className="text-caption text-muted-foreground/70">
                    {versions.find(v => v.version === activeVersion)?.created_at
                      ? new Date(versions.find(v => v.version === activeVersion)!.created_at).toLocaleDateString()
                      : ''}
                  </span>
                )}
              </div>
            )}

            {/* Export toolbar — persistent at top (Phase 3E) */}
            <ExportToolbar
              markdown={effectiveMarkdown}
              data={effectiveData}
              title={title}
              docNumber={docNumber}
              jobId={jobId}
              onExportPdf={effectiveMarkdown ? handleDownloadPDF : undefined}
              onExportDocx={effectiveMarkdown ? handleDownloadDocx : undefined}
            />

            {/* Content — reading column centered at 900px on wide screens */}
            <div className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
              <div className="max-w-[900px] mx-auto">
                <ResearchDocumentRenderer
                  docNumber={docNumber}
                  data={effectiveData}
                  markdown={effectiveMarkdown}
                  showDetails={showDetails}
                />
              </div>
            </div>

            {/* Footer - sticky on mobile */}
            <div className="flex-shrink-0 flex items-center justify-between gap-2 sm:gap-3 px-4 sm:px-6 py-3 sm:py-4 border-t border-border bg-card/50">
              {/* Details toggle - left side */}
              {hasContent ? (
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className={`px-3 py-2 rounded-lg text-xs font-medium transition flex items-center gap-2 min-h-[44px] touch-manipulation ${
                    showDetails
                      ? 'bg-blue-600/30 text-blue-300 border border-blue-600/50'
                      : 'bg-muted/50 text-muted-foreground border border-border/50 hover:bg-muted'
                  }`}
                  title={showDetails ? 'Hide internal IDs' : 'Show internal IDs for debugging'}
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  <span className="hidden sm:inline">{showDetails ? 'Hide IDs' : 'Show IDs'}</span>
                  <span className="sm:hidden">IDs</span>
                </button>
              ) : (
                <div />
              )}

              {/* Right side buttons */}
              <div className="flex items-center gap-2">
                {/* Share button - only show for shareable doc types with jobId */}
                {jobId && docNumber !== 'B' && (
                  <ShareButton
                    jobId={jobId}
                    docType={`doc_${docNumber}` as 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3'}
                    docTitle={docTitles[docNumber]}
                  />
                )}

                {/* Download dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                    className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-emerald-300 bg-emerald-900/40 hover:bg-emerald-800/60 border border-emerald-700/50 transition min-h-[44px] touch-manipulation"
                    title="Download document"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span className="hidden sm:inline">Download</span>
                  </button>

                  {showDownloadMenu && (
                    <>
                      {/* Backdrop to close menu */}
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setShowDownloadMenu(false)}
                      />
                      <div className="absolute right-0 bottom-full mb-1 z-20 w-48 rounded-lg border border-border bg-card py-1 shadow-lg">
                        {!!effectiveMarkdown && (
                          <>
                            <button
                              onClick={handleDownloadPDF}
                              className="w-full px-3 py-2 text-left text-sm text-muted-foreground hover:bg-muted flex items-center gap-2"
                            >
                              <svg className="h-4 w-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                              Download PDF
                            </button>
                            <button
                              onClick={handleDownloadDocx}
                              className="w-full px-3 py-2 text-left text-sm text-muted-foreground hover:bg-muted flex items-center gap-2"
                            >
                              <svg className="h-4 w-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                              Download Word (.docx)
                            </button>
                            <div className="border-t border-border my-1" />
                            <button
                              onClick={handleDownloadMarkdown}
                              className="w-full px-3 py-2 text-left text-sm text-muted-foreground/70 hover:bg-muted hover:text-muted-foreground flex items-center gap-2"
                            >
                              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                              </svg>
                              Markdown (.md)
                            </button>
                          </>
                        )}
                        {hasData && (
                          <button
                            onClick={handleDownloadJSON}
                            className="w-full px-3 py-2 text-left text-sm text-muted-foreground/70 hover:bg-muted hover:text-muted-foreground flex items-center gap-2"
                          >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                            </svg>
                            JSON (.json)
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>

                <button
                  onClick={handleCopy}
                  className="px-3 sm:px-4 py-2 sm:py-2 rounded-lg text-sm font-medium bg-muted text-muted-foreground hover:bg-secondary transition flex items-center gap-2 min-h-[44px] touch-manipulation"
                >
                  {copied ? (
                    <>
                      <svg className="h-4 w-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-green-400 hidden sm:inline">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      <span className="hidden sm:inline">Copy</span>
                    </>
                  )}
                </button>
                <button
                  onClick={onClose}
                  className="px-3 sm:px-4 py-2 sm:py-2 rounded-lg text-sm font-medium bg-secondary text-foreground hover:bg-muted transition min-h-[44px] touch-manipulation hidden sm:flex"
                >
                  Close
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export default DocumentViewerModal;
