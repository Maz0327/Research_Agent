/**
 * ReadingGuide — Banner above artifact cards suggesting reading order.
 *
 * Shows only when job is completed. Tells users to start with
 * the Creator Brief (Doc 3) — the hero document.
 */

import { motion } from 'framer-motion';

interface ReadingGuideProps {
  /** Whether the Creator Brief (Doc 3) is available */
  hasCreatorBrief: boolean;
  /** Click handler to open the Creator Brief directly */
  onStartReading: () => void;
}

export function ReadingGuide({ hasCreatorBrief, onStartReading }: ReadingGuideProps) {
  if (!hasCreatorBrief) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="mb-4 sm:mb-6 rounded-xl border border-amber-800/30 bg-amber-900/10 px-4 sm:px-5 py-3 sm:py-4"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="text-lg flex-shrink-0 mt-0.5">&#9733;</span>
          <div>
            <p className="text-sm font-medium text-foreground">
              Your research is ready
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Start with the Creator Brief — it&apos;s your script blueprint. Explore the other documents for deeper research.
            </p>
          </div>
        </div>
        <button
          onClick={onStartReading}
          className="flex-shrink-0 inline-flex items-center gap-2 rounded-lg bg-amber-600 hover:bg-amber-500 px-4 py-2 text-sm font-medium text-white transition-colors"
        >
          Start Reading
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
          </svg>
        </button>
      </div>
    </motion.div>
  );
}
