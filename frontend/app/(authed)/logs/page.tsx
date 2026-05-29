"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { ChevronDown, ChevronRight, Filter } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { Toolbar } from "@/components/macos/toolbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import { formatLatency, formatNumber, formatUsd } from "@/lib/format";
import type { LogFilters, RequestLogRow } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function LogsPage() {
  return (
    <>
      <Toolbar title="Request Logs" subtitle="Per-request audit trail" showWindowPicker={false} />
      <LogsContent />
    </>
  );
}

function LogsContent() {
  const [filters, setFilters] = useState<LogFilters>({});
  const queryKey = useMemo(() => ["logs", filters], [filters]);

  const q = useInfiniteQuery({
    queryKey,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      api.logs({ ...filters, cursor: pageParam, limit: 50 }),
    getNextPageParam: (last) => last.next_cursor,
  });

  const rows = (q.data?.pages ?? []).flatMap((p) => p.items);
  const total = q.data?.pages[0]?.total ?? 0;

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <FilterBar
        filters={filters}
        onChange={(next) => setFilters(next)}
        total={total}
      />

      <Card className="overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left">
              <tr className="border-b border-border/60 bg-surface-subtle/60">
                <th className="px-3 py-2 w-8"></th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Time</th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Provider</th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Model</th>
                <th className="px-3 py-2 font-medium text-muted-foreground text-right">Tokens</th>
                <th className="px-3 py-2 font-medium text-muted-foreground text-right">Cost</th>
                <th className="px-3 py-2 font-medium text-muted-foreground text-right">Latency</th>
                <th className="px-3 py-2 font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {q.isPending ? (
                Array.from({ length: 12 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/40">
                    <td colSpan={8} className="p-2">
                      <Skeleton className="h-6 w-full" />
                    </td>
                  </tr>
                ))
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-sm text-muted-foreground">
                    No log entries matching the current filters.
                  </td>
                </tr>
              ) : (
                rows.map((row) => <LogRow key={row.id} row={row} />)
              )}
            </tbody>
          </table>
        </div>
        <div className="p-3 border-t border-border/60 flex justify-between items-center">
          <span className="text-xs text-muted-foreground">
            Showing {rows.length} of {formatNumber(total)} entries
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => q.fetchNextPage()}
            disabled={!q.hasNextPage || q.isFetchingNextPage}
          >
            {q.isFetchingNextPage
              ? "Loading…"
              : q.hasNextPage
                ? "Load more"
                : "End of results"}
          </Button>
        </div>
      </Card>
    </div>
  );
}

function FilterBar({
  filters,
  onChange,
  total,
}: {
  filters: LogFilters;
  onChange: (next: LogFilters) => void;
  total: number;
}) {
  const set = <K extends keyof LogFilters>(key: K, value: LogFilters[K]) => {
    const next: LogFilters = { ...filters, [key]: value };
    if (value === undefined || value === "") delete next[key];
    onChange(next);
  };

  return (
    <div className="flex flex-wrap items-center gap-2 vibrancy rounded-2xl border border-border/60 px-3 py-2">
      <Filter className="h-4 w-4 text-muted-foreground mx-1" />
      <Select
        value={filters.provider ?? "all"}
        onValueChange={(v) => set("provider", v === "all" ? undefined : v)}
      >
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Provider" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All providers</SelectItem>
          <SelectItem value="openai">OpenAI</SelectItem>
          <SelectItem value="anthropic">Anthropic</SelectItem>
          <SelectItem value="mock">Mock</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={filters.status ?? "all"}
        onValueChange={(v) =>
          set("status", v === "all" ? undefined : (v as LogFilters["status"]))
        }
      >
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="ok">OK</SelectItem>
          <SelectItem value="error">Errors</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={
          filters.cache_hit === undefined ? "all" : filters.cache_hit ? "hit" : "miss"
        }
        onValueChange={(v) =>
          set(
            "cache_hit",
            v === "all" ? undefined : v === "hit",
          )
        }
      >
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="Cache" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">Cache: all</SelectItem>
          <SelectItem value="hit">Cache: hit</SelectItem>
          <SelectItem value="miss">Cache: miss</SelectItem>
        </SelectContent>
      </Select>

      <Input
        placeholder="Model prefix…"
        value={filters.model ?? ""}
        onChange={(e) => set("model", e.target.value || undefined)}
        className="w-[180px]"
      />

      <span className="ml-auto text-xs text-muted-foreground tabular-nums">
        {formatNumber(total)} entries
      </span>
    </div>
  );
}

function LogRow({ row }: { row: RequestLogRow }) {
  const [open, setOpen] = useState(false);
  return (
    <Fragment>
      <tr
        className={cn(
          "border-b border-border/40 hover:bg-secondary/40 cursor-pointer transition-colors",
          open && "bg-secondary/50",
        )}
        onClick={() => setOpen((o) => !o)}
      >
        <td className="px-2 text-muted-foreground">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </td>
        <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">
          {format(new Date(row.created_at), "MMM d, HH:mm:ss")}
        </td>
        <td className="px-3 py-2 capitalize">{row.provider}</td>
        <td className="px-3 py-2 font-mono text-xs">{row.model}</td>
        <td className="px-3 py-2 text-right tabular-nums">
          {formatNumber(row.tokens_in)}<span className="text-muted-foreground"> / </span>
          {formatNumber(row.tokens_out)}
        </td>
        <td className="px-3 py-2 text-right tabular-nums">{formatUsd(row.cost_usd)}</td>
        <td className="px-3 py-2 text-right tabular-nums">{formatLatency(row.latency_ms)}</td>
        <td className="px-3 py-2">
          {row.status === "ok" ? (
            row.cache_hit ? (
              <Badge variant="success">cache hit</Badge>
            ) : row.streamed ? (
              <Badge>streamed</Badge>
            ) : (
              <Badge variant="success">ok</Badge>
            )
          ) : (
            <Badge variant="destructive">{row.error_code ?? "error"}</Badge>
          )}
        </td>
      </tr>
      {open && (
        <tr className="border-b border-border/40 bg-surface-subtle/40">
          <td colSpan={8} className="px-6 py-3">
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1.5 text-xs">
              <KV label="ID" value={row.id} mono />
              <KV label="HTTP status" value={String(row.status_code)} />
              <KV label="Cache hit" value={row.cache_hit ? "yes" : "no"} />
              <KV label="Streamed" value={row.streamed ? "yes" : "no"} />
              <KV label="Tokens in" value={formatNumber(row.tokens_in)} />
              <KV label="Tokens out" value={formatNumber(row.tokens_out)} />
              <KV label="Cost USD" value={formatUsd(row.cost_usd)} />
              <KV
                label="Created at"
                value={new Date(row.created_at).toISOString()}
                mono
              />
            </dl>
          </td>
        </tr>
      )}
    </Fragment>
  );
}

function KV({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <dt className="text-muted-foreground w-24 shrink-0">{label}</dt>
      <dd className={cn("truncate", mono && "font-mono")}>{value}</dd>
    </div>
  );
}
