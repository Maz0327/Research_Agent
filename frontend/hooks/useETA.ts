/**
 * Hook for calculating dynamic ETA for job completion.
 */
import { useState, useEffect, useRef } from 'react';

interface UseETAOptions {
  progress: number;
  status: string;
  createdAt: string;
}

interface ETAResult {
  eta: string | null;
  elapsed: string;
  estimatedTotal: number | null;
  isCalculating: boolean;
}

// Average stage durations in seconds (based on typical job performance)
const STAGE_DURATIONS: Record<string, number> = {
  quick: 300, // 5 min
  full: 900, // 15 min
  breaking_news: 180, // 3 min
  investigation: 600, // 10 min
  profile: 420, // 7 min
  controversy: 480, // 8 min
};

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
}

export default function useETA({
  progress,
  status,
  createdAt,
}: UseETAOptions): ETAResult {
  const [elapsed, setElapsed] = useState(0);
  const progressHistoryRef = useRef<Array<{ progress: number; time: number }>>([]);
  const [estimatedTotal, setEstimatedTotal] = useState<number | null>(null);

  // Update elapsed time every second
  useEffect(() => {
    if (status !== 'running' && status !== 'queued') {
      return;
    }

    const startTime = new Date(createdAt).getTime();

    const updateElapsed = () => {
      const now = Date.now();
      setElapsed(Math.floor((now - startTime) / 1000));
    };

    updateElapsed();
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [createdAt, status]);

  // Track progress history for rate calculation
  useEffect(() => {
    if (status !== 'running') return;

    const now = Date.now();
    const history = progressHistoryRef.current;

    // Add current progress point
    history.push({ progress, time: now });

    // Keep only last 10 data points for smoothing
    if (history.length > 10) {
      history.shift();
    }

    // Calculate estimated total time based on progress rate
    if (history.length >= 2 && progress > 0) {
      const oldest = history[0];
      const newest = history[history.length - 1];

      const progressDelta = newest.progress - oldest.progress;
      const timeDelta = (newest.time - oldest.time) / 1000; // in seconds

      if (progressDelta > 0 && timeDelta > 0) {
        const progressRate = progressDelta / timeDelta; // percent per second
        const remainingProgress = 100 - progress;
        const remainingTime = remainingProgress / progressRate;

        // Total estimated time
        const total = elapsed + remainingTime;
        setEstimatedTotal(Math.round(total));
      }
    }
  }, [progress, status, elapsed]);

  // Calculate ETA
  const calculateETA = (): string | null => {
    if (status !== 'running' || progress === 0) {
      return null;
    }

    if (estimatedTotal && estimatedTotal > elapsed) {
      const remaining = estimatedTotal - elapsed;
      return formatDuration(remaining);
    }

    // Fallback: simple linear extrapolation
    if (progress > 0) {
      const remainingProgress = 100 - progress;
      const timePerPercent = elapsed / progress;
      const remainingTime = remainingProgress * timePerPercent;
      return formatDuration(remainingTime);
    }

    return null;
  };

  return {
    eta: calculateETA(),
    elapsed: formatDuration(elapsed),
    estimatedTotal,
    isCalculating: status === 'running' && progress > 0 && progress < 100,
  };
}
