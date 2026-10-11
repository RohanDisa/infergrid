#!/usr/bin/env python3
"""Run one bench config through AIPerf (or write a not_run document)."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from bench.aiperf import (
    aiperf_command,
    choose_client,
    cost_per_1m,
    empty_metrics,
    parse_aiperf_json,
)
from bench.sanity import itl_beats_floor

REQUIRED = {"name", "backend", "precision", "concurrency", "input_tokens", "output_tokens"}


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    missing = REQUIRED - set(config)
    if missing:
        raise SystemExit(f"config missing keys: {sorted(missing)}")
    return config


def run(
    config: dict[str, Any],
    *,
    endpoint: str,
    out_dir: Path,
    commit: str,
    gpu_usd_per_hour: float,
    execute: bool,
) -> dict[str, Any]:
    client = choose_client()
    metrics = empty_metrics()
    status = "not_run"
    notes = "AIPerf not executed."
    command = aiperf_command(config, endpoint)

    if execute and client == "aiperf":
        subprocess.run(command, check=True)
        raw = out_dir / f"{config['name']}.aiperf.json"
        if raw.exists():
            metrics.update(parse_aiperf_json(raw))
            status = "ok"
            notes = f"client={client}"
    elif execute and client == "missing":
        notes = "aiperf binary not on PATH; wrote placeholder."
    else:
        notes = f"dry-run command: {' '.join(command)}"

    metrics["usd_per_1m_output_tokens"] = cost_per_1m(
        metrics.get("output_tokens_per_s"), gpu_usd_per_hour
    )
    warnings: list[str] = []
    if itl_beats_floor(str(config["precision"]), metrics.get("itl_p50_ms")):
        warnings.append("ITL faster than L4 bandwidth floor; measurement bug likely.")

    result = {
        "config": config,
        "status": status,
        "metrics": metrics,
        "logged_at": datetime.now(UTC).isoformat(),
        "git_commit": commit,
        "client": client,
        "command": command,
        "notes": notes,
        "warnings": warnings,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{config['name']}.json"
    dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("bench/results"))
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080")
    parser.add_argument("--gpu-usd-per-hour", type=float, default=0.70)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    result = run(
        load_config(args.config),
        endpoint=args.endpoint,
        out_dir=args.out_dir,
        commit=args.commit,
        gpu_usd_per_hour=args.gpu_usd_per_hour,
        execute=args.execute,
    )
    print(json.dumps({"wrote": result["config"]["name"], "status": result["status"]}))


if __name__ == "__main__":
    main()
