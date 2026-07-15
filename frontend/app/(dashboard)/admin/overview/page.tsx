"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { Activity, AlertTriangle, Repeat, Users } from "lucide-react";

import { adminApi } from "@/lib/api";
import type { ModelDistribution, PlatformOverview, UsageDaily } from "@/types";
import { Header } from "@/components/layout/Header";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { UsageChart } from "@/components/dashboard/UsageChart";
import { ModelDistributionChart } from "@/components/dashboard/ModelDistributionChart";

export default function AdminOverviewPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const [ov, setOv] = useState<PlatformOverview | null>(null);
  const [usage, setUsage] = useState<UsageDaily[]>([]);
  const [dist, setDist] = useState<ModelDistribution[]>([]);

  useEffect(() => {
    if (!token) return;
    adminApi.overview(token).then(setOv);
    adminApi.usageDaily(token).then(setUsage);
    adminApi.modelDistribution(token).then(setDist);
  }, [token]);

  return (
    <>
      <Header title="Platform Overview" subtitle="Every user's traffic, across the platform." />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard label="Total Users" value={ov?.total_users ?? "—"} icon={Users} />
          <StatsCard label="Total Requests" value={ov?.total_requests ?? "—"} icon={Activity} />
          <StatsCard label="Error Rate" value={ov ? `${ov.error_rate}%` : "—"} icon={AlertTriangle} />
          <StatsCard label="Fallback Rate" value={ov ? `${ov.fallback_rate}%` : "—"} icon={Repeat} />
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <UsageChart data={usage} />
          <ModelDistributionChart data={dist} />
        </div>
      </main>
    </>
  );
}
