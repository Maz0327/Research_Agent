/**
 * DocumentViewerModal - Full-screen modal to view document content.
 *
 * Supports:
 * - Markdown rendering for formatted documents
 * - JSON viewer for raw data
 * - Copy to clipboard functionality
 */
import { useEffect, useRef } from 'react';
import DOMPurify from 'dompurify';

export interface DocumentViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  docNumber: 0 | 1 | 2;
  title: string;
  markdown?: string;
  data: Record<string, unknown>;
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

export function DocumentViewerModal({
  isOpen,
  onClose,
  docNumber,
  title,
  markdown,
  data,
}: DocumentViewerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const style = docStyles[docNumber];

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

  if (!isOpen) return null;

  const content = markdown || JSON.stringify(data, null, 2);
  const isMarkdown = !!markdown;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-4xl max-h-[90vh] bg-gray-900 rounded-xl border border-gray-700 flex flex-col overflow-hidden shadow-2xl"
      >
        {/* Header */}
        <div className={`flex items-center justify-between px-6 py-4 border-b ${style.headerBorder} ${style.headerBg}`}>
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 rounded text-xs font-medium ${style.badge}`}>
              DOC {docNumber}
            </span>
            <h2 className="text-lg font-semibold text-gray-100">{title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs ${style.accent}`}>
              {isMarkdown ? 'Markdown' : 'JSON'}
            </span>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition"
              title="Close (Esc)"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isMarkdown ? (
            <div className="prose prose-invert prose-sm max-w-none">
              <MarkdownRenderer content={markdown} />
            </div>
          ) : (
            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap bg-gray-800/50 rounded-lg p-4 overflow-x-auto">
              {content}
            </pre>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-700 bg-gray-800/50">
          <button
            onClick={async () => {
              await navigator.clipboard.writeText(content);
            }}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition flex items-center gap-2"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
            </svg>
            Copy
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-600 text-gray-200 hover:bg-gray-500 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
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
