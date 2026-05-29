# Orchestrix Gateway — User Guide

Welcome to Orchestrix Gateway. We sit between your application and AI model providers (OpenAI, Anthropic, and more) so you get **one endpoint, lower costs, automatic failover, and a dashboard for everything that's happening** — without changing your prompt code.

This guide is for everything you'll do as a user: signing up, making your first call, reading your dashboard, managing keys.

---

## Contents

1. [Get started in 90 seconds](#get-started-in-90-seconds)
2. [Point your app at Orchestrix](#point-your-app-at-orchestrix)
3. [Choosing a model](#choosing-a-model)
4. [Your dashboard](#your-dashboard)
5. [Managing API keys](#managing-api-keys)
6. [Caching, retries, and failover](#caching-retries-and-failover)
7. [Rate limits](#rate-limits)
8. [Account settings](#account-settings)
9. [FAQs](#faqs)
10. [Getting help](#getting-help)

---

## Get started in 90 seconds

### 1. Create your account

Open Orchestrix and click **Get started**.

Enter your email, a name (optional), and a password — at least 8 characters. We hash it with Argon2id; the plaintext never touches our database.

You'll land on the dashboard immediately, signed in.

### 2. Grab your API key

When you sign up, Orchestrix automatically creates one API key for you and shows it **once** on the welcome card.

It looks like this:

```
ogw_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789
```

**Copy it now and save it somewhere safe** (a password manager, your `.env` file, etc.). You won't be shown the full key again — only the last few characters. If you lose it, just create a new one from the Settings page.

### 3. Make your first request

Open a terminal and run:

```bash
curl https://your-orchestrix-host/v1/chat/completions \
  -H "Authorization: Bearer ogw_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mock",
    "messages": [{"role": "user", "content": "Hello, Orchestrix!"}]
  }'
```

You should get back an OpenAI-shaped JSON response immediately. The `mock` model doesn't need any provider configuration — perfect for testing the wiring.

Refresh your dashboard and you'll see your first request reflected in the **Requests** tile.

That's it — you're live. Read on for what to do next.

---

## Point your app at Orchestrix

The whole pitch of Orchestrix is: **change one URL, get everything else for free**.

### With the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    api_key="ogw_YOUR_KEY",
    base_url="https://your-orchestrix-host/v1",   # the only change
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hi"}],
)
print(resp.choices[0].message.content)
```

### With the OpenAI Node SDK

```ts
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: "ogw_YOUR_KEY",
  baseURL: "https://your-orchestrix-host/v1",
});

const resp = await client.chat.completions.create({
  model: "gpt-4o-mini",
  messages: [{ role: "user", content: "Hi" }],
});
```

### With anything else

Anything that can talk to OpenAI can talk to Orchestrix — LangChain, LlamaIndex, Vercel AI SDK, Continue.dev, Cursor, your custom Go service, etc. Point it at `/v1/chat/completions` with your `ogw_…` key as the bearer token.

### Streaming

Set `"stream": true` on the request and Orchestrix returns OpenAI-compatible SSE events:

```bash
curl -N https://your-orchestrix-host/v1/chat/completions \
  -H "Authorization: Bearer ogw_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "stream": true,
    "messages": [{"role": "user", "content": "Write a limerick about caching."}]
  }'
```

You'll get `data: {…}` chunks ending with `data: [DONE]`. Anthropic models stream in the same shape — Orchestrix translates the upstream format for you, so your client code doesn't need branching logic.

### Useful response headers

Every response carries:

| Header | What it means |
| --- | --- |
| `X-Cache: HIT` or `MISS` | Was this served from cache, or did we call the upstream? |
| `X-Served-By` | Which provider actually answered: `openai`, `anthropic`, or `mock` |
| `X-Request-ID` | Unique ID for this request — quote it when contacting support |

`X-Served-By` is especially useful when failover is in play: you asked for `gpt-4o-mini` but Orchestrix may have served you from Anthropic because OpenAI was down. You'll see that here.

---

## Choosing a model

You ask for a model by name. Orchestrix decides which provider answers.

| You request | Primary provider | If primary fails |
| --- | --- | --- |
| `gpt-4o`, `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo` | OpenAI | Falls back to Anthropic |
| `o1-preview`, `o1-mini`, `o3-*` | OpenAI | (no fallback) |
| `claude-3-5-sonnet`, `claude-3-5-haiku`, `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku` | Anthropic | Falls back to OpenAI |
| `mock` | Built-in | (test only) |

Versioned model names like `gpt-4o-2024-08-06` or `claude-3-5-sonnet-20241022` route by prefix — they behave the same as the base name.

### How failover works (and what it costs you)

If the primary provider returns a terminal upstream error (5xx, network unreachable, etc.), Orchestrix automatically retries the same request against the next provider in the chain.

- **You don't pay double** — the failed attempt costs nothing because we never got a successful response from it.
- **The response shape stays consistent** — even if the request ends up being served by Anthropic, your client receives an OpenAI-shaped response.
- **You'll see what happened** — `X-Served-By` tells you which provider actually answered, and the dashboard logs both attempts.

Failover is for resilience, not load-balancing. We don't randomly split traffic — your primary always gets the first shot.

### How to pick the right model

- **Highest quality, willing to pay**: `gpt-4o` or `claude-3-5-sonnet`
- **Best cost/quality balance**: `gpt-4o-mini` or `claude-3-5-haiku`
- **Cheap and fast for simple tasks**: `claude-3-haiku` or `gpt-3.5-turbo`
- **Reasoning-heavy tasks**: `o1-preview` (slow, expensive) or `o1-mini`
- **Just testing the integration**: `mock`

Cost-per-token is tracked per model on your dashboard so you can directly compare.

---

## Your dashboard

The dashboard has four pages, accessible from the sidebar on the left.

### Dashboard (`/dashboard`)

Your at-a-glance overview. Use the **time window picker** in the top-right (`Last 15 min` through `Last 7 days`) to scope everything on the page.

**The four KPI tiles**:

| Tile | What it measures | What to do with it |
| --- | --- | --- |
| **Requests** | Total chat completion calls in the window | Sanity-check that your app is talking to us at all |
| **Cache hit ratio** | % of requests served from cache (free, fast) | A high number means you're saving money. < 5% with deterministic prompts? See [caching](#caching-retries-and-failover) |
| **p95 latency** | 95th-percentile end-to-end latency | If this is creeping up, something upstream is slowing down |
| **Spend** | Total upstream cost (USD) in the window | Budget tracking |

**The charts**:

- **Request volume** — area chart of requests per bucket. Spot traffic spikes, scheduled jobs, dead zones.
- **Providers** — donut showing how requests split across OpenAI / Anthropic / mock. If you expect 100% OpenAI but see Anthropic traffic, that's failover firing — investigate the logs.
- **Top model** / **Errors** / **Tokens** — supporting cards.

### Request Logs (`/logs`)

Every request, audit-trail style. Each row shows time, provider, model, prompt + completion tokens, cost, latency, and outcome (OK, cached, streamed, or an error).

Use the filter bar to scope by:

- **Provider** — drill into just OpenAI or just Anthropic
- **Status** — show only errors when investigating an incident
- **Cache** — see what's hitting cache vs missing
- **Model prefix** — type `gpt-4o` to see all GPT-4o variants

Click any row to expand it and see the full request ID, HTTP status code, ISO timestamps, and other details. The `X-Request-ID` you got in your response headers matches the ID here — useful for tracing one specific request your customer reported.

"Load more" at the bottom walks backwards in time through your history.

### Analytics (`/analytics`)

Four time-series charts for spotting trends:

- **Average latency** — line chart. Are responses getting slower over time?
- **Tokens** — stacked bars showing prompt vs completion volume. Are your prompts growing?
- **Cost** — bars in USD. When does your spend spike?
- **Cache performance** — % of cache hits over time. Is your caching getting better or worse as your prompts evolve?

Good for weekly reviews and answering questions like _"why was Wednesday so expensive?"_

### Settings (`/settings`)

Profile and API key management. Detailed in the next two sections.

### Light / dark mode

The sun/moon button in the top-right of any page toggles the theme. By default we follow your system theme — switch your laptop to dark mode and the dashboard follows.

---

## Managing API keys

Open Settings to see all the API keys on your account.

### Creating a new key

Click **New key**. Give it a label like _"prod web"_, _"local dev"_, or _"customer-X integration"_. We'll show you the full key **once** in a modal — copy it before closing.

Best practices:

- **One key per workload.** Separate keys for prod, staging, dev, and each integration make it easy to revoke just one without breaking everything.
- **Name them descriptively.** _"prod-2026-q2"_ beats _"key1"_.
- **Don't commit keys to git.** Use environment variables (`OGW_API_KEY`) and a secret manager.
- **Rotate periodically.** Every 90 days for sensitive workloads.

### Revoking a key

In the API keys list, click the trash icon next to any key. It's instant — within seconds, requests using that key start receiving `401 invalid_api_key`.

Revoke immediately if:

- A key was committed to a public repo
- A key shows up in client-side JavaScript
- A laptop or device with the key was lost
- A team member with key access leaves

The key preview (`ogw_…abc123`) shows the last 6 characters of its hash — match against your password manager to identify which key to revoke if you have several.

### "Last used" tells you what's actually in use

Each key shows when it was last used. If a key hasn't been touched in months, you can probably revoke it safely — the worst case is a deploy in some forgotten cron job starts failing and you'll get paged to rotate.

---

## Caching, retries, and failover

Three things Orchestrix does for you automatically.

### Caching

**When it kicks in:** When you send the same `messages` array with the same model and a low temperature (≤ 0.1), we return the previous response from Redis instead of calling the upstream.

The result:

- The response is identical to the first time
- It returns in 5-15 milliseconds instead of hundreds
- It costs you nothing (no upstream call = no tokens billed)
- Your headers say `X-Cache: HIT`

**When it doesn't:**

- Temperature > 0.1 (you've signaled you want variation)
- Any tiny difference in the messages (a trailing space, a different timestamp in your system prompt)
- Streaming requests (we don't cache streams)

**How to force a fresh response:** Bump the temperature, or add a unique random nonce to your system prompt. (We're working on an explicit `cache: false` flag — let us know if you want this prioritized.)

The dashboard's **Cache hit ratio** tile and the per-bucket cache performance chart on Analytics show how often you're hitting cache. A high ratio is money saved.

### Retries

Transient upstream failures (HTTP `429`, `502`, `503`, `504`, connection resets) are retried automatically with exponential backoff and jitter, up to 3 attempts per provider. Your request just succeeds — you don't see a thing.

We only retry **safe-to-retry** failures. Real errors (`400 bad request`, `401 invalid key`, `404 model not found`) come back to you immediately.

### Failover

If a provider exhausts its retries, we try the next provider in the failover chain (see [Choosing a model](#choosing-a-model)). The response comes back to you in the same shape — `choices[].message.content` regardless of who answered.

`X-Served-By` in your response tells you whether failover fired. The request log also shows the attempt against the primary provider that failed, with its error code.

---

## Rate limits

Each API key has a sliding-window rate limit: a maximum number of requests per minute (RPM).

Default: **60 requests/minute per key**. Higher tiers can be configured — talk to us if you need it raised.

### What a 429 looks like

When you exceed your limit, you get:

```json
{
  "error": {
    "code": "rate_limited",
    "message": "Rate limit exceeded (60 requests/min).",
    "detail": { "retry_after_seconds": 12 }
  }
}
```

Wait `retry_after_seconds` and retry, or back off with your own queue.

### Avoiding rate limits

- **Use multiple keys.** Different workloads on different keys means one runaway loop doesn't starve the others.
- **Cache aggressively.** Cache hits don't count against your limit.
- **Batch when possible.** One request with three questions in the prompt costs one slot; three separate requests cost three.
- **Add backoff in your client.** When you hit a 429, exponential backoff (1s, 2s, 4s, 8s) plays nice with our sliding window.

---

## Account settings

### Changing your name

Settings → profile field. Updates immediately.

### Changing your password

For security, password changes go through a flow that requires your current password. (If you've forgotten it, use the "forgot password" link on the login page — you'll get a reset email.)

### Signing out

Click the sign-out button (the door icon) in your profile card at the bottom of the sidebar. We revoke your session on the server side — even if someone steals your cookie before it expires, they can't use it.

### Deleting your account

We don't offer self-serve account deletion yet — email support@orchestrix.example and we'll handle it.

---

## FAQs

**How is Orchestrix different from calling OpenAI directly?**

Same response shape, but with: caching (lower bill), automatic retries + failover (higher uptime), per-request cost tracking, a unified endpoint across providers, and a dashboard for everything. You pay nothing extra to Orchestrix on top of upstream costs while you're in beta.

**Do you store my prompts and responses?**

We store request metadata (timestamps, model, token counts, latency, cost, status) for your dashboard. We do **not** store prompt bodies or response content. We do store a SHA-256 hash of your prompts when caching is in play — that hash is one-way and can't be reversed to recover the text.

**Can you see my data?**

Only your account can see your dashboard, logs, and analytics. Other users on Orchestrix see only their own data. Operators can see aggregate health metrics (request rates, error rates) but not your individual requests.

**Why is my response slower than calling OpenAI directly?**

For cache misses, Orchestrix adds 5-20ms of overhead (auth, routing, logging). For cache hits, you save hundreds of milliseconds. If you're consistently slower than expected, check the **Average latency** chart on Analytics — if upstream is slow, we're a victim, not the cause.

**Can I use my own OpenAI / Anthropic key?**

Yes — that's actually how Orchestrix works under the hood. We use the provider keys configured on the gateway. If you're self-hosting, you configure your own keys. If you're using our hosted service, talk to us about bring-your-own-key.

**What happens if I lose my API key?**

It's not recoverable — we only ever store the hash, not the plaintext. Create a new key from Settings and update your application. Revoke the old one if you suspect it may have leaked.

**Does Orchestrix work with non-chat endpoints (embeddings, image gen)?**

Not yet — we currently support `/v1/chat/completions` only. Embeddings and image generation are on the roadmap.

**Is there an SDK?**

We're OpenAI-compatible by design, so the OpenAI SDK in any language works directly. You just change `base_url`. A native Orchestrix SDK is on the roadmap for richer features (per-request routing hints, explicit cache control, etc.).

**Can I see what each model costs per token?**

The per-model cost table is reflected automatically in your dashboard's **Spend** metric. The current rates we use:

| Model | Input / 1M tokens | Output / 1M tokens |
| --- | --- | --- |
| `gpt-4o` | $2.50 | $10.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `o1-preview` | $15.00 | $60.00 |
| `o1-mini` | $3.00 | $12.00 |
| `claude-3-5-sonnet` | $3.00 | $15.00 |
| `claude-3-5-haiku` | $0.80 | $4.00 |
| `claude-3-opus` | $15.00 | $75.00 |
| `claude-3-haiku` | $0.25 | $1.25 |

Snapshot from May 2026 — we update these as upstream pricing changes.

---

## Getting help

- **In-app:** the chat bubble on the bottom-right of any dashboard page
- **Email:** support@orchestrix.example (reply within one business day during beta)
- **Status:** status.orchestrix.example for incident updates
- **Include in your message:** your `X-Request-ID` for any specific failing request, plus what you saw vs. what you expected

Thanks for using Orchestrix. We're building this in the open — feedback, gripes, and feature requests are all very welcome.
