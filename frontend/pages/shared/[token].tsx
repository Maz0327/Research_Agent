/**
 * Public shared document page.
 *
 * This page displays shared documents without requiring authentication.
 * The token in the URL serves as the authorization.
 *
 * Features:
 * - Markdown rendering for formatted documents
 * - Mobile-responsive design
 * - View count and expiration info
 * - Error handling for expired/revoked links
 */
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import { motion } from 'framer-motion';
import DOMPurify from 'dompurify';
import { API_URL } from '../../lib/constants';
import { PublicHeader } from '../../components/PublicHeader';
import { transformMarkdownWithDetails } from '@/lib/document-formatters';

interface SharedDocument {
  job_id: string;
  job_title: string | null;
  doc_type: string;
  doc_title: string;
  markdown: string | null;
  data: Record<string, unknown> | null;
  expires_at: string;
  view_count: number;
}

interface ErrorState {
  status: number;
  message: string;
}

export default function SharedDocumentPage() {
  const router = useRouter();
  const { token } = router.query;
  
  const [document, setDocument] = useState<SharedDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorState | null>(null);

  useEffect(() => {
    if (!token || typeof token !== 'string') return;

    const fetchDocument = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_URL}/shared/${token}`);
        const data = await response.json();

        if (!response.ok) {
          setError({
            status: response.status,
            message: data.detail || 'Failed to load document',
          });
          setLoading(false);
          return;
        }

        setDocument(data);
      } catch (err) {
        setError({
          status: 500,
          message: 'Network error. Please try again.',
        });
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [token]);

  // Format expiration time
  const formatExpiration = (expiresAt: string): string => {
    const expires = new Date(expiresAt);
    const now = new Date();
    const diffMs = expires.getTime() - now.getTime();
    
    if (diffMs < 0) return 'Expired';
    
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} remaining`;
    }
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} remaining`;
    }
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} remaining`;
  };

  // Render error page
  if (error) {
    return (
      <>
        <Head>
          <title>Share Link Error | Research Agent</title>
          <meta name="robots" content="noindex" />
        </Head>
        <div className="min-h-screen bg-gray-900 flex flex-col">
          <PublicHeader showHomeLink />
          <main className="flex-1 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-md w-full text-center"
            >
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-8">
                {error.status === 410 ? (
                  /* Expired or revoked */
                  <>
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-900/30 flex items-center justify-center">
                      <svg className="w-8 h-8 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h1 className="text-xl font-semibold text-gray-100 mb-2">Link No Longer Available</h1>
                    <p className="text-gray-400 mb-6">{error.message}</p>
                  </>
                ) : error.status === 404 ? (
                  /* Not found */
                  <>
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-700 flex items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h1 className="text-xl font-semibold text-gray-100 mb-2">Link Not Found</h1>
                    <p className="text-gray-400 mb-6">{error.message}</p>
                  </>
                ) : (
                  /* Other errors */
                  <>
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-900/30 flex items-center justify-center">
                      <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <h1 className="text-xl font-semibold text-gray-100 mb-2">Something Went Wrong</h1>
                    <p className="text-gray-400 mb-6">{error.message}</p>
                  </>
                )}
                <p className="text-sm text-gray-500">
                  Ask the document owner for a new link if needed.
                </p>
              </div>
            </motion.div>
          </main>
        </div>
      </>
    );
  }

  // Render loading state
  if (loading) {
    return (
      <>
        <Head>
          <title>Loading... | Research Agent</title>
          <meta name="robots" content="noindex" />
        </Head>
        <div className="min-h-screen bg-gray-900 flex flex-col">
          <PublicHeader />
          <main className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-400">Loading shared document...</p>
            </div>
          </main>
        </div>
      </>
    );
  }

  // Render document
  if (!document) return null;

  return (
    <>
      <Head>
        <title>{document.doc_title} | Shared Document</title>
        <meta name="robots" content="noindex" />
        <meta name="description" content={`Shared research document: ${document.doc_title}`} />
      </Head>

      <div className="min-h-screen bg-gray-900 flex flex-col">
        <PublicHeader showHomeLink />

        <main className="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4 py-6">
          {/* Header card */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-800 rounded-xl border border-gray-700 p-4 sm:p-6 mb-6"
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-900/50 text-blue-300">
                    {document.doc_type.toUpperCase().replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-500">Shared Document</span>
                </div>
                <h1 className="text-xl font-semibold text-gray-100">
                  {document.doc_title}
                </h1>
                {document.job_title && (
                  <p className="text-sm text-gray-400 mt-1">
                    From: {document.job_title}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <span>{document.view_count} view{document.view_count !== 1 ? 's' : ''}</span>
                </div>
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{formatExpiration(document.expires_at)}</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Document content */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-800 rounded-xl border border-gray-700 flex-1 overflow-hidden"
          >
            <div className="p-4 sm:p-6 lg:p-8 overflow-auto max-h-[calc(100vh-300px)]">
              {document.markdown ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <MarkdownRenderer content={transformMarkdownWithDetails(document.markdown, false)} />
                </div>
              ) : document.data ? (
                <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap bg-gray-900/50 rounded-lg p-4 overflow-x-auto">
                  {JSON.stringify(document.data, null, 2)}
                </pre>
              ) : (
                <p className="text-gray-400 text-center py-8">
                  No content available
                </p>
              )}
            </div>
          </motion.div>

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-gray-500">
            <p>
              This is a shared document from Research Agent.{' '}
              <Link href="/" className="text-blue-400 hover:text-blue-300 transition">
                Learn more
              </Link>
            </p>
          </div>
        </main>
      </div>
    </>
  );
}

/**
 * Simple markdown renderer - converts basic markdown to HTML.
 * Uses DOMPurify to sanitize output and prevent XSS attacks.
 */
function MarkdownRenderer({ content }: { content: string }) {
  const parseMarkdown = (text: string): string => {
    return text
      // Code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-900 rounded p-3 my-2 overflow-x-auto"><code>$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code class="bg-gray-900 px-1 rounded text-blue-300">$1</code>')
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
