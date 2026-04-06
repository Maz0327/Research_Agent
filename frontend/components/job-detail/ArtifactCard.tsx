/**
 * ArtifactCard - Premium artifact card component
 *
 * Design language: Linear/Vercel-inspired dark theme
 * - Semi-transparent borders (white/[0.06])
 * - Opacity-based text hierarchy (white, white/60, white/35)
 * - SVG icons (no emojis)
 * - Thin gradient progress bar with glow
 * - Spring animations with proper easing
 */
import { motion } from 'framer-motion';

// ─── Types ──────────────────────────────────────────────────────────────────────

export type ArtifactState =
  | 'not_available'
  | 'ready'
  | 'queued'
  | 'waiting'
  | 'running'
  | 'nearly_ready'
  | 'completed'
  | 'failed';

export type ArtifactType =
  | 'doc_0'
  | 'doc_1'
  | 'doc_2'
  | 'doc_3'
  | 'doc_4'
  | 'doc_5'
  | 'doc_6'
  | 'doc_7'
  | 'booster'
  | 'iteration'
  | 'claims_doc';

// ─── SVG Icons ──────────────────────────────────────────────────────────────────

/** Clean SVG icons for each artifact type */
function DocIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="3" y="2" width="14" height="16" rx="2" />
      <line x1="6" y1="6" x2="14" y2="6" />
      <line x1="6" y1="9" x2="14" y2="9" />
      <line x1="6" y1="12" x2="10" y2="12" />
    </svg>
  );
}

function CompassIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="10" cy="10" r="8" />
      <polygon points="10,4 12,10 10,16 8,10" fill="currentColor" opacity="0.3" />
      <circle cx="10" cy="10" r="1.5" fill="currentColor" />
    </svg>
  );
}

function PrismIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <polygon points="10,2 18,16 2,16" />
      <line x1="10" y1="2" x2="10" y2="16" opacity="0.3" />
      <line x1="6" y1="9" x2="14" y2="9" opacity="0.3" />
    </svg>
  );
}

function SparkIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M10 2 L12 8 L18 10 L12 12 L10 18 L8 12 L2 10 L8 8 Z" />
    </svg>
  );
}

function FilmIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="3" width="16" height="14" rx="2" />
      <line x1="2" y1="7" x2="18" y2="7" />
      <line x1="2" y1="13" x2="18" y2="13" />
      <line x1="6" y1="3" x2="6" y2="7" />
      <line x1="14" y1="3" x2="14" y2="7" />
      <line x1="6" y1="13" x2="6" y2="17" />
      <line x1="14" y1="13" x2="14" y2="17" />
    </svg>
  );
}

function ScopeIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="10" cy="10" r="7" />
      <circle cx="10" cy="10" r="3" />
      <line x1="10" y1="1" x2="10" y2="4" />
      <line x1="10" y1="16" x2="10" y2="19" />
      <line x1="1" y1="10" x2="4" y2="10" />
      <line x1="16" y1="10" x2="19" y2="10" />
    </svg>
  );
}

function LayersIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <polygon points="10,2 18,7 10,12 2,7" />
      <polyline points="2,10 10,15 18,10" />
      <polyline points="2,13 10,18 18,13" />
    </svg>
  );
}

function ClipboardIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="4" y="4" width="12" height="14" rx="2" />
      <path d="M8 2 h4 a1 1 0 0 1 1 1 v1 H7 V3 a1 1 0 0 1 1-1z" />
      <line x1="7" y1="9" x2="13" y2="9" />
      <line x1="7" y1="12" x2="11" y2="12" />
    </svg>
  );
}

function ScriptIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="3" y="2" width="14" height="16" rx="2" />
      <line x1="6" y1="6" x2="14" y2="6" />
      <line x1="6" y1="9" x2="12" y2="9" />
      <line x1="6" y1="12" x2="14" y2="12" />
      <line x1="6" y1="15" x2="10" y2="15" />
      <circle cx="15" cy="14" r="2" fill="currentColor" opacity="0.3" />
    </svg>
  );
}

function ShareIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="5" cy="10" r="2.5" />
      <circle cx="15" cy="5" r="2.5" />
      <circle cx="15" cy="15" r="2.5" />
      <line x1="7" y1="9" x2="13" y2="6" />
      <line x1="7" y1="11" x2="13" y2="14" />
    </svg>
  );
}

function BlogIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="16" height="16" rx="2" />
      <line x1="5" y1="6" x2="15" y2="6" />
      <line x1="5" y1="9" x2="15" y2="9" />
      <line x1="5" y1="12" x2="11" y2="12" />
      <rect x="12" y="11" width="3" height="4" rx="0.5" fill="currentColor" opacity="0.2" />
    </svg>
  );
}

/** SVG spinner - replaces CSS border hack */
function Spinner({ size = 18, color = 'currentColor' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="animate-spin">
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.15" />
      <path d="M12 2 a10 10 0 0 1 10 10" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

/** Animated checkmark SVG */
function CheckIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="9" fill="currentColor" opacity="0.15" />
      <path d="M6 10 L9 13 L14 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function XIcon({ className = 'w-5 h-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="9" fill="currentColor" opacity="0.15" />
      <path d="M7 7 L13 13 M13 7 L7 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// ─── Configuration ──────────────────────────────────────────────────────────────

/** Accent color per artifact type (used for icon tint and progress bar) */
const ACCENT_COLORS: Record<ArtifactType, { icon: string; bar: string; glow: string }> = {
  doc_0: { icon: 'text-muted-foreground', bar: 'from-gray-500 to-gray-400', glow: 'rgba(156,163,175,0.3)' },
  doc_1: { icon: 'text-blue-400', bar: 'from-blue-500 to-blue-400', glow: 'rgba(59,130,246,0.3)' },
  doc_2: { icon: 'text-purple-400', bar: 'from-purple-500 to-purple-400', glow: 'rgba(139,92,246,0.3)' },
  doc_3: { icon: 'text-amber-400', bar: 'from-amber-500 to-amber-400', glow: 'rgba(245,158,11,0.3)' },
  doc_4: { icon: 'text-green-400', bar: 'from-green-500 to-green-400', glow: 'rgba(34,197,94,0.3)' },
  doc_5: { icon: 'text-cyan-400', bar: 'from-cyan-500 to-cyan-400', glow: 'rgba(6,182,212,0.3)' },
  doc_6: { icon: 'text-pink-400', bar: 'from-pink-500 to-pink-400', glow: 'rgba(236,72,153,0.3)' },
  doc_7: { icon: 'text-emerald-400', bar: 'from-emerald-500 to-emerald-400', glow: 'rgba(16,185,129,0.3)' },
  booster: { icon: 'text-indigo-400', bar: 'from-indigo-500 to-indigo-400', glow: 'rgba(99,102,241,0.3)' },
  iteration: { icon: 'text-teal-400', bar: 'from-teal-500 to-teal-400', glow: 'rgba(20,184,166,0.3)' },
  claims_doc: { icon: 'text-rose-400', bar: 'from-rose-500 to-rose-400', glow: 'rgba(244,63,94,0.3)' },
};

/** Icon component per artifact type */
const ARTIFACT_ICONS: Record<ArtifactType, React.FC<{ className?: string }>> = {
  doc_0: DocIcon,
  doc_1: CompassIcon,
  doc_2: PrismIcon,
  doc_3: SparkIcon,
  doc_4: FilmIcon,
  doc_5: ScriptIcon,
  doc_6: ShareIcon,
  doc_7: BlogIcon,
  booster: ScopeIcon,
  iteration: LayersIcon,
  claims_doc: ClipboardIcon,
};

const ARTIFACT_CONFIG: Record<ArtifactType, {
  title: string;
  subtitle: string;
  readyLabel: string;
}> = {
  doc_0: { title: 'Source Ledger', subtitle: 'Cataloged sources', readyLabel: 'View Sources' },
  doc_1: { title: 'Jump-Start', subtitle: 'Research directions', readyLabel: 'View Directions' },
  doc_2: { title: 'Semantic Brief', subtitle: 'Themes & insights', readyLabel: 'View Brief' },
  doc_3: { title: 'Creator Brief', subtitle: 'Production-ready brief', readyLabel: 'Generate' },
  doc_4: { title: 'Producer Packet', subtitle: 'Production notes', readyLabel: 'Generate' },
  doc_5: { title: 'Script', subtitle: 'Video script', readyLabel: 'Generate' },
  doc_6: { title: 'Social Kit', subtitle: 'Social media posts', readyLabel: 'Generate' },
  doc_7: { title: 'Blog Post', subtitle: 'SEO article', readyLabel: 'Generate' },
  booster: { title: 'Deep Research', subtitle: 'Expanded analysis', readyLabel: 'Start Analysis' },
  iteration: { title: 'Iterations', subtitle: 'Additional passes', readyLabel: 'Run New Pass' },
  claims_doc: { title: 'Claims', subtitle: 'Extracted claims', readyLabel: 'View Claims' },
};

/** States that block clicks */
const NON_INTERACTIVE_STATES: ArtifactState[] = [
  'not_available', 'queued', 'waiting', 'running', 'nearly_ready',
];

// ─── Props ──────────────────────────────────────────────────────────────────────

export interface ArtifactCardProps {
  type: ArtifactType;
  state: ArtifactState;
  progressPercent?: number;
  runningDescription?: string;
  error?: string;
  iterationCount?: number;
  iterationId?: string;
  onClick: () => void;
  onRetry?: () => void;
  /** Reading order badge (e.g. "1 · Start Here") */
  readingOrder?: string;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function ArtifactCard({
  type,
  state,
  progressPercent = 0,
  runningDescription,
  error,
  iterationCount = 0,
  iterationId,
  onClick,
  onRetry,
  readingOrder,
}: ArtifactCardProps) {
  const config = ARTIFACT_CONFIG[type];
  const accent = ACCENT_COLORS[type];
  const IconComponent = ARTIFACT_ICONS[type];
  const isInteractive = !NON_INTERACTIVE_STATES.includes(state);

  const getStatusText = () => {
    if (runningDescription) return runningDescription;
    switch (state) {
      case 'not_available':
        return 'Not available yet';
      case 'ready':
        return config.readyLabel;
      case 'queued':
        return 'Queued';
      case 'waiting':
        return 'Waiting for pipeline';
      case 'running':
        return type === 'doc_0' ? 'Cataloging sources' :
               type === 'doc_1' ? 'Finding directions' :
               type === 'doc_2' ? 'Synthesizing themes' :
               type === 'doc_3' ? 'Generating brief' :
               type === 'doc_5' ? 'Writing script' :
               type === 'doc_6' ? 'Creating social posts' :
               type === 'doc_7' ? 'Writing blog post' :
               type === 'booster' ? 'Expanding research' :
               type === 'iteration' ? 'Running analysis' :
               type === 'claims_doc' ? 'Extracting claims' :
               'Processing';
      case 'nearly_ready':
        return 'Almost done';
      case 'completed':
        if (type === 'iteration' && iterationCount > 0) {
          return `${iterationCount} pass${iterationCount > 1 ? 'es' : ''} complete`;
        }
        return 'Complete';
      case 'failed':
        return 'Failed';
      default:
        return '';
    }
  };

  const handleClick = () => {
    if (!isInteractive) return;
    if (state === 'failed' && onRetry) {
      onRetry();
    } else {
      onClick();
    }
  };

  // Border + background per state — restrained, no color flooding
  const cardClasses = (() => {
    switch (state) {
      case 'not_available':
        return 'border-white/[0.04] bg-white/[0.02]';
      case 'waiting':
        return 'border-dashed border-white/[0.06] bg-white/[0.02]';
      case 'queued':
        return 'border-white/[0.08] bg-white/[0.03]';
      case 'ready':
        return 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.05]';
      case 'running':
        return 'border-white/[0.1] bg-white/[0.03]';
      case 'nearly_ready':
        return 'border-white/[0.1] bg-white/[0.03]';
      case 'completed':
        return 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.15] hover:bg-white/[0.05]';
      case 'failed':
        return 'border-red-500/20 bg-red-500/[0.03] hover:border-red-500/30 hover:bg-red-500/[0.05]';
      default:
        return 'border-white/[0.06] bg-white/[0.03]';
    }
  })();

  const showProgress = state === 'running' || state === 'nearly_ready';

  return (
    <motion.div
      whileHover={isInteractive ? { y: -1 } : {}}
      whileTap={isInteractive ? { scale: 0.99 } : {}}
      onClick={handleClick}
      className={`
        relative rounded-lg border overflow-hidden transition-colors duration-200
        ${cardClasses}
        ${isInteractive ? 'cursor-pointer' : state === 'not_available' ? 'cursor-default' : 'cursor-default'}
      `}
      style={state === 'running' ? {
        boxShadow: `0 0 0 1px rgba(255,255,255,0.04), 0 0 24px -8px ${accent.glow}`,
      } : undefined}
    >
      <div className="p-4">
        {/* Header: icon + title + status indicator */}
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`
            flex-shrink-0 mt-0.5 transition-opacity duration-300
            ${state === 'waiting' || state === 'not_available' ? 'opacity-30' : 'opacity-100'}
            ${state === 'completed' ? 'text-emerald-400' : state === 'failed' ? 'text-red-400' : accent.icon}
          `}>
            <IconComponent className="w-5 h-5" />
          </div>

          {/* Title + subtitle + reading order badge */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className={`
                text-sm font-semibold tracking-tight transition-opacity duration-300
                ${state === 'waiting' || state === 'not_available' ? 'text-white/30' : 'text-white/90'}
              `}>
                {config.title}
              </h3>
              {readingOrder && state === 'completed' && (
                <span className={`
                  text-caption px-1.5 py-0.5 rounded-full font-medium
                  ${type === 'doc_3'
                    ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
                    : 'bg-white/[0.06] text-white/40 border border-white/[0.06]'
                  }
                `}>
                  {readingOrder}
                </span>
              )}
            </div>
            <p className={`
              text-xs mt-0.5 transition-opacity duration-300
              ${state === 'waiting' || state === 'not_available' ? 'text-white/15' : 'text-white/40'}
            `}>
              {config.subtitle}
            </p>
          </div>

          {/* Status indicator */}
          <div className="flex-shrink-0 mt-0.5">
            {state === 'completed' && (
              <motion.div
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              >
                <CheckIcon className="w-5 h-5 text-emerald-400" />
              </motion.div>
            )}
            {state === 'failed' && (
              <XIcon className="w-5 h-5 text-red-400" />
            )}
            {(state === 'running' || state === 'nearly_ready') && (
              <Spinner size={16} color={state === 'nearly_ready' ? '#60a5fa' : '#9ca3af'} />
            )}
            {state === 'queued' && (
              <motion.div
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                className="w-2 h-2 rounded-full bg-amber-400"
              />
            )}
            {state === 'waiting' && (
              <div className="w-1.5 h-1.5 rounded-full bg-white/15" />
            )}
          </div>
        </div>

        {/* Progress bar — thin gradient with glow */}
        {showProgress && (
          <div className="mt-3">
            <div className="h-[3px] rounded-full bg-white/[0.06] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{
                  width: `${progressPercent}%`,
                  opacity: state === 'nearly_ready' ? [1, 0.6, 1] : 1,
                }}
                transition={state === 'nearly_ready'
                  ? {
                      width: { type: 'spring', stiffness: 100, damping: 20 },
                      opacity: { duration: 2, repeat: Infinity, ease: 'easeInOut' },
                    }
                  : { type: 'spring', stiffness: 100, damping: 20 }
                }
                className={`h-full rounded-full bg-gradient-to-r ${accent.bar}`}
                style={{ boxShadow: `0 0 8px ${accent.glow}` }}
              />
            </div>
            {iterationId && (
              <p className="text-caption text-white/25 mt-1.5 font-mono">{iterationId}</p>
            )}
          </div>
        )}

        {/* Status text / action label */}
        <div className="mt-3 flex items-center justify-between">
          {state === 'completed' && type !== 'iteration' ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-white/60 hover:text-white/80 transition-colors">
              View
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 16 16" stroke="currentColor" strokeWidth="2">
                <path d="M6 4 L10 8 L6 12" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          ) : state === 'running' || state === 'nearly_ready' ? (
            <div className="flex items-center justify-between w-full">
              <span className="text-xs text-white/40">{getStatusText()}</span>
              {state === 'running' && (
                <span className="text-caption font-mono text-white/30">{progressPercent}%</span>
              )}
            </div>
          ) : state === 'failed' ? (
            <span className="text-xs font-medium text-red-400/80">Retry</span>
          ) : state === 'ready' ? (
            <span className="text-xs font-medium text-white/60">{config.readyLabel}</span>
          ) : (
            <span className={`text-xs ${state === 'waiting' || state === 'not_available' ? 'text-white/20' : 'text-white/35'}`}>
              {getStatusText()}
            </span>
          )}
        </div>

        {/* Error preview */}
        {state === 'failed' && error && (
          <p className="mt-2 text-caption text-red-400/60 line-clamp-2">{error}</p>
        )}
      </div>
    </motion.div>
  );
}

export default ArtifactCard;
