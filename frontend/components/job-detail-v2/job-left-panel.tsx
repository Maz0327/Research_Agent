'use client';

/**
 * JobLeftPanel — Composes JobMetaCard + SourceSummary + DocumentNav + VersionSelector.
 */
import { Separator } from '@/components/ui/separator';
import { JobMetaCard } from './job-meta-card';
import { SourceSummary } from './source-summary';
import { DocumentNav } from './document-nav';
import { VersionSelector } from './version-selector';
import type { Job } from '@/store/jobs';
import type { DocVersion } from './version-selector';

interface JobLeftPanelProps {
  job: Job;
  selectedDoc: number;
  selectedVersion: string;
  versions: DocVersion[];
  onSelectDoc: (docType: number) => void;
  onSelectVersion: (version: string) => void;
}

export function JobLeftPanel({
  job,
  selectedDoc,
  selectedVersion,
  versions,
  onSelectDoc,
  onSelectVersion,
}: JobLeftPanelProps) {
  return (
    <div className="space-y-4">
      <JobMetaCard job={job} />

      <SourceSummary job={job} />

      <Separator className="bg-border" />

      <DocumentNav
        artifacts={job.artifacts}
        selectedDoc={selectedDoc}
        onSelectDoc={onSelectDoc}
      />

      {versions.length > 1 && (
        <>
          <Separator className="bg-border" />
          <VersionSelector
            versions={versions}
            selectedVersion={selectedVersion}
            onSelectVersion={onSelectVersion}
          />
        </>
      )}
    </div>
  );
}
