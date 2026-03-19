/**
 * Dashboard page — server component wrapper.
 * All interactivity is inside DashboardContent (client component).
 */
import { DashboardContent } from '@/components/dashboard/dashboard-content';

export default function DashboardPage() {
  return <DashboardContent />;
}
