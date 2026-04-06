/**
 * ClaimIndicators — Unified visual language tokens for claims and facts.
 *
 * These components provide consistent styling for claim-related UI elements
 * across Creator Brief, Semantic Brief, and other document views.
 */

// =============================================================================
// DisputedClaimBadge
// =============================================================================

/** Framing types for disputed claims */
type ClaimFraming = 'disputed' | 'speculative' | 'contradicts' | 'hedged';

const FRAMING_CONFIG: Record<ClaimFraming, { label: string; color: string; bgColor: string }> = {
  disputed: { label: 'Disputed', color: 'text-red-400', bgColor: 'bg-red-900/30' },
  speculative: { label: 'Speculative', color: 'text-yellow-400', bgColor: 'bg-yellow-900/30' },
  contradicts: { label: 'Contradicts', color: 'text-orange-400', bgColor: 'bg-orange-900/30' },
  hedged: { label: 'Hedged', color: 'text-blue-400', bgColor: 'bg-blue-900/30' },
};

export interface DisputedClaimBadgeProps {
  /** The claim framing type */
  framing: string;
  /** Optional additional className */
  className?: string;
}

/**
 * Warning badge for disputed, speculative, or contradicting claims.
 */
export function DisputedClaimBadge({ framing, className = '' }: DisputedClaimBadgeProps) {
  const config = FRAMING_CONFIG[framing as ClaimFraming] || FRAMING_CONFIG.disputed;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium ${config.bgColor} ${config.color} ${className}`}
    >
      <span aria-hidden="true">⚠️</span>
      {config.label}
    </span>
  );
}

// =============================================================================
// VerifiedFactBadge
// =============================================================================

export interface VerifiedFactBadgeProps {
  /** Source ID for linking (e.g., "SRC_1") */
  sourceId?: string;
  /** Click handler to navigate to source */
  onSourceClick?: (sourceId: string) => void;
  /** Optional additional className */
  className?: string;
}

/**
 * Checkmark badge for verified facts with optional source link.
 */
export function VerifiedFactBadge({ sourceId, onSourceClick, className = '' }: VerifiedFactBadgeProps) {
  const handleClick = () => {
    if (sourceId && onSourceClick) {
      onSourceClick(sourceId);
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-green-900/30 text-green-400 ${
        sourceId && onSourceClick ? 'cursor-pointer hover:bg-green-900/50 transition-colors' : ''
      } ${className}`}
      onClick={handleClick}
      role={sourceId && onSourceClick ? 'button' : undefined}
      tabIndex={sourceId && onSourceClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <span aria-hidden="true">✓</span>
      Verified
      {sourceId && (
        <span className="text-green-500 ml-0.5">({sourceId})</span>
      )}
    </span>
  );
}

// =============================================================================
// SignificanceIndicator
// =============================================================================

type SignificanceLevel = 'high' | 'medium' | 'low';

const SIGNIFICANCE_CONFIG: Record<SignificanceLevel, { label: string; color: string; bgColor: string; bars: number }> = {
  high: { label: 'High', color: 'text-green-400', bgColor: 'bg-green-500', bars: 3 },
  medium: { label: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-500', bars: 2 },
  low: { label: 'Low', color: 'text-muted-foreground', bgColor: 'bg-gray-500', bars: 1 },
};

export interface SignificanceIndicatorProps {
  /** Significance level */
  level: string;
  /** Whether to show the text label */
  showLabel?: boolean;
  /** Optional additional className */
  className?: string;
}

/**
 * Visual bar indicator for fact/claim significance (high/medium/low).
 */
export function SignificanceIndicator({ level, showLabel = true, className = '' }: SignificanceIndicatorProps) {
  const config = SIGNIFICANCE_CONFIG[level as SignificanceLevel] || SIGNIFICANCE_CONFIG.medium;

  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      {/* Visual bars */}
      <span className="inline-flex items-end gap-0.5" aria-hidden="true">
        {[1, 2, 3].map((bar) => (
          <span
            key={bar}
            className={`w-1 rounded-sm ${
              bar <= config.bars ? config.bgColor : 'bg-muted'
            }`}
            style={{ height: `${bar * 4 + 4}px` }}
          />
        ))}
      </span>
      {showLabel && (
        <span className={`text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
      )}
    </span>
  );
}

// =============================================================================
// SourceCitation
// =============================================================================

export interface SourceCitationProps {
  /** Source ID (e.g., "SRC_1") */
  sourceId: string;
  /** Source title for display */
  title?: string;
  /** Click handler to navigate to source */
  onClick?: (sourceId: string) => void;
  /** Optional additional className */
  className?: string;
}

/**
 * Formatted source citation reference with click-to-navigate.
 */
export function SourceCitation({ sourceId, title, onClick, className = '' }: SourceCitationProps) {
  const displayId = sourceId.replace(/^SRC_/, 'Source ');

  const handleClick = () => {
    if (onClick) {
      onClick(sourceId);
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs ${
        onClick
          ? 'text-blue-400 hover:text-blue-300 cursor-pointer transition-colors'
          : 'text-muted-foreground'
      } ${className}`}
      onClick={handleClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && onClick) {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <span className="text-muted-foreground/70" aria-hidden="true">📎</span>
      {title || displayId}
    </span>
  );
}

// =============================================================================
// ConfidenceBadge
// =============================================================================

export interface ConfidenceBadgeProps {
  /** Confidence level (high, medium, low) */
  level: string;
  /** Optional additional className */
  className?: string;
}

const CONFIDENCE_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  high: { label: 'High', color: 'text-green-400', bgColor: 'bg-green-900/30' },
  medium: { label: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-900/30' },
  low: { label: 'Low', color: 'text-orange-400', bgColor: 'bg-orange-900/30' },
};

/**
 * Badge showing confidence level with color coding.
 */
export function ConfidenceBadge({ level, className = '' }: ConfidenceBadgeProps) {
  const config = CONFIDENCE_CONFIG[level?.toLowerCase()] || { label: level, color: 'text-muted-foreground', bgColor: 'bg-background/30' };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${config.bgColor} ${config.color} ${className}`}>
      {config.label}
    </span>
  );
}
