/**
 * Export button with dropdown menu for video analysis results.
 * Supports exporting to Google Docs, downloading markdown, and copying.
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getAccessToken } from '../../lib/supabase';
import { API_URL } from '../../lib/constants';
import { Spinner } from '@/components/ui/Spinner';

interface ExportButtonProps {
  jobId: string;
  onExportStart?: () => void;
  onExportComplete?: (success: boolean, message: string) => void;
}

type ExportStatus = 'idle' | 'exporting' | 'success' | 'error';

export function ExportButton({ jobId, onExportStart, onExportComplete }: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<ExportStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');
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

  const handleExportToGoogleDocs = async () => {
    setStatus('exporting');
    setStatusMessage('Creating Google Doc...');
    onExportStart?.();

    try {
      const token = await getAccessToken();
      const response = await fetch(`${API_URL}/jobs/${jobId}/export/google-docs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (data.success && data.doc_url) {
        setStatus('success');
        setStatusMessage('Document created!');
        onExportComplete?.(true, 'Document created successfully');
        
        // Open the doc in a new tab
        window.open(data.doc_url, '_blank');
        
        setTimeout(() => {
          setStatus('idle');
          setIsOpen(false);
        }, 2000);
      } else {
        setStatus('error');
        setStatusMessage(data.error || 'Failed to create document');
        onExportComplete?.(false, data.error || 'Export failed');
        
        setTimeout(() => setStatus('idle'), 3000);
      }
    } catch (error) {
      setStatus('error');
      setStatusMessage('Network error');
      onExportComplete?.(false, 'Network error');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const handleDownloadMarkdown = async () => {
    setStatus('exporting');
    setStatusMessage('Preparing download...');

    try {
      const token = await getAccessToken();
      const response = await fetch(
        `${API_URL}/jobs/${jobId}/export/markdown?download=true`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `video-analysis-${jobId.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setStatus('success');
      setStatusMessage('Downloaded!');
      setTimeout(() => {
        setStatus('idle');
        setIsOpen(false);
      }, 1500);
    } catch (error) {
      setStatus('error');
      setStatusMessage('Download failed');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const handleCopyToClipboard = async () => {
    setStatus('exporting');
    setStatusMessage('Copying...');

    try {
      const token = await getAccessToken();
      const response = await fetch(`${API_URL}/jobs/${jobId}/export/markdown`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch');

      const text = await response.text();
      await navigator.clipboard.writeText(text);

      setStatus('success');
      setStatusMessage('Copied!');
      setTimeout(() => {
        setStatus('idle');
        setIsOpen(false);
      }, 1500);
    } catch (error) {
      setStatus('error');
      setStatusMessage('Copy failed');
      setTimeout(() => setStatus('idle'), 3000);
    }
  };

  const statusColors = {
    idle: 'bg-purple-600 hover:bg-purple-500',
    exporting: 'bg-purple-700 cursor-wait',
    success: 'bg-green-600',
    error: 'bg-red-600',
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={status === 'exporting'}
        className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition ${statusColors[status]}`}
      >
        {status === 'exporting' ? (
          <>
            <Spinner size="sm" />
            {statusMessage}
          </>
        ) : status === 'success' ? (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            {statusMessage}
          </>
        ) : status === 'error' ? (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            {statusMessage}
          </>
        ) : (
          <>
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>

      <AnimatePresence>
        {isOpen && status === 'idle' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-2 w-56 rounded-lg bg-gray-800 border border-gray-700 shadow-xl z-50"
          >
            <div className="py-1">
              <button
                onClick={handleExportToGoogleDocs}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-200 hover:bg-gray-700 transition"
              >
                <svg className="h-5 w-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm4 18H6V4h7v5h5v11z" />
                </svg>
                <div className="text-left">
                  <div className="font-medium">Export to Google Docs</div>
                  <div className="text-xs text-gray-400">Opens in new tab</div>
                </div>
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-200 hover:bg-gray-700 transition"
              >
                <svg className="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                <div className="text-left">
                  <div className="font-medium">Download Markdown</div>
                  <div className="text-xs text-gray-400">.md file</div>
                </div>
              </button>

              <button
                onClick={handleCopyToClipboard}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-gray-200 hover:bg-gray-700 transition"
              >
                <svg className="h-5 w-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                </svg>
                <div className="text-left">
                  <div className="font-medium">Copy to Clipboard</div>
                  <div className="text-xs text-gray-400">Plain text</div>
                </div>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default ExportButton;

