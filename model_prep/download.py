"""Download a Hugging Face checkpoint and optionally upload it to GCS."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from model_prep.manifest import build, write


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gcs", default="")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.dry_run:
        subprocess.run(
            [
                "huggingface-cli",
                "download",
                args.repo,
                "--revision",
                args.revision,
                "--local-dir",
                str(args.out),
            ],
            check=True,
            env=os.environ.copy(),
        )
    row = build(
        artifact="fp16-hf",
        source_repo=args.repo,
        source_revision=args.revision,
        tool="huggingface-cli",
        tool_version="dry-run" if args.dry_run else "huggingface-cli",
        precision="fp16",
        flags={"out": str(args.out), "gcs": args.gcs},
    )
    write(args.out / "manifest.json", row)
    print(json.dumps(row, indent=2))
    if args.gcs and not args.dry_run:
        subprocess.run(
            ["gcloud", "storage", "rsync", "--recursive", str(args.out), args.gcs],
            check=True,
        )
