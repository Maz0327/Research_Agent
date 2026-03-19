/**
 * Settings page — server wrapper for App Router (app) group.
 */
import type { Metadata } from 'next';
import { SettingsContent } from '@/components/settings-v2/settings-content';

export const metadata: Metadata = {
  title: 'Settings',
};

export default function SettingsPage() {
  return (
    <div className="p-6">
      <SettingsContent />
    </div>
  );
}
