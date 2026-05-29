// Types mirror the backend Pydantic models in backend/app/api/admin.py and auth.py.
// Keep these in sync when the backend schema changes.

export interface User {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
}

export interface SignupResponse {
  user: User;
  api_key: string;
}

export interface SignupRequest {
  email: string;
  password: string;
  name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export type WindowPreset = "15m" | "1h" | "6h" | "24h" | "7d";
export type BucketGranularity = "minute" | "hour" | "day";

export interface OverviewStats {
  window_seconds: number;
  total_requests: number;
  cache_hits: number;
  cache_hit_ratio: number;
  error_count: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
}

export interface TimeBucket {
  bucket: string; // ISO timestamp
  requests: number;
  cache_hits: number;
  errors: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  avg_latency_ms: number;
}

export interface ProviderSlice {
  provider: string;
  requests: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  error_count: number;
}

export interface RequestLogRow {
  id: string;
  created_at: string;
  provider: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  status: "ok" | "error";
  status_code: number;
  error_code: string | null;
  cache_hit: boolean;
  streamed: boolean;
}

export interface LogsPage {
  items: RequestLogRow[];
  next_cursor: string | null;
  total: number;
}

export interface ApiKeyRow {
  id: string;
  name: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
  is_active: boolean;
  key_preview: string;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  key: string;
}

export interface LogFilters {
  provider?: string;
  status?: "ok" | "error";
  cache_hit?: boolean;
  model?: string;
}
