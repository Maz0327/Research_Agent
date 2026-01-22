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
import DOMPurify from 'dompurify';
import { transformMarkdownForDisplay } from '@/lib/document-formatters';

export interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  docNumber: 0 | 1 | 2;
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
  // Optional: job title for breadcrumb
  jobTitle?: string;
}

// Document type styling
const docStyles = {
  0: {
    headerBg: 'bg-gray-800',
    headerBorder: 'border-gray-700',
    badge: 'bg-gray-700 text-gray-300',
    accent: 'text-gray-400',
  },
  1: {
    headerBg: 'bg-blue-900/30',
    headerBorder: 'border-blue-800/50',
    badge: 'bg-blue-900/50 text-blue-300',
    accent: 'text-blue-400',
  },
  2: {
    headerBg: 'bg-purple-900/30',
    headerBorder: 'border-purple-800/50',
    badge: 'bg-purple-900/50 text-purple-300',
    accent: 'text-purple-400',
  },
};

// Document titles for breadcrumbs
const docTitles = {
  0: 'Source Ledger',
  1: 'Jump-Start Directions',
  2: 'Semantic Brief',
};

export function DocumentViewerModal({
  isOpen,
  onClose,
  docNumber,
  title,
  markdown,
  data,
  jobTitle,
}: DocumentViewerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const style = docStyles[docNumber];
  const [copied, setCopied] = useState(false);

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
    const content = markdown || JSON.stringify(data, null, 2);
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [markdown, data]);

  const content = markdown || JSON.stringify(data, null, 2);
  const isMarkdown = !!markdown;

  return (
    <AnimatePresence>
      {isOpen && (
        <div
          className="fixed inset-0 z-50"
          onClick={handleBackdropClick}
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
            className="absolute inset-0 lg:inset-4 lg:left-auto lg:right-4 lg:w-full lg:max-w-4xl bg-gray-900 lg:rounded-xl border-l lg:border border-gray-700 flex flex-col overflow-hidden shadow-2xl"
          >
            {/* Header with breadcrumb */}
            <div className={`flex-shrink-0 ${style.headerBg} border-b ${style.headerBorder}`}>
              {/* Breadcrumb - shown if jobTitle is provided */}
              {jobTitle && (
                <div className="px-4 sm:px-6 pt-3 flex items-center gap-2 text-xs text-gray-500">
                  <span className="truncate max-w-[150px] sm:max-w-none">{jobTitle}</span>
                  <svg className="h-3 w-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span className={`${style.accent} font-medium`}>Doc {docNumber}: {docTitles[docNumber]}</span>
                </div>
              )}

              {/* Main header */}
              <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4">
                <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                  <span className={`px-2 py-1 rounded text-xs font-medium flex-shrink-0 ${style.badge}`}>
                    DOC {docNumber}
                  </span>
                  <h2 className="text-base sm:text-lg font-semibold text-gray-100 truncate">{title}</h2>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-xs ${style.accent} hidden sm:inline`}>
                    {isMarkdown ? 'Markdown' : 'JSON'}
                  </span>
                  <button
                    onClick={onClose}
                    className="p-2 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
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

            {/* Swipe hint on mobile */}
            <div className="lg:hidden flex justify-center py-1.5 bg-gray-800/50">
              <div className="w-10 h-1 rounded-full bg-gray-600" />
            </div>

            {/* Content - max-w-prose for better readability */}
            <div className="flex-1 overflow-auto p-4 sm:p-6">
              <div className="max-w-prose mx-auto">
                {isMarkdown ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <MarkdownRenderer content={transformMarkdownForDisplay(markdown)} />
                  </div>
                ) : (
                  <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap bg-gray-800/50 rounded-lg p-4 overflow-x-auto">
                    {content}
                  </pre>
                )}
              </div>
            </div>

            {/* Footer - sticky on mobile */}
            <div className="flex-shrink-0 flex items-center justify-end gap-2 sm:gap-3 px-4 sm:px-6 py-3 sm:py-4 border-t border-gray-700 bg-gray-800/50">
              <button
                onClick={handleCopy}
                className="px-3 sm:px-4 py-2 sm:py-2 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition flex items-center gap-2 min-h-[44px] touch-manipulation"
              >
                {copied ? (
                  <>
                    <svg className="h-4 w-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-green-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                    Copy
                  </>
                )}
              </button>
              <button
                onClick={onClose}
                className="px-3 sm:px-4 py-2 sm:py-2 rounded-lg text-sm font-medium bg-gray-600 text-gray-200 hover:bg-gray-500 transition min-h-[44px] touch-manipulation"
              >
                Close
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/**
 * Simple markdown renderer - converts basic markdown to HTML.
 * For full markdown support, consider using react-markdown.
 * Uses DOMPurify to sanitize output and prevent XSS attacks.
 */
function MarkdownRenderer({ content }: { content: string }) {
  // Simple markdown parsing for headers, lists, bold, italic, code
  const parseMarkdown = (text: string): string => {
    return text
      // Code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-800 rounded p-3 my-2 overflow-x-auto"><code>$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="bg-gray-800 px-1 rounded text-blue-300">$1</code>')
      // Headers
      .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-200 mt-4 mb-2">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold text-gray-100 mt-6 mb-3">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-white mt-6 mb-4">$1</h1>')
      // Bold
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-100">$1</strong>')
      // Italic
      .replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>')
      // Unordered lists
      .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
      .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="my-2">$&</ul>')
      // Ordered lists
      .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')
      // Horizontal rule
      .replace(/^---$/gm, '<hr class="border-gray-700 my-4" />')
      // Paragraphs (lines not already converted)
      .replace(/^(?!<[hl]|<ul|<li|<pre|<hr)(.+)$/gm, '<p class="my-2">$1</p>')
      // Line breaks
      .replace(/\n/g, '');
  };

  // Sanitize HTML to prevent XSS attacks
  const sanitizedHtml = DOMPurify.sanitize(parseMarkdown(content));

  return (
    <div
      className="text-gray-300"
      dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
    />
  );
}

export default DocumentViewerModal;
