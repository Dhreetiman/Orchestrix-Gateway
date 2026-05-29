import { Cpu } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

interface AuthShellProps {
  title: string;
  subtitle: string;
  footer: ReactNode;
  children: ReactNode;
}

export function AuthShell({ title, subtitle, footer, children }: AuthShellProps) {
  return (
    <div className="min-h-screen grid lg:grid-cols-[1fr_1.1fr]">
      {/* Left: form */}
      <div className="flex flex-col px-6 py-10 sm:px-10">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-primary/15 text-primary grid place-items-center">
            <Cpu className="h-4 w-4" />
          </div>
          <span className="font-semibold tracking-tight">Orchestrix Gateway</span>
        </Link>

        <div className="flex-1 grid place-items-center py-10">
          <div className="w-full max-w-sm animate-fade-in">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-7">{children}</div>
            <div className="mt-8 text-sm text-muted-foreground">{footer}</div>
          </div>
        </div>

        <div className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} Orchestrix Gateway
        </div>
      </div>

      {/* Right: marketing panel (hidden on small screens) */}
      <aside className="hidden lg:flex relative items-center justify-center overflow-hidden border-l border-border/60">
        <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--chart-1)/0.10)] via-[hsl(var(--chart-4)/0.08)] to-[hsl(var(--chart-3)/0.10)]" />
        <div className="absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]">
          <div className="absolute inset-0 bg-[radial-gradient(hsl(var(--border))_1px,transparent_1px)] [background-size:24px_24px] opacity-50" />
        </div>
        <div className="relative z-10 max-w-md px-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border/60 vibrancy text-xs text-muted-foreground mb-6">
            Welcome to Orchestrix
          </div>
          <h2 className="text-3xl font-semibold tracking-tight leading-tight">
            One gateway between you and every LLM provider.
          </h2>
          <p className="mt-4 text-muted-foreground leading-relaxed">
            Routing. Caching. Failover. Rate limiting. Cost tracking. All behind
            a single OpenAI-compatible endpoint.
          </p>
        </div>
      </aside>
    </div>
  );
}
