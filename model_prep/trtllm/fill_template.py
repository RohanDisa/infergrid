"""Fill ${KEY} placeholders in Triton config.pbtxt templates.

Mirrors tensorrtllm_backend's fill_template.py so engine-build Jobs stay
scripted. Keys come from a YAML/JSON file or --set KEY=VALUE flags.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

PLACEHOLDER = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_values(path: Path | None, sets: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is not None:
        raw = path.read_text(encoding="utf-8")
        loaded = yaml.safe_load(raw) if path.suffix in {".yaml", ".yml"} else json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError("values file must be a mapping")
        values.update({str(key): str(value) for key, value in loaded.items()})
    for item in sets:
        if "=" not in item:
            raise ValueError(f"expected KEY=VALUE, got {item}")
        key, value = item.split("=", 1)
        values[key] = value
    return values


def render(template: str, values: dict[str, str], *, strict: bool = True) -> str:
    missing: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            missing.add(key)
            return match.group(0)
        return values[key]

    rendered = PLACEHOLDER.sub(replace, template)
    if strict and missing:
        raise KeyError(f"unresolved placeholders: {sorted(missing)}")
    return rendered


def fill_tree(src: Path, dest: Path, values: dict[str, str]) -> list[Path]:
    written: list[Path] = []
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(src)
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".pbtxt" or "${" in text:
            text = render(text, values)
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--values", type=Path, default=None)
    parser.add_argument("--set", dest="sets", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    values = load_values(args.values, args.sets)
    written = fill_tree(args.src, args.dest, values)
    print(f"wrote {len(written)} files to {args.dest}")
