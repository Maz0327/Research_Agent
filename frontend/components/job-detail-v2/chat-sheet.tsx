'use client';

/**
 * ChatSheet — Right-side Sheet with Iterate and Brainstorm tabs.
 * Iterate: quick-action cards (2×2 grid) + optional custom text input.
 * Brainstorm: topic prompt + submit.
 */
import { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Search, Plus, Microscope, RefreshCw } from 'lucide-react';
import { useJobsStore } from '@/store/jobs';
import type { Job, DocumentVersion } from '@/store/jobs';
import { formatDistanceToNow } from 'date-fns';

/** Maps backend trigger names to creator-friendly labels. */
const TRIGGER_LABELS: Record<string, string> = {
  initial_run:     'Original research',
  deep_dive:       "Found what's missing",
  expand_sources:  'Added more sources',
  deeper:          'Dug deeper',
  different_angle: 'New angle',
  custom:          'Custom update',
};

/** Quick-action card definition. */
interface QuickAction {
  icon: React.ElementType;
  title: string;
  description: string;
  mode: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: Search,
    title: "Find What's Missing",
    description: 'Uncover gaps and new research directions',
    mode: 'deep_dive',
  },
  {
    icon: Plus,
    title: 'Add More Sources',
    description: 'Add new videos or articles',
    mode: 'expand_sources',
  },
  {
    icon: Microscope,
    title: 'Dig Deeper',
    description: 'Re-analyze with more depth',
    mode: 'deeper',
  },
  {
    icon: RefreshCw,
    title: 'Try a New Angle',
    description: 'Same research, fresh perspective',
    mode: 'different_angle',
  },
];

interface ChatSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job: Job;
  /** Pre-select a mode when opening from a quick-action button. */
  initialMode?: string;
}

