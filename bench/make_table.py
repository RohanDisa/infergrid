#!/usr/bin/env python3
"""Turn bench/results/*.json into a Markdown table. Medians across repeats."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

COLUMNS = [
    ("backend", "Backend"),
    ("precision", "Precision"),
    ("concurrency", "Concurrency"),
    ("ttft", "TTFT p50/p95 (ms)"),
    ("itl", "ITL p50 (ms)"),
    ("toks", "Output tok/s"),
    ("kv", "KV cache capacity (tokens)"),
    ("acc", "Accuracy"),
    ("cost", "$/1M tokens"),
]

KEY_FIELDS = ("backend", "precision", "concurrency", "workload")
METRIC_FIELDS = (
    "ttft_p50_ms",
    "ttft_p95_ms",
    "itl_p50_ms",
    "output_tokens_per_s",
    "requests_per_s",
    "kv_cache_capacity_tokens",
    "accuracy",
    "usd_per_1m_output_tokens",
)


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def flatten(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept either a flat row or a run_bench.py result document."""
    if "config" in payload and isinstance(payload.get("config"), dict):
        config = payload["config"]
        metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
        row: dict[str, Any] = {**config, **metrics}
        return row
    return dict(payload)


def median_by_config(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in KEY_FIELDS)
        groups[key].append(row)

    merged_rows: list[dict[str, Any]] = []
    for key, items in groups.items():
        merged: dict[str, Any] = {
            field: value for field, value in zip(KEY_FIELDS, key, strict=True)
        }
        for field in METRIC_FIELDS:
            values = [item[field] for item in items if item.get(field) is not None]
            merged[field] = float(median(values)) if values else None
        merged_rows.append(merged)
    return merged_rows


def row_from_result(payload: dict[str, Any]) -> dict[str, str]:
    metrics = flatten(payload)
    ttft = ""
    if metrics.get("ttft_p50_ms") is not None:
        ttft = f"{_fmt(metrics.get('ttft_p50_ms'))}/{_fmt(metrics.get('ttft_p95_ms'))}"
    return {
        "backend": _fmt(metrics.get("backend")),
        "precision": _fmt(metrics.get("precision")),
        "concurrency": _fmt(metrics.get("concurrency")),
        "ttft": ttft,
        "itl": _fmt(metrics.get("itl_p50_ms")),
        "toks": _fmt(metrics.get("output_tokens_per_s")),
        "kv": _fmt(metrics.get("kv_cache_capacity_tokens")),
        "acc": _fmt(metrics.get("accuracy")),
        "cost": _fmt(metrics.get("usd_per_1m_output_tokens")),
    }


def render(rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(title for _key, title in COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    lines = [header, sep]
    if not rows:
        lines.append("| no results yet |  |  |  |  |  |  |  |  |")
        return "\n".join(lines) + "\n"
    display = [row_from_result(item) for item in rows]
    for row in display:
        lines.append("| " + " | ".join(row[key] for key, _title in COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("bench/results"))
    args = parser.parse_args()
    payloads = [
        flatten(json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(args.results.glob("*.json"))
    ]
    print(render(median_by_config(payloads) if payloads else []), end="")


if __name__ == "__main__":
    main()
