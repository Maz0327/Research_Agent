/**
 * Landing page - redirects to dashboard if authenticated.
 */
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import { useAuth } from '../components/AuthProvider';

export default function Home() {
  const router = useRouter();
  const { user, loading } = useAuth();

  // Redirect to dashboard if logged in
  useEffect(() => {
    if (!loading && user) {
      router.push('/dashboard');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-lg text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Research Agent</title>
        <meta
          name="description"
          content="Research Agent - AI-powered research tool for documentary creators"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
        {/* Hero Section */}
        <div className="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 lg:px-8">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
            <span className="block">Research Agent</span>
            <span className="block text-blue-600">for Documentary Creators</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-xl text-gray-500">
            AI-powered research tool that aggregates content from YouTube, articles, Reddit, and
            more. Extract transcripts, validate claims, and generate comprehensive research packets
            for your documentary projects.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="rounded-lg bg-blue-600 px-8 py-4 text-lg font-medium text-white transition hover:bg-blue-700"
            >
              Get Started
            </Link>
            <Link
              href="/login"
              className="rounded-lg border border-gray-300 bg-white px-8 py-4 text-lg font-medium text-gray-700 transition hover:bg-gray-50"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features Section */}
        <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
          <h2 className="mb-12 text-center text-3xl font-bold text-gray-900">Features</h2>

          <div className="grid gap-8 md:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100">
                <svg
                  className="h-6 w-6 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
              </div>
              <h3 className="mb-2 text-lg font-semibold text-gray-900">Transcript Extraction</h3>
              <p className="text-gray-600">
                Extract transcripts from YouTube videos with automatic caption detection and Whisper
                AI fallback.
              </p>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-green-100">
                <svg
                  className="h-6 w-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="mb-2 text-lg font-semibold text-gray-900">Claim Validation</h3>
              <p className="text-gray-600">
                Automatically extract and validate claims from your sources using AI-powered fact
                checking.
              </p>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100">
                <svg
                  className="h-6 w-6 text-purple-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                  />
                </svg>
              </div>
              <h3 className="mb-2 text-lg font-semibold text-gray-900">Research Packets</h3>
              <p className="text-gray-600">
                Generate comprehensive Google Docs with all your research organized and ready for
                NotebookLM.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="border-t border-gray-200 py-8">
          <p className="text-center text-sm text-gray-500">Research Agent - Built for Documentary Creators</p>
        </footer>
      </main>
    </>
  );
}
