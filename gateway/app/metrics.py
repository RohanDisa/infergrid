from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUESTS = Counter(
    "infergrid_gateway_requests_total",
    "Gateway requests",
    ["backend", "model", "status"],
)
ERRORS = Counter(
    "infergrid_gateway_errors_total",
    "Gateway errors",
    ["backend", "model", "reason"],
)
DURATION = Histogram(
    "infergrid_gateway_request_duration_seconds",
    "End-to-end gateway request duration",
    ["backend", "model"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)
OVERHEAD = Histogram(
    "infergrid_gateway_overhead_seconds",
    "Time from request receipt to first upstream byte",
    ["backend"],
    buckets=(0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1),
)
INFLIGHT = Gauge(
    "infergrid_gateway_inflight_requests",
    "In-flight gateway requests",
    ["backend"],
)
BACKEND_READY = Gauge(
    "infergrid_gateway_backend_ready",
    "1 if the last readiness probe for this backend succeeded",
    ["backend", "route"],
)


def render() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
