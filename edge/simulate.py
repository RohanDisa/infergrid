"""Phase 10 option B: simulate an 8 GB edge device on a 24 GB L4.

Sets --gpu-memory-utilization 0.3 (~7.2 GB) for a 1B-3B INT4 stand-in.
Label results as a simulation in the README. Not a substitute for Jetson.
"""

from __future__ import annotations

import argparse
import json


def vllm_args(
    *,
    model: str = "Qwen/Qwen2.5-1.5B-Instruct",
    utilization: float = 0.3,
    max_model_len: int = 4096,
) -> list[str]:
    return [
        "--model",
        model,
        "--quantization",
        "awq",
        "--gpu-memory-utilization",
        str(utilization),
        "--max-model-len",
        str(max_model_len),
        "--served-model-name",
        "edge-sim",
    ]


def tradeoffs() -> str:
    return (
        "Edge wins on privacy, offline use, and first-token latency to a nearby "
        "user. Cloud wins on tokens/s, context length, and operational toil. "
        "An 8B FP16 model does not fit an 8 GB Jetson; use 1B-3B INT4 there."
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    args = parser.parse_args(argv)
    print(json.dumps({"vllm_args": vllm_args(model=args.model), "tradeoffs": tradeoffs()}))
