"use client";

import dynamic from "next/dynamic";

import type { ModelDistribution } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";

// recharts is ~100kB gzipped and measures the DOM to size itself — keep it out of
// the initial bundle and off the server render.
const Chart = dynamic(() => import("./ModelDistributionChartInner"), {
  ssr: false,
  loading: () => <div className="h-full w-full" />,
});

export function ModelDistributionChart({ data }: { data: ModelDistribution[] | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Which models answered</CardTitle>
      </CardHeader>
      <CardContent>
        {data === null ? (
          <div className="h-64 w-full" />
        ) : data.length === 0 ? (
          <EmptyState title="No requests yet." hint="Once traffic flows, you'll see which models answered." />
        ) : (
          <div className="h-64 w-full">
            <Chart data={data} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
