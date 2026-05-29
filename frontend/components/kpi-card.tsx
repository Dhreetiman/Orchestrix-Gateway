import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: LucideIcon;
  accent?: "blue" | "green" | "orange" | "purple" | "red";
  loading?: boolean;
}

const ACCENTS: Record<NonNullable<KpiCardProps["accent"]>, string> = {
  blue: "bg-chart-1/10 text-[hsl(var(--chart-1))]",
  green: "bg-chart-2/10 text-[hsl(var(--chart-2))]",
  orange: "bg-chart-3/10 text-[hsl(var(--chart-3))]",
  purple: "bg-chart-4/10 text-[hsl(var(--chart-4))]",
  red: "bg-chart-5/10 text-[hsl(var(--chart-5))]",
};

export function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "blue",
  loading,
}: KpiCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-medium text-muted-foreground">{label}</div>
        {Icon && (
          <div
            className={cn(
              "h-8 w-8 rounded-lg grid place-items-center",
              ACCENTS[accent],
            )}
          >
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-2">
        {loading ? (
          <Skeleton className="h-9 w-32" />
        ) : (
          <div className="text-3xl font-semibold tracking-tight tabular-nums">
            {value}
          </div>
        )}
      </div>
      {hint && (
        <div className="mt-1.5 text-xs text-muted-foreground">{hint}</div>
      )}
    </Card>
  );
}
