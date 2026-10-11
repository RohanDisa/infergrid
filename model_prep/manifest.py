"""Artifact manifest for weights and engines. Every GCS object gets one row."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

REQUIRED = (
    "artifact",
    "source_repo",
    "source_revision",
    "tool",
    "tool_version",
    "precision",
    "flags",
)


def build(
    *,
    artifact: str,
    source_repo: str,
    source_revision: str,
    tool: str,
    tool_version: str,
    precision: str,
    flags: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact": artifact,
        "source_repo": source_repo,
        "source_revision": source_revision,
        "tool": tool,
        "tool_version": tool_version,
        "precision": precision,
        "flags": flags,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if extra:
        row.update(extra)
    return row


def validate(row: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED if key not in row]
    if missing:
        raise ValueError(f"manifest missing keys: {missing}")


def write(path: Path, row: dict[str, Any]) -> None:
    validate(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")


def read(path: Path) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    validate(row)
    return row
