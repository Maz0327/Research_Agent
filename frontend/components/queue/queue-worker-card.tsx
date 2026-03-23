'use client';

/**
 * Worker status card — shows active job progress or idle state.
 */
interface WorkerCardProps {
  name: string;
  jobTitle?: string;
  progress?: number;
  idle?: boolean;
}

export function WorkerCard({ name, jobTitle, progress, idle }: WorkerCardProps) {
  return (
    <div className={`bg-surface-1 border border-border rounded-xl p-3 ${idle ? 'opacity-50' : ''}`}>
      <div className="flex items-center gap-2 mb-2">
        {idle ? (
          <span className="w-2 h-2 rounded-full bg-muted-foreground/60" />
        ) : (
          <span className="w-2 h-2 rounded-full bg-accent-green motion-safe:animate-pulse" />
        )}
        <span className={`text-xs font-medium ${idle ? 'text-muted-foreground/60' : 'text-muted-foreground'}`}>
          {name}
        </span>
      </div>

      {idle ? (
        <p className="text-[11px] text-muted-foreground/60">Idle — ready for next job</p>
      ) : (
        <>
          <p className="text-[11px] text-muted-foreground truncate">{jobTitle}</p>
          <div className="mt-2 h-1 rounded-full bg-surface-3 overflow-hidden">
            <div
              className="h-full rounded-full bg-accent-blue transition-all"
              style={{ width: `${progress ?? 0}%` }}
            />
          </div>
        </>
      )}
    </div>
  );
}
