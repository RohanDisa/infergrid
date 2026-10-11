"""Static FP8 HF checkpoint for a fair vLLM comparison."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path

from model_prep.manifest import build, write


def plan(args: argparse.Namespace) -> dict[str, object]:
    return {
        "model_dir": str(args.model_dir),
        "out": str(args.out),
        "calib_dataset": args.calib_dataset,
        "calib_samples": args.calib_samples,
        "scheme": "FP8",
        "target": "vllm",
    }


def run_llm_compressor(args: argparse.Namespace) -> str:
    try:
        from llmcompressor import oneshot  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "llm-compressor is not installed. On the GPU job: "
            "pip install llmcompressor && re-run, or pass --dry-run."
        ) from exc
    oneshot(
        model=str(args.model_dir),
        dataset=args.calib_dataset,
        num_calibration_samples=args.calib_samples,
        output_dir=str(args.out),
    )
    try:
        return importlib.metadata.version("llmcompressor")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-repo", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--source-revision", default="unknown")
    parser.add_argument("--calib-dataset", default="HuggingFaceH4/ultrachat_200k")
    parser.add_argument("--calib-samples", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    flags = plan(args)
    tool_version = "dry-run"
    if not args.dry_run:
        tool_version = run_llm_compressor(args)
    row = build(
        artifact="fp8-hf",
        source_repo=args.source_repo,
        source_revision=args.source_revision,
        tool="llm-compressor",
        tool_version=tool_version,
        precision="fp8",
        flags=flags,
    )
    write(args.out / "manifest.json", row)
    print(json.dumps(row, indent=2))
