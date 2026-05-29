"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ProviderSlice } from "@/lib/types";

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

export function ProviderDonut({ data }: { data: ProviderSlice[] }) {
  if (!data.length) {
    return (
      <div className="grid place-items-center h-full text-sm text-muted-foreground">
        No traffic in window
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Tooltip
          contentStyle={{
            background: "hsl(var(--surface))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 12,
            fontSize: 12,
          }}
        />
        <Pie
          data={data}
          dataKey="requests"
          nameKey="provider"
          innerRadius="55%"
          outerRadius="85%"
          paddingAngle={2}
          stroke="hsl(var(--surface))"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}
