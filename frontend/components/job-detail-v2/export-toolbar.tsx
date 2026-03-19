'use client';

/**
 * ExportToolbar — PDF and DOCX export buttons for the active document.
 * Wires into existing lib/pdf-export.ts and lib/docx-export.ts.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { FileDown, FileText } from 'lucide-react';
import { exportToPdf } from '@/lib/pdf-export';
import { exportToDocx } from '@/lib/docx-export';
import type { Job } from '@/store/jobs';

interface ExportToolbarProps {
  job: Job;
  activeDocument: number;
  activeVersion: string;
}

/** Extract markdown content for a given doc type from job artifacts */
function getDocMarkdown(job: Job, docType: number): string | null {
  const a = job.artifacts;
  if (!a) return null;
  switch (docType) {
    case 0: return (a.source_ledger as any)?.markdown ?? null;
    case 1: return (a.jump_start as any)?.markdown ?? null;
    case 2: return (a.semantic_brief as any)?.markdown ?? null;
    case 3: return a.creator_brief_md ?? null;
    case 4: return a.producer_packet_md ?? null;
    default: return null;
  }
}

const DOC_NAMES: Record<number, string> = {
  0: 'Source-Ledger',
  1: 'Jump-Start',
  2: 'Semantic-Brief',
  3: 'Creator-Brief',
  4: 'Producer-Packet',
};

export function ExportToolbar({ job, activeDocument, activeVersion }: ExportToolbarProps) {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [docxLoading, setDocxLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const docName = DOC_NAMES[activeDocument] ?? `Doc-${activeDocument}`;
  const filename = `${docName}-${activeVersion}`;

  const handlePdf = async () => {
    const markdown = getDocMarkdown(job, activeDocument);
    if (!markdown) { setError('No content to export'); return; }
    setError(null);
    setPdfLoading(true);
    try {
      await exportToPdf(markdown, filename);
    } catch (e) {
      setError('PDF export failed');
    } finally {
      setPdfLoading(false);
    }
  };

  const handleDocx = async () => {
    const markdown = getDocMarkdown(job, activeDocument);
    if (!markdown) { setError('No content to export'); return; }
    setError(null);
    setDocxLoading(true);
    try {
      await exportToDocx(markdown, filename);
    } catch (e) {
      setError('DOCX export failed');
    } finally {
      setDocxLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {error && (
        <span className="text-xs text-destructive">{error}</span>
      )}
      <Button
        variant="outline"
        size="sm"
        onClick={handlePdf}
        disabled={pdfLoading || docxLoading}
        className="h-7 text-xs gap-1.5 border-border text-muted-foreground hover:text-foreground"
      >
        <FileDown className="h-3.5 w-3.5" aria-hidden="true" />
        {pdfLoading ? 'Exporting…' : 'PDF'}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={handleDocx}
        disabled={pdfLoading || docxLoading}
        className="h-7 text-xs gap-1.5 border-border text-muted-foreground hover:text-foreground"
      >
        <FileText className="h-3.5 w-3.5" aria-hidden="true" />
        {docxLoading ? 'Exporting…' : 'DOCX'}
      </Button>
    </div>
  );
}
