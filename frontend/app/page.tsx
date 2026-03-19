/**
 * Root landing page — server component.
 * Redirects to /dashboard if session exists, otherwise /login.
 */
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export default async function RootPage() {
  // Check for Supabase session cookie (sb-*-auth-token)
  const cookieStore = await cookies();
  const allCookies = cookieStore.getAll();
  const hasSession = allCookies.some(
    (c) => c.name.startsWith('sb-') && c.name.endsWith('-auth-token')
  );

  if (hasSession) {
    redirect('/dashboard');
  } else {
    redirect('/login');
  }
}
