"""Expand the Phase 8 matrix: backend x precision x concurrency x workload."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BACKENDS = (
    ("vllm", "fp16"),
    ("vllm", "awq"),
    ("vllm", "fp8"),
    ("triton", "fp16"),
    ("triton", "fp8"),
    ("triton", "awq"),  # optional in the spec
)
CONCURRENCIES = (1, 8, 32, 64)
WORKLOADS = {
    "chat": {"input_tokens": 512, "output_tokens": 256},
    "rag": {"input_tokens": 2048, "output_tokens": 128},
}


def model_name(backend: str, precision: str) -> str:
    if backend == "vllm":
        return f"llama-8b-vllm-{precision}"
    return f"llama-8b-trtllm-{precision}"


def configs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for backend, precision in BACKENDS:
        for concurrency in CONCURRENCIES:
            for workload, lengths in WORKLOADS.items():
                name = f"{backend}-{precision}-c{concurrency}-{workload}"
                rows.append(
                    {
                        "name": name,
                        "backend": backend,
                        "precision": precision,
                        "model": model_name(backend, precision),
                        "concurrency": concurrency,
                        "workload": workload,
                        "input_tokens": lengths["input_tokens"],
                        "output_tokens": lengths["output_tokens"],
                        "warmup_requests": 30,
                        "requests": 300,
                        "repeats": 3,
                        "max_model_len": 4096,
                        "client": "aiperf",
                    }
                )
    return rows


def write_all(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for row in configs():
        path = directory / f"{row['name']}.yaml"
        path.write_text(yaml.safe_dump(row, sort_keys=False), encoding="utf-8")
        written.append(path)
    return written
