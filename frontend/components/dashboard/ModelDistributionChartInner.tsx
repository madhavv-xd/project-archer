"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { ModelDistribution } from "@/types";

// Nocturne donut slices — accent ramp, no red (README §Dashboard.4).
const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--accent-700)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export default function ModelDistributionChartInner({
  data,
}: {
  data: ModelDistribution[];
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="model"
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
          stroke="var(--card)"
        >
          {data.map((d, i) => (
            <Cell key={d.model} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, name, entry) => [
            `${value} (${entry.payload.percentage}%)`,
            name,
          ]}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            color: "var(--foreground)",
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted-foreground)" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
