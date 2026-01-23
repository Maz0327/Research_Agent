/**
 * ShareButton - Button to create and copy share links for documents.
 *
 * Supports:
 * - Creating time-limited share links
 * - Configuring expiration (1-720 hours)
 * - Optional view limits
 * - Copy to clipboard functionality
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAccessToken } from '../../lib/supabase';
import { API_URL } from '../../lib/constants';

interface ShareButtonProps {
  jobId: string;
  docType: 'doc_0' | 'doc_1' | 'doc_2' | 'doc_3' | 'all';
  docTitle?: string;
}

type ShareStatus = 'idle' | 'creating' | 'success' | 'error';

const DOC_TYPE_NAMES: Record<string, string> = {
  doc_0: 'Source Ledger',
  doc_1: 'Jump-Start Directions',
  doc_2: 'Semantic Brief',
  doc_3: 'Producer Packet',
  all: 'All Documents',
};

export function ShareButton({ jobId, docType, docTitle }: ShareButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<ShareStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [shareUrl, setShareUrl] = useState('');
  const [expiresInHours, setExpiresInHours] = useState(72);
  const [maxViews, setMaxViews] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleCreateShare = async () => {
    setStatus('creating');
    setStatusMessage('Creating share link...');

    try {
      const token = await getAccessToken();
      const response = await fetch(`${API_URL}/jobs/${jobId}/share`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          doc_type: docType,
          expires_in_hours: expiresInHours,
          max_views: maxViews,
        }),
      });

      const data = await response.json();

      if (response.ok && data.share_url) {
        setShareUrl(data.share_url);
        setStatus('success');
        setStatusMessage('Share link created!');
        
        // Auto-copy to clipboard
        await navigator.clipboard.writeText(data.share_url);
        setCopied(true);
        setTimeout(() => setCopied(false), 3000);
      } else {
        setStatus('error');
        setStatusMessage(data.detail || 'Failed to create share link');
        setTimeout(() => setStatus('idle'), 3000);
      }
    } catch (error) {
      setStatus('error');
      setStatusMessage('Network error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const handleCopyUrl = async () => {
    if (shareUrl) {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatExpiration = (hours: number): string => {
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''}`;
    const days = Math.floor(hours / 24);
    return `${days} day${days > 1 ? 's' : ''}`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={status === 'creating'}
        className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-300 bg-gray-700/50 hover:bg-gray-700 border border-gray-600/50 transition min-h-[40px] touch-manipulation"
        title={`Share ${docTitle || DOC_TYPE_NAMES[docType]}`}
      >
        {status === 'creating' ? (
          <>
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="hidden sm:inline">Creating...</span>
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            <span className="hidden sm:inline">Share</span>
          </>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-72 rounded-lg bg-gray-800 border border-gray-700 shadow-xl z-50"
          >
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-200 mb-3">
                Share {docTitle || DOC_TYPE_NAMES[docType]}
              </h3>

              {status === 'success' && shareUrl ? (
                /* Success state - show URL and copy button */
                <div className="space-y-3">
                  <div className="bg-gray-900 rounded-lg p-3">
                    <p className="text-xs text-gray-400 mb-1">Share Link</p>
                    <p className="text-sm text-gray-200 break-all font-mono">
                      {shareUrl}
                    </p>
                  </div>
                  
                  <button
                    onClick={handleCopyUrl}
                    className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition"
                  >
                    {copied ? (
                      <>
                        <svg className="h-4 w-4 text-green-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Copied!
                      </>
                    ) : (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                        </svg>
                        Copy Link
                      </>
                    )}
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    Link expires in {formatExpiration(expiresInHours)}
                    {maxViews && ` or after ${maxViews} views`}
                  </p>

                  <button
                    onClick={() => {
                      setShareUrl('');
                      setStatus('idle');
                    }}
                    className="w-full text-xs text-gray-500 hover:text-gray-400 transition"
                  >
                    Create another link
                  </button>
                </div>
              ) : status === 'error' ? (
                /* Error state */
                <div className="text-center py-2">
                  <p className="text-sm text-red-400 mb-2">{statusMessage}</p>
                  <button
                    onClick={() => setStatus('idle')}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    Try again
                  </button>
                </div>
              ) : (
                /* Configuration state */
                <div className="space-y-4">
                  {/* Expiration selector */}
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">
                      Expires in
                    </label>
                    <select
                      value={expiresInHours}
                      onChange={(e) => setExpiresInHours(Number(e.target.value))}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={1}>1 hour</option>
                      <option value={6}>6 hours</option>
                      <option value={24}>1 day</option>
                      <option value={72}>3 days</option>
                      <option value={168}>7 days</option>
                      <option value={720}>30 days</option>
                    </select>
                  </div>

                  {/* Max views (optional) */}
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">
                      View limit (optional)
                    </label>
                    <select
                      value={maxViews || ''}
                      onChange={(e) => setMaxViews(e.target.value ? Number(e.target.value) : null)}
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Unlimited</option>
                      <option value={1}>1 view</option>
                      <option value={10}>10 views</option>
                      <option value={50}>50 views</option>
                      <option value={100}>100 views</option>
                    </select>
                  </div>

                  {/* Create button */}
                  <button
                    onClick={handleCreateShare}
                    disabled={status === 'creating'}
                    className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-wait text-white text-sm font-medium transition"
                  >
                    {status === 'creating' ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Creating...
                      </>
                    ) : (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                        Create Share Link
                      </>
                    )}
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    Anyone with the link can view this document
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ShareButton;
