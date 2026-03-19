'use client';

/**
 * Dashboard stats bar — 4 quick-look stat cards with accent icons.
 * Data derived from the useJobs hook output.
 */
import { Briefcase, Activity, CheckCircle, DollarSign } from 'lucide-react';
import { useJobs } from '@/hooks/use-jobs';

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  subAccent?: boolean;
  icon: React.ReactNode;
  iconBg: string;
}

function StatCard({ label, value, sub, subAccent, icon, iconBg }: StatCardProps) {
  return (
    <div className="bg-[#12121a] border border-[#27272a] rounded-xl p-4 hover:shadow-[0_0_24px_rgba(59,130,246,0.08)] transition-shadow cursor-pointer">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-medium text-[#71717a] uppercase tracking-wider">{label}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${iconBg}`}>
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold text-[#f5f5f5]">{value}</p>
      {sub && (
        <p className={`text-xs mt-1 ${subAccent ? 'text-[#22c55e]' : 'text-[#71717a]'}`}>{sub}</p>
      )}
    </div>
  );
}

export function DashboardStats() {
  const { data: jobs = [] } = useJobs();

  const total = jobs.length;
  const running = jobs.filter((j) => j.status === 'running').length;
  const completed = jobs.filter(
    (j) => j.status === 'completed' || j.status === 'completed_with_warnings'
  ).length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        label="Total Jobs"
        value={total}
        sub={total > 0 ? `${total} total` : 'No jobs yet'}
        icon={<Briefcase className="w-4 h-4 text-[#3b82f6]" />}
        iconBg="bg-[#3b82f6]/10"
      />
      <StatCard
        label="Running"
        value={running}
        sub={running > 0 ? 'Pipeline active' : 'None active'}
        subAccent={running > 0}
        icon={
          running > 0 ? (
            <span className="w-2.5 h-2.5 rounded-full bg-[#22c55e] animate-pulse" />
          ) : (
            <Activity className="w-4 h-4 text-[#22c55e]" />
          )
        }
        iconBg="bg-[#22c55e]/10"
      />
      <StatCard
        label="Completed"
        value={completed}
        sub="All time"
        icon={<CheckCircle className="w-4 h-4 text-[#8b5cf6]" />}
        iconBg="bg-[#8b5cf6]/10"
      />
      <StatCard
        label="API Spend"
        value="—"
        sub="Coming soon"
        icon={<DollarSign className="w-4 h-4 text-[#f97316]" />}
        iconBg="bg-[#f97316]/10"
      />
    </div>
  );
}
