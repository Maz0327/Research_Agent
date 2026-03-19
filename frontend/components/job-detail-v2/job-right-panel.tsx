'use client';

/**
 * JobRightPanel — ActivityFeed + ChatToggle button that opens ChatSheet.
 */
import { Button } from '@/components/ui/button';
import { Sparkles } from 'lucide-react';
import { Separator } from '@/components/ui/separator';
import { ActivityFeed } from './activity-feed';
import type { Job } from '@/store/jobs';

interface JobRightPanelProps {
  job: Job;
  onOpenChat: () => void;
}

export function JobRightPanel({ job, onOpenChat }: JobRightPanelProps) {
  return (
    <div className="space-y-4">
      {/* AI Actions trigger */}
      <Button
        onClick={onOpenChat}
        size="sm"
        className="w-full gap-2 text-xs bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-700/40"
        variant="outline"
      >
        <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
        AI Actions (Iterate / Brainstorm)
      </Button>

      <Separator className="bg-border" />

      <ActivityFeed job={job} />
    </div>
  );
}
