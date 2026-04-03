/**
 * FloatingActionButton - Mobile FAB for quick actions.
 * Shown at bottom-right when create panel is collapsed.
 */
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

interface FloatingActionButtonProps {
  onClick: () => void;
  visible: boolean;
  label?: string;
}

export function FloatingActionButton({ onClick, visible, label = 'Create new job' }: FloatingActionButtonProps) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          initial={prefersReducedMotion ? false : { scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={prefersReducedMotion ? {} : { scale: 0, opacity: 0 }}
          transition={prefersReducedMotion ? { duration: 0 } : { type: 'spring', stiffness: 260, damping: 20 }}
          onClick={onClick}
          aria-label={label}
          className="fixed bottom-20 right-4 z-overlay lg:hidden flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 active:scale-95 transition-all touch-manipulation"
          style={{
            // Account for safe area on iOS
            marginBottom: 'env(safe-area-inset-bottom, 0px)'
          }}
        >
          <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </motion.button>
      )}
    </AnimatePresence>
  );
}

export default FloatingActionButton;
