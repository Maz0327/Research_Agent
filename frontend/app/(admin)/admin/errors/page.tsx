/**
 * Admin error logs page — server wrapper.
 * Passes initial filter from searchParams so /admin/errors?resolved=false works.
 */
import type { Metadata } from 'next';
import { ErrorLogTable } from '@/components/admin-v2/error-log-table';

export const metadata: Metadata = { title: 'Admin — Error Logs' };

interface Props {
  searchParams: Promise<{ resolved?: string }>;
}

export default async function AdminErrorsPage({ searchParams }: Props) {
  const params = await searchParams;
  return <ErrorLogTable initialResolvedFilter={params.resolved === 'false' ? 'false' : ''} />;
}
