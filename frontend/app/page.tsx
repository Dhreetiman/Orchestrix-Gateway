import {
  ArrowRight,
  Cpu,
  Database,
  Gauge,
  LineChart,
  Lock,
  ScrollText,
  Sparkles,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { TrafficLights } from "@/components/macos/traffic-lights";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <LandingNav />
      <Hero />
      <Features />
      <CodeSection />
      <Footer />
    </div>
  );
}

function LandingNav() {
  return (
    <header className="sticky top-0 z-30 vibrancy border-b border-border/60">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-primary/15 text-primary grid place-items-center">
            <Cpu className="h-4 w-4" />
          </div>
          <span className="font-semibold tracking-tight">Orchestrix</span>
          <span className="text-xs text-muted-foreground hidden sm:inline">
            Gateway
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link href="/login">Log in</Link>
          </Button>
          <Button asChild>
            <Link href="/signup">
              Get started <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="max-w-6xl mx-auto px-6 pt-20 pb-24 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border/60 vibrancy text-xs text-muted-foreground mb-6">
          <Sparkles className="h-3 w-3 text-[hsl(var(--chart-3))]" />
          One gateway. Every LLM provider. Full observability.
        </div>
        <h1 className="text-5xl sm:text-6xl font-semibold tracking-tight leading-[1.05]">
          The AI gateway your{" "}
          <span className="bg-gradient-to-r from-[hsl(var(--chart-1))] via-[hsl(var(--chart-4))] to-[hsl(var(--chart-3))] bg-clip-text text-transparent">
            infrastructure
          </span>{" "}
          deserves.
        </h1>
        <p className="mt-5 text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Drop in a single OpenAI-compatible endpoint and get intelligent
          routing, distributed caching, automatic failover, rate limiting, and
          per-request cost tracking — across OpenAI, Anthropic, and beyond.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Button size="lg" asChild>
            <Link href="/signup">
              Start free <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
          <Button variant="outline" size="lg" asChild>
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
        <div className="mt-14 mx-auto max-w-4xl">
          <BrowserMock />
        </div>
      </div>
    </section>
  );
}

function BrowserMock() {
  return (
    <div className="rounded-2xl border border-border/60 vibrancy-strong card-rim overflow-hidden text-left">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/60 bg-surface-subtle/60">
        <TrafficLights />
        <div className="text-xs text-muted-foreground font-mono">
          orchestrix.gateway / dashboard
        </div>
        <div className="w-12" />
      </div>
      <div className="p-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Requests", value: "12.4k", accent: "chart-1" },
          { label: "Cache hits", value: "62.1%", accent: "chart-2" },
          { label: "p95 latency", value: "412 ms", accent: "chart-3" },
          { label: "Spend", value: "$3.27", accent: "chart-4" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-xl border border-border/60 bg-surface/60 p-3"
          >
            <div className="text-[11px] text-muted-foreground">{kpi.label}</div>
            <div
              className="mt-1 text-2xl font-semibold tabular-nums"
              style={{ color: `hsl(var(--${kpi.accent}))` }}
            >
              {kpi.value}
            </div>
          </div>
        ))}
      </div>
      <div className="px-6 pb-6">
        <div className="h-28 rounded-xl border border-border/60 bg-gradient-to-b from-[hsl(var(--chart-1)/0.15)] to-transparent relative overflow-hidden">
          <svg
            className="absolute inset-0 w-full h-full"
            viewBox="0 0 400 100"
            preserveAspectRatio="none"
          >
            <path
              d="M0,70 C40,50 80,80 120,60 S200,30 240,45 S320,80 400,40"
              fill="none"
              stroke="hsl(var(--chart-1))"
              strokeWidth="2"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
  accent: string;
}

