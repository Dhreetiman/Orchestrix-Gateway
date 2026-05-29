"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  DollarSign,
  Gauge,
  Layers,
  TrendingUp,
  Zap,
} from "lucide-react";
import { ProviderDonut } from "@/components/charts/provider-donut";
import { TrafficSparkline } from "@/components/charts/traffic-sparkline";
import { KpiCard } from "@/components/kpi-card";
import { Toolbar } from "@/components/macos/toolbar";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import {
  formatLatency,
  formatNumber,
  formatPercent,
  formatUsd,
} from "@/lib/format";
import { useAppStore } from "@/lib/store";
import type { BucketGranularity, WindowPreset } from "@/lib/types";

function bucketFor(window: WindowPreset): BucketGranularity {
  if (window === "15m" || window === "1h") return "minute";
  if (window === "7d") return "day";
  return "hour";
}

export default function DashboardPage() {
  return (
    <>
      <Toolbar title="Dashboard" subtitle="Real-time gateway activity" />
      <DashboardContent />
    </>
  );
}

function DashboardContent() {
  const window = useAppStore((s) => s.window);
  const bucket = bucketFor(window);

  const overview = useQuery({
    queryKey: ["overview", window],
    queryFn: () => api.overview(window),
  });
  const series = useQuery({
    queryKey: ["series", window, bucket],
    queryFn: () => api.series(window, bucket),
  });
  const providers = useQuery({
    queryKey: ["providers", window],
    queryFn: () => api.providers(window),
  });

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Requests"
          icon={Activity}
          accent="blue"
          loading={overview.isPending}
          value={formatNumber(overview.data?.total_requests ?? 0, true)}
        />
        <KpiCard
          label="Cache hit ratio"
          icon={Zap}
          accent="green"
          loading={overview.isPending}
          value={formatPercent(overview.data?.cache_hit_ratio ?? 0)}
          hint={
            overview.data
              ? `${formatNumber(overview.data.cache_hits)} of ${formatNumber(overview.data.total_requests)}`
              : undefined
          }
        />
        <KpiCard
          label="p95 latency"
          icon={Gauge}
          accent="orange"
          loading={overview.isPending}
          value={formatLatency(overview.data?.p95_latency_ms ?? 0)}
          hint={
            overview.data
              ? `p50 ${formatLatency(overview.data.p50_latency_ms)}`
              : undefined
          }
        />
        <KpiCard
          label="Spend"
          icon={DollarSign}
          accent="purple"
          loading={overview.isPending}
          value={formatUsd(overview.data?.cost_usd ?? 0)}
          hint={
            overview.data
              ? `${formatNumber(overview.data.tokens_in + overview.data.tokens_out, true)} tokens`
              : undefined
          }
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 p-0">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-base">Request volume</CardTitle>
              <p className="text-sm text-muted-foreground">
                Requests per {bucket}
              </p>
            </div>
            {overview.data && overview.data.error_count > 0 && (
              <Badge variant="destructive">
                {overview.data.error_count} errors
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              {series.isPending ? (
                <Skeleton className="h-full w-full" />
              ) : series.data && series.data.length ? (
                <TrafficSparkline data={series.data} />
              ) : (
                <EmptyChart />
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="p-0">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              Providers
            </CardTitle>
            <p className="text-sm text-muted-foreground">Share by requests</p>
          </CardHeader>
          <CardContent>
            <div className="h-[200px]">
              {providers.isPending ? (
                <Skeleton className="h-full w-full" />
              ) : (
                <ProviderDonut data={providers.data ?? []} />
              )}
            </div>
            <ul className="mt-3 space-y-1.5 text-sm">
              {(providers.data ?? []).map((p) => (
                <li key={p.provider} className="flex justify-between">
                  <span className="capitalize text-muted-foreground">
                    {p.provider}
                  </span>
                  <span className="font-medium tabular-nums">
                    {formatNumber(p.requests)}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <div className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Tokens
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs text-muted-foreground">In</div>
              <div className="text-2xl font-semibold tabular-nums">
                {formatNumber(overview.data?.tokens_in ?? 0, true)}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Out</div>
              <div className="text-2xl font-semibold tabular-nums">
                {formatNumber(overview.data?.tokens_out ?? 0, true)}
              </div>
            </div>
          </div>
        </Card>
        <Card className="p-5">
          <div className="text-sm font-medium text-muted-foreground">
            Top model
          </div>
          <div className="mt-2 text-xl font-semibold">
            {providers.data?.[0]?.provider ?? "—"}
          </div>
          <div className="text-xs text-muted-foreground">
            {formatNumber(providers.data?.[0]?.requests ?? 0)} requests
          </div>
        </Card>
        <Card className="p-5">
          <div className="text-sm font-medium text-muted-foreground">Errors</div>
          <div className="mt-2 text-3xl font-semibold tabular-nums">
            {formatNumber(overview.data?.error_count ?? 0)}
          </div>
          <div className="text-xs text-muted-foreground">
            {overview.data && overview.data.total_requests > 0
              ? formatPercent(
                  overview.data.error_count / overview.data.total_requests,
                )
              : "—"}{" "}
            of total
          </div>
        </Card>
      </section>
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="grid place-items-center h-full text-sm text-muted-foreground">
      No data in window. Try issuing a request.
    </div>
  );
}
