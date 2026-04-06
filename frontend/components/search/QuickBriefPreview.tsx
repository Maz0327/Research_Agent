/**
 * QuickBriefPreview — Preview version of the Creator Brief from search candidates.
 *
 * Renders a simplified Creator Brief in a desaturated "preview" style
 * with a "Preview" badge. Used in the search approval flow to show
 * what the full research will produce.
 */
import { motion } from 'framer-motion';

interface QuickBriefPreviewProps {
  brief: Record<string, unknown>;
  isLoading?: boolean;
}

export default function QuickBriefPreview({ brief, isLoading }: QuickBriefPreviewProps) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-amber-700/30 bg-amber-900/5 p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="animate-spin h-5 w-5 border-2 border-amber-400 border-t-transparent rounded-full" />
          <span className="text-sm text-amber-300">Generating Quick Brief preview…</span>
        </div>
        <div className="space-y-3 animate-pulse">
          <div className="h-4 w-3/4 bg-card rounded" />
          <div className="h-4 w-1/2 bg-card rounded" />
          <div className="h-4 w-2/3 bg-card rounded" />
        </div>
      </div>
    );
  }

  // Extract brief sections with safe fallbacks
  const hookOptions = (brief?.hook_options as Array<{ text?: string; why_it_works?: string }>) || [];
  const setup = brief?.setup as { text?: string } | undefined;
  const twist = brief?.twist as { text?: string } | undefined;
  const coreFacts = (brief?.core_facts as Array<{ statement?: string; significance?: string }>) || [];
  const analogy = brief?.analogy as { text?: string } | undefined;
  const cliffhanger = brief?.cliffhanger as { text?: string } | undefined;

  const hasContent = hookOptions.length > 0 || setup?.text || coreFacts.length > 0;

  if (!hasContent) {
    return (
      <div className="rounded-xl border border-border bg-background/50 p-6 text-center">
        <p className="text-sm text-muted-foreground/70">No preview available yet. Click &ldquo;Generate Quick Brief&rdquo; to see a preview.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-amber-700/30 bg-gradient-to-br from-gray-900 to-amber-950/10 p-5 relative overflow-hidden"
    >
      {/* Preview badge */}
      <div className="absolute top-3 right-3">
        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
          Preview
        </span>
      </div>

      <h3 className="text-lg font-semibold text-amber-200 mb-4 flex items-center gap-2">
        <span>✨</span>
        <span>Quick Brief Preview</span>
      </h3>

      <div className="space-y-4 opacity-90">
        {/* Hooks */}
        {hookOptions.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Hook Options</h4>
            <div className="space-y-2">
              {hookOptions.slice(0, 2).map((hook, i) => (
                <div key={i} className="rounded-lg border border-border/50 bg-card/30 p-3">
                  <p className="text-sm text-foreground">{hook.text}</p>
                  {hook.why_it_works && (
                    <p className="text-xs text-muted-foreground/70 mt-1 italic">{hook.why_it_works}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Setup */}
        {setup?.text && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Setup</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">{setup.text}</p>
          </div>
        )}

        {/* Twist */}
        {twist?.text && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Twist</h4>
            <div className="rounded-lg border-l-2 border-amber-500/50 pl-3">
              <p className="text-sm text-muted-foreground">{twist.text}</p>
            </div>
          </div>
        )}

        {/* Core Facts */}
        {coreFacts.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Core Facts</h4>
            <div className="space-y-2">
              {coreFacts.slice(0, 3).map((fact, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="text-amber-400 mt-0.5 text-xs">●</span>
                  <div>
                    <p className="text-sm text-foreground">{fact.statement}</p>
                    {fact.significance && (
                      <p className="text-xs text-muted-foreground/70 mt-0.5">{fact.significance}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analogy */}
        {analogy?.text && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Analogy</h4>
            <div className="rounded-lg bg-card/30 border border-border/50 p-3">
              <p className="text-sm text-muted-foreground italic">{analogy.text}</p>
            </div>
          </div>
        )}

        {/* Cliffhanger */}
        {cliffhanger?.text && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Cliffhanger</h4>
            <p className="text-sm text-amber-200/80 font-medium">{cliffhanger.text}</p>
          </div>
        )}
      </div>

      {/* Desaturation overlay */}
      <div className="absolute inset-0 pointer-events-none bg-background/10 mix-blend-saturation rounded-xl" />
    </motion.div>
  );
}
