/**
 * API Usage tracking page with cost estimates and dashboard links.
 */
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import { ProtectedRoute } from '../components/AuthProvider';
import { getAccessToken } from '../lib/supabase';
import { API_URL } from '../lib/constants';

interface UsageStats {
  total_jobs: number;
  jobs_with_cost_tracking: number;
  estimated_costs: {
    openai: number;
    perplexity: number;
    whisper: number;
    tavily: number;
    total: number;
  };
  dashboards: {
    openai: string;
    perplexity: string;
    google_cloud: string;
    supabase: string;
  };
  note: string;
}

function UsageSkeleton() {
  return (
    <div className="space-y-6">
      {[1, 2].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-gray-800 bg-gray-900 p-6 animate-pulse"
        >
          <div className="h-6 w-32 rounded bg-gray-800 mb-4" />
          <div className="space-y-3">
            <div className="h-10 rounded bg-gray-800" />
            <div className="h-10 w-2/3 rounded bg-gray-800" />
          </div>
        </div>
      ))}
    </div>
  );
}

function UsageContent() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUsage() {
      try {
        const token = await getAccessToken();
        if (!token) {
          setError('Not authenticated');
          setIsLoading(false);
          return;
        }

        const response = await fetch(`${API_URL}/jobs/usage/stats`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch usage stats');
        }

        const data = await response.json();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load usage');
      } finally {
        setIsLoading(false);
      }
    }

    fetchUsage();
  }, []);

  if (isLoading) {
    return (
      <Layout>
        <div className="mx-auto max-w-3xl">
          <div className="mb-8">
            <div className="h-8 w-32 rounded bg-gray-800 animate-pulse" />
            <div className="mt-2 h-5 w-64 rounded bg-gray-800 animate-pulse" />
          </div>
          <UsageSkeleton />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
            API Usage
          </h1>
          <p className="mt-2 text-gray-400">
            Track your API costs and access provider dashboards
          </p>
        </motion.div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 rounded-xl border border-red-500/30 bg-red-900/30 p-4"
          >
            <p className="text-sm text-red-300">{error}</p>
          </motion.div>
        )}

        {stats && (
          <div className="space-y-6">
            {/* Estimated Costs Card */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-xl border border-gray-800 bg-gray-900 p-6"
            >
              <h2 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                <svg className="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Estimated Costs
              </h2>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="rounded-lg bg-gray-800 p-4">
                  <p className="text-sm text-gray-400">Total Jobs</p>
                  <p className="text-3xl font-bold text-gray-100">{stats.total_jobs}</p>
                </div>
                <div className="rounded-lg bg-gray-800 p-4">
                  <p className="text-sm text-gray-400">Total Estimated</p>
                  <p className="text-3xl font-bold text-green-400">${stats.estimated_costs.total.toFixed(4)}</p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">OpenAI (GPT-4o-mini)</span>
                  <span className="text-gray-100 font-mono">${stats.estimated_costs.openai.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Perplexity</span>
                  <span className="text-gray-100 font-mono">${stats.estimated_costs.perplexity.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Whisper (transcription)</span>
                  <span className="text-gray-100 font-mono">${stats.estimated_costs.whisper.toFixed(4)}</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-gray-300">Tavily</span>
                  <span className="text-gray-100 font-mono">${stats.estimated_costs.tavily.toFixed(4)}</span>
                </div>
              </div>

              <p className="mt-4 text-xs text-gray-500">{stats.note}</p>
            </motion.div>

            {/* Provider Dashboards Card */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="rounded-xl border border-gray-800 bg-gray-900 p-6"
            >
              <h2 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Provider Dashboards
              </h2>
              <p className="text-sm text-gray-400 mb-4">
                View exact usage and manage your API keys
              </p>

              <div className="grid gap-3">
                <a
                  href={stats.dashboards.openai}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 p-4 transition hover:border-gray-600 hover:bg-gray-750"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-green-900/50 flex items-center justify-center">
                      <span className="text-lg font-bold text-green-400">O</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-100">OpenAI</p>
                      <p className="text-xs text-gray-400">GPT-4o-mini usage & billing</p>
                    </div>
                  </div>
                  <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>

                <a
                  href={stats.dashboards.perplexity}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 p-4 transition hover:border-gray-600 hover:bg-gray-750"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-blue-900/50 flex items-center justify-center">
                      <span className="text-lg font-bold text-blue-400">P</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-100">Perplexity</p>
                      <p className="text-xs text-gray-400">API settings & usage</p>
                    </div>
                  </div>
                  <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>

                <a
                  href={stats.dashboards.google_cloud}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 p-4 transition hover:border-gray-600 hover:bg-gray-750"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-yellow-900/50 flex items-center justify-center">
                      <span className="text-lg font-bold text-yellow-400">G</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-100">Google Cloud</p>
                      <p className="text-xs text-gray-400">YouTube API, Drive, Gemini</p>
                    </div>
                  </div>
                  <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>

                <a
                  href={stats.dashboards.supabase}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 p-4 transition hover:border-gray-600 hover:bg-gray-750"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-lg bg-purple-900/50 flex items-center justify-center">
                      <span className="text-lg font-bold text-purple-400">S</span>
                    </div>
                    <div>
                      <p className="font-medium text-gray-100">Supabase</p>
                      <p className="text-xs text-gray-400">Database & auth billing</p>
                    </div>
                  </div>
                  <svg className="h-5 w-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>
              </div>
            </motion.div>

            {/* Budget Reference Card */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="rounded-xl border border-gray-800 bg-gray-900 p-6"
            >
              <h2 className="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">
                <svg className="h-5 w-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
                Budget Reference
              </h2>
              <p className="text-sm text-gray-400 mb-4">
                Approximate cost per job by research mode
              </p>

              <div className="space-y-2">
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Quick</span>
                  <span className="text-gray-400">~$1</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Breaking News</span>
                  <span className="text-gray-400">~$2</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Full</span>
                  <span className="text-gray-400">~$5</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Profile</span>
                  <span className="text-gray-400">~$8</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-gray-800">
                  <span className="text-gray-300">Controversy</span>
                  <span className="text-gray-400">~$10</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-gray-300">Investigation</span>
                  <span className="text-gray-400">~$15</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </Layout>
  );
}

export default function UsagePage() {
  return (
    <ProtectedRoute>
      <UsageContent />
    </ProtectedRoute>
  );
}
