"use client";

import {
  Cpu,
  LayoutDashboard,
  LineChart,
  LogOut,
  ScrollText,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { TrafficLights } from "@/components/macos/traffic-lights";
import { Button } from "@/components/ui/button";
import { useCurrentUser, useLogout } from "@/lib/use-auth";
import { cn } from "@/lib/utils";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/logs", label: "Request Logs", icon: ScrollText },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const logout = useLogout();

  return (
    <aside className="hidden md:flex w-64 shrink-0 flex-col vibrancy border-r border-border/60">
      <header className="flex items-center justify-between p-4 pb-3">
        <TrafficLights />
        <span className="text-xs text-muted-foreground tracking-wide uppercase">
          Orchestrix
        </span>
      </header>

      <div className="px-3 pt-2 pb-4">
        <div className="flex items-center gap-2 px-2 py-1.5 mb-2">
          <div className="h-8 w-8 rounded-lg bg-primary/15 text-primary grid place-items-center">
            <Cpu className="h-4 w-4" />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-semibold">Gateway</span>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              v0.1
            </span>
          </div>
        </div>

        <nav className="flex flex-col gap-0.5">
          {items.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors",
                  "hover:bg-secondary/70",
                  active
                    ? "bg-secondary text-sidebar-accent font-medium shadow-sm"
                    : "text-sidebar-foreground/85",
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4",
                    active ? "text-sidebar-accent" : "text-muted-foreground",
                  )}
                />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto px-3 pb-4">
        <div className="rounded-xl border border-border/60 bg-surface/70 backdrop-blur p-3 flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-primary/15 text-primary grid place-items-center text-xs font-semibold uppercase">
            {(user?.name ?? user?.email ?? "?").slice(0, 1)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium truncate">
              {user?.name ?? "Signed in"}
            </div>
            <div className="text-[11px] text-muted-foreground truncate">
              {user?.email ?? "—"}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
