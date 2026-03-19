/**
 * Admin overview page — server wrapper.
 */
import type { Metadata } from 'next';
import { AdminDashboard } from '@/components/admin-v2/admin-dashboard';

export const metadata: Metadata = { title: 'Admin — Overview' };

export default function AdminPage() {
  return <AdminDashboard />;
}
