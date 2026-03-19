/**
 * Transcripts page — server wrapper for App Router (app) group.
 */
import type { Metadata } from 'next';
import { TranscriptsContent } from '@/components/transcripts/transcripts-content';

export const metadata: Metadata = {
  title: 'Transcript Extractor',
};

export default function TranscriptsPage() {
  return (
    <div className="p-6">
      <TranscriptsContent />
    </div>
  );
}
