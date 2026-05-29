"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppStore } from "@/lib/store";
import type { WindowPreset } from "@/lib/types";

const WINDOW_OPTIONS: { value: WindowPreset; label: string }[] = [
  { value: "15m", label: "Last 15 min" },
  { value: "1h", label: "Last hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
];

interface ToolbarProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  showWindowPicker?: boolean;
}

export function Toolbar({
  title,
  subtitle,
  actions,
  showWindowPicker = true,
}: ToolbarProps) {
  const timeWindow = useAppStore((s) => s.window);
  const setWindow = useAppStore((s) => s.setWindow);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const isDark = mounted && (resolvedTheme ?? theme) === "dark";

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between gap-3 px-6 py-4 vibrancy border-b border-border/60">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold tracking-tight truncate">{title}</h1>
        {subtitle && (
          <p className="text-sm text-muted-foreground truncate">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-2">
        {showWindowPicker && (
          <Select
            value={timeWindow}
            onValueChange={(v) => setWindow(v as WindowPreset)}
          >
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WINDOW_OPTIONS.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {mounted && (
          <Button
            variant="outline"
            size="icon"
            onClick={() => setTheme(isDark ? "light" : "dark")}
            title="Toggle theme"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        )}

        {actions}
      </div>
    </header>
  );
}
