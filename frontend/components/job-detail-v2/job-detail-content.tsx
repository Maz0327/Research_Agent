'use client';

/**
 * JobDetailContent — Main orchestrator for the 3-column job detail view.
 * Manages selected doc, version, chat sheet state.
 * Uses useJobDetail TanStack Query hook for data + polling.
 */
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ThreeColumnLayout } from '@/components/layout/three-column-layout';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/button';
import { useJobDetail } from '@/hooks/use-job-detail';
import { JobLeftPanel } from './job-left-panel';
import { JobCenterPanel } from './job-center-panel';
import { JobRightPanel } from './job-right-panel';
import { ChatSheet } from './chat-sheet';
import type { DocVersion } from './version-selector';

interface JobDetailContentProps {
  jobId: string;
}

/** Derive a default selected doc based on what artifacts exist */
function getDefaultDoc(artifacts: Record<string, unknown> | undefined): number {
  if (!artifacts) return 0;
  if (artifacts.doc_3_path || artifacts.creator_brief_md) return 3;
  if (artifacts.doc_2_path || artifacts.semantic_brief) return 2;
  if (artifacts.doc_1_path || artifacts.jump_start) return 1;
  return 0;
}

/** Build a minimal versions list for the active doc */
function buildVersions(version: string): DocVersion[] {
  return [{ version, created_at: undefined, trigger: 'baseline' }];
}

export function JobDetailContent({ jobId }: JobDetailContentProps) {
  const router = useRouter();
  const { data: job, isLoading, isError, error, refetch } = useJobDetail(jobId);

  const [selectedDoc, setSelectedDoc] = useState<number | null>(null);
  const [selectedVersion, setSelectedVersion] = useState('v1');
  const [chatOpen, setChatOpen] = useState(false);

  // Derive selected doc once job loads (only on first load)
  const resolvedDoc = selectedDoc !== null
    ? selectedDoc
    : getDefaultDoc(job?.artifacts as Record<string, unknown> | undefined);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-64" />
          <Skeleton className="h-64 col-span-1" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  // Error state
  if (isError || !job) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center px-6">
        <div className="h-14 w-14 rounded-full bg-surface-2 flex items-center justify-center mb-4">
          <span className="text-2xl">⚠️</span>
        </div>
        <h2 className="text-base font-semibold text-foreground mb-1">
          {isError ? 'Failed to load job' : 'Job not found'}
        </h2>
        <p className="text-sm text-muted-foreground mb-6">
          {(error as Error)?.message ?? 'The job may have been deleted or does not exist.'}
        </p>
        <div className="flex gap-3">
          <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs">
            Retry
          </Button>
          <Button size="sm" onClick={() => router.push('/dashboard')} className="text-xs">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const versions = buildVersions(selectedVersion);

  return (
    <>
      <ThreeColumnLayout
        leftPanelLabel="Job Details"
        rightPanelLabel="Activity"
        leftPanel={
          <JobLeftPanel
            job={job}
            selectedDoc={resolvedDoc}
            selectedVersion={selectedVersion}
            versions={versions}
            onSelectDoc={(d) => setSelectedDoc(d)}
            onSelectVersion={setSelectedVersion}
          />
        }
        centerContent={
          <JobCenterPanel
            job={job}
            activeDocument={resolvedDoc}
            activeVersion={selectedVersion}
          />
        }
        rightPanel={
          <JobRightPanel
            job={job}
            onOpenChat={() => setChatOpen(true)}
          />
        }
      />

      <ChatSheet
        open={chatOpen}
        onOpenChange={setChatOpen}
        job={job}
      />
    </>
  );
}
