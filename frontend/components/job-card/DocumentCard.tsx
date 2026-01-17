/**
 * DocumentCard - Displays a single research document (Doc 0/1/2) with view and download actions.
 *
 * Color coding:
 * - Doc 0 (Source Ledger): Gray - reference/data layer
 * - Doc 1 (Jump-Start): Blue - exploration/directions
 * - Doc 2 (Semantic Brief): Purple - insights/analysis
 */
import { useState } from 'react';

export interface DocumentCardProps {
  docNumber: 0 | 1 | 2;
  title: string;
  subtitle: string;
  stats: { label: string; value: number | string }[];
  data: Record<string, unknown>;
  markdown?: string;
  onView: () => void;
}

// Document type configuration
const docConfig = {
  0: {
    color: 'gray',
    bgColor: 'bg-gray-800/50',
    borderColor: 'border-gray-700',
    textColor: 'text-gray-300',
    badgeColor: 'bg-gray-700 text-gray-400',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  1: {
    color: 'blue',
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-800/50',
    textColor: 'text-blue-300',
    badgeColor: 'bg-blue-900/50 text-blue-400',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
      </svg>
    ),
  },
  2: {
    color: 'purple',
    bgColor: 'bg-purple-900/20',
    borderColor: 'border-purple-800/50',
    textColor: 'text-purple-300',
    badgeColor: 'bg-purple-900/50 text-purple-400',
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
};

export function DocumentCard({ docNumber, title, subtitle, stats, data, markdown, onView }: DocumentCardProps) {
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const config = docConfig[docNumber];

  // Download as JSON
  const handleDownloadJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadMenu(false);
  };

  // Download as Markdown
  const handleDownloadMarkdown = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `doc-${docNumber}-${title.toLowerCase().replace(/\s+/g, '-')}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadMenu(false);
  };

  // Copy to clipboard
  const handleCopyToClipboard = async () => {
    const content = markdown || JSON.stringify(data, null, 2);
    await navigator.clipboard.writeText(content);
    setShowDownloadMenu(false);
  };

  return (
    <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} p-4 flex flex-col h-full`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.badgeColor}`}>
            DOC {docNumber}
          </span>
        </div>
        <div className={config.textColor}>
          {config.icon}
        </div>
      </div>

      {/* Title & Subtitle */}
      <h4 className="font-semibold text-gray-100 mb-1">{title}</h4>
      <p className="text-xs text-gray-500 mb-3">{subtitle}</p>

      {/* Stats */}
      <div className="flex-1">
        {stats.map((stat, idx) => (
          <div key={idx} className="flex justify-between text-sm mb-1">
            <span className="text-gray-500">{stat.label}</span>
            <span className={config.textColor}>{stat.value}</span>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-3 pt-3 border-t border-gray-800">
        <button
          onClick={onView}
          className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
            config.color === 'gray'
              ? 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              : config.color === 'blue'
              ? 'bg-blue-600/30 text-blue-300 hover:bg-blue-600/40'
              : 'bg-purple-600/30 text-purple-300 hover:bg-purple-600/40'
          }`}
        >
          View
        </button>

        {/* Download dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowDownloadMenu(!showDownloadMenu)}
            className="rounded-lg px-3 py-2 text-sm font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>

          {showDownloadMenu && (
            <>
              {/* Backdrop to close menu */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowDownloadMenu(false)}
              />
              <div className="absolute right-0 bottom-full mb-1 z-20 w-44 rounded-lg border border-gray-700 bg-gray-800 py-1 shadow-lg">
                <button
                  onClick={handleCopyToClipboard}
                  className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  Copy to Clipboard
                </button>
                {markdown && (
                  <button
                    onClick={handleDownloadMarkdown}
                    className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    Download Markdown
                  </button>
                )}
                <button
                  onClick={handleDownloadJSON}
                  className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  Download JSON
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default DocumentCard;
