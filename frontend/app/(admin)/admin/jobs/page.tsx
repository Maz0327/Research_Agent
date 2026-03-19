/**
 * Admin jobs page — server wrapper.
 * Passes initial status filter from searchParams so /admin/jobs?status=running works.
 */
import type { Metadata } from 'next';
import { JobManagementTable } from '@/components/admin-v2/job-management-table';

export const metadata: Metadata = { title: 'Admin — Jobs' };

interface Props {
  searchParams: Promise<{ status?: string }>;
}

export default async function AdminJobsPage({ searchParams }: Props) {
  const params = await searchParams;
  return <JobManagementTable initialStatusFilter={params.status ?? ''} />;
}
