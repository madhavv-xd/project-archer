"use client";

import dynamic from "next/dynamic";

import type { UsageDaily } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// recharts is ~100kB gzipped and measures the DOM to size itself — keep it out of
// the initial bundle and off the server render.
const Chart = dynamic(() => import("./UsageChartInner"), {
  ssr: false,
  loading: () => <div className="h-full w-full" />,
});

export function UsageChart({ data }: { data: UsageDaily[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Requests over time</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">No requests yet.</p>
        ) : (
          <div className="h-64 w-full">
            <Chart data={data} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
