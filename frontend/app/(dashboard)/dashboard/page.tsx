"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Activity, CalendarClock, Coins, Target } from "lucide-react";

import { api } from "@/lib/api";
import type { DashboardStats, RequestLog } from "@/types";
import { Header } from "@/components/layout/Header";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { RecentRequests } from "@/components/dashboard/RecentRequests";

export default function DashboardPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);

  useEffect(() => {
    if (!token) return;
    api.stats(token).then(setStats);
    api.logs(token, 1, 10).then((res) => setLogs(res.items));
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
        <div className="mt-6">
          <RecentRequests logs={logs} />
        </div>
      </main>
    </>
  );
}
