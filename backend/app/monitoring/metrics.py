"""Prometheus metrics for the gateway.

Metrics are exposed at /metrics. Cardinality matters — keep label sets bounded
(provider/model/status, not arbitrary user data).
"""
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

requests_total = Counter(
    "orchestrix_requests_total",
    "Total chat completion requests handled by the gateway.",
    labelnames=("provider", "model", "status", "cache_hit"),
)

request_latency_seconds = Histogram(
    "orchestrix_request_latency_seconds",
    "End-to-end gateway latency for chat completion requests.",
    labelnames=("provider", "model"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

tokens_total = Counter(
    "orchestrix_tokens_total",
    "Total tokens processed, partitioned by direction.",
    labelnames=("provider", "model", "direction"),  # direction: prompt | completion
)

cost_usd_total = Counter(
    "orchestrix_cost_usd_total",
    "Cumulative upstream cost in USD.",
    labelnames=("provider", "model"),
)

provider_errors_total = Counter(
    "orchestrix_provider_errors_total",
    "Upstream provider errors.",
    labelnames=("provider", "model", "error_code"),
)

rate_limit_rejections_total = Counter(
    "orchestrix_rate_limit_rejections_total",
    "Requests rejected by the rate limiter.",
    labelnames=("api_key_id",),
)

active_streams = Gauge(
    "orchestrix_active_streams",
    "Number of in-flight streaming responses.",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


__all__ = [
    "CONTENT_TYPE_LATEST",
    "active_streams",
    "cost_usd_total",
    "provider_errors_total",
    "rate_limit_rejections_total",
    "render_metrics",
    "request_latency_seconds",
    "requests_total",
    "tokens_total",
]
