/**
 * Job detail page — App Router server component.
 * Delegates all interactivity to JobDetailContent (client component).
 */
import { JobDetailContent } from '@/components/job-detail-v2/job-detail-content';

interface JobDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function JobDetailPage({ params }: JobDetailPageProps) {
  const { id } = await params;
  return <JobDetailContent jobId={id} />;
}
