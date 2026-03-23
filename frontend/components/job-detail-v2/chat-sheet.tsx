'use client';

/**
 * ChatSheet — Right-side Sheet with Iterate and Brainstorm tabs.
 * Iterate: mode select + text input + submit.
 * Brainstorm: topic prompt + submit.
 */
import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useJobsStore } from '@/store/jobs';
import type { Job } from '@/store/jobs';

const ITERATE_MODES = [
  { value: 'deep_dive',       label: 'Deep Dive' },
  { value: 'expand_sources',  label: 'Expand Sources' },
  { value: 'deeper',          label: 'Go Deeper' },
  { value: 'different_angle', label: 'Different Angle' },
  { value: 'custom',          label: 'Custom' },
  { value: 'inline_edit',     label: 'Inline Edit' },
];

interface ChatSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  job: Job;
}

export function ChatSheet({ open, onOpenChange, job }: ChatSheetProps) {
  const { iterateJob, brainstormTopic, isBrainstorming } = useJobsStore();

  // Iterate state
  const [iterateMode, setIterateMode] = useState('deep_dive');
  const [iteratePrompt, setIteratePrompt] = useState('');
  const [iterating, setIterating] = useState(false);
  const [iterateError, setIterateError] = useState<string | null>(null);

  // Brainstorm state
  const [brainstormPrompt, setBrainstormPrompt] = useState('');
  const [brainstormError, setBrainstormError] = useState<string | null>(null);

  const handleIterate = async () => {
    if (!iteratePrompt.trim()) return;
    setIterating(true);
    setIterateError(null);
    try {
      await iterateJob(job.id, {
        mode: iterateMode as any,
        user_prompt: iteratePrompt.trim(),
        max_new_sources: 5,
      });
      setIteratePrompt('');
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
      <SheetContent side="right" className="w-80 p-0 bg-card border-border flex flex-col">
        <SheetHeader className="px-4 py-3 border-b border-border flex-shrink-0">
          <SheetTitle className="text-sm text-foreground">AI Actions</SheetTitle>
        </SheetHeader>

        <Tabs defaultValue="iterate" className="flex-1 flex flex-col min-h-0">
          <TabsList className="mx-4 mt-3 grid grid-cols-2 flex-shrink-0 bg-secondary">
            <TabsTrigger value="iterate" className="text-xs">Iterate</TabsTrigger>
            <TabsTrigger value="brainstorm" className="text-xs">Brainstorm</TabsTrigger>
          </TabsList>

          {/* Iterate tab */}
          <TabsContent value="iterate" className="flex-1 px-4 pb-4 pt-3 space-y-3 overflow-y-auto">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Mode</label>
              <Select value={iterateMode} onValueChange={setIterateMode}>
                <SelectTrigger className="h-8 text-xs bg-secondary border-border text-foreground">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-card border-border">
                  {ITERATE_MODES.map((m) => (
                    <SelectItem key={m.value} value={m.value} className="text-xs">
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Instructions</label>
              <textarea
                value={iteratePrompt}
                onChange={(e) => setIteratePrompt(e.target.value)}
                placeholder="Describe what you want to change or explore…"
                rows={5}
                className="w-full rounded-md border border-border bg-secondary px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
              />
            </div>

            {iterateError && (
              <p className="text-xs text-destructive">{iterateError}</p>
            )}

            <Button
              onClick={handleIterate}
              disabled={iterating || !iteratePrompt.trim()}
              size="sm"
              className="w-full text-xs bg-blue-600 hover:bg-blue-500 text-white"
            >
              {iterating ? 'Submitting…' : 'Run Iteration'}
            </Button>
          </TabsContent>

          {/* Brainstorm tab */}
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
