/**
 * Admin users page — server wrapper.
 */
import type { Metadata } from 'next';
import { UserManagementTable } from '@/components/admin-v2/user-management-table';

export const metadata: Metadata = { title: 'Admin — Users' };

export default function AdminUsersPage() {
  return <UserManagementTable />;
}
