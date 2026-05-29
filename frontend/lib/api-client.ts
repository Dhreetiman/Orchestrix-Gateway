/**
 * Typed fetch client for the Orchestrix Gateway admin + auth API.
 *
 * Auth model:
 * - Browsers use httpOnly session cookies set by /auth/login. `credentials: "include"` makes
 *   the browser send and accept those cookies through the Next.js proxy rewrite.
 * - The dashboard never sees or stores the gateway API key — that key is for /v1 only.
 */
import type {
  ApiKeyCreated,
  ApiKeyRow,
  LogFilters,
  LogsPage,
  LoginRequest,
  OverviewStats,
  ProviderSlice,
  SignupRequest,
  SignupResponse,
  TimeBucket,
  User,
  WindowPreset,
} from "./types";

const BASE = "/api/gateway";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const body = await res.json();
      message =
        body?.error?.message ?? body?.detail ?? body?.message ?? message;
    } catch {
      // ignore parse failures
    }
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  auth: {
    signup: (body: SignupRequest) =>
      request<SignupResponse>("/auth/signup", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    login: (body: LoginRequest) =>
      request<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    logout: () => request<void>("/auth/logout", { method: "POST" }),
    me: () => request<User>("/auth/me"),
  },
  overview: (window: WindowPreset) =>
    request<OverviewStats>(`/admin/stats/overview?window=${window}`),
  series: (
    window: WindowPreset,
    bucket: "minute" | "hour" | "day",
  ) =>
    request<TimeBucket[]>(
      `/admin/stats/series?window=${window}&bucket=${bucket}`,
    ),
  providers: (window: WindowPreset) =>
    request<ProviderSlice[]>(`/admin/stats/providers?window=${window}`),
  logs: (
    opts: { limit?: number; cursor?: string | null } & LogFilters = {},
  ) => {
    const params = new URLSearchParams();
    if (opts.limit) params.set("limit", String(opts.limit));
    if (opts.cursor) params.set("cursor", opts.cursor);
    if (opts.provider) params.set("provider", opts.provider);
    if (opts.status) params.set("status", opts.status);
    if (opts.cache_hit !== undefined)
      params.set("cache_hit", String(opts.cache_hit));
    if (opts.model) params.set("model", opts.model);
    const qs = params.toString();
    return request<LogsPage>(`/admin/logs${qs ? `?${qs}` : ""}`);
  },
  apiKeys: {
    list: () => request<ApiKeyRow[]>("/admin/api-keys"),
    create: (name: string) =>
      request<ApiKeyCreated>("/admin/api-keys", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    revoke: (id: string) =>
      request<ApiKeyRow>(`/admin/api-keys/${id}/revoke`, { method: "POST" }),
  },
};

export { ApiError };
