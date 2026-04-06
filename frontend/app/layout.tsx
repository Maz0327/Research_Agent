/**
 * Root layout for the App Router.
 * Server component — wraps all app/ routes with fonts, metadata, and client providers.
 * pages/ directory continues to use pages/_app.tsx independently.
 */

import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import { SkipLink } from '@/components/SkipLink';

// Load Plus Jakarta Sans with CSS variable for flexible usage in Tailwind
const plusJakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: {
    default: 'Research Agent',
    template: '%s | Research Agent',
  },
  description:
    'AI-powered research assistant that extracts, synthesises, and documents insights from multiple sources.',
  robots: {
    index: false, // Private tool — do not index
    follow: false,
  },
};

// Validate critical env vars at module load (server-side)
if (process.env.NODE_ENV === 'production' && !process.env.NEXT_PUBLIC_API_URL) {
  console.error(
    '[Research Agent] NEXT_PUBLIC_API_URL is not set. API requests will fail.'
  );
}

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    // suppressHydrationWarning required by next-themes to avoid
    // hydration mismatch when switching between server/client theme class.
    <html lang="en" className={plusJakarta.variable} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <SkipLink />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
