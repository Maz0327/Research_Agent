'use client';

/**
 * UsageContent — stat cards, daily spend bar chart, cost breakdown table.
 * Matches the Usage & Billing tab in 07-settings.html mockup.
 * Real data fetched from /jobs/usage/stats; falls back to zeros on error.
 */
import { useEffect, useState } from 'react';
import { getAccessToken } from '@/lib/supabase';
import { API_URL } from '@/lib/constants';

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

// Daily spend data — placeholder until backend exposes per-day breakdown
const DAILY_DATA = [20, 35, 15, 55, 40, 75, 25, 30, 90, 50, 18, 38, 65, 35, 48, 80, 42, 110];

const MODEL_ROWS = [
  { model: 'Gemini 2.5 Flash', calls: '1,102', tokens: '4.2M', cost: null as number | null, costKey: 'openai' as const },
  { model: 'Gemini 2.5 Pro', calls: '182', tokens: '1.1M', cost: null as number | null, costKey: 'perplexity' as const },
];

export function UsageContent() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchUsage() {
      try {
        const token = await getAccessToken();
        if (!token) { setIsLoading(false); return; }
        const res = await fetch(`${API_URL}/jobs/usage/stats`, {
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        });
        if (!res.ok) throw new Error('Failed to fetch usage stats');
        setStats(await res.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load usage');
      } finally {
        setIsLoading(false);
      }
    }
    fetchUsage();
  }, []);

  const totalCost = stats?.estimated_costs.total ?? 0;
  const totalJobs = stats?.total_jobs ?? 0;
  const avgCostPerJob = totalJobs > 0 ? (totalCost / totalJobs).toFixed(2) : '0.00';
  const maxBar = Math.max(...DAILY_DATA);

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-4 animate-pulse">
              <div className="h-3 w-20 rounded bg-muted mb-2" />
              <div className="h-7 w-16 rounded bg-muted" />
            </div>
          ))}
        </div>
        <div className="bg-card border border-border rounded-xl p-5 animate-pulse h-64" />
        <div className="bg-card border border-border rounded-xl p-5 animate-pulse h-32" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-lg font-bold mb-1">Usage & Billing</h1>
        <p className="text-xs text-muted-foreground">Track API costs and usage for the current billing period</p>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground mb-1">This Month</p>
          <p className="text-2xl font-bold">${totalCost.toFixed(2)}</p>
          <p className="text-[10px] text-accent-green mt-1">Estimated total</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground mb-1">Jobs Run</p>
          <p className="text-2xl font-bold">{totalJobs}</p>
          <p className="text-[10px] text-muted-foreground mt-1">Avg ${avgCostPerJob}/job</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-xs text-muted-foreground mb-1">API Calls</p>
          <p className="text-2xl font-bold">{stats?.jobs_with_cost_tracking ?? 0}</p>
          <p className="text-[10px] text-muted-foreground mt-1">Jobs with cost tracking</p>
        </div>
      </div>

      {/* Daily spend bar chart */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="text-sm font-semibold mb-4">Daily Spend (March 2026)</h2>
        <div className="h-48 flex items-end gap-1 px-2">
          {DAILY_DATA.map((height, i) => {
            const isToday = i === DAILY_DATA.length - 1;
            const pct = Math.round((height / maxBar) * 100);
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t transition-all ${isToday ? 'bg-accent-blue' : 'bg-accent-blue/30'}`}
                  style={{ height: `${Math.round((height / maxBar) * 160)}px` }}
                  title={`Day ${i + 1}: ~$${(height / 100).toFixed(2)}`}
                />
                <span className={`text-[8px] ${isToday ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                  {i + 1}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Cost breakdown table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-border">
          <h2 className="text-sm font-semibold">Cost Breakdown by Provider</h2>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-5 py-2.5">Provider</th>
              <th className="text-right text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-5 py-2.5">Cost</th>
            </tr>
          </thead>
          <tbody>
            {[
              { label: 'OpenAI (GPT-4o-mini)', value: stats?.estimated_costs.openai ?? 0 },
              { label: 'Perplexity', value: stats?.estimated_costs.perplexity ?? 0 },
              { label: 'Whisper (transcription)', value: stats?.estimated_costs.whisper ?? 0 },
              { label: 'Tavily', value: stats?.estimated_costs.tavily ?? 0 },
            ].map((row, i, arr) => (
              <tr key={row.label} className={`${i < arr.length - 1 ? 'border-b border-border' : ''} hover:bg-muted/30 transition-colors`}>
                <td className="px-5 py-3 text-sm text-foreground/80">{row.label}</td>
                <td className="px-5 py-3 text-sm text-right font-medium">${row.value.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-secondary">
              <td className="px-5 py-3 text-sm font-semibold">Total</td>
              <td className="px-5 py-3 text-sm font-bold text-right">${totalCost.toFixed(4)}</td>
            </tr>
          </tfoot>
        </table>
        {stats?.note && (
          <p className="px-5 py-3 text-xs text-muted-foreground border-t border-border">{stats.note}</p>
        )}
      </div>
    </div>
  );
}
