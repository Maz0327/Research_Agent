/**
 * VersionSelector — Dropdown for browsing document versions.
 *
 * Shows all available versions for a document with metadata
 * (date, trigger, diff summary). Used inside the document drawer
 * or as a standalone dropdown.
 */
import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useJobsStore, type DocumentVersion } from '../../store/jobs';
import { formatTimestamp } from '../../lib/document-formatters';

// =============================================================================
// Trigger label mapping
// =============================================================================

const TRIGGER_LABELS: Record<string, { label: string; color: string }> = {
  initial_run: { label: 'Initial', color: 'text-gray-400' },
  deep_dive: { label: 'Deep Dive', color: 'text-blue-400' },
  expand_sources: { label: 'Expand', color: 'text-green-400' },
  deeper: { label: 'Deeper', color: 'text-purple-400' },
  different_angle: { label: 'New Angle', color: 'text-orange-400' },
  custom: { label: 'Custom', color: 'text-gray-300' },
};

// =============================================================================
// Props
// =============================================================================

export interface VersionSelectorProps {
  /** Job ID */
  jobId: string;
  /** Document type (doc_0, doc_1, doc_2, doc_3, doc_4) */
  docType: string;
  /** Currently selected version (undefined = latest) */
  currentVersion?: number;
  /** Callback when a version is selected */
  onSelectVersion: (docType: string, version: number) => void;
  /** Optional className */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function VersionSelector({
  jobId,
  docType,
  currentVersion,
  onSelectVersion,
  className = '',
}: VersionSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const fetchDocumentVersions = useJobsStore((s) => s.fetchDocumentVersions);
  const cachedVersions = useJobsStore((s) => s.documentVersions[`${jobId}_${docType}`]);

  // Load versions on first open
  useEffect(() => {
    if (cachedVersions) {
      setVersions(cachedVersions);
    }
  }, [cachedVersions]);

  const handleOpen = async () => {
    setIsOpen(true);
    if (versions.length === 0 && !loading) {
      setLoading(true);
      try {
        const result = await fetchDocumentVersions(jobId, docType);
        setVersions(result);
      } catch {
        // Silently fail — versions will show empty
      } finally {
        setLoading(false);
      }
    }
  };

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  const latestVersion = versions.length > 0 ? Math.max(...versions.map((v) => v.version)) : currentVersion;
  const displayVersion = currentVersion || latestVersion;

  if (!displayVersion && versions.length === 0) {
    return null;
  }

  return (
    <div ref={dropdownRef} className={`relative inline-block ${className}`}>
      {/* Trigger button */}
      <button
        onClick={handleOpen}
        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-mono text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
        title="View versions"
      >
        v{displayVersion || '?'}
        <svg
          className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-1 w-64 max-w-[calc(100vw-2rem)] rounded-lg bg-gray-800 border border-gray-700 shadow-xl z-[60] overflow-hidden"
          >
            {/* Header */}
            <div className="px-3 py-2 border-b border-gray-700">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Version History
              </p>
            </div>

            {/* Version list */}
            <div className="max-h-64 overflow-y-auto">
              {loading ? (
                <div className="px-3 py-4 text-center">
                  <div className="w-4 h-4 border-2 border-gray-600 border-t-gray-300 rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-gray-500 mt-2">Loading versions...</p>
                </div>
              ) : versions.length === 0 ? (
                <div className="px-3 py-4 text-center">
                  <p className="text-xs text-gray-500">No version history available</p>
                </div>
              ) : (
                [...versions]
                  .sort((a, b) => b.version - a.version)
                  .map((version) => {
                    const isSelected = version.version === currentVersion;
                    const triggerInfo = TRIGGER_LABELS[version.trigger] || {
                      label: version.trigger,
                      color: 'text-gray-400',
                    };

                    return (
                      <button
                        key={version.version}
                        onClick={() => {
                          onSelectVersion(docType, version.version);
                          setIsOpen(false);
                        }}
                        className={`
                          w-full px-3 py-2.5 text-left hover:bg-gray-700/50 transition-colors
                          ${isSelected ? 'bg-amber-900/20 border-l-2 border-amber-500' : 'border-l-2 border-transparent'}
                        `}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono text-gray-200">
                              v{version.version}
                            </span>
                            <span className={`text-xs ${triggerInfo.color}`}>
                              {triggerInfo.label}
                            </span>
                          </div>
                          <span className="text-xs text-gray-500">
                            {formatTimestamp(version.created_at)}
                          </span>
                        </div>
                        {version.diff_summary && (
                          <p className="text-xs text-gray-500 mt-0.5 truncate">
                            {version.diff_summary}
                          </p>
                        )}
                        <div className="flex items-center gap-3 mt-1">
                          {version.source_count > 0 && (
                            <span className="text-xs text-gray-600">
                              {version.source_count} sources
                            </span>
                          )}
                          {version.claim_count > 0 && (
                            <span className="text-xs text-gray-600">
                              {version.claim_count} claims
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default VersionSelector;
