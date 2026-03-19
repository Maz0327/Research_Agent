'use client';

/**
 * JobCenterPanel — Composes PipelineStatusBar + ExportToolbar + DocumentViewer.
 */
import { PipelineStatusBar } from '@/components/layout/pipeline-status-bar';
import { ExportToolbar } from './export-toolbar';
import { DocumentViewer } from './document-viewer';
import type { Job } from '@/store/jobs';

type PipelineStatus = 'running' | 'completed' | 'failed' | 'queued';

function resolvePipelineStatus(job: Job): PipelineStatus {
  if (job.status === 'running') return 'running';
  if (job.status === 'queued') return 'queued';
  if (job.status === 'failed' || job.status === 'failed_insufficient') return 'failed';
  return 'completed';
}

interface JobCenterPanelProps {
  job: Job;
  activeDocument: number;
  activeVersion: string;
}

export function JobCenterPanel({ job, activeDocument, activeVersion }: JobCenterPanelProps) {
  const pipelineStatus = resolvePipelineStatus(job);
  const showStatusBar = job.status === 'running' || job.status === 'queued' || job.status === 'failed' || job.status === 'failed_insufficient';

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Pipeline status bar — only when relevant */}
      {showStatusBar && (
        <PipelineStatusBar
          stage={job.stage ?? 'queued'}
          progress={job.progress_percent ?? 0}
          status={pipelineStatus}
          errorMessage={job.error}
          className="rounded-md border border-border"
        />
      )}

      {/* Export toolbar */}
      <div className="flex items-center justify-between flex-shrink-0">
        <p className="text-xs text-muted-foreground">
          {activeVersion && `Version ${activeVersion}`}
        </p>
        <ExportToolbar
          job={job}
          activeDocument={activeDocument}
          activeVersion={activeVersion}
        />
      </div>

      {/* Document content */}
      <div className="flex-1 min-h-0">
        <DocumentViewer docType={activeDocument} job={job} />
      </div>
    </div>
  );
}
