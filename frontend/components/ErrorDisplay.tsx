/**
 * User-friendly error display component with expandable technical details.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ErrorDisplayProps {
  error: string;
  showTechnical?: boolean;
  className?: string;
}

// Map technical errors to user-friendly messages
const ERROR_MAPPINGS: Record<string, string> = {
  'OpenAI API': 'The AI service is temporarily unavailable. Please try again in a few minutes.',
  'rate limit': 'The system is busy. Your request will be processed shortly.',
  'SIGKILL': 'Processing was interrupted due to resource limits. Try with fewer sources.',
  'memory': 'Processing was interrupted. Try with a smaller research scope.',
  'timeout': 'The request took too long. Please try again.',
  'authentication': 'Your session has expired. Please log in again.',
  'network': 'Unable to connect to the server. Check your internet connection.',
  'Perplexity': 'The research service is temporarily unavailable. Please try again.',
  'YouTube': 'Unable to fetch video content. Some videos may be unavailable.',
  'Google Drive': 'Unable to save to Google Drive. Check your folder permissions.',
  'validation': 'Some information could not be verified. Results may be incomplete.',
};

function getUserFriendlyMessage(technicalError: string): string {
  // Check for known error patterns
  for (const [pattern, message] of Object.entries(ERROR_MAPPINGS)) {
    if (technicalError.toLowerCase().includes(pattern.toLowerCase())) {
      return message;
    }
  }

  // Default message for unknown errors
  return 'An unexpected error occurred. Please try again or contact support if the problem persists.';
}

export default function ErrorDisplay({
  error,
  showTechnical = false,
  className = '',
}: ErrorDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const userMessage = getUserFriendlyMessage(error);
  const hasTechnicalDetails = error !== userMessage;

  return (
    <div
      className={`rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 ${className}`}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Error icon */}
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-red-500 dark:text-red-400"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          </div>

          {/* Error content */}
          <div className="flex-1">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
              Error
            </h3>
            <p className="mt-1 text-sm text-red-700 dark:text-red-300">
              {userMessage}
            </p>

            {/* Technical details toggle */}
            {(showTechnical || hasTechnicalDetails) && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-2 flex items-center gap-1 text-xs text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
              >
                <svg
                  className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                {isExpanded ? 'Hide' : 'Show'} technical details
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Technical details panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-red-200 bg-red-100 px-4 py-3 dark:border-red-800 dark:bg-red-900/30">
              <p className="font-mono text-xs text-red-800 dark:text-red-300 break-all">
                {error}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Inline error for form fields
export function InlineError({ message }: { message: string }) {
  return (
    <motion.p
      initial={{ opacity: 0, y: -5 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-1 text-sm text-red-600 dark:text-red-400"
    >
      {message}
    </motion.p>
  );
}

// Toast-style error notification
export function ErrorToast({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 50, scale: 0.9 }}
      className="fixed bottom-4 right-4 z-50 flex items-center gap-3 rounded-lg border border-red-200 bg-white px-4 py-3 shadow-lg dark:border-red-800 dark:bg-card"
    >
      <svg
        className="h-5 w-5 flex-shrink-0 text-red-500"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
      <p className="text-sm text-foreground">{message}</p>
      <button
        onClick={onDismiss}
        className="ml-2 text-muted-foreground hover:text-muted-foreground/60 dark:hover:text-foreground"
      >
        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </motion.div>
  );
}
