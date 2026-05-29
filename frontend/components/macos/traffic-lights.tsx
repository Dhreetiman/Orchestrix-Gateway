import { cn } from "@/lib/utils";

export function TrafficLights({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-1.5", className)} aria-hidden="true">
      <span className="traffic-light bg-[hsl(var(--traffic-close))]" />
      <span className="traffic-light bg-[hsl(var(--traffic-minimize))]" />
      <span className="traffic-light bg-[hsl(var(--traffic-maximize))]" />
    </div>
  );
}
