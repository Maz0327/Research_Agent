/**
 * Usage page — server wrapper for App Router (app) group.
 */
import type { Metadata } from 'next';
import { UsageContent } from '@/components/usage/usage-content';

export const metadata: Metadata = {
  title: 'API Usage',
};

export default function UsagePage() {
  return (
    <div className="p-6">
      <UsageContent />
    </div>
  );
}
