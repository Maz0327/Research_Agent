/**
 * Queue page — server component wrapper.
 * All interactivity is inside QueueContent (client component).
 */
import { QueueContent } from '@/components/queue/queue-content';

export default function QueuePage() {
  return <QueueContent />;
}
