/**
 * Panel for selecting interpretations when a job is in 'disambiguating' status.
 */
import { useState } from 'react';
import { Interpretation, useJobsStore } from '../../store/jobs';

interface DisambiguationPanelProps {
  jobId: string;
  interpretations: Interpretation[];
}

export function DisambiguationPanel({ jobId, interpretations }: DisambiguationPanelProps) {
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectInterpretation = useJobsStore((state) => state.selectInterpretation);

  const toggleSelection = (index: number) => {
    setSelectedIndices((prev) =>
      prev.includes(index)
        ? prev.filter((i) => i !== index)
        : [...prev, index]
    );
  };

  const handleResearchSelected = async () => {
    if (selectedIndices.length === 0) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await selectInterpretation(jobId, selectedIndices);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit selection');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResearchAll = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      await selectInterpretation(jobId, 'all');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit selection');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-yellow-500/30 bg-yellow-900/20 p-4">
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="h-5 w-5 text-yellow-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-sm font-medium text-yellow-300">
          This topic could mean different things. Which would you like to research?
        </p>
      </div>

      <div className="space-y-2">
        {interpretations.map((interp, idx) => (
          <label
            key={idx}
            className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
              selectedIndices.includes(idx)
                ? 'bg-yellow-800/40 border border-yellow-500/50'
                : 'bg-card/50 border border-border hover:border-border'
            }`}
          >
            <input
              type="checkbox"
              checked={selectedIndices.includes(idx)}
              onChange={() => toggleSelection(idx)}
              disabled={isSubmitting}
              className="mt-1 h-4 w-4 rounded border-border bg-muted text-yellow-500 focus:ring-yellow-500 focus:ring-offset-0"
            />
            <div className="flex-1 min-w-0">
              <span className="font-medium text-foreground">{interp.label}</span>
              <p className="text-sm text-muted-foreground mt-0.5">{interp.description}</p>
            </div>
          </label>
        ))}
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-400">{error}</p>
      )}

      <div className="flex gap-3 mt-4">
        <button
          onClick={handleResearchSelected}
          disabled={selectedIndices.length === 0 || isSubmitting}
          className="flex-1 rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-yellow-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Starting...' : `Research Selected (${selectedIndices.length})`}
        </button>
        <button
          onClick={handleResearchAll}
          disabled={isSubmitting}
          className="rounded-lg bg-muted px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? 'Starting...' : 'Research All'}
        </button>
      </div>
    </div>
  );
}
