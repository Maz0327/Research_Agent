/**
 * ClaimDrillDown — Slide-over panel for exploring fact provenance.
 *
 * Triggered when the user clicks a core fact in CreatorBriefView.
 * Shows the claim from Doc 2, speaker attribution, rhetorical framing,
 * significance, related claims, and source link to Doc 0.
 *
 * Uses Radix Dialog primitives for focus trapping and Escape handling (WCAG 2.4.3, 2.1.1).
 */
import { useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import {
  SignificanceIndicator,
  SourceCitation,
} from '../common/ClaimIndicators';

// =============================================================================
// Types
// =============================================================================

/** Core fact from the Creator Brief (same as in CreatorBriefView) */
export interface CoreFact {
  fact_id: string;
  statement: string;
  say_it_like: string;
  significance: string;
  claim_id: string;
  source_id: string;
  speaker?: string;
}

export interface ClaimDrillDownProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** The fact to display details for */
  fact: CoreFact | null;
  /** Close handler */
  onClose: () => void;
  /** Navigate to a document (e.g., doc_0 to see the source) */
  onNavigateToDoc?: (docType: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function ClaimDrillDown({
  isOpen,
  fact,
  onClose,
  onNavigateToDoc,
}: ClaimDrillDownProps) {
  // useRef kept for potential future use but focus is now handled by Radix
  const panelRef = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();

  // Body scroll lock (Radix handles Escape and focus trap)
  useEffect(() => {
    if (!isOpen) return;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  return (
    <DialogPrimitive.Root open={isOpen && !!fact} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <AnimatePresence>
          {isOpen && fact && (
            <>
              {/* Backdrop — Radix overlay for semantics, motion.div for animation */}
              <DialogPrimitive.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
                  className="fixed inset-0 bg-black/50 z-40"
                  onClick={onClose}
                />
              </DialogPrimitive.Overlay>

              {/* Slide-over panel */}
              <DialogPrimitive.Content asChild aria-labelledby="claim-drilldown-title">
                <motion.div
                  ref={panelRef}
                  initial={{ x: prefersReducedMotion ? 0 : '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: prefersReducedMotion ? 0 : '100%' }}
                  transition={prefersReducedMotion ? { duration: 0 } : { type: 'spring', damping: 30, stiffness: 300 }}
                  className="fixed right-0 top-0 bottom-0 w-full sm:w-[480px] bg-gray-900 border-l border-gray-700 z-50 overflow-y-auto"
                >
            {/* Header */}
            <div className="sticky top-0 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 px-6 py-4 z-10">
              <div className="flex items-center justify-between">
                <h2 id="claim-drilldown-title" className="text-lg font-semibold text-gray-100">
                  Fact Details
                </h2>
                <button
                  onClick={onClose}
                  className="p-2.5 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition-colors"
                  aria-label="Close panel"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <span className="text-xs font-mono text-gray-500 mt-1 block">
                {fact.fact_id} → {fact.claim_id} → {fact.source_id}
              </span>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-6">
              {/* Statement */}
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Statement
                </h3>
                <p className="text-gray-200 leading-relaxed">
                  {fact.statement}
                </p>
              </section>

              {/* Say It Like */}
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Say It Like
                </h3>
                <div className="rounded-lg bg-amber-900/15 border border-amber-800/30 p-4">
                  <p className="text-amber-300/90 italic">
                    &ldquo;{fact.say_it_like}&rdquo;
                  </p>
                </div>
              </section>

              {/* Metadata grid */}
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Details
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {/* Significance */}
                  <div className="rounded-lg bg-gray-800/50 p-3">
                    <p className="text-xs text-gray-500 mb-1">Significance</p>
                    <SignificanceIndicator level={fact.significance} />
                  </div>

                  {/* Speaker */}
                  <div className="rounded-lg bg-gray-800/50 p-3">
                    <p className="text-xs text-gray-500 mb-1">Speaker</p>
                    <p className="text-sm text-gray-300">
                      {fact.speaker || 'Not attributed'}
                    </p>
                  </div>

                  {/* Claim ID */}
                  <div className="rounded-lg bg-gray-800/50 p-3">
                    <p className="text-xs text-gray-500 mb-1">Claim Reference</p>
                    <p className="text-sm text-purple-400 font-mono">
                      {fact.claim_id}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      From Doc 2 (Semantic Brief)
                    </p>
                  </div>

                  {/* Source ID */}
                  <div className="rounded-lg bg-gray-800/50 p-3">
                    <p className="text-xs text-gray-500 mb-1">Source Reference</p>
                    <SourceCitation
                      sourceId={fact.source_id}
                      onClick={onNavigateToDoc ? () => onNavigateToDoc('doc_0') : undefined}
                    />
                    <p className="text-xs text-gray-500 mt-0.5">
                      From Doc 0 (Source Ledger)
                    </p>
                  </div>
                </div>
              </section>

              {/* Provenance Chain */}
              <section>
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                  Provenance Chain
                </h3>
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-1 rounded bg-amber-900/30 text-amber-400 text-xs font-mono">
                    {fact.fact_id}
                  </span>
                  <span className="text-gray-600">→</span>
                  <span className="px-2 py-1 rounded bg-purple-900/30 text-purple-400 text-xs font-mono">
                    {fact.claim_id}
                  </span>
                  <span className="text-gray-600">→</span>
                  <span className="px-2 py-1 rounded bg-gray-700 text-gray-300 text-xs font-mono">
                    {fact.source_id}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Creator Brief → Semantic Brief → Source Ledger
                </p>
              </section>

              {/* Navigation actions */}
              {onNavigateToDoc && (
                <section className="pt-4 border-t border-gray-800">
                  <div className="space-y-2">
                    <button
                      onClick={() => onNavigateToDoc('doc_2')}
                      className="w-full px-4 py-2.5 rounded-lg bg-purple-900/20 border border-purple-700/50 text-purple-300 text-sm font-medium hover:bg-purple-900/30 transition-colors text-left"
                    >
                      📊 View claim in Semantic Brief
                    </button>
                    <button
                      onClick={() => onNavigateToDoc('doc_0')}
                      className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 text-sm font-medium hover:bg-gray-700 transition-colors text-left"
                    >
                      📋 View source in Source Ledger
                    </button>
                  </div>
                </section>
              )}
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

export default ClaimDrillDown;
