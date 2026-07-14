"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Activity, CalendarClock, Coins, Target } from "lucide-react";

import { api } from "@/lib/api";
import type { DashboardStats, ModelDistribution, RequestLog, UsageDaily } from "@/types";
import { Header } from "@/components/layout/Header";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { RecentRequests } from "@/components/dashboard/RecentRequests";
import { UsageChart } from "@/components/dashboard/UsageChart";
import { ModelDistributionChart } from "@/components/dashboard/ModelDistributionChart";
import { CostSavedCard } from "@/components/dashboard/CostSavedCard";
import { QuotaMeter } from "@/components/dashboard/QuotaMeter";

export default function DashboardPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [usage, setUsage] = useState<UsageDaily[]>([]);
  const [distribution, setDistribution] = useState<ModelDistribution[]>([]);

  useEffect(() => {
    if (!token) return;
    api.stats(token).then(setStats);
    api.logs(token, 1, 10).then((res) => setLogs(res.items));
    api.usageDaily(token).then(setUsage);
    api.modelDistribution(token).then(setDistribution);
  }, [token]);

  return (
    <>
      <Header title="Dashboard" subtitle="Every shot you've taken, at a glance." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            label="Total Requests"
            value={stats?.total_requests ?? "—"}
            icon={Activity}
          />
          <StatsCard
            label="Requests Today"
            value={stats?.requests_today ?? "—"}
            icon={CalendarClock}
          />
          <StatsCard
            label="Total Tokens"
            value={stats ? stats.total_tokens.toLocaleString() : "—"}
            icon={Coins}
          />
          <StatsCard
            label="Success Rate"
            value={stats ? `${stats.success_rate}%` : "—"}
            icon={Target}
          />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <CostSavedCard totalTokens={stats?.total_tokens ?? 0} />
          <QuotaMeter used={stats?.requests_this_month ?? 0} />
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <UsageChart data={usage} />
          <ModelDistributionChart data={distribution} />
        </div>

        <div className="mt-6">
          <RecentRequests logs={logs} />
        </div>
      </main>
    </>
  );
}
