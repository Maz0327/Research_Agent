/**
 * Animated circular progress indicator.
 * SVG-based with smooth animation.
 */
interface ProgressRingProps {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  color?: 'blue' | 'purple' | 'green' | 'orange';
  showPercentage?: boolean;
  className?: string;
}

const ringColors = {
  blue: {
    track: 'stroke-gray-700',
    progress: 'stroke-blue-500',
    text: 'text-blue-400',
  },
  purple: {
    track: 'stroke-gray-700',
    progress: 'stroke-purple-500',
    text: 'text-purple-400',
  },
  green: {
    track: 'stroke-gray-700',
    progress: 'stroke-green-500',
    text: 'text-green-400',
  },
  orange: {
    track: 'stroke-gray-700',
    progress: 'stroke-orange-500',
    text: 'text-orange-400',
  },
};

export default function ProgressRing({
  progress,
  size = 48,
  strokeWidth = 4,
  color = 'blue',
  showPercentage = true,
  className = '',
}: ProgressRingProps) {
  // Clamp progress between 0 and 100
  const clampedProgress = Math.min(100, Math.max(0, progress));

  // Calculate SVG dimensions
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (clampedProgress / 100) * circumference;

  const colors = ringColors[color];

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          className={colors.track}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={`${colors.progress} transition-all duration-500 ease-out`}
          style={{
            filter: 'drop-shadow(0 0 4px currentColor)',
          }}
        />
      </svg>
      {showPercentage && (
        <span
          className={`absolute text-xs font-semibold ${colors.text}`}
          style={{ fontSize: size * 0.22 }}
        >
          {Math.round(clampedProgress)}%
        </span>
      )}
    </div>
  );
}
