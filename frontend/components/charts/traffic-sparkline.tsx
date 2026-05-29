"use client";

import { format } from "date-fns";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimeBucket } from "@/lib/types";

export function TrafficSparkline({ data }: { data: TimeBucket[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        data={data}
        margin={{ top: 4, right: 8, bottom: 0, left: -28 }}
      >
        <defs>
          <linearGradient id="traffic-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--chart-1))" stopOpacity={0.5} />
            <stop offset="100%" stopColor="hsl(var(--chart-1))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="bucket"
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => format(new Date(v), "HH:mm")}
          minTickGap={32}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          allowDecimals={false}
          width={32}
        />
        <Tooltip
          contentStyle={{
            background: "hsl(var(--surface))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 12,
            fontSize: 12,
          }}
          labelFormatter={(v) => format(new Date(v), "PPpp")}
        />
        <Area
          type="monotone"
          dataKey="requests"
          stroke="hsl(var(--chart-1))"
          strokeWidth={2}
          fill="url(#traffic-grad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
