"""Build and parse AIPerf (or GenAI-Perf fallback) commands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def choose_client() -> str:
    if shutil.which("aiperf"):
        return "aiperf"
    if shutil.which("genai-perf"):
        return "genai-perf"
    return "missing"


def aiperf_command(config: dict[str, Any], endpoint: str) -> list[str]:
    return [
        "aiperf",
        "profile",
        "-m",
        str(config["model"]),
        "--endpoint-type",
        "chat",
        "--streaming",
        "--url",
        endpoint,
        "--concurrency",
        str(config["concurrency"]),
        "--synthetic-input-tokens-mean",
        str(config["input_tokens"]),
        "--output-tokens-mean",
        str(config["output_tokens"]),
        "--request-count",
        str(config.get("requests", 300)),
        "--warmup-request-count",
        str(config.get("warmup_requests", 30)),
    ]


def empty_metrics() -> dict[str, None]:
    return {
        "ttft_p50_ms": None,
        "ttft_p95_ms": None,
        "itl_p50_ms": None,
        "output_tokens_per_s": None,
        "requests_per_s": None,
        "kv_cache_capacity_tokens": None,
        "accuracy": None,
        "usd_per_1m_output_tokens": None,
    }


def parse_aiperf_json(path: Path) -> dict[str, float | None]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    metrics = empty_metrics()
    mapping = {
        "ttft_p50_ms": ("time_to_first_token", "p50"),
        "ttft_p95_ms": ("time_to_first_token", "p95"),
        "itl_p50_ms": ("inter_token_latency", "p50"),
        "output_tokens_per_s": ("output_token_throughput", "avg"),
        "requests_per_s": ("request_throughput", "avg"),
    }
    for dest, (section, stat) in mapping.items():
        block = raw.get(section) or raw.get("metrics", {}).get(section) or {}
        value = block.get(stat)
        if value is not None:
            metrics[dest] = float(value)
    return metrics


def cost_per_1m(output_tokens_per_s: float | None, gpu_usd_per_hour: float) -> float | None:
    if not output_tokens_per_s:
        return None
    tokens_per_hour = output_tokens_per_s * 3600.0
    return (gpu_usd_per_hour / tokens_per_hour) * 1_000_000