export function ChatSheet({ open, onOpenChange, job, initialMode }: ChatSheetProps) {
  const { iterateJob, brainstormTopic, isBrainstorming, fetchDocumentVersions, documentVersions } =
    useJobsStore();

  // Iterate state
  const [selectedMode, setSelectedMode] = useState<string | null>(initialMode ?? null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [iterating, setIterating] = useState(false);
  const [iterateError, setIterateError] = useState<string | null>(null);

  // Brainstorm state
  const [brainstormPrompt, setBrainstormPrompt] = useState('');
  const [brainstormError, setBrainstormError] = useState<string | null>(null);

  // Apply initialMode when it changes (e.g. opened from quick-action button)
  useEffect(() => {
    if (initialMode) setSelectedMode(initialMode);
  }, [initialMode]);

  // Load doc_1 versions for history (doc_1 = Jump-Start / iterations)
  useEffect(() => {
    if (open && job?.id) {
      fetchDocumentVersions(job.id, 'doc_1').catch(() => {/* non-fatal */});
    }
  }, [open, job?.id, fetchDocumentVersions]);

  const versionHistory: DocumentVersion[] = documentVersions[`${job.id}_doc_1`] ?? [];

  /** Determine the effective mode for submission. */
  const effectiveMode = customPrompt.trim() ? 'custom' : selectedMode;

  const canSubmit = Boolean(effectiveMode) && (customPrompt.trim().length > 0 || selectedMode !== null);

  const handleIterate = async () => {
    if (!effectiveMode) return;
    setIterating(true);
    setIterateError(null);
    try {
      await iterateJob(job.id, {
        mode: effectiveMode as any,
        user_prompt: customPrompt.trim() || undefined,
        max_new_sources: 5,
      });
      setCustomPrompt('');
      setSelectedMode(null);
      onOpenChange(false);
    } catch (e: any) {
      setIterateError(e?.message ?? 'Iterate failed');
    } finally {
      setIterating(false);
    }
  };

  const handleBrainstorm = async () => {
    if (!brainstormPrompt.trim()) return;
    setBrainstormError(null);
    try {
      await brainstormTopic(brainstormPrompt.trim());
      setBrainstormPrompt('');
    } catch (e: any) {
      setBrainstormError(e?.message ?? 'Brainstorm failed');
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:w-[420px] p-0 bg-card border-border flex flex-col"
      >
        <SheetHeader className="px-4 py-3 border-b border-border flex-shrink-0">
          <SheetTitle className="text-sm text-foreground">AI Actions</SheetTitle>
        </SheetHeader>

        <Tabs defaultValue="iterate" className="flex-1 flex flex-col min-h-0">
          <TabsList className="mx-4 mt-3 grid grid-cols-2 flex-shrink-0 bg-secondary">
            <TabsTrigger value="iterate" className="text-xs">Iterate</TabsTrigger>
            <TabsTrigger value="brainstorm" className="text-xs">Brainstorm</TabsTrigger>
          </TabsList>

          {/* ── Iterate tab ── */}
          <TabsContent value="iterate" className="flex-1 px-4 pb-4 pt-3 space-y-4 overflow-y-auto">

            {/* Section heading */}
            <p className="text-xs text-muted-foreground">What would you like to do?</p>

            {/* 2×2 quick-action card grid */}
            <div className="grid grid-cols-2 gap-2">
              {QUICK_ACTIONS.map((action) => {
                const Icon = action.icon;
                const isSelected = selectedMode === action.mode;
                return (
                  <button
                    key={action.mode}
                    onClick={() => setSelectedMode(isSelected ? null : action.mode)}
                    className={[
                      'flex flex-col gap-1 rounded-lg border p-3 text-left cursor-pointer transition-colors',
                      isSelected
                        ? 'bg-primary/10 border-primary text-foreground'
                        : 'bg-card hover:bg-secondary border-border text-foreground',
                    ].join(' ')}
                  >
                    <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    <span className="text-xs font-medium leading-tight">{action.title}</span>
                    <span className="text-[10px] text-muted-foreground leading-tight">
                      {action.description}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Custom text area */}
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Or describe what you need…</label>
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Type any custom instructions here…"
                rows={3}
                className="w-full rounded-md border border-border bg-secondary px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {iterateError && (
              <p className="text-xs text-destructive">{iterateError}</p>
            )}

            <Button
              onClick={handleIterate}
              disabled={iterating || !canSubmit}
              size="sm"
              className="w-full text-xs bg-blue-600 hover:bg-blue-500 text-white"
            >
              {iterating ? 'Submitting…' : 'Go'}
            </Button>

            {/* ── Iteration history ── */}
            {versionHistory.length > 0 && (
              <div className="space-y-2 pt-1">
                <p className="text-xs font-medium text-muted-foreground">History</p>
                <ul className="space-y-1.5">
                  {[...versionHistory].reverse().map((v) => {
                    const label = TRIGGER_LABELS[v.trigger] ?? v.trigger;
                    const ago = formatDistanceToNow(new Date(v.created_at), { addSuffix: true });
                    return (
                      <li key={v.version} className="flex items-start gap-2 text-[11px] text-muted-foreground">
                        <span className="shrink-0 font-medium text-foreground">v{v.version}</span>
                        <span className="flex-1 leading-tight">{label}</span>
                        <span className="shrink-0">{ago}</span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </TabsContent>

          {/* ── Brainstorm tab ── */}
          <TabsContent value="brainstorm" className="flex-1 px-4 pb-4 pt-3 space-y-3 overflow-y-auto">
            <p className="text-xs text-muted-foreground">
              Generate creative angles and narrative directions for a topic.
            </p>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Topic or question</label>
              <textarea
                value={brainstormPrompt}
                onChange={(e) => setBrainstormPrompt(e.target.value)}
                placeholder="What angles do you want to explore?"
                rows={4}
                className="w-full rounded-md border border-border bg-secondary px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
              />
            </div>

            {brainstormError && (
              <p className="text-xs text-destructive">{brainstormError}</p>
            )}

            <Button
              onClick={handleBrainstorm}
              disabled={isBrainstorming || !brainstormPrompt.trim()}
              size="sm"
              className="w-full text-xs bg-purple-600 hover:bg-purple-500 text-white"
            >
              {isBrainstorming ? 'Brainstorming…' : 'Brainstorm'}
            </Button>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
