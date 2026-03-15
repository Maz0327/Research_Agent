/**
 * DocumentAccordion — Collapsed accordion for supporting documents.
 *
 * Phase 3D: Progressive Document Reveal
 * Shows Doc 2, 1, 0, and 4 in collapsed accordion sections below the
 * hero Creator Brief. Uses CollapsibleSection pattern from Phase 2C.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Job } from '../../store/jobs';

interface AccordionItem {
  docNumber: 0 | 1 | 2 | 4;
  title: string;
  subtitle: string;
  accentColor: string;
  available: boolean;
}

interface DocumentAccordionProps {
  job: Job;
  onOpenDoc: (docNumber: 0 | 1 | 2 | 4, title: string) => void;
}

export function DocumentAccordion({ job, onOpenDoc }: DocumentAccordionProps) {
  const [expandedDoc, setExpandedDoc] = useState<number | null>(null);
  const { artifacts } = job;

  const items: AccordionItem[] = [
    {
      docNumber: 2,
      title: 'Deep Research',
      subtitle: 'Themes, tensions, and confidence assessment',
      accentColor: 'border-purple-500/40 text-purple-400',
      available: !!(artifacts?.doc_2_path || artifacts?.semantic_brief),
    },
    {
      docNumber: 1,
      title: 'Next Steps',
      subtitle: 'Search directions and gap-based suggestions',
      accentColor: 'border-blue-500/40 text-blue-400',
      available: !!(artifacts?.doc_1_path || artifacts?.jump_start),
    },
    {
      docNumber: 0,
      title: 'All Sources',
      subtitle: 'Source metadata, URLs, and analysis modes',
      accentColor: 'border-gray-500/40 text-gray-400',
      available: !!(artifacts?.doc_0_path || artifacts?.source_ledger),
    },
    {
      docNumber: 4,
      title: 'Production Notes',
      subtitle: 'Detailed production packet for advanced users',
      accentColor: 'border-amber-500/40 text-amber-400',
      available: !!artifacts?.doc_4_path,
    },
  ];

  const availableItems = items.filter((item) => item.available);

  if (availableItems.length === 0) return null;

  return (
    <div className="space-y-1">
      <p className="text-[11px] text-white/25 uppercase tracking-wider font-medium mb-2">Supporting Documents</p>
      {availableItems.map((item) => {
        const isExpanded = expandedDoc === item.docNumber;

        return (
          <div
            key={item.docNumber}
            className="rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden"
          >
            {/* Accordion header */}
            <button
              onClick={() => setExpandedDoc(isExpanded ? null : item.docNumber)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={`w-1 h-6 rounded-full border-l-2 ${item.accentColor.split(' ')[0]}`} />
                <div className="text-left">
                  <p className="text-[13px] font-medium text-white/80">
                    Doc {item.docNumber}: {item.title}
                  </p>
                  <p className="text-[11px] text-white/30">{item.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <svg
                  className={`w-4 h-4 text-white/30 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </button>

            {/* Expanded content */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-3 border-t border-white/[0.04]">
                    <div className="pt-3 flex items-center justify-between">
                      <p className="text-[12px] text-white/40">{item.subtitle}</p>
                      <button
                        onClick={() => onOpenDoc(item.docNumber, item.title)}
                        className={`text-[12px] font-medium px-3 py-1.5 rounded-lg border transition-colors ${item.accentColor} hover:bg-white/[0.04]`}
                      >
                        Open Document
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
