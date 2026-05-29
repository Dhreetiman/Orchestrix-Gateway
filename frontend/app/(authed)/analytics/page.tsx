"use client";

import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Toolbar } from "@/components/macos/toolbar";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import { formatLatency, formatNumber, formatUsd } from "@/lib/format";
import { useAppStore } from "@/lib/store";
import type { BucketGranularity, TimeBucket, WindowPreset } from "@/lib/types";

function bucketFor(window: WindowPreset): BucketGranularity {
  if (window === "15m" || window === "1h") return "minute";
  if (window === "7d") return "day";
  return "hour";
}

export default function AnalyticsPage() {
  return (
    <>
      <Toolbar title="Analytics" subtitle="Trends over your selected window" />
      <AnalyticsContent />
    </>
  );
}

function AnalyticsContent() {
  const window = useAppStore((s) => s.window);
  const bucket = bucketFor(window);

  const series = useQuery({
    queryKey: ["series", window, bucket],
    queryFn: () => api.series(window, bucket),
  });
  const providers = useQuery({
    queryKey: ["providers", window],
    queryFn: () => api.providers(window),
  });

  const data = series.data ?? [];
  const isPending = series.isPending || providers.isPending;

  return (
    <div className="p-6 grid gap-4 lg:grid-cols-2 animate-fade-in">
      <ChartCard
        title="Average latency"
        description="Mean latency per bucket"
        loading={isPending}
        empty={data.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="2 4" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => format(new Date(v), bucketFmt(bucket))}
              minTickGap={32}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v)}ms`}
              width={50}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(v) => format(new Date(v), "PPpp")}
              formatter={(v: number) => [formatLatency(v), "avg latency"]}
            />
            <Line
              type="monotone"
              dataKey="avg_latency_ms"
              stroke="hsl(var(--chart-3))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Tokens"
        description="Input vs output tokens per bucket"
        loading={isPending}
        empty={data.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="2 4" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => format(new Date(v), bucketFmt(bucket))}
              minTickGap={32}
            />
            <YAxis tick={{ fontSize: 11 }} width={40} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(v) => format(new Date(v), "PPpp")}
              formatter={(v: number) => formatNumber(v)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar
              dataKey="tokens_in"
              stackId="t"
              fill="hsl(var(--chart-1))"
              radius={[2, 2, 0, 0]}
            />
            <Bar
              dataKey="tokens_out"
              stackId="t"
              fill="hsl(var(--chart-2))"
              radius={[2, 2, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Cost"
        description="Cumulative USD by bucket"
        loading={isPending}
        empty={data.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="2 4" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => format(new Date(v), bucketFmt(bucket))}
              minTickGap={32}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `$${v.toFixed(2)}`}
              width={56}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(v) => format(new Date(v), "PPpp")}
              formatter={(v: number) => formatUsd(v)}
            />
            <Bar
              dataKey="cost_usd"
              fill="hsl(var(--chart-4))"
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Cache performance"
        description="Hit rate per bucket"
        loading={isPending}
        empty={data.length === 0}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data.map((d: TimeBucket) => ({
              bucket: d.bucket,
              ratio: d.requests ? d.cache_hits / d.requests : 0,
            }))}
            margin={{ top: 4, right: 12, bottom: 0, left: -10 }}
          >
            <CartesianGrid strokeDasharray="2 4" />
            <XAxis
              dataKey="bucket"
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => format(new Date(v), bucketFmt(bucket))}
              minTickGap={32}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              domain={[0, 1]}
              width={42}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={(v) => format(new Date(v), "PPpp")}
              formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            />
            <Line
              type="monotone"
              dataKey="ratio"
              stroke="hsl(var(--chart-2))"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

const tooltipStyle = {
  background: "hsl(var(--surface))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 12,
  fontSize: 12,
};

function bucketFmt(b: BucketGranularity): string {
  return b === "day" ? "MMM d" : b === "minute" ? "HH:mm" : "MMM d HH:mm";
}

function ChartCard({
  title,
  description,
  loading,
  empty,
  children,
}: {
  title: string;
  description: string;
  loading: boolean;
  empty: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-0">
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[260px]">
          {loading ? (
            <Skeleton className="h-full w-full" />
          ) : empty ? (
            <div className="grid place-items-center h-full text-sm text-muted-foreground">
              No data in window
            </div>
          ) : (
            children
          )}
        </div>
      </CardContent>
    </Card>
  );
}