const FEATURES: Feature[] = [
  {
    icon: Zap,
    title: "Intelligent routing & failover",
    body: "Route each model to its best provider. If a primary upstream returns 502, the gateway automatically falls back to a configured equivalent — without dropping the request.",
    accent: "chart-1",
  },
  {
    icon: Database,
    title: "Response caching",
    body: "Identical low-temperature prompts return from Redis in single-digit milliseconds. Cut both your bill and your p95 latency without changing client code.",
    accent: "chart-2",
  },
  {
    icon: LineChart,
    title: "Cost & token analytics",
    body: "Every request is logged with tokens, latency, provider, and dollar cost. See exactly which model and which prompt is burning your budget.",
    accent: "chart-3",
  },
  {
    icon: Gauge,
    title: "Per-key rate limiting",
    body: "Sliding-window rate limits in Redis, scoped per API key. No one client can starve the rest, and 429s come back with a precise Retry-After.",
    accent: "chart-4",
  },
  {
    icon: ScrollText,
    title: "Production-grade observability",
    body: "Structured JSON logs with secret redaction, Prometheus metrics at /metrics, and a provisioned Grafana dashboard included.",
    accent: "chart-5",
  },
  {
    icon: Lock,
    title: "Secure by default",
    body: "Argon2id password hashing, httpOnly session cookies, scoped multi-tenant API keys, request body size limits, and CORS hardened from day one.",
    accent: "chart-1",
  },
];

function Features() {
  return (
    <section
      id="features"
      className="border-t border-border/60 py-20 bg-surface-subtle/30"
    >
      <div className="max-w-6xl mx-auto px-6">
        <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
          Everything you wish your AI stack had.
        </h2>
        <p className="mt-3 text-center text-muted-foreground max-w-2xl mx-auto">
          Orchestrix Gateway centralizes the plumbing every LLM application
          ends up writing — so yours stays thin.
        </p>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <article
              key={f.title}
              className="rounded-2xl border border-border/60 bg-surface/70 backdrop-blur p-6 card-rim transition-transform hover:-translate-y-0.5"
            >
              <div
                className="h-10 w-10 rounded-xl grid place-items-center"
                style={{
                  background: `hsl(var(--${f.accent}) / 0.12)`,
                  color: `hsl(var(--${f.accent}))`,
                }}
              >
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-semibold tracking-tight">{f.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed">
                {f.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function CodeSection() {
  return (
    <section className="py-20 border-t border-border/60">
      <div className="max-w-5xl mx-auto px-6 grid lg:grid-cols-2 gap-10 items-center">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight">
            One endpoint. Drop-in compatible.
          </h2>
          <p className="mt-3 text-muted-foreground leading-relaxed">
            Orchestrix speaks the OpenAI Chat Completions API. Point your
            existing SDK at the gateway and you immediately get routing,
            caching, retries, failover, metrics, and cost tracking.
          </p>
          <ul className="mt-6 space-y-2 text-sm">
            {[
              "OpenAI · Anthropic · more on the way",
              "Streaming + non-streaming, same shape",
              "Hot reload of models without redeploys",
              "Per-tenant API keys you can revoke instantly",
            ].map((it) => (
              <li key={it} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                {it}
              </li>
            ))}
          </ul>
          <Button className="mt-8" asChild>
            <Link href="/signup">
              Create your account <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
        <div className="rounded-2xl border border-border/60 vibrancy-strong card-rim overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/60 bg-surface-subtle/60">
            <TrafficLights />
            <span className="text-[11px] text-muted-foreground font-mono">
              terminal
            </span>
            <div className="w-12" />
          </div>
          <pre className="p-5 text-[12px] leading-relaxed font-mono overflow-x-auto">
{`curl https://your-gateway/v1/chat/completions \\
  -H "Authorization: Bearer ogw_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Hello, Orchestrix!"}
    ]
  }'

# → cached response, X-Cache: HIT, served in 8 ms`}
          </pre>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border/60 py-10 mt-auto">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-md bg-primary/15 text-primary grid place-items-center">
            <Cpu className="h-3 w-3" />
          </div>
          <span className="font-medium text-foreground">Orchestrix Gateway</span>
          <span>© {new Date().getFullYear()}</span>
        </div>
        <div className="flex items-center gap-5">
          <Link href="/login" className="hover:text-foreground">
            Log in
          </Link>
          <Link href="/signup" className="hover:text-foreground">
            Sign up
          </Link>
        </div>
      </div>
    </footer>
  );
}
