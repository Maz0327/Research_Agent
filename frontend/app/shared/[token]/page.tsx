/**
 * Public shared document page — App Router server component.
 * No authentication required. Token in URL serves as authorization.
 */

import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { SharedJobView } from '@/components/shared/shared-job-view';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SharedDocument {
  job_id: string;
  job_title: string | null;
  doc_type: string;
  doc_title: string;
  markdown: string | null;
  data: Record<string, unknown> | null;
  expires_at: string;
  view_count: number;
}

interface PageProps {
  params: { token: string };
}

async function fetchSharedDocument(token: string): Promise<{
  document: SharedDocument | null;
  error: { status: number; message: string } | null;
}> {
  try {
    const response = await fetch(`${API_URL}/shared/${token}`, {
      // No caching — view count increments on each fetch
      cache: 'no-store',
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        document: null,
        error: {
          status: response.status,
          message: data.detail || 'Failed to load document',
        },
      };
    }

    return { document: data, error: null };
  } catch {
    return {
      document: null,
      error: { status: 500, message: 'Network error. Please try again.' },
    };
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { document } = await fetchSharedDocument(params.token);
  if (!document) {
    return { title: 'Share Link Error', robots: { index: false } };
  }
  return {
    title: `${document.doc_title} | Shared Document`,
    description: `Shared research document: ${document.doc_title}`,
    robots: { index: false, follow: false },
  };
}

export default async function SharedDocumentPage({ params }: PageProps) {
  const { token } = params;
  const { document, error } = await fetchSharedDocument(token);

  // Error states
  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        {/* Minimal header */}
        <header className="border-b border-border bg-background/80 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto px-4 h-14 flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-sm font-semibold text-foreground">Research Agent</span>
          </div>
        </header>

        <main id="main-content" className="flex-1 flex items-center justify-center p-4">
          <div className="max-w-md w-full text-center">
            <div className="bg-card rounded-xl border border-border p-8">
              {error.status === 410 ? (
                <>
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/10 flex items-center justify-center">
                    <svg className="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h1 className="text-xl font-semibold text-foreground mb-2">Link No Longer Available</h1>
                  <p className="text-muted-foreground mb-6">{error.message}</p>
                </>
              ) : error.status === 404 ? (
                <>
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
                    <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h1 className="text-xl font-semibold text-foreground mb-2">Link Not Found</h1>
                  <p className="text-muted-foreground mb-6">{error.message}</p>
                </>
              ) : (
                <>
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-destructive/10 flex items-center justify-center">
                    <svg className="w-8 h-8 text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <h1 className="text-xl font-semibold text-foreground mb-2">Something Went Wrong</h1>
                  <p className="text-muted-foreground mb-6">{error.message}</p>
                </>
              )}
              <p className="text-sm text-muted-foreground">
                Ask the document owner for a new link if needed.
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  if (!document) {
    notFound();
  }

  return <SharedJobView document={document} />;
}
