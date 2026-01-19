/**
 * Job action buttons component (cancel, delete, archive, view results, booster, producer packet).
 */
import { useState, useCallback, useEffect } from 'react';
import { JobStatus } from './job-card-config';
import { useJobsStore } from '../../store/jobs';

interface JobActionsProps {
  jobId: string;
  status: JobStatus;
  driveFolderUrl?: string;
  pipeline?: string;
  hasDocuments?: boolean;
  onRefresh?: () => void;
}

export function JobActions({
  jobId,
  status,
  driveFolderUrl,
  pipeline,
  hasDocuments,
  onRefresh,
}: JobActionsProps) {
  const [isCancelling, setIsCancelling] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [isTriggeringBooster, setIsTriggeringBooster] = useState(false);
  const [isTriggeringProducer, setIsTriggeringProducer] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const cancelJob = useJobsStore((state) => state.cancelJob);
  const deleteJob = useJobsStore((state) => state.deleteJob);
  const archiveJob = useJobsStore((state) => state.archiveJob);
  const triggerBooster = useJobsStore((state) => state.triggerBooster);
  const triggerProducerPacket = useJobsStore((state) => state.triggerProducerPacket);

  // Auto-dismiss action errors after 5 seconds
  useEffect(() => {
    if (actionError) {
      const timer = setTimeout(() => setActionError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [actionError]);

  const handleCancel = useCallback(async () => {
    if (isCancelling) return;
    setIsCancelling(true);
    setActionError(null);
    try {
      await cancelJob(jobId);
      onRefresh?.();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to cancel');
    } finally {
      setIsCancelling(false);
    }
  }, [jobId, isCancelling, onRefresh, cancelJob]);

  const handleDelete = useCallback(async () => {
    if (isDeleting) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await deleteJob(jobId);
      setShowDeleteConfirm(false);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to delete');
    } finally {
      setIsDeleting(false);
    }
  }, [jobId, isDeleting, deleteJob]);

  const handleArchive = useCallback(async () => {
    if (isArchiving) return;
    setIsArchiving(true);
    setActionError(null);
    try {
      await archiveJob(jobId);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to archive');
    } finally {
      setIsArchiving(false);
    }
  }, [jobId, isArchiving, archiveJob]);

  const handleBooster = useCallback(async () => {
    if (isTriggeringBooster) return;
    setIsTriggeringBooster(true);
    setActionError(null);
    try {
      await triggerBooster(jobId);
      onRefresh?.();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to trigger deep research');
    } finally {
      setIsTriggeringBooster(false);
    }
  }, [jobId, isTriggeringBooster, triggerBooster, onRefresh]);

  const handleProducerPacket = useCallback(async () => {
    if (isTriggeringProducer) return;
    setIsTriggeringProducer(true);
    setActionError(null);
    try {
      await triggerProducerPacket(jobId);
      onRefresh?.();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to generate producer packet');
    } finally {
      setIsTriggeringProducer(false);
    }
  }, [jobId, isTriggeringProducer, triggerProducerPacket, onRefresh]);

  const canCancel = status === 'running' || status === 'queued';
  const canDeleteOrArchive = !canCancel; // Can delete/archive when not running
  const hasResults = (status === 'completed' || status === 'completed_with_warnings') && driveFolderUrl;
  // Can trigger booster/producer packet for completed jobs with semantic documents
  const canEnhance = (status === 'completed' || status === 'completed_with_warnings') && hasDocuments;

  return (
    <div className="space-y-3 pt-2">
      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-red-900/20 border border-red-700/50">
          <span className="text-sm text-red-300">Delete this job permanently?</span>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(); }}
            disabled={isDeleting}
            className="px-3 py-1 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-500 disabled:opacity-50"
          >
            {isDeleting ? 'Deleting...' : 'Yes, Delete'}
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(false); }}
            className="px-3 py-1 text-sm font-medium text-gray-300 bg-gray-700 rounded hover:bg-gray-600"
          >
            Cancel
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {/* Cancel button - only for running/queued */}
        {canCancel && (
          <button
            onClick={(e) => { e.stopPropagation(); handleCancel(); }}
            disabled={isCancelling}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-700 px-3 py-1.5 text-sm font-medium text-red-400 transition hover:bg-red-900/30 disabled:opacity-50"
          >
            {isCancelling ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Cancelling
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Cancel
              </>
            )}
          </button>
        )}

        {/* Archive button - for completed/failed/cancelled jobs */}
        {canDeleteOrArchive && (
          <button
            onClick={(e) => { e.stopPropagation(); handleArchive(); }}
            disabled={isArchiving}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-400 transition hover:bg-gray-800 hover:text-gray-300 disabled:opacity-50"
          >
            {isArchiving ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Archiving
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Archive
              </>
            )}
          </button>
        )}

        {/* Delete button - for completed/failed/cancelled jobs */}
        {canDeleteOrArchive && !showDeleteConfirm && (
          <button
            onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(true); }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-600 px-3 py-1.5 text-sm font-medium text-gray-400 transition hover:border-red-700 hover:text-red-400 hover:bg-red-900/20"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Delete
          </button>
        )}

        {/* View results link */}
        {hasResults && (
          <a
            href={driveFolderUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600/20 border border-blue-600/30 px-3 py-1.5 text-sm font-medium text-blue-400 transition hover:bg-blue-600/30"
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            View Results
          </a>
        )}

        {/* Deep Research button - for completed jobs with semantic docs */}
        {canEnhance && (
          <button
            onClick={(e) => { e.stopPropagation(); handleBooster(); }}
            disabled={isTriggeringBooster}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600/20 border border-indigo-600/30 px-3 py-1.5 text-sm font-medium text-indigo-400 transition hover:bg-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTriggeringBooster ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Starting...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Deep Research
              </>
            )}
          </button>
        )}

        {/* Producer Packet button - for completed jobs with semantic docs */}
        {canEnhance && (
          <button
            onClick={(e) => { e.stopPropagation(); handleProducerPacket(); }}
            disabled={isTriggeringProducer}
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600/20 border border-amber-600/30 px-3 py-1.5 text-sm font-medium text-amber-400 transition hover:bg-amber-600/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTriggeringProducer ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
                Producer Packet
              </>
            )}
          </button>
        )}
      </div>

      {actionError && (
        <span className="text-sm text-red-400">{actionError}</span>
      )}
    </div>
  );
}

export default JobActions;
