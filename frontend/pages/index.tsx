/**
 * Landing page - redirects to dashboard if authenticated.
 * Dark mode design with gradient accents and modern styling.
 * WCAG 2.1 AA compliant with semantic landmarks.
 */
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { useAuth } from '../components/AuthProvider';
import { SkipLink } from '../components/SkipLink';
import { PublicHeader } from '../components/PublicHeader';

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
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <div className="flex items-center gap-3 text-lg text-gray-400">
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </div>
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

      <SkipLink />

      <div className="min-h-screen bg-dark-bg-primary text-gray-100">
        {/* Background gradient effects */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl" />
        </div>

        <PublicHeader />

        <main id="main-content" role="main">
          {/* Hero Section */}
          <section aria-labelledby="hero-heading" className="relative mx-auto max-w-5xl px-4 py-24 text-center sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 id="hero-heading" className="text-5xl font-extrabold tracking-tight sm:text-6xl md:text-7xl">
              <span className="block text-gray-100">Research Agent</span>
              <span className="block bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                for Documentary Creators
              </span>
            </h1>
            <p className="mx-auto mt-8 max-w-2xl text-xl text-gray-400">
              AI-powered research tool that aggregates content from YouTube, articles, Reddit, and
              more. Extract transcripts, validate claims, and generate comprehensive research packets
              for your documentary projects.
            </p>

            <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href="/login"
                className="rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-8 py-4 text-lg font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30"
              >
                Get Started
              </Link>
              <Link
                href="/login"
                className="rounded-xl border border-gray-700 bg-gray-800/50 px-8 py-4 text-lg font-medium text-gray-300 transition-all duration-200 hover:bg-gray-800 hover:text-gray-100"
              >
                Sign In
              </Link>
            </div>
          </motion.div>
          </section>

          {/* Features Section */}
          <section aria-labelledby="features-heading" className="relative mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3, duration: 0.6 }}
          >
            <h2 id="features-heading" className="mb-12 text-center text-3xl font-bold text-gray-100">Features</h2>

            <div className="grid gap-6 md:grid-cols-3">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 shadow-lg transition-all duration-300 hover:border-gray-700 hover:shadow-xl"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                  <svg
                    className="h-6 w-6 text-blue-400"
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
                <h3 className="mb-2 text-lg font-semibold text-gray-100">Transcript Extraction</h3>
                <p className="text-gray-400">
                  Extract transcripts from YouTube videos with automatic caption detection and Whisper
                  AI fallback.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 shadow-lg transition-all duration-300 hover:border-gray-700 hover:shadow-xl"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                  <svg
                    className="h-6 w-6 text-green-400"
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
                <h3 className="mb-2 text-lg font-semibold text-gray-100">Claim Validation</h3>
                <p className="text-gray-400">
                  Automatically extract and validate claims from your sources using AI-powered fact
                  checking.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 shadow-lg transition-all duration-300 hover:border-gray-700 hover:shadow-xl"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500/20">
                  <svg
                    className="h-6 w-6 text-purple-400"
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
                <h3 className="mb-2 text-lg font-semibold text-gray-100">Research Packets</h3>
                <p className="text-gray-400">
                  Generate comprehensive Google Docs with all your research organized and ready for
                  NotebookLM.
                </p>
              </motion.div>
            </div>
          </motion.div>
          </section>
        </main>

        {/* Footer */}
        <footer role="contentinfo" className="relative border-t border-gray-800 py-8">
          <p className="text-center text-sm text-gray-500">
            Research Agent - Built for Documentary Creators
          </p>
        </footer>
      </div>
    </>
  );
}
