/**
 * DocumentDrawer — Right-side sidebar for navigating between documents.
 *
 * Shows CORE documents (Creator Brief, Semantic Brief, Jump-Start, Source Ledger)
 * and OPTIONAL documents (Producer Packet, Script).
 * Each item shows status, version number, and is clickable.
 * Mobile: full overlay with swipe-to-close. Desktop: toggleable sidebar.
 */
import { useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import * as DialogPrimitive from '@radix-ui/react-dialog';

// =============================================================================
// Types
// =============================================================================

export type DocStatus = 'available' | 'not_available' | 'running' | 'locked';

export interface DrawerDocItem {
  /** Document type key (doc_0, doc_1, doc_2, doc_3, doc_4) */
  docType: string;
  /** Display title */
  title: string;
  /** Short subtitle */
  subtitle: string;
  /** Icon */
  icon: string;
  /** Availability status */
  status: DocStatus;
  /** Current version number */
  version?: number;
  /** Whether this is the hero document */
  isHero?: boolean;
}

export interface DocumentDrawerProps {
  /** Whether the drawer is open */
  isOpen: boolean;
  /** Close handler */
  onClose: () => void;
  /** Currently selected document type */
  selectedDocType?: string;
  /** Document items to display */
  documents: DrawerDocItem[];
  /** Callback when a document is selected */
  onSelectDocument: (docType: string) => void;
  /** Callback to open version selector for a document */
  onOpenVersions?: (docType: string) => void;
}

// =============================================================================
// Status styling
// =============================================================================

const STATUS_STYLES: Record<DocStatus, { text: string; bg: string; label: string }> = {
  available: { text: 'text-green-400', bg: 'bg-green-900/30', label: 'Ready' },
  not_available: { text: 'text-gray-600', bg: 'bg-gray-800/50', label: 'Not available' },
  running: { text: 'text-blue-400', bg: 'bg-blue-900/30', label: 'Running...' },
  locked: { text: 'text-gray-600', bg: 'bg-gray-800/50', label: 'Coming Soon' },
};

// =============================================================================
// Component
// =============================================================================

export function DocumentDrawer({
  isOpen,
  onClose,
  selectedDocType,
  documents,
  onSelectDocument,
  onOpenVersions,
}: DocumentDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();

  // Radix handles Escape key and focus trap; no manual keydown listener needed

  // Separate core and optional documents
  const coreDocs = documents.filter((d) =>
    ['doc_3', 'doc_2', 'doc_1', 'doc_0'].includes(d.docType)
  );
  const optionalDocs = documents.filter((d) =>
    ['doc_4'].includes(d.docType)
  );
  const lockedDocs: DrawerDocItem[] = [
    { docType: 'script', title: 'Script', subtitle: 'Coming in v2', icon: '📜', status: 'locked' },
  ];

  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <AnimatePresence>
          {isOpen && (
            <>
              {/* Backdrop (mobile only) */}
              <DialogPrimitive.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
                  className="fixed inset-0 bg-black/40 z-40 lg:hidden"
                  onClick={onClose}
                />
              </DialogPrimitive.Overlay>

              {/* Drawer panel */}
              <DialogPrimitive.Content asChild aria-label="Document navigation">
                <motion.div
                  ref={drawerRef}
                  initial={{ x: prefersReducedMotion ? 0 : '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: prefersReducedMotion ? 0 : '100%' }}
                  transition={prefersReducedMotion ? { duration: 0 } : { type: 'spring', damping: 30, stiffness: 300 }}
                  className="fixed right-0 top-0 bottom-0 w-80 bg-gray-900 border-l border-gray-700 z-50 overflow-y-auto"
                >
            {/* Header */}
            <div className="sticky top-0 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 px-5 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-gray-200">Documents</h2>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
                  aria-label="Close drawer"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Core Documents */}
            <div className="px-4 py-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1 mb-2">
                Core
              </p>
              <div className="space-y-1">
                {coreDocs.map((doc) => (
                  <DrawerItem
                    key={doc.docType}
                    doc={doc}
                    isSelected={selectedDocType === doc.docType}
                    onClick={() => {
                      onSelectDocument(doc.docType);
                      onClose();
                    }}
                    onVersionClick={
                      onOpenVersions && doc.version != null
                        ? () => onOpenVersions(doc.docType)
                        : undefined
                    }
                  />
                ))}
              </div>
            </div>

            {/* Optional Documents */}
            <div className="px-4 pb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1 mb-2">
                Optional
              </p>
              <div className="space-y-1">
                {optionalDocs.map((doc) => (
                  <DrawerItem
                    key={doc.docType}
                    doc={doc}
                    isSelected={selectedDocType === doc.docType}
                    onClick={() => {
                      if (doc.status !== 'not_available' && doc.status !== 'locked') {
                        onSelectDocument(doc.docType);
                        onClose();
                      }
                    }}
                  />
                ))}
                {lockedDocs.map((doc) => (
                  <DrawerItem
                    key={doc.docType}
                    doc={doc}
                    isSelected={false}
                    onClick={() => {}}
                  />
                ))}
              </div>
            </div>
                </motion.div>
              </DialogPrimitive.Content>
            </>
          )}
        </AnimatePresence>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

// =============================================================================
// DrawerItem
// =============================================================================

interface DrawerItemProps {
  doc: DrawerDocItem;
  isSelected: boolean;
  onClick: () => void;
  onVersionClick?: () => void;
}

function DrawerItem({ doc, isSelected, onClick, onVersionClick }: DrawerItemProps) {
  const statusStyle = STATUS_STYLES[doc.status];
  const isClickable = doc.status === 'available' || doc.status === 'running';

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      className={`
        flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150
        ${isSelected
          ? 'bg-amber-900/20 border border-amber-700/40'
          : isClickable
            ? 'hover:bg-gray-800 cursor-pointer border border-transparent'
            : 'opacity-50 cursor-not-allowed border border-transparent'
        }
      `}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && isClickable) {
          e.preventDefault();
          onClick();
        }
      }}
    >
      {/* Icon */}
      <span className="text-lg flex-shrink-0">{doc.icon}</span>

      {/* Title + subtitle */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className={`text-sm font-medium ${isClickable ? 'text-gray-200' : 'text-gray-500'}`}>
            {doc.title}
          </span>
          {doc.isHero && (
            <span className="text-amber-400 text-xs" title="Hero Document">⭐</span>
          )}
        </div>
        <p className="text-xs text-gray-500 truncate">{doc.subtitle}</p>
      </div>

      {/* Right side: version or status */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {doc.version != null && isClickable && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onVersionClick?.();
            }}
            className="text-xs text-gray-500 hover:text-gray-300 font-mono px-1.5 py-0.5 rounded hover:bg-gray-700 transition-colors"
            title="View versions"
          >
            v{doc.version}
          </button>
        )}
        {doc.status === 'available' && (
          <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
        )}
        {doc.status === 'running' && (
          <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
        )}
        {doc.status === 'locked' && (
          <span className="text-gray-600 text-xs">🔒</span>
        )}
      </div>
    </div>
  );
}

export default DocumentDrawer;
